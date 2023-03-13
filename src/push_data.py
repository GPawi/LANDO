#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to upload age determination data to database

Author: Gregor Pfalz
github: GPawi
"""

import numpy as np
import pandas as pd
import os
import sqlalchemy
from sqlalchemy.exc import IntegrityError

class PushIt(object):
    def __init__(self, agg, engine, model = ''):
        """
        parameters:
        @self.agg: object containing the results from the aggregation function
        @self.engine: SQLalchemy specific engine for PostgreSQL
        @self.model: string of name of model that the aggregation object is coming from; default value: ''
        @self.age_model_result: model-specific dataframe holding the results from the aggregation 
        """
        self.agg = agg
        self.engine = engine
        self.model = model
        if self.model == 'Undatable':
            self.age_model_result = agg.age_model_result_Undatable
        elif self.model == 'Bchron':
            self.age_model_result = agg.age_model_result_Bchron
        elif self.model == 'hamstr':
            self.age_model_result = agg.age_model_result_hamstr
        elif self.model == 'Bacon':
            self.age_model_result = agg.age_model_result_Bacon
        elif self.model == 'OxCal':
            self.age_model_result = agg.age_model_result_OxCal
        elif self.model == 'clam':
            self.age_model_result = agg.age_model_result_clam        
        else: 
            raise Exception(f'Please specify the model that you are using')
        
    def push_to_db(self):
        """
        Function to upload data to the database, specified by engine
        
        returns:
        print statement, whether upload was successful or not
        """
        self.__results__ = self.age_model_result
        if not all(self.__results__) == True:
            print ('Information: The result list was empty, so nothing was uploaded.')
        elif type(self.__results__) == list:
            print ('Information: The result list was empty, so nothing was uploaded.')
        elif self.engine == 'No Database':
            print ('Information: LANDO is not connected to a database, so nothing was uploaded.')
        else:
            self.__measurementids__ = self.age_model_result.copy()
            model = self.model
            engine = self.engine
            try:
                self.__measurementids__[['coreid','compositedepth']] = self.__measurementids__['measurementid'].str.split(' ', n = 1, expand = True)
                self.__measurementids__ = self.__measurementids__[['measurementid','coreid','compositedepth']]
                self.__measurementids__ = self.__measurementids__.astype(dtype = {'measurementid':str, 'coreid': str, 'compositedepth': float}).drop_duplicates()
                try:
                    con = engine.connect()
                    self.__down_measurement__ = pd.read_sql('measurement', con)
                    self.__down_measurement__ = self.__down_measurement__.astype(dtype = {'measurementid':str, 'coreid': str, 'compositedepth': float})
                    self.__measurement___duplicate_check = pd.concat([self.__measurementids__.reset_index(drop=True),self.__down_measurement__.reset_index(drop=True)])
                    self.__measurement___duplicates = self.__measurement___duplicate_check[self.__measurement___duplicate_check.duplicated() == True].reset_index(drop=True)
                    self.__measurement___duplicate_free = self.__measurementids__.append(self.__measurement___duplicates)
                    self.__measurement___duplicate_free = self.__measurement___duplicate_free.drop_duplicates(keep = False)
                    self.__measurement___duplicate_free.to_sql('measurement', con, if_exists='append', index = False)
                except IntegrityError:
                    raise Exception(f'There is a problem in the upload!')
                finally:
                    self.__results__.to_sql('modeloutput', con, if_exists='append', index = False)
                    con.close()
                    print (f'I am done with uploading the results from {model}')
            except IntegrityError:   
                con.close()
                print (f'There was an issue - Please report to Gregor Pfalz (Gregor.Pfalz@awi.de)!')
            
    def delete_files(self, location_UndatableFolder, coreids):
        """
        Function to remove files that were generated during the process of modeling with Undatable
        
        parameters:
        @self.location_UndatableFolder: string containing the location for the Undatable folder that is used by MATLAB
        @self.coreids: list of CoreIDs used within the LANDO environment
        """
        self.location_UndatableFolder = location_UndatableFolder
        self.coreids = coreids
        self.coreids = self.coreids[1:].reset_index(drop = True)
        #
        os.chdir(fr'{self.location_UndatableFolder}')
        for i in range(0, len(self.coreids)):
            os.remove(f'{self.coreids.iloc[i,0]}.txt')
            os.remove(f'{self.coreids.iloc[i,0]}_admodel.txt')
            os.remove(f'{self.coreids.iloc[i,0]}_temage.mat')
        print ('Information: All unwanted Undatable files have been deleted')
