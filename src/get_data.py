#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to retrieve data from either database or file

Author: Gregor Pfalz
github: GPawi
"""

import numpy as np
import pandas as pd
import os
import sqlalchemy
import getpass
import xlrd
import datetime
import ipysheet
import ipywidgets
#xlrd.xlsx.ensure_elementtree_imported(False, None)
#xlrd.xlsx.Element_has_iter = True
from IPython.display import display
from ipyfilechooser import FileChooser
from ipysheet import from_dataframe, to_dataframe
from psycopg2.extras import NumericRange
from sqlalchemy.exc import IntegrityError


class AgeFromDBMultiCores(object):
    def __init__(self, db = None, password = None):
        """
        parameters:
        @db: string with the name of PostgreSQL database 
        @password: string with password for specific database
        
        returns:
        @self.engine: SQLalchemy specific engine for PostgreSQL
        """
        if db is not None and password is not None:
            self.__db = db
            self.__password = password
        elif db is None and password is None:
            self.__db = input('What is the name of the database? ')
            self.__password = getpass.getpass(prompt='What is the password for that database? ')
        elif db is not None and password is None:
            self.__db = db
            self.__password = getpass.getpass(prompt='What is the password for that database? ')
        else:
            self.__db = input('What is the name of the database? ')
            self.__password = password
            
        self.engine = sqlalchemy.create_engine(f'postgresql://postgres:{self.__password}@localhost/{self.__db}', 
                                                 executemany_mode='batch')
        
    def __data_retrieval_fdmc(self):
        """
        Helper function to retrieve the data from the database
        
        returns:
        @self.__db_all_ages: dataframe with all age determination data
        @self.__db_all_expedition: dataframe with two columns CoreID and expedition year
        @self.__db_all_coreids_list: list with all CoreIDs loaded from the database
        @self.__core_lengths: dataframe with two columns CoreID and core length
        """
        engine = self.engine
        self.__con = engine.connect()
        self.__db_all_ages = pd.read_sql('agedetermination', self.__con)
        for index, row in self.__db_all_ages.iterrows():
            if type(row['age']) == NumericRange and row['age'].upper == row['age'].lower:
                self.__db_all_ages.at[index, 'age'] = row['age'].upper
            else:
                self.__db_all_ages.drop(index, inplace=True)
        self.__db_all_ages.reset_index(drop = True, inplace = True)
        self.__db_all_expedition_age = pd.read_sql('drilling', self.__con, columns = ['coreid', 'expeditionyear'])
        self.__db_all_coreids = pd.read_sql('drilling', self.__con, columns = ['coreid'])
        self.__db_all_coreids_list = self.__db_all_coreids['coreid'].values.tolist()
        self.__core_lengths = pd.read_sql('drilling', self.__con, columns = ['coreid', 'corelength'])
        self.__core_lengths['corelength'] = self.__core_lengths['corelength']*100
        self.__con.close()
        
    def __adding_surface_sample_fdmc(self):
        """
        Helper function to add artificial surface sample to age determination data based on the expedition year
        
        returns:
        @self.__db_all_ages: altered dataframe with all age determination data plus added surface sample
        """
        __db_all_expedition_age = self.__db_all_expedition_age
        __db_all_expedition_age['expeditionyearBP'] = 1950 - __db_all_expedition_age['expeditionyear']
        self.__db_all_ages_columns = self.__db_all_ages.columns
        self.__db_all_surface = pd.DataFrame(columns = self.__db_all_ages_columns)
        for i in range(0, len(__db_all_expedition_age)):
            self.__surface_df = pd.DataFrame(np.array([[__db_all_expedition_age.iloc[i,0] + str(' 0'),
                                                0,
                                                __db_all_expedition_age.iloc[i,0] + str('_Surface'),
                                                'NaN',
                                                'other',
                                                'derived surface age',
                                                'NaN',
                                                __db_all_expedition_age.iloc[i,2],
                                                self.__surface_uncertainty,
                                                'None',
                                                0,
                                                0]]), columns = self.__db_all_ages_columns)
            #self.__db_all_surface = self.__db_all_surface.append(self.__surface_df)
            self.__db_all_surface = pd.concat([self.__db_all_surface, self.__surface_df], axis = 0)
        self.__db_all_surface.reset_index(drop = True)
        self.__db_all_ages = pd.concat([self.__db_all_ages, self.__db_all_surface])
    
    def __check_for_None_fdmc(self):
        """
        Helper function to check, if there are more age determination data than the surface sample
        
        returns:
        @self.__db_all_ages: altered dataframe with cores that have age determination data
        """
        self.__db_all_ages[['coreid','compositedepth']] = self.__db_all_ages['measurementid'].str.split(' ', n = 1, expand = True)
        self.__db_all_ages = self.__db_all_ages.reset_index(drop = True)
        self.__db_all_ages = self.__db_all_ages[self.__db_all_ages.duplicated(['coreid'], keep = False) == True] 
        self.__db_all_ages['compositedepth'] = self.__db_all_ages['compositedepth'].astype(float)
        self.__db_all_ages = self.__db_all_ages.sort_values(by = ['coreid','compositedepth'], ignore_index = True)
        
    def get_dates(self, surface_uncertainty = 5):
        """
        Main function that calls helper functions and renames the variables
        
        parameters:
        @surface_uncertainty: age uncertainty that should be added to the generated surface sample; default value: 5
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        @self.all_coreid_list: list with all CoreIDs loaded from the database
        @self.all_core_lengths: dataframe with two columns CoreID and core length
        """
        self.__surface_uncertainty = surface_uncertainty
        self.__data_retrieval_fdmc()
        self.__adding_surface_sample_fdmc()
        self.__check_for_None_fdmc()
        self.all_ages = self.__db_all_ages
        self.all_coreid_list = self.__db_all_coreids_list
        self.all_core_lengths = self.__core_lengths
        
    def select_calibration_curve(self, default_curve = 'IntCal20', hemisphere = 'NH',  user_selection = True):
        """
        Function to add a calibration curve to the age determination data
        
        parameters:
        @default_curve: string with calibration curve that should be used for samples, such as 'IntCal20', 'Marine20', 'SHCal20', or 'none'; default value: 'IntCal20'
        @hemisphere: string with abbreviation of hemisphere from which the samples are from - 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere; default value: 'NH'
        @user_selection: boolean value, if user wants to change the calibration curve selection manually; default value: True
        
        returns:
        @self.__all_ages_cc: dataframe with all age determination data plus automatically added calibration curve
        @self.sheet: sheet widget with input changes by user
        """
        self.default_curve = default_curve
        self.user_selection = user_selection
        self.hemisphere = hemisphere
        # Check input values
        possible_curves = ['IntCal20', 'Marine20', 'SHCal20', 'none']
        check_curves = [ele for ele in possible_curves if (ele in self.default_curve)]
        if bool(check_curves) == False:
            raise Exception("Please provide one of the following curves as default curve: 'IntCal20', 'Marine20', 'SHCal20', or 'none'")
        if self.hemisphere != 'NH' and self.hemisphere != 'SH':
            raise Exception("Please provie one of the following abbreviations for hemisphere: 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere")
        # Copy exisiting age dataframe
        self.__all_ages_cc = self.all_ages.copy()
        # Initialize calibration curve column
        self.__all_ages_cc['calibration_curve'] = None
        # Add values based on material category and default curve
        for i,r in self.__all_ages_cc.iterrows():
            # First case: surface sample without calibration
            if self.__all_ages_cc.at[i, 'material_description'] == 'derived surface age':
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Second case: 14C sediment in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C sediment') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = self.default_curve
            
            # Third case: 14C terrestrial fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                if self.hemisphere == 'NH':
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'IntCal20'
                else:
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'SHCal20'
            
            # Fourth case: 14C marine fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'Marine20'
            
            # Fifth case: radiocarbon dating results outside the boundaries of calibration curve
            elif  (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil' or self.__all_ages_cc.at[i, 'material_category'] == '14C sediment' or self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 50000 or (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) < 75 or \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) < (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Sixth case: Everything else :) 
            else:
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
                
        # Allow user to change the calibration curve
        if self.user_selection == True:
            col_for_selection = ['measurementid',
                                 'labid',
                                 'material_category', 
                                 'material_description', 
                                 'age', 
                                 'age_error', 
                                 'calibration_curve']
            view_ages = self.__all_ages_cc[~self.__all_ages_cc.labid.str.contains('_Surface')].copy()
            view_ages = view_ages[col_for_selection]
            view_ages.reset_index(inplace = True, drop = True)
            self.sheet = from_dataframe(view_ages)
            col_headers = ['MeasurementID',
                           'LabID',
                           'Category',
                           'Material',
                           'Uncalibrated Age (yr BP)',
                           'Uncalibrated Age Error (+/- yr)',
                           'Calibration Curve'
                          ]
            self.sheet.column_headers = col_headers
            choices_curve = ['IntCal20',
                            'Marine20',
                            'SHCal20',
                            'none']
            for header in range(len(col_headers)):
                if header == col_headers.index('Calibration Curve'):
                    self.sheet.cells[header].style['backgroundColor'] = '#eefbdd'
                    self.sheet.cells[header].choice = choices_curve
                    self.sheet.cells[header].type = 'dropdown'
                    self.sheet.cells[header].send_state()
                else:
                    self.sheet.cells[header].read_only = True
                    self.sheet.cells[header].squeeze_column = True
                    self.sheet.cells[header].textAlign = 'right'
                    self.sheet.cells[header].send_state()
            display(self.sheet)
    
    def add_calibration_curve(self):
        """
        Function to update information on calibration curve
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        """
        if self.user_selection == True:
            df_sheet_user_input = ipysheet.to_dataframe(self.sheet)
            df_sheet_user_input = df_sheet_user_input[['MeasurementID', 'LabID', 'Calibration Curve']]
            df_sheet_user_input.columns = ['measurementid', 'labid', 'calibration_curve']
            initial_columns = self.__all_ages_cc.columns
            self.__all_ages_cc.set_index(['measurementid','labid'], inplace=True)
            self.__all_ages_cc.update(df_sheet_user_input.set_index(['measurementid','labid']))
            self.__all_ages_cc.reset_index(inplace = True)
            self.__all_ages_cc = self.__all_ages_cc[initial_columns]
            self.all_ages = self.__all_ages_cc
        else:
            self.all_ages = self.__all_ages_cc
    
class AgeFromDBOneCore(object):
    def __init__(self, db = None, password = None, coreid = None):
        """
        parameters:
        @db: string with the name of PostgreSQL database 
        @password: string with password for specific database
        @coreid: string with unique CoreID to be retrieved from database
        
        returns:
        @self.engine: SQLalchemy specific engine for PostgreSQL
        """
        if db is not None and password is not None and coreid is not None:
            self.__db = db
            self.__password = password
            self.coreid = coreid
        elif db is None and password is None and coreid is None:
            self.__db = input('What is the name of the database? ')
            self.__password = getpass.getpass(prompt='What is the password for that database? ')
            self.coreid = input('What is the CoreID of the core? ')
        elif db is not None and password is None and coreid is None:
            self.__db = db
            self.__password = getpass.getpass(prompt='What is the password for that database? ')
            self.coreid = input('What is the CoreID of the core? ')
        elif db is not None and password is not None and coreid is None:
            self.__db = db
            self.__password = password            
            self.coreid = input('What is the CoreID of the core? ')
        elif db is not None and password is None and coreid is not None:
            self.__db = db
            self.__password = getpass.getpass(prompt='What is the password for that database? ')
            self.coreid = coreid        
        else:
            self.__db = input('What is the name of the database? ')
            self.__password = password
            self.coreid = coreid
            
        self.engine = sqlalchemy.create_engine(f'postgresql://postgres:{self.__password}@localhost/{self.__db}', 
                                                 executemany_mode='batch')
    
    def __data_retrieval_fdoc(self):
        """
        Helper function to retrieve the data from the database
        
        returns:
        @self.__db_all_ages: dataframe with all age determination data
        @self.__db_one_expedition: dataframe with two columns CoreID and expedition year
        @self.__db_all_coreids_list: list with all CoreIDs loaded from the database
        @self.__core_lengths: dataframe with two columns CoreID and core length
        """
        engine = self.engine
        coreid = self.coreid
        self.__con = engine.connect()
        self.__db_all_ages = pd.read_sql('agedetermination', self.__con)
        self.__db_all_ages[['coreid','compositedepth']] = self.__db_all_ages['measurementid'].str.split(' ', n = 1, expand = True)
        self.__db_all_ages = self.__db_all_ages.reset_index(drop = True)
        self.__db_all_ages = self.__db_all_ages[self.__db_all_ages['coreid'] == coreid]
        self.__db_all_ages = self.__db_all_ages[self.__db_all_ages.duplicated(['coreid'], keep = False) == True] 
        for index, row in self.__db_all_ages.iterrows():
            if type(row['age']) == NumericRange and row['age'].upper == row['age'].lower:
                self.__db_all_ages.at[index, 'age'] = row['age'].upper
            else:
                self.__db_all_ages.drop(index, inplace=True)
        self.__db_all_expedition_age = pd.read_sql('drilling', self.__con, columns = ['coreid', 'expeditionyear'])
        self.__db_one_expedition_age = self.__db_all_expedition_age[self.__db_all_expedition_age['coreid'] == coreid]
        self.__core_lengths = pd.read_sql('drilling', self.__con, columns = ['coreid', 'corelength'])
        self.__core_lengths = self.__core_lengths[self.__core_lengths['coreid'] == coreid]
        self.__core_lengths['corelength'] = self.__core_lengths['corelength']*100
        self.__con.close()
        
    def __adding_surface_sample_fdoc(self):
        """
        Helper function to add artificial surface sample to age determination data based on the expedition year
        
        returns:
        @self.__db_all_ages: altered dataframe with all age determination data plus added surface sample
        """
        __db_one_expedition_age = self.__db_one_expedition_age.copy()
        coreid = self.coreid
        __db_one_expedition_age['expeditionyearBP'] = 1950 - __db_one_expedition_age['expeditionyear']
        self.__db_all_ages_columns = self.__db_all_ages.columns
        self.__db_all_surface = pd.DataFrame(columns = self.__db_all_ages_columns)
        self.__surface_df = pd.DataFrame(np.array([[coreid + str(' 0'),
                                                0,
                                                coreid + str('_Surface'),
                                                'NaN',
                                                'other',
                                                'derived surface age',
                                                'NaN',
                                                __db_one_expedition_age.iloc[0,2],
                                                self.__surface_uncertainty,
                                                'None',
                                                0,
                                                0,
                                                coreid,
                                                float(0)]]), columns = self.__db_all_ages_columns)
        #self.__db_all_surface = self.__db_all_surface.append(self.__surface_df)
        self.__db_all_surface = pd.concat([self.__db_all_surface, self.__surface_df], axis = 0)
        self.__db_all_surface.reset_index(drop = True)
        self.__db_all_ages = pd.concat([self.__db_all_ages, self.__db_all_surface])
        self.__db_all_ages['compositedepth'] = self.__db_all_ages['compositedepth'].astype(float)
        self.__db_all_ages = self.__db_all_ages.sort_values(by = ['compositedepth'], ignore_index = True)
        self.__db_all_ages.reset_index(drop = True, inplace = True)
        
 
    def get_dates(self, surface_uncertainty = 5):
        """
        Main function that calls helper functions and renames the variables
        
        parameters:
        @surface_uncertainty: age uncertainty that should be added to the generated surface sample; default value: 5
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        @self.all_coreid_list: list with all CoreIDs loaded from the database
        @self.all_core_lengths: dataframe with two columns CoreID and core length
        """
        self.__surface_uncertainty = surface_uncertainty
        self.__data_retrieval_fdoc()
        self.__adding_surface_sample_fdoc()
        self.all_ages = self.__db_all_ages
        self.all_coreid_list = list([self.coreid]) 
        self.all_core_lengths = self.__core_lengths
        
    def select_calibration_curve(self, default_curve = 'IntCal20', hemisphere = 'NH',  user_selection = True):
        """
        Function to add a calibration curve to the age determination data
        
        parameters:
        @default_curve: string with calibration curve that should be used for samples, such as 'IntCal20', 'Marine20', 'SHCal20', or 'none'; default value: 'IntCal20'
        @hemisphere: string with abbreviation of hemisphere from which the samples are from - 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere; default value: 'NH'
        @user_selection: boolean value, if user wants to change the calibration curve selection manually; default value: True
        
        returns:
        @self.__all_ages_cc: dataframe with all age determination data plus automatically added calibration curve
        @self.sheet: sheet widget with input changes by user
        """
        self.default_curve = default_curve
        self.user_selection = user_selection
        self.hemisphere = hemisphere
        # Check input values
        possible_curves = ['IntCal20', 'Marine20', 'SHCal20', 'none']
        check_curves = [ele for ele in possible_curves if (ele in self.default_curve)]
        if bool(check_curves) == False:
            raise Exception("Please provide one of the following curves as default curve: 'IntCal20', 'Marine20', 'SHCal20', or 'none'")
        if self.hemisphere != 'NH' and self.hemisphere != 'SH':
            raise Exception("Please provie one of the following abbreviations for hemisphere: 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere")
        # Copy exisiting age dataframe
        self.__all_ages_cc = self.all_ages.copy()
        # Initialize calibration curve column
        self.__all_ages_cc['calibration_curve'] = None
        # Add values based on material category and default curve
        for i,r in self.__all_ages_cc.iterrows():
            # First case: surface sample without calibration
            if self.__all_ages_cc.at[i, 'material_description'] == 'derived surface age':
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Second case: 14C sediment in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C sediment') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = self.default_curve
            
            # Third case: 14C terrestrial fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                if self.hemisphere == 'NH':
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'IntCal20'
                else:
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'SHCal20'
            
            # Fourth case: 14C marine fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'Marine20'
            
            # Fifth case: radiocarbon dating results outside the boundaries of calibration curve
            elif  (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil' or self.__all_ages_cc.at[i, 'material_category'] == '14C sediment' or self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 50000 or (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) < 75 or \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) < (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Sixth case: Everything else :) 
            else:
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
                
        # Allow user to change the calibration curve
        if self.user_selection == True:
            col_for_selection = ['measurementid',
                                 'labid',
                                 'material_category', 
                                 'material_description', 
                                 'age', 
                                 'age_error', 
                                 'calibration_curve']
            view_ages = self.__all_ages_cc[~self.__all_ages_cc.labid.str.contains('_Surface')].copy()
            view_ages = view_ages[col_for_selection]
            view_ages.reset_index(inplace = True, drop = True)
            self.sheet = from_dataframe(view_ages)
            col_headers = ['MeasurementID',
                           'LabID',
                           'Category',
                           'Material',
                           'Uncalibrated Age (yr BP)',
                           'Uncalibrated Age Error (+/- yr)',
                           'Calibration Curve'
                          ]
            self.sheet.column_headers = col_headers
            choices_curve = ['IntCal20',
                            'Marine20',
                            'SHCal20',
                            'none']
            for header in range(len(col_headers)):
                if header == col_headers.index('Calibration Curve'):
                    self.sheet.cells[header].style['backgroundColor'] = '#eefbdd'
                    self.sheet.cells[header].choice = choices_curve
                    self.sheet.cells[header].type = 'dropdown'
                    self.sheet.cells[header].send_state()
                else:
                    self.sheet.cells[header].read_only = True
                    self.sheet.cells[header].squeeze_column = True
                    self.sheet.cells[header].textAlign = 'right'
                    self.sheet.cells[header].send_state()
            display(self.sheet)
    
    def add_calibration_curve(self):
        """
        Function to update information on calibration curve
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        """
        if self.user_selection == True:
            df_sheet_user_input = ipysheet.to_dataframe(self.sheet)
            df_sheet_user_input = df_sheet_user_input[['MeasurementID', 'LabID', 'Calibration Curve']]
            df_sheet_user_input.columns = ['measurementid', 'labid', 'calibration_curve']
            initial_columns = self.__all_ages_cc.columns
            self.__all_ages_cc.set_index(['measurementid','labid'], inplace=True)
            self.__all_ages_cc.update(df_sheet_user_input.set_index(['measurementid','labid']))
            self.__all_ages_cc.reset_index(inplace = True)
            self.__all_ages_cc = self.__all_ages_cc[initial_columns]
            self.all_ages = self.__all_ages_cc
        else:
            self.all_ages = self.__all_ages_cc
    
class AgeFromFileOneCore(object):
    def __init__(self, filename = None):
        """
        parameters:
        @filename: string with the address to file on system
        """
        self.__filename = filename
        if self.__filename == None:
            __data_dir = os.path.abspath('./input_files')
            self.fc = FileChooser(__data_dir)
            self.fc.use_dir_icons = True
            self.fc.filter_pattern = ['*.xlsx']
            display(self.fc)
                   
    def __select_data_one_core(self):
        """
        Helper function to store age determination data from file in dictionary
        
        returns:
        @self.__input_dictionary: dictionary with age determination data indexed by 'Age' 
        (as per naming convention of example spreadsheet / input file)
        """
        xl = pd.ExcelFile(self.__filename)
        self.__input_dictionary = {}
        if 'Age' in xl.sheet_names:
            for sheet in xl.sheet_names:
                self.__input_dictionary[f'{sheet}']= pd.read_excel(xl,sheet_name=sheet)
        else:
            raise Exception('There is no sheet named "Age" in selected file')
                
    def __age_input_one_core(self):
        """
        Helper function to transform input data into the same format as database approach
        
        returns:
        @self.coreid: string with unique CoreID derived from input file column 'CoreID'
        @self.__input_age_one_core: dataframe with all age determination data for one sediment core
        """
        __input_dictionary = self.__input_dictionary
        try:
            self.__input_age_one_core = __input_dictionary['Age']
            self.__input_age_one_core.rename(columns={'CoreID':'coreid',
                                             'Depth mid-point (cm)':'compositedepth',
                                            'Thickness (cm)':'thickness',
                                            'Lab-ID':'labid',
                                            'Lab-Location':'lab_location',
                                            'Category':'material_category',
                                            'Material':'material_description', 
                                            'Weight (µg C)':'material_weight', 
                                            'Uncalibrated Age (yr BP)':'age', 
                                            'Uncalibrated Age Error (+/- yr)':'age_error', 
                                            'Pretreatment':'pretreatment_dating', 
                                            'Reservoir Age (yr)':'reservoir_age', 
                                            'Reservoir Error (+/- yr)':'reservoir_error'}, inplace=True)
            self.coreid = ''.join(map(str, self.__input_age_one_core['coreid'].unique()))
            ### For detection limit
            self.__input_age_one_core.reset_index(drop = True, inplace = True)
            for i in range(0, len(self.__input_age_one_core)):
                if type(self.__input_age_one_core.iloc[i,8]) is str and '>' in self.__input_age_one_core.iloc[i,8]:
                    __age_array= self.__input_age_one_core.iloc[i,8].split('>')
                    __age_indi = NumericRange(int(__age_array[1]), None, bounds = '[)', empty = False)
                    self.__input_age_one_core.iloc[i,8] = __age_indi
                elif type(self.__input_age_one_core.iloc[i,8]) is str and '<' in self.__input_age_one_core.iloc[i,8]:
                    __age_array= self.__input_age_one_core.iloc[i,8].split('<')
                    __age_indi = NumericRange(None, int(__age_array[1]), bounds = '()', empty = False)
                    self.__input_age_one_core.iloc[i,8] = __age_indi
                else:
                    __age_indi = NumericRange(int(self.__input_age_one_core.iloc[i,8]), int(self.__input_age_one_core.iloc[i,8]), bounds = '[]', empty = False)
                    self.__input_age_one_core.iloc[i,8] = __age_indi
            ###
            for index, row in self.__input_age_one_core.iterrows():
                if type(row['age']) == NumericRange and row['age'].upper == row['age'].lower:
                    self.__input_age_one_core.at[index, 'age'] = row['age'].upper
                else:
                    self.__input_age_one_core.drop(index, inplace=True)
            ### Adding measurementid
            self.__input_age_one_core['measurementid'] = self.__input_age_one_core['coreid'] + ' ' + self.__input_age_one_core['compositedepth'].astype(str)
        except KeyError:
            raise Exception(f'No age data found!')
            
    def __metadata_input_one_cores(self):
        """
        Helper function to transform metadata into one dataframe for core length and one variable for expediton year to be comparable to database implementation
        
        returns:
        @self.__core_lengths: dataframe with two columns CoreID and core length
        @self.__expedition_year: integer value with expedition year
        """
        __input_dictionary = self.__input_dictionary
        try:
            self.__input_metadata_one_core = __input_dictionary['Metadata']
            self.__input_metadata_one_core.rename(columns={'CoreID':'coreid',
                                                           'Expedition Year': 'expeditionyear',
                                                           'Core Length (cm)' : 'corelength'}, inplace = True)
            self.__core_lengths = self.__input_metadata_one_core[['coreid', 'corelength']].copy()
            self.__core_lengths['corelength'] = self.__core_lengths['corelength'].astype(float)
            self.__expedition_year = self.__input_metadata_one_core['expeditionyear'][0].astype(int).copy()
        except KeyError:
            self.__expedition_year = input('In which year was the sediment core retrieved? (e.g., 2020) ')
            self.__core_lengths = input('How long was the entire core in centimeter (cm)? ')
            self.all_core_lengths = pd.DataFrame([[self.coreid,self.__core_lengths]], columns = ['coreid', 'corelength'])
            self.all_core_lengths['corelength'] = self.all_core_lengths['corelength'].astype(float) 
            
    def __adding_surface_sample_ffoc(self):
        """
        Helper function to add artificial surface sample to age determination data based on the expedition year
        
        returns:
        @self.__file_all_ages_one_core: altered dataframe with all age determination data plus added surface sample
        """
        coreid = self.coreid
        self.__expedition_year = 1950 - int(self.__expedition_year)
        self.__input_age_one_core_columns = self.__input_age_one_core.columns
        self.__surface_df = pd.DataFrame(np.array([[coreid,
                                                    float(0),
                                                    0,
                                                    coreid + str('_Surface'),
                                                    'NaN',
                                                    'other',
                                                    'derived surface age',
                                                    'NaN',
                                                    self.__expedition_year,
                                                    self.__surface_uncertainty,
                                                    'None',
                                                    0,
                                                    0,
                                                   f'{coreid} 0']]), columns = self.__input_age_one_core_columns)
        self.__file_all_ages_one_core = pd.concat([self.__input_age_one_core, self.__surface_df])
        self.__file_all_ages_one_core['compositedepth'] = self.__file_all_ages_one_core['compositedepth'].astype(float)
        self.__file_all_ages_one_core = self.__file_all_ages_one_core.sort_values(by = ['compositedepth'], ignore_index = True)
        self.__file_all_ages_one_core.reset_index(drop = True, inplace = True)
    

    def get_dates(self, surface_uncertainty = 5):
        """
        Main function that calls helper functions and renames the variables
        
        parameters:
        @surface_uncertainty: age uncertainty that should be added to the generated surface sample; default value: 5
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        @self.all_coreid_list: list with all CoreIDs
        @self.all_core_lengths: dataframe with two columns CoreID and core length
        @self.engine: string saying that SQLalchemy specific engine for PostgreSQL is not available
        """
        self.__surface_uncertainty = surface_uncertainty
        if self.__filename == None:
            self.__filename = self.fc.value
        self.__select_data_one_core()
        self.__age_input_one_core()
        self.__metadata_input_one_cores()
        self.__adding_surface_sample_ffoc()
        self.all_ages = self.__file_all_ages_one_core
        self.all_coreid_list = list([self.coreid])
        self.all_core_lengths = self.__core_lengths
        self.engine = 'No Database'
        self.all_ages = self.all_ages.astype(dtype = {'labid' : str,
                                                      'age' : int,
                                                      'age_error' : int,
                                                      'reservoir_age' : int,
                                                      'reservoir_error': int})
        
        
    def select_calibration_curve(self, default_curve = 'IntCal20', hemisphere = 'NH',  user_selection = True):
        """
        Function to add a calibration curve to the age determination data
        
        parameters:
        @default_curve: string with calibration curve that should be used for samples, such as 'IntCal20', 'Marine20', 'SHCal20', or 'none'; default value: 'IntCal20'
        @hemisphere: string with abbreviation of hemisphere from which the samples are from - 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere; default value: 'NH'
        @user_selection: boolean value, if user wants to change the calibration curve selection manually; default value: True
        
        returns:
        @self.__all_ages_cc: dataframe with all age determination data plus automatically added calibration curve
        @self.sheet: sheet widget with input changes by user
        """
        self.default_curve = default_curve
        self.user_selection = user_selection
        self.hemisphere = hemisphere
        # Check input values
        possible_curves = ['IntCal20', 'Marine20', 'SHCal20', 'none']
        check_curves = [ele for ele in possible_curves if (ele in self.default_curve)]
        if bool(check_curves) == False:
            raise Exception("Please provide one of the following curves as default curve: 'IntCal20', 'Marine20', 'SHCal20', or 'none'")
        if self.hemisphere != 'NH' and self.hemisphere != 'SH':
            raise Exception("Please provie one of the following abbreviations for hemisphere: 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere")
        # Copy exisiting age dataframe
        self.__all_ages_cc = self.all_ages.copy()
        # Initialize calibration curve column
        self.__all_ages_cc['calibration_curve'] = None
        # Add values based on material category and default curve
        for i,r in self.__all_ages_cc.iterrows():
            # First case: surface sample without calibration
            if self.__all_ages_cc.at[i, 'material_description'] == 'derived surface age':
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Second case: 14C sediment in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C sediment') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = self.default_curve
            
            # Third case: 14C terrestrial fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                if self.hemisphere == 'NH':
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'IntCal20'
                else:
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'SHCal20'
            
            # Fourth case: 14C marine fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'Marine20'
            
            # Fifth case: radiocarbon dating results outside the boundaries of calibration curve
            elif  (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil' or self.__all_ages_cc.at[i, 'material_category'] == '14C sediment' or self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 50000 or (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) < 75 or \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) < (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Sixth case: Everything else :) 
            else:
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
                
        # Allow user to change the calibration curve
        if self.user_selection == True:
            col_for_selection = ['measurementid',
                                 'labid',
                                 'material_category', 
                                 'material_description', 
                                 'age', 
                                 'age_error', 
                                 'calibration_curve']
            view_ages = self.__all_ages_cc[~self.__all_ages_cc.labid.str.contains('_Surface')].copy()
            view_ages = view_ages[col_for_selection]
            view_ages.reset_index(inplace = True, drop = True)
            self.sheet = from_dataframe(view_ages)
            col_headers = ['MeasurementID',
                           'LabID',
                           'Category',
                           'Material',
                           'Uncalibrated Age (yr BP)',
                           'Uncalibrated Age Error (+/- yr)',
                           'Calibration Curve'
                          ]
            self.sheet.column_headers = col_headers
            choices_curve = ['IntCal20',
                            'Marine20',
                            'SHCal20',
                            'none']
            for header in range(len(col_headers)):
                if header == col_headers.index('Calibration Curve'):
                    self.sheet.cells[header].style['backgroundColor'] = '#eefbdd'
                    self.sheet.cells[header].choice = choices_curve
                    self.sheet.cells[header].type = 'dropdown'
                    self.sheet.cells[header].send_state()
                else:
                    self.sheet.cells[header].read_only = True
                    self.sheet.cells[header].squeeze_column = True
                    self.sheet.cells[header].textAlign = 'right'
                    self.sheet.cells[header].send_state()
            display(self.sheet)
    
    def add_calibration_curve(self):
        """
        Function to update information on calibration curve
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        """
        if self.user_selection == True:
            df_sheet_user_input = ipysheet.to_dataframe(self.sheet)
            df_sheet_user_input = df_sheet_user_input[['MeasurementID', 'LabID', 'Calibration Curve']]
            df_sheet_user_input.columns = ['measurementid', 'labid', 'calibration_curve']
            initial_columns = self.__all_ages_cc.columns
            self.__all_ages_cc.set_index(['measurementid','labid'], inplace=True)
            self.__all_ages_cc.update(df_sheet_user_input.set_index(['measurementid','labid']))
            self.__all_ages_cc.reset_index(inplace = True)
            self.__all_ages_cc = self.__all_ages_cc[initial_columns]
            self.all_ages = self.__all_ages_cc
        else:
            self.all_ages = self.__all_ages_cc
                         
class AgeFromFileMultiCores(object):
    def __init__(self, filename = None):
        """
        parameters:
        @filename: string with the address to file on system
        """
        self.__filename = filename
        if self.__filename == None:
            __data_dir = os.path.abspath('./input_files')
            self.fc = FileChooser(__data_dir)
            self.fc.use_dir_icons = True
            self.fc.filter_pattern = ['*.xlsx']
            display(self.fc)
        
    def __select_data_multi_cores(self):
        """
        Helper function to store age determination data from file in dictionary
        
        returns:
        @self.__input_dictionary: dictionary with age determination data indexed by 'Age'
        and metadata ('CoreID' and 'Expedition Year') index by 'Metadata'
        (as per naming convention of example spreadsheet / input file)
        """
        xl = pd.ExcelFile(self.__filename)
        self.__input_dictionary = {}
        if 'Age' in xl.sheet_names and 'Metadata' in xl.sheet_names:
            for sheet in xl.sheet_names:
                self.__input_dictionary[f'{sheet}']= pd.read_excel(xl,sheet_name=sheet)
        else:
            raise Exception('The naming convention within selected file is not correct. Please rename the tabs to "Age" and "Metadata".')
    
    def __age_input_multi_cores(self):
        """
        Helper function to transform input data into the same format as database approach
        
        returns:
        @self.all_coreid_list: list with all CoreID 
        @self.__input_age_multi_core: dataframe with all age determination data for one sediment core
        """
        __input_dictionary = self.__input_dictionary
        try:
            self.__input_age_multi_cores = __input_dictionary['Age']
            self.__input_age_multi_cores.rename(columns={'CoreID':'coreid',
                                             'Depth mid-point (cm)':'compositedepth',
                                            'Thickness (cm)':'thickness',
                                            'Lab-ID':'labid',
                                            'Lab-Location':'lab_location',
                                            'Category':'material_category',
                                            'Material':'material_description', 
                                            'Weight (µg C)':'material_weight', 
                                            'Uncalibrated Age (yr BP)':'age', 
                                            'Uncalibrated Age Error (+/- yr)':'age_error', 
                                            'Pretreatment':'pretreatment_dating', 
                                            'Reservoir Age (yr)':'reservoir_age', 
                                            'Reservoir Error (+/- yr)':'reservoir_error'}, inplace=True)
            self.all_coreid_list = self.__input_age_multi_cores['coreid'].unique().tolist()
            #### For detection limit
            self.__input_age_multi_cores.reset_index(drop = True, inplace = True)
            for i in range(0, len(self.__input_age_multi_cores)):
                if type(self.__input_age_multi_cores.iloc[i,8]) is str and '>' in self.__input_age_multi_cores.iloc[i,8]:
                    __age_array= self.__input_age_multi_cores.iloc[i,8].split('>')
                    __age_indi = NumericRange(int(__age_array[1]), None, bounds = '[)', empty = False)
                    self.__input_age_multi_cores.iloc[i,8] = __age_indi
                elif type(self.__input_age_multi_cores.iloc[i,8]) is str and '<' in self.__input_age_multi_cores.iloc[i,8]:
                    __age_array= self.__input_age_multi_cores.iloc[i,8].split('<')
                    __age_indi = NumericRange(None, int(__age_array[1]), bounds = '()', empty = False)
                    self.__input_age_multi_cores.iloc[i,8] = __age_indi
                else:
                    __age_indi = NumericRange(int(self.__input_age_multi_cores.iloc[i,8]), int(self.__input_age_multi_cores.iloc[i,8]), bounds = '[]', empty = False)
                    self.__input_age_multi_cores.iloc[i,8] = __age_indi
            ###
            for index, row in self.__input_age_multi_cores.iterrows():
                if type(row['age']) == NumericRange and row['age'].upper == row['age'].lower:
                    self.__input_age_multi_cores.at[index, 'age'] = row['age'].upper
                else:
                    self.__input_age_multi_cores.drop(index, inplace=True)
            #### Adding measurementid
            self.__input_age_multi_cores['measurementid'] = self.__input_age_multi_cores['coreid'] + ' ' + self.__input_age_multi_cores['compositedepth'].astype(str)
        except KeyError:
            raise Exception(f'No age data found!')
            
    def __metadata_input_multi_cores(self):
        """
        Helper function to transform metadata into two dataframe for core length and expediton year to be comparable to database implementation
        
        returns:
        @self.__core_lengths: dataframe with two columns CoreID and core length
        @self.__file_all_expedition_year: dataframe with two columns CoreID and expedition year
        """
        __input_dictionary = self.__input_dictionary
        try:
            self.__input_metadata_multi_cores = __input_dictionary['Metadata']
            self.__input_metadata_multi_cores.rename(columns={'CoreID':'coreid',
                                                              'Expedition Year': 'expeditionyear',
                                                              'Core Length (cm)' : 'corelength'}, inplace = True)
            self.__core_lengths = self.__input_metadata_multi_cores[['coreid', 'corelength']].copy()
            self.__core_lengths['corelength'] = self.__core_lengths['corelength'].astype(float)
            self.__file_all_expedition_age = self.__input_metadata_multi_cores[['coreid', 'expeditionyear']].copy()
            self.__file_all_expedition_age['expeditionyear'] = self.__file_all_expedition_age['expeditionyear'].astype(int)
        except KeyError:
            raise Exception(f'No metadata found!')   
   
    def __adding_surface_sample_ffmc(self):
        """
        Helper function to add artificial surface sample to age determination data based on the expedition year
        
        returns:
        @self.__file_all_ages_multi_core: altered dataframe with all age determination data plus added surface sample
        """
        __file_all_expedition_age = self.__file_all_expedition_age
        __file_all_expedition_age['expeditionyearBP'] = 1950 - __file_all_expedition_age['expeditionyear']
        self.__input_age_multi_cores_columns = self.__input_age_multi_cores.columns  
        self.__file_all_surface = pd.DataFrame(columns = self.__input_age_multi_cores_columns)
        for i in range(len(__file_all_expedition_age)):
            self.__surface_df = pd.DataFrame(np.array([[__file_all_expedition_age.iloc[i,0], #coreid
                                                        float(0), #compositedepth
                                                        0, #thickness
                                                        __file_all_expedition_age.iloc[i,0] + str('_Surface'), #labid
                                                        'NaN', #lab_location
                                                        'other', #material_category
                                                        'derived surface age', #material_description
                                                        'NaN', #material_weight
                                                        __file_all_expedition_age.iloc[i,2],#age
                                                        self.__surface_uncertainty, #age_error
                                                        'None', #pretreatment_dating
                                                        0, #reservoir_age
                                                        0, #reservoir_error
                                                        __file_all_expedition_age.iloc[i,0] + str(' 0')]]), #measurementid
                                             columns = self.__input_age_multi_cores_columns)
            #self.__file_all_surface = self.__file_all_surface.append(self.__surface_df)
            self.__file_all_surface = pd.concat([self.__file_all_surface, self.__surface_df], axis = 0)
        self.__file_all_surface.reset_index(drop = True)
        self.__file_all_ages_multi_cores = pd.concat([self.__input_age_multi_cores, self.__file_all_surface])
        self.__file_all_ages_multi_cores['compositedepth'] = self.__file_all_ages_multi_cores['compositedepth'].astype(float)
        self.__file_all_ages_multi_cores = self.__file_all_ages_multi_cores.sort_values(by = ['coreid','compositedepth'], ignore_index = True)
        
    
    
    def get_dates(self, surface_uncertainty = 5):
        """
        Main function that calls helper functions and renames the variables
        
        parameters:
        @surface_uncertainty: age uncertainty that should be added to the generated surface sample; default value: 5
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        @self.all_core_lengths: dataframe with two columns CoreID and core length
        @self.engine: string saying that SQLalchemy specific engine for PostgreSQL is not available
        """
        self.__surface_uncertainty = surface_uncertainty
        if self.__filename == None:
            self.__filename = self.fc.value
        self.__select_data_multi_cores()
        self.__age_input_multi_cores()
        self.__metadata_input_multi_cores()
        self.__adding_surface_sample_ffmc()
        self.all_ages = self.__file_all_ages_multi_cores
        self.all_ages = self.all_ages.astype(dtype = {'age' : int,
                                                      'age_error' : int,
                                                      'reservoir_age' : int,
                                                      'reservoir_error': int})
        
        self.all_core_lengths = self.__core_lengths
        self.engine = 'No Database'   
        
    def select_calibration_curve(self, default_curve = 'IntCal20', hemisphere = 'NH',  user_selection = True):
        """
        Function to add a calibration curve to the age determination data
        
        parameters:
        @default_curve: string with calibration curve that should be used for samples, such as 'IntCal20', 'Marine20', 'SHCal20', or 'none'; default value: 'IntCal20'
        @hemisphere: string with abbreviation of hemisphere from which the samples are from - 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere; default value: 'NH'
        @user_selection: boolean value, if user wants to change the calibration curve selection manually; default value: True
        
        returns:
        @self.__all_ages_cc: dataframe with all age determination data plus automatically added calibration curve
        @self.sheet: sheet widget with input changes by user
        """
        self.default_curve = default_curve
        self.user_selection = user_selection
        self.hemisphere = hemisphere
        # Check input values
        possible_curves = ['IntCal20', 'Marine20', 'SHCal20', 'none']
        check_curves = [ele for ele in possible_curves if (ele in self.default_curve)]
        if bool(check_curves) == False:
            raise Exception("Please provide one of the following curves as default curve: 'IntCal20', 'Marine20', 'SHCal20', or 'none'")
        if self.hemisphere != 'NH' and self.hemisphere != 'SH':
            raise Exception("Please provie one of the following abbreviations for hemisphere: 'NH' for Northern Hemisphere or 'SH' for Southern Hemisphere")
        # Copy exisiting age dataframe
        self.__all_ages_cc = self.all_ages.copy()
        # Initialize calibration curve column
        self.__all_ages_cc['calibration_curve'] = None
        # Add values based on material category and default curve
        for i,r in self.__all_ages_cc.iterrows():
            # First case: surface sample without calibration
            if self.__all_ages_cc.at[i, 'material_description'] == 'derived surface age':
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Second case: 14C sediment in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C sediment') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = self.default_curve
            
            # Third case: 14C terrestrial fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                if self.hemisphere == 'NH':
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'IntCal20'
                else:
                    self.__all_ages_cc.at[i, 'calibration_curve'] = 'SHCal20'
            
            # Fourth case: 14C marine fossil in boundaries of calibration curve
            elif (self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) <= 50000 and (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 75 and \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'Marine20'
            
            # Fifth case: radiocarbon dating results outside the boundaries of calibration curve
            elif  (self.__all_ages_cc.at[i, 'material_category'] == '14C terrestrial fossil' or self.__all_ages_cc.at[i, 'material_category'] == '14C sediment' or self.__all_ages_cc.at[i, 'material_category'] == '14C marine fossil') and \
            ((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) > 50000 or (self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) < 75 or \
            (((self.__all_ages_cc.at[i, 'age'] - self.__all_ages_cc.at[i,'reservoir_age']) - (self.__all_ages_cc.at[i, 'age_error'] + self.__all_ages_cc.at[i,'reservoir_error'])) < (1950 - datetime.datetime.now().year))):
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
            
            # Sixth case: Everything else :) 
            else:
                self.__all_ages_cc.at[i, 'calibration_curve'] = 'none'
                
        # Allow user to change the calibration curve
        if self.user_selection == True:
            col_for_selection = ['measurementid',
                                 'labid',
                                 'material_category', 
                                 'material_description', 
                                 'age', 
                                 'age_error', 
                                 'calibration_curve']
            view_ages = self.__all_ages_cc[~self.__all_ages_cc.labid.str.contains('_Surface')].copy()
            view_ages = view_ages[col_for_selection]
            view_ages.reset_index(inplace = True, drop = True)
            self.sheet = from_dataframe(view_ages)
            col_headers = ['MeasurementID',
                           'LabID',
                           'Category',
                           'Material',
                           'Uncalibrated Age (yr BP)',
                           'Uncalibrated Age Error (+/- yr)',
                           'Calibration Curve'
                          ]
            self.sheet.column_headers = col_headers
            choices_curve = ['IntCal20',
                            'Marine20',
                            'SHCal20',
                            'none']
            for header in range(len(col_headers)):
                if header == col_headers.index('Calibration Curve'):
                    self.sheet.cells[header].style['backgroundColor'] = '#eefbdd'
                    self.sheet.cells[header].choice = choices_curve
                    self.sheet.cells[header].type = 'dropdown'
                    self.sheet.cells[header].send_state()
                else:
                    self.sheet.cells[header].read_only = True
                    self.sheet.cells[header].squeeze_column = True
                    self.sheet.cells[header].textAlign = 'right'
                    self.sheet.cells[header].send_state()
            display(self.sheet)
    
    def add_calibration_curve(self):
        """
        Function to update information on calibration curve
        
        returns:
        @self.all_ages: dataframe with all age determination data 
        """
        if self.user_selection == True:
            df_sheet_user_input = ipysheet.to_dataframe(self.sheet)
            df_sheet_user_input = df_sheet_user_input[['MeasurementID', 'LabID', 'Calibration Curve']]
            df_sheet_user_input.columns = ['measurementid', 'labid', 'calibration_curve']
            initial_columns = self.__all_ages_cc.columns
            self.__all_ages_cc.set_index(['measurementid','labid'], inplace=True)
            self.__all_ages_cc.update(df_sheet_user_input.set_index(['measurementid','labid']))
            self.__all_ages_cc.reset_index(inplace = True)
            self.__all_ages_cc = self.__all_ages_cc[initial_columns]
            self.all_ages = self.__all_ages_cc
        else:
            self.all_ages = self.__all_ages_cc
        
class ProxyFromDB(object):
    def __init__(self, engine, coreid, proxy_group = None):
        """
        parameters:
        @self.engine: SQLalchemy specific engine for PostgreSQL
        @self.coreid: list containing all CoreIDs 
        @self.proxy_group: string containing the name of proxy group, 
        currently 'element' or 'organic' implemented; default value: None
        
        returns:
        @self.proxy_df: dataframe containing all proxy data for proxy group from database
        """
        self.engine = engine
        self.coreid = coreid
        if proxy_group is None:
            self.proxy_group = input('From which proxy group would you like to retrieve data? \nChironomid, Diatom, Element, GrainSize, Mineral, Organic, Pollen \n')
            self.proxy_group = self.proxy_group.lower()
            try:
                con = self.engine.connect()
                self.proxy_df = pd.read_sql(self.proxy_group, con)
                con.close()
            except IntegrityError:   
                con.close()
                print (f'There was an issue. Please try again!')
        else:
            self.proxy_group = proxy_group.lower()
            try:
                con = self.engine.connect()
                self.proxy_df = pd.read_sql(self.proxy_group, con)
                con.close()
            except IntegrityError:   
                con.close()
                print (f'There was an issue. Please try again!')
                
    def get_proxy(self, proxy):
        """
        Function to transform entire proxy dataframe into time-series-like dataframe
        
        parameters:
        @proxy: either str containing the name of the proxy or dictionary containing coreid and proxy name
        @self.search_element: dictionary containing the name of the proxy for each coreid
        
        returns:
        @self.name: dictionary with proxy name for coreid
        @self.proxy_ts: dictionary containing time-series-like dataframe with proxy data with columns for composite depth and value
        """
        self.search_element = {}
        if isinstance(proxy, str) == True and len(self.coreid) == 1:
            self.search_element[self.coreid] = proxy
        elif isinstance(proxy, str) == True and len(self.coreid) > 1:
            for core in self.coreid:
                self.search_element[core] = proxy
        else:
            self.search_element = proxy
        self.name = {}
        self.proxy_ts = {}
        for core in self.coreid:
            if self.proxy_group == 'element':
                input_df = self.proxy_df[self.proxy_df.measurementid.str.contains(core) & self.proxy_df.element_name.str.contains(f'{self.search_element[core]}_Area')].reset_index(drop = True)
                if len(input_df) != 0:
                    self.name[core] = proxy
                    for index, row in input_df.iterrows():
                        if type(row['element_value']) == NumericRange and row['element_value'].upper == row['element_value'].lower:
                            input_df.at[index, 'element_value'] = row['element_value'].upper
                        else:
                            input_df.drop(index, inplace=True)
                    input_df[['coreid','compositedepth']] = input_df['measurementid'].str.split(' ', n = 1, expand = True)
                    input_df['compositedepth'].replace(regex=True,inplace=True,to_replace=(r'_duplicate'+r'\d'),value=r'')
                    input_df = input_df.astype(dtype = {'compositedepth': float, 'element_value': float})
                    input_df = input_df.rename(columns = {'element_value' : 'value'})
                    self.proxy_ts[core] = input_df[['compositedepth','value']]
                else:
                    pass
            
            elif self.proxy_group == 'organic':
                self.search_element[core] = self.search_element[core].lower()
                organics = self.proxy_df[self.proxy_df.measurementid.str.contains(core)].reset_index(drop = True)
                input_df = organics[['measurementid',self.search_element[core]]].copy()
                input_df.dropna(inplace = True)
                if len(input_df) != 0:
                    self.name[core] = proxy
                    for index, row in input_df.iterrows():
                        if type(row[self.search_element[core]]) == NumericRange and row[self.search_element[core]].upper == row[self.search_element[core]].lower:
                            input_df.at[index, self.search_element[core]] = row[self.search_element[core]].upper
                        else:
                            input_df.drop(index, inplace=True)
                    input_df[['coreid','compositedepth']] = input_df['measurementid'].str.split(' ', n = 1, expand = True)
                    input_df['compositedepth'].replace(regex=True,inplace=True,to_replace=(r'_duplicate'+r'\d'),value=r'')
                    input_df = input_df.astype(dtype = {'compositedepth': float, self.search_element[core]: float})
                    input_df = input_df.rename(columns = {self.search_element[core] : 'value'})
                    self.proxy_ts[core] = input_df[['compositedepth','value']]
                else:
                    pass
            
            else:
                print('Other proxy groups will be implemented soon.')
        
        return self.proxy_ts
                
class ProxyFromFile(object):
    def __init__(self, filename = None):
        """
        parameters:
        @filename: string with the address to file on system
        """
        self.__filename = filename
        if self.__filename == None:
            __data_dir = os.path.abspath('./input_files')
            self.fc = FileChooser(__data_dir)
            self.fc.use_dir_icons = True
            self.fc.filter_pattern = ['*.xlsx']
            display(self.fc)
     
    def __proxy_data_multi_cores(self):
        """
        Helper function to store proxy data from file in dictionary
        
        returns:
        @self.__proxy_dictionary: dictionary with proxy data indexed by their CoreID
        """
        xl = pd.ExcelFile(self.__filename)
        self.__proxy_dictionary = {}
        for sheet in xl.sheet_names:
            self.__proxy_dictionary[f'{sheet}']= pd.read_excel(xl,sheet_name=sheet)
           
    def get_proxy(self):
        """
        Main function that calls helper function to get proxy data from file
        
        returns:
        @self.name: dictionary with proxy name for each coreid
        @self.proxy_ts: dictionary containing time-series-like dataframe with proxy data with columns for composite depth and value
        """
        if self.__filename == None:
            self.__filename = self.fc.value
        self.__proxy_data_multi_cores()
        self.name = {}
        self.proxy_ts = {}
        for key in self.__proxy_dictionary.keys():
            self.name[key] = self.__proxy_dictionary[key].columns[1].split('(')[1].split(')')[0]
            self.proxy_ts[key] = self.__proxy_dictionary[key]
            self.proxy_ts[key].columns = ['compositedepth','value']
        return self.proxy_ts
