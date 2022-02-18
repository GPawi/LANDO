#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to prepare age determination data for each age-depth modeling software

Author: Gregor Pfalz
github: GPawi
"""

import numpy as np
import pandas as pd
import os
import tempfile
import math
import datetime


### For Undatable ### 
class PrepForUndatable(object):
    def __init__(self, all_ages, all_coreid_list, location_UndatableFolder = 'src/UndatableFolder'):
        """
        parameters:
        @self.__all_ages: dataframe with all age determination data 
        @self.__all_coreid_list: list of CoreIDs used within the LANDO environment
        @self.location_UndatableFolder: string containing the location for the Undatable folder that is used by MATLAB
        """
        self.__all_ages = all_ages
        self.__all_coreid_list = all_coreid_list
        self.location_UndatableFolder = location_UndatableFolder
        
        if self.location_UndatableFolder is None:
            while True:
                self.location_UndatableFolder = input('Please give the location of the Undatable Folder! ')
                if 'UndatableFolder' not in self.location_UndatableFolder:
                    print ('Your link does not provide the "UndatableFolder" folder, please try again! ')
                else:
                    break
            os.chdir(fr'{self.location_UndatableFolder}')
        
        else:
            os.chdir(fr'{self.location_UndatableFolder}')
            
    def __prep_format_Undatable__(self):
        """
        Helper function to transform age determination data into the format of Undatable 
        
        returns:
        @self.__txt_df_Undatable: dataframe with age determination data in the format usable with Undatable
        """
        __all_ages = self.__all_ages
        self.__txt_Undatable_columns = ['Sample ID',
                                        'Depth 1',
                                        'Depth 2', 
                                        'Age', 
                                        'Age error', 
                                        'Data Type', 
                                        'Calibration', 
                                        'Resage', 
                                        'Reserr', 
                                        'Bootstrap']
        self.__txt_df_Undatable = pd.DataFrame(columns = self.__txt_Undatable_columns)
        
        for i,r in __all_ages.iterrows():
            self.__core_Undatable = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                            (float(__all_ages.at[i, 'compositedepth']) - (float(__all_ages.at[i,'thickness'])/2)),
                                                            (float(__all_ages.at[i, 'compositedepth']) + (float(__all_ages.at[i,'thickness'])/2)),
                                                            __all_ages.at[i, 'age'],
                                                            __all_ages.at[i, 'age_error'],
                                                            __all_ages.at[i, 'material_category'],
                                                            __all_ages.at[i, 'calibration_curve'],
                                                            __all_ages.at[i, 'reservoir_age'],
                                                            __all_ages.at[i, 'reservoir_error'],
                                                            'Yes']]), columns = self.__txt_Undatable_columns)
            self.__txt_df_Undatable = self.__txt_df_Undatable.append(self.__core_Undatable)

                
    def __prep_file_Undatable__(self):
        """
        Helper function to save dataframes as txt file in the Undatable folder
        
        returns:
        txt files for each CoreID with age determination data
        """
        __coreid_list = self.__all_coreid_list
        __txt_df_Undatable = self.__txt_df_Undatable
        #### Check if more than 2 samples are available to run with Undatable
        self.new_coreid_list = []
        for ID in __coreid_list:
            if len(__txt_df_Undatable[__txt_df_Undatable['Sample ID'].str.contains(ID) == True]) < 3:
                print (f'{ID} not enough dates')
                __txt_df_Undatable = __txt_df_Undatable[~(__txt_df_Undatable['Sample ID'].str.contains(ID) == True)]
            else:
                self.new_coreid_list.append(ID)
        #### Create Files
        for ID in self.new_coreid_list:
            if __txt_df_Undatable[__txt_df_Undatable['Sample ID'].str.contains(ID)].empty == False:
                temp = __txt_df_Undatable[__txt_df_Undatable['Sample ID'].str.contains(ID) == True]
                temp.to_csv(f'{ID}.txt', header = True, index = False, sep = '\t')
            else:
                continue
        print ('New files for Undatable created!')
        
    def prep_it(self):
        """
        Main function to call helper functions
        """
        self.__prep_format_Undatable__()
        self.__prep_file_Undatable__()
        self.coreid_df = pd.DataFrame(self.new_coreid_list, columns = ['coreid'])
        self.coreid_df = pd.concat([pd.DataFrame(['linebreak'], columns = ['coreid']), self.coreid_df], ignore_index = True)

### For Bchron ###
class PrepForBchron(object):
    def __init__(self, all_ages):
        """
        parameters:
        @self.__all_ages: dataframe with all age determination data 
        """
        self.__all_ages = all_ages
    
    def __prep_format_Bchron__(self):
        """
        Helper function to transform age determination data into the format of Bchron 
        
        returns:
        @self.__txt_df_Bchron: dataframe with age determination data in the format usable with Bchron
        """
        __all_ages = self.__all_ages
        __all_ages = __all_ages.astype(dtype = {'age' : float,
                                                'age_error' : float,
                                                'reservoir_age' : float,
                                                'reservoir_error': float})
        self.__txt_Bchron_columns = ['id',
                                     'ages',
                                     'ageSds',
                                     'position',
                                     'thickness',
                                     'calCurves']

        self.__txt_df_Bchron = pd.DataFrame(columns = self.__txt_Bchron_columns)
        self.__txt_df_Bchron = self.__txt_df_Bchron.astype(dtype = {'id' : str,
                                                                    'ages' : float,
                                                                    'ageSds': float,
                                                                    'position': float,
                                                                    'thickness': float,
                                                                    'calCurves': str})
        
        for i,r in __all_ages.iterrows():
            if __all_ages.at[i, 'calibration_curve'] == 'none':
                self.__core_Bchron = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']), 
                                                             (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error']),
                                                             __all_ages.at[i, 'compositedepth'],
                                                             __all_ages.at[i,'thickness'],
                                                             'normal']]), columns = self.__txt_Bchron_columns)
                self.__core_Bchron = self.__core_Bchron.astype(dtype = {'id' : str,
                                                                        'ages' : float,
                                                                        'ageSds': float,
                                                                        'position': float,
                                                                        'thickness': float,
                                                                        'calCurves': str})
                self.__txt_df_Bchron = self.__txt_df_Bchron.append(self.__core_Bchron)
            else:
                self.__core_Bchron = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']), 
                                                             (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error']),
                                                             __all_ages.at[i, 'compositedepth'],
                                                             __all_ages.at[i,'thickness'],
                                                             __all_ages.at[i, 'calibration_curve'].lower()]]), columns = self.__txt_Bchron_columns)
                self.__core_Bchron = self.__core_Bchron.astype(dtype = {'id' : str,
                                                                        'ages' : float,
                                                                        'ageSds': float,
                                                                        'position': float,
                                                                        'thickness': float,
                                                                        'calCurves': str})
                self.__txt_df_Bchron = self.__txt_df_Bchron.append(self.__core_Bchron)
        
        self.__txt_df_Bchron = self.__txt_df_Bchron.reset_index(drop = True)
        
        ### Due to Bchron update 4.7.6
        name_groups = self.__txt_df_Bchron.groupby('id')['id']
        suffix = name_groups.cumcount()+1
        repeats = name_groups.transform('size')

        self.__txt_df_Bchron['id'] = np.where(repeats > 1, self.__txt_df_Bchron['id'] + '_dup' + suffix.map(str), self.__txt_df_Bchron['id'])
        
        
    def prep_it(self):
        """
        Main function to call helper function and renames variable
        
        returns:
        @self.Bchron_Frame: dataframe with age determination data in the format usable with Bchron
        """
        self.__prep_format_Bchron__()
        self.Bchron_Frame = self.__txt_df_Bchron
        
        
### For hamstr ###      
class PrepForHamstr(object):
    def __init__(self, all_ages):
        """
        parameters:
        @self.__all_ages: dataframe with all age determination data 
        """
        self.__all_ages = all_ages
    
    def __prep_format_hamstr__(self):
        """
        Helper function to transform age determination data into the format of hamstr 
        
        returns:
        @self.__txt_df_hamstr: dataframe with age determination data in the format usable with hamstr
        """
        __all_ages = self.__all_ages
        __all_ages = __all_ages.astype(dtype = {'age' : float,
                                                'age_error' : float,
                                                'reservoir_age' : float,
                                                'reservoir_error': float})
        self.__txt_hamstr_columns = ['id',
                                     'ages',
                                     'ageSds',
                                     'position',
                                     'thickness',
                                     'calCurves']

        self.__txt_df_hamstr = pd.DataFrame(columns = self.__txt_hamstr_columns)
        self.__txt_df_hamstr = self.__txt_df_hamstr.astype(dtype = {'id' : str,
                                                                    'ages' : float,
                                                                    'ageSds': float,
                                                                    'position': float,
                                                                    'thickness': float,
                                                                    'calCurves': str})
        
        for i,r in __all_ages.iterrows():
            if __all_ages.at[i, 'calibration_curve'] == 'none':
                self.__core_hamstr = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']), 
                                                             (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error']),
                                                             __all_ages.at[i, 'compositedepth'],
                                                             __all_ages.at[i,'thickness'],
                                                             'normal']]), columns = self.__txt_hamstr_columns)
                self.__core_hamstr = self.__core_hamstr.astype(dtype = {'id' : str,
                                                                        'ages' : float,
                                                                        'ageSds': float,
                                                                        'position': float,
                                                                        'thickness': float,
                                                                        'calCurves': str})
                self.__txt_df_hamstr = self.__txt_df_hamstr.append(self.__core_hamstr)
            else:
                self.__core_hamstr = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']), 
                                                             (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error']),
                                                             __all_ages.at[i, 'compositedepth'],
                                                             __all_ages.at[i,'thickness'],
                                                             __all_ages.at[i, 'calibration_curve'].lower()]]), columns = self.__txt_hamstr_columns)
                self.__core_hamstr = self.__core_hamstr.astype(dtype = {'id' : str,
                                                                        'ages' : float,
                                                                        'ageSds': float,
                                                                        'position': float,
                                                                        'thickness': float,
                                                                        'calCurves': str})
                self.__txt_df_hamstr = self.__txt_df_hamstr.append(self.__core_hamstr)
        
        self.__txt_df_hamstr = self.__txt_df_hamstr.reset_index(drop = True)
        
        
    def prep_it(self):
        """
        Main function to call helper function and renames variable
        
        returns:
        @self.hamstr_Frame: dataframe with age determination data in the format usable with hamstr
        """
        self.__prep_format_hamstr__()
        self.hamstr_Frame = self.__txt_df_hamstr

        
### For Bacon ###      
class PrepForBacon(object):
    def __init__(self, all_ages):
        """
        parameters:
        @self.__all_ages: dataframe with all age determination data 
        """
        self.__all_ages = all_ages
    
    def __prep_format_Bacon__(self):
        """
        Helper function to transform age determination data into the format of Bacon 
        
        returns:
        @self.__txt_df_Bacon: dataframe with age determination data in the format usable with Bacon
        """
        __all_ages = self.__all_ages
        __all_ages = __all_ages.astype(dtype = {'age' : float,
                                                'age_error' : float,
                                                'reservoir_age' : float,
                                                'reservoir_error': float})
        self.__txt_Bacon_columns = ['id',
                                     'obs_age',
                                     'obs_err',
                                     'depth',
                                     'cc',
                                     'delta_R',
                                     'delta_STD']

        self.__txt_df_Bacon = pd.DataFrame(columns = self.__txt_Bacon_columns)
        self.__txt_df_Bacon = self.__txt_df_Bacon.astype(dtype = {'id' : str,
                                                                  'obs_age' : float,
                                                                  'obs_err' : float,
                                                                  'depth' : float,
                                                                  'cc' : int,
                                                                  'delta_R' : float,
                                                                  'delta_STD' : float})
        
        for i,r in __all_ages.iterrows():
            if __all_ages.at[i, 'calibration_curve'] == 'IntCal20':  
                self.__core_Bacon = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             __all_ages.at[i, 'age'], 
                                                             __all_ages.at[i, 'age_error'],
                                                             __all_ages.at[i, 'compositedepth'],
                                                             1,
                                                             __all_ages.at[i,'reservoir_age'],
                                                             __all_ages.at[i,'reservoir_error']]]), columns = self.__txt_Bacon_columns)
                self.__core_Bacon = self.__core_Bacon.astype(dtype = {'id' : str,
                                                                      'obs_age' : float,
                                                                      'obs_err' : float,
                                                                      'depth' : float,
                                                                      'cc' : int,
                                                                      'delta_R' : float,
                                                                      'delta_STD' : float})
                self.__txt_df_Bacon = self.__txt_df_Bacon.append(self.__core_Bacon)
        

                
            elif __all_ages.at[i, 'calibration_curve'] == 'Marine20':  
                self.__core_Bacon = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             __all_ages.at[i, 'age'], 
                                                             __all_ages.at[i, 'age_error'],
                                                             __all_ages.at[i, 'compositedepth'],
                                                             2,
                                                             __all_ages.at[i,'reservoir_age'],
                                                             __all_ages.at[i,'reservoir_error']]]), columns = self.__txt_Bacon_columns)
                self.__core_Bacon = self.__core_Bacon.astype(dtype = {'id' : str,
                                                                      'obs_age' : float,
                                                                      'obs_err' : float,
                                                                      'depth' : float,
                                                                      'cc' : int,
                                                                      'delta_R' : float,
                                                                      'delta_STD' : float})
                self.__txt_df_Bacon = self.__txt_df_Bacon.append(self.__core_Bacon)
            
            elif __all_ages.at[i, 'calibration_curve'] == 'SHCal20':  
                self.__core_Bacon = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             __all_ages.at[i, 'age'], 
                                                             __all_ages.at[i, 'age_error'],
                                                             __all_ages.at[i, 'compositedepth'],
                                                             3,
                                                             __all_ages.at[i,'reservoir_age'],
                                                             __all_ages.at[i,'reservoir_error']]]), columns = self.__txt_Bacon_columns)
                self.__core_Bacon = self.__core_Bacon.astype(dtype = {'id' : str,
                                                                      'obs_age' : float,
                                                                      'obs_err' : float,
                                                                      'depth' : float,
                                                                      'cc' : int,
                                                                      'delta_R' : float,
                                                                      'delta_STD' : float})
                self.__txt_df_Bacon = self.__txt_df_Bacon.append(self.__core_Bacon)
            
            else:
                self.__core_Bacon = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'], ## Bacon might need another ID
                                                            __all_ages.at[i, 'age'], 
                                                            __all_ages.at[i, 'age_error'],
                                                            __all_ages.at[i, 'compositedepth'],
                                                            0,
                                                            __all_ages.at[i,'reservoir_age'],
                                                            __all_ages.at[i,'reservoir_error']]]), columns = self.__txt_Bacon_columns)
                self.__core_Bacon = self.__core_Bacon.astype(dtype = {'id' : str,
                                                                      'obs_age' : float,
                                                                      'obs_err' : float,
                                                                      'depth' : float,
                                                                      'cc' : int,
                                                                      'delta_R' : float,
                                                                      'delta_STD' : float})
                self.__txt_df_Bacon = self.__txt_df_Bacon.append(self.__core_Bacon)
        
        self.__txt_df_Bacon = self.__txt_df_Bacon.reset_index(drop = True)
        
        
    def prep_it(self):
        """
        Main function to call helper function and renames variable
        
        returns:
        @self.Bacon_Frame: dataframe with age determination data in the format usable with Bacon
        """
        self.__prep_format_Bacon__()
        self.Bacon_Frame = self.__txt_df_Bacon
              
### For clam ###
class PrepForClam(object):
    def __init__(self, all_ages):
        """
        parameters:
        @self.__all_ages: dataframe with all age determination data 
        """
        self.__all_ages = all_ages
    
    def __prep_format_clam__(self):
        """
        Helper function to transform age determination data into the format of clam 
        
        returns:
        @self.__txt_df_clam: dataframe with age determination data in the format usable with clam
        """
        __all_ages = self.__all_ages
        __all_ages = __all_ages.astype(dtype = {'age' : int,
                                                'reservoir_age' : int})
        
        self.__txt_clam_columns = ['lab_ID',
                                    '14C_age',
                                    'cal_age',
                                    'error',
                                    'reservoir',
                                    'depth',
                                    'thickness']

        self.__txt_df_clam = pd.DataFrame(columns = self.__txt_clam_columns)
        
        for i,r in __all_ages.iterrows():
            if (__all_ages.at[i, 'material_category'] == '14C terrestrial fossil' or __all_ages.at[i, 'material_category'] == '14C sediment' or __all_ages.at[i, 'material_category'] == '14C marine fossil') and \
            ((__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']) <= 50000 and (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']) > 75 and \
             (((__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']) - (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error'])) > (1950 - datetime.datetime.now().year))):  
                self.__core_clam = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                            __all_ages.at[i, 'age'],
                                                            '',
                                                            __all_ages.at[i, 'age_error'],
                                                            __all_ages.at[i,'reservoir_age'],
                                                            __all_ages.at[i, 'compositedepth'],
                                                            __all_ages.at[i,'thickness']]]), columns = self.__txt_clam_columns)
                self.__txt_df_clam = self.__txt_df_clam.append(self.__core_clam)
            else:
                self.__core_clam = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                           '', 
                                                           __all_ages.at[i, 'age'],
                                                            __all_ages.at[i, 'age_error'],
                                                            __all_ages.at[i,'reservoir_age'],
                                                            __all_ages.at[i, 'compositedepth'],
                                                            __all_ages.at[i,'thickness']]]), columns = self.__txt_clam_columns)
                self.__txt_df_clam = self.__txt_df_clam.append(self.__core_clam)
        
        self.__txt_df_clam = self.__txt_df_clam.reset_index(drop = True)
    
    def prep_it(self):
        """
        Main function to call helper function and renames variable
        
        returns:
        @self.clam_Frame: dataframe with age determination data in the format usable with clam
        """
        self.__prep_format_clam__()
        self.clam_Frame = self.__txt_df_clam
        
### For ReservoirCorrection ###      
class PrepForReservoirCorrection(object):
    def __init__(self, all_ages):
        """
        parameters:
        @self.__all_ages: dataframe with all age determination data 
        """
        self.__all_ages = all_ages
        
    def __split_data_ReservoirCorrection__(self):
        """
        Helper function to split dataframe with age determination data into two separate dataframes
        
        returns:
        @self.__desired_surface_dates: dataframe with surface samples dervied from the expedition year 
        @self.__all_ages: altered dataframe with all age determination data, whereas the surface sample is removed
        """
        self.__desired_surface_dates = self.__all_ages[self.__all_ages.labid.str.contains('_Surface')]
        self.__dates_without_surface_sample = self.__all_ages[~self.__all_ages.labid.isin(self.__desired_surface_dates.labid)]
        self.__dates_without_surface_sample = self.__dates_without_surface_sample[self.__dates_without_surface_sample.material_category.str.contains('14C')]
        for ID in self.__dates_without_surface_sample.coreid.unique():
            if len(self.__dates_without_surface_sample[self.__dates_without_surface_sample.coreid == ID]) < 2:
                self.__dates_without_surface_sample = self.__dates_without_surface_sample[~(self.__dates_without_surface_sample.coreid == ID)]
        self.__all_ages = self.__dates_without_surface_sample
    
    def __prep_format_ReservoirCorrection__(self):
        """
        Helper function to transform age determination data into the format of hamstr 
        
        returns:
        @self.__txt_df_ReservoirCorrection: dataframe with age determination data in the format usable with hamstr
        """
        __all_ages = self.__all_ages
        __all_ages = __all_ages.astype(dtype = {'age' : float,
                                                'age_error' : float,
                                                'reservoir_age' : float,
                                                'reservoir_error': float})
        self.__txt_ReservoirCorrection_columns = ['id',
                                     'ages',
                                     'ageSds',
                                     'position',
                                     'thickness',
                                     'calCurves']

        self.__txt_df_ReservoirCorrection = pd.DataFrame(columns = self.__txt_ReservoirCorrection_columns)
        self.__txt_df_ReservoirCorrection = self.__txt_df_ReservoirCorrection.astype(dtype = {'id' : str,
                                                                    'ages' : float,
                                                                    'ageSds': float,
                                                                    'position': float,
                                                                    'thickness': float,
                                                                    'calCurves': str})
        
        for i,r in __all_ages.iterrows():
            if __all_ages.at[i, 'calibration_curve'] == 'none':
                self.__core_ReservoirCorrection = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']), 
                                                             (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error']),
                                                             __all_ages.at[i, 'compositedepth'],
                                                             __all_ages.at[i,'thickness'],
                                                             'normal']]), columns = self.__txt_ReservoirCorrection_columns)
                self.__core_ReservoirCorrection = self.__core_ReservoirCorrection.astype(dtype = {'id' : str,
                                                                        'ages' : float,
                                                                        'ageSds': float,
                                                                        'position': float,
                                                                        'thickness': float,
                                                                        'calCurves': str})
                self.__txt_df_ReservoirCorrection = self.__txt_df_ReservoirCorrection.append(self.__core_ReservoirCorrection)
            else:
                self.__core_ReservoirCorrection = pd.DataFrame(np.array([[__all_ages.at[i, 'measurementid'],
                                                             (__all_ages.at[i, 'age'] - __all_ages.at[i,'reservoir_age']), 
                                                             (__all_ages.at[i, 'age_error'] + __all_ages.at[i,'reservoir_error']),
                                                             __all_ages.at[i, 'compositedepth'],
                                                             __all_ages.at[i,'thickness'],
                                                             __all_ages.at[i, 'calibration_curve'].lower()]]), columns = self.__txt_ReservoirCorrection_columns)
                self.__core_ReservoirCorrection = self.__core_ReservoirCorrection.astype(dtype = {'id' : str,
                                                                        'ages' : float,
                                                                        'ageSds': float,
                                                                        'position': float,
                                                                        'thickness': float,
                                                                        'calCurves': str})
                self.__txt_df_ReservoirCorrection = self.__txt_df_ReservoirCorrection.append(self.__core_ReservoirCorrection)
        
        self.__txt_df_ReservoirCorrection = self.__txt_df_ReservoirCorrection.reset_index(drop = True)
        
        
    def prep_it(self):
        """
        Main function to call helper function and renames variable
        
        returns:
        @self.RC_Frame: dataframe with age determination data 
        @self.RC_CoreIDs: list with CoreIDs that have radiocarbon age determination data
        @self.desired_surface_dates: dataframe with surface samples dervied from the expedition year
        """
        self.__split_data_ReservoirCorrection__()
        self.__prep_format_ReservoirCorrection__()
        self.__coreid_df = pd.DataFrame(self.__all_ages['coreid'].unique(), columns = ['coreid'])
        self.RC_CoreIDs = self.__coreid_df['coreid'].to_list()
        self.RC_Frame = self.__txt_df_ReservoirCorrection
        self.desired_surface_dates = self.__desired_surface_dates
