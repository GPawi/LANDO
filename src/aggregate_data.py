#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module within LANDO to aggregate data from the 10,000 itertations for each modeling software

Author: Gregor Pfalz
github: GPawi
"""

import numpy as np
import pandas as pd
import os
import scipy.io as sio
import datetime


#### Undatable
class AggDataUndatable(object):
    def __init__(self, prep_Undatable, orig_dir, dttp):
        """
        parameters:
        @self.prep_Undatable: object containing the variables from the Undatable object from preparation phase
        @self.location_UndatableFolder: string containing the location for the Undatable folder that is used by MATLAB/Octave
        @self.CoreIDs: list of CoreIDs used within the LANDO environment
        @self.orig_dir: original directory, where user excute LANDO
        @self.dttp: value 'Yes' or 'No', if reservoir correction took place
        """
        self.prep_Undatable = prep_Undatable
        self.location_UndatableFolder = prep_Undatable.location_UndatableFolder
        self.CoreIDs = prep_Undatable.coreid_df
        self.CoreIDs = self.CoreIDs[1:].reset_index(drop = True)
        self.orig_dir = orig_dir
        self.dttp = dttp
    
    def results_agg(self):
        """
        Main function to aggregate data
        
        returns:
        @self.age_model_result_Undatable: dataframe holding the results from the aggregation 
        @self.Undatable_core_results: iteration results from Undatable with MeasurementID and model name added
        """
        CoreIDs = self.CoreIDs
        dttp = self.dttp
        self.__age_model_columns = ['measurementid',
                                    'modeloutput_median',
                                    'modeloutput_mean',
                                    'lower_2_sigma',
                                    'lower_1_sigma',
                                    'upper_1_sigma',
                                    'upper_2_sigma',
                                    'model_name']
        self.age_model_result_Undatable = pd.DataFrame(columns = self.__age_model_columns)
        
        #### This section reads the individual txt files that are produced by Undatable
        os.chdir(fr'{self.orig_dir}/{self.location_UndatableFolder}')
        __individual_result_columns = ['measurementid',
                                     'modeloutput_median',
                                     'modeloutput_mean',
                                     'lower_2_sigma',
                                     'lower_1_sigma',
                                     'upper_1_sigma',
                                     'upper_2_sigma']
        for i in range(0, len(CoreIDs)):
            __individual_result = pd.read_csv(f'{CoreIDs.iloc[i,0]}_admodel.txt',sep = '\t', 
                                            header = 1,
                                            index_col = False,
                                            usecols = [0,1,2,3,4,5,6],
                                            names = __individual_result_columns,
                                            converters = {'measurementid': str,
                                                          'modeloutput_median': np.int64,
                                                          'modeloutput_mean': np.int64,
                                                          'lower_2_sigma': np.int64,
                                                          'lower_1_sigma': np.int64,
                                                          'upper_1_sigma': np.int64,
                                                          'upper_2_sigma': np.int64}
                                           )
            __individual_result['measurementid'] = __individual_result['measurementid'].str.replace('.000000', '', regex = True)
            __individual_result['measurementid'] = __individual_result['measurementid'].str.replace('00000', '', regex = True)
            __individual_result['measurementid'] = __individual_result['measurementid'].str.replace('0000', '', regex = True)
            __individual_result['measurementid'] = CoreIDs.iloc[i,0] + ' ' + __individual_result['measurementid']
            __individual_result.insert(7, 'model_name', 'Undatable', True)
            __individual_result.insert(8, 'preselection', dttp, True)
            #self.age_model_result_Undatable = self.age_model_result_Undatable.append(__individual_result)
            self.age_model_result_Undatable = pd.concat([self.age_model_result_Undatable, __individual_result], axis = 0)
        
        self.age_model_result_Undatable = self.age_model_result_Undatable.reset_index(drop = True)
        
        #### This section loads the iteration results from the additional .mat file into the variable
        self.Undatable_core_results = pd.DataFrame()
        for i in range(0, len(CoreIDs)):
            __load_temp_age = sio.loadmat(f'{CoreIDs.iloc[i,0]}_temage.mat')
            __individual_temp_age = pd.DataFrame(__load_temp_age['tempage'])
            __individual_temp_age = __individual_temp_age.assign(model_name = 'Undatable')
            #self.Undatable_core_results = self.Undatable_core_results.append(__individual_temp_age)
            self.Undatable_core_results = pd.concat([self.Undatable_core_results, __individual_temp_age], axis = 0)
        self.Undatable_core_results = self.Undatable_core_results.reset_index(drop = True)
        self.Undatable_core_results = self.Undatable_core_results.assign(measurementid = self.age_model_result_Undatable['measurementid'])
            
#### Bchron  
class AggDataBchron(object):
    def __init__(self, Bchron_core_results, dttp):
        """
        parameters:
        @self.Bchron_core_results: dataframe with 10,000 iteration results from Bchron
        @self.dttp: value 'Yes' or 'No', if reservoir correction took place
        """
        self.Bchron_core_results = Bchron_core_results
        self.dttp = dttp
    
    def __confidence_intervals(self, g):
        """
        Helper function to get basic statistics (median, mean, 1-sigma range, 2-sigma range)
        
        returns:
        @median: median value of input data
        @mean:  mean value of input data
        @two_sigma_lo: lower boundary value of 2-sigma range of input data
        @one_sigma_lo: lower boundary value of 1-sigma range of input data
        @one_sigma_hi: upper boundary value of 1-sigma range of input data
        @two_sigma_hi: upper boundary value of 2-sigma range of input data
        """
        median = g.median()
        mean = g.mean()
        two_sigma_hi = g.quantile(q = 0.954, interpolation = 'nearest') 
        two_sigma_lo = g.quantile(q = 0.046, interpolation = 'nearest')
        one_sigma_hi = g.quantile(q = 0.683, interpolation = 'nearest') 
        one_sigma_lo = g.quantile(q = 0.317, interpolation = 'nearest')
        return median, mean, two_sigma_lo, one_sigma_lo, one_sigma_hi, two_sigma_hi
    
    def __sort_data(self, data):
        """
        Helper function to sort MeasurementID
        
        returns:
        @data: dataframe with sorted MeasurementID, where composite depth is sorted numeric not as string
        """
        data[['coreid','compositedepth']] = data['measurementid'].str.split(' ', n = 1, expand = True)
        data = data.astype(dtype = {'compositedepth' : float}).sort_values(by = ['coreid','compositedepth'], ignore_index = True)
        data.drop(['compositedepth','coreid'], axis = 1, inplace = True)
        return data 
    
    def results_agg(self):
        """
        Main function to aggregate data
        
        returns:
        @self.age_model_result_Bchron: dataframe holding the results from the aggregation 
        @self.Bchron_core_results: altered 10,000 iteration results from Bchron with MeasurementID and model name added
        """
        Bchron_core_results = self.Bchron_core_results
        dttp = self.dttp
        self.age_model_result_Bchron = Bchron_core_results.apply(self.__confidence_intervals, axis = 1, result_type='expand')
        self.age_model_result_Bchron.columns = ['modeloutput_median',
                                           'modeloutput_mean',
                                           'lower_2_sigma',
                                           'lower_1_sigma',
                                           'upper_1_sigma',
                                           'upper_2_sigma']
        self.age_model_result_Bchron = self.age_model_result_Bchron.astype(int)
        self.age_model_result_Bchron = self.age_model_result_Bchron.reset_index()
        self.age_model_result_Bchron = self.age_model_result_Bchron.rename(columns={"index": "measurementid"})
        self.age_model_result_Bchron = self.__sort_data(self.age_model_result_Bchron)
        self.age_model_result_Bchron.insert(7, 'model_name', 'Bchron', True)
        self.age_model_result_Bchron.insert(8, 'preselection', dttp, True)
        ###
        self.Bchron_core_results.reset_index(inplace = True)
        self.Bchron_core_results['model_name'] = 'Bchron'
        self.Bchron_core_results.rename(columns={"index": "measurementid"}, inplace = True)

#### hamstr     
class AggDataHamstr(object):
    def __init__(self, hamstr_core_results, dttp):
        """
        parameters:
        @self.hamstr_core_results: dataframe with 10,000 iteration results from hamstr
        @self.dttp: value 'Yes' or 'No', if reservoir correction took place
        """
        self.hamstr_core_results = hamstr_core_results
        self.dttp = dttp
    
    def __confidence_intervals(self, g):
        """
        Helper function to get basic statistics (median, mean, 1-sigma range, 2-sigma range)
        
        returns:
        @median: median value of input data
        @mean:  mean value of input data
        @two_sigma_lo: lower boundary value of 2-sigma range of input data
        @one_sigma_lo: lower boundary value of 1-sigma range of input data
        @one_sigma_hi: upper boundary value of 1-sigma range of input data
        @two_sigma_hi: upper boundary value of 2-sigma range of input data
        """
        median = g.median()
        mean = g.mean()
        two_sigma_hi = g.quantile(q = 0.954, interpolation = 'nearest') 
        two_sigma_lo = g.quantile(q = 0.046, interpolation = 'nearest')
        one_sigma_hi = g.quantile(q = 0.683, interpolation = 'nearest') 
        one_sigma_lo = g.quantile(q = 0.317, interpolation = 'nearest')
        return median, mean, two_sigma_lo, one_sigma_lo, one_sigma_hi, two_sigma_hi
    
    def __sort_data(self, data):
        """
        Helper function to sort MeasurementID
        
        returns:
        @data: dataframe with sorted MeasurementID, where composite depth is sorted numeric not as string
        """
        data[['coreid','compositedepth']] = data['measurementid'].str.split(' ', n = 1, expand = True)
        data = data.astype(dtype = {'compositedepth' : float}).sort_values(by = ['coreid','compositedepth'], ignore_index = True)
        data.drop(['compositedepth','coreid'], axis = 1, inplace = True)
        return data 
    
    def results_agg(self):
        """
        Main function to aggregate data
        
        returns:
        @self.age_model_result_hamstr: dataframe holding the results from the aggregation 
        @self.hamstr_core_results: altered 10,000 iteration results from hamstr with MeasurementID and model name added
        """
        hamstr_core_results = self.hamstr_core_results
        hamstr_core_results.set_index('depth', inplace = True)
        hamstr_core_results.rename_axis('index', inplace = True)
        hamstr_core_results.dropna(axis = 0, inplace = True)
        dttp = self.dttp
        self.age_model_result_hamstr = hamstr_core_results.apply(self.__confidence_intervals, axis = 1, result_type='expand')
        self.age_model_result_hamstr.columns = ['modeloutput_median',
                                           'modeloutput_mean',
                                           'lower_2_sigma',
                                           'lower_1_sigma',
                                           'upper_1_sigma',
                                           'upper_2_sigma']
        self.age_model_result_hamstr = self.age_model_result_hamstr.astype(int)
        self.age_model_result_hamstr = self.age_model_result_hamstr.reset_index()
        self.age_model_result_hamstr = self.age_model_result_hamstr.rename(columns={"index": "measurementid"})
        self.age_model_result_hamstr = self.__sort_data(self.age_model_result_hamstr)
        self.age_model_result_hamstr.insert(7, 'model_name', 'hamstr', True)
        self.age_model_result_hamstr.insert(8, 'preselection', dttp, True)
        ###
        self.hamstr_core_results.reset_index(inplace = True)
        self.hamstr_core_results = self.hamstr_core_results.rename(columns={"index": "measurementid"})
        self.hamstr_core_results = self.__sort_data(self.hamstr_core_results)
        self.hamstr_core_results['model_name'] = 'hamstr'

#### Bacon
class AggDataBacon(object):
    def __init__(self, Bacon_core_results, dttp):
        """
        parameters:
        @self.Bacon_core_results: dataframe with 10,000 iteration results from Bacon
        @self.dttp: value 'Yes' or 'No', if reservoir correction took place
        """
        self.Bacon_core_results = Bacon_core_results
        self.dttp = dttp
    
    def __confidence_intervals(self, g):
        """
        Helper function to get basic statistics (median, mean, 1-sigma range, 2-sigma range)
        
        returns:
        @median: median value of input data
        @mean:  mean value of input data
        @two_sigma_lo: lower boundary value of 2-sigma range of input data
        @one_sigma_lo: lower boundary value of 1-sigma range of input data
        @one_sigma_hi: upper boundary value of 1-sigma range of input data
        @two_sigma_hi: upper boundary value of 2-sigma range of input data
        """
        median = g.median()
        mean = g.mean()
        two_sigma_hi = g.quantile(q = 0.954, interpolation = 'nearest') 
        two_sigma_lo = g.quantile(q = 0.046, interpolation = 'nearest')
        one_sigma_hi = g.quantile(q = 0.683, interpolation = 'nearest') 
        one_sigma_lo = g.quantile(q = 0.317, interpolation = 'nearest')
        return median, mean, two_sigma_lo, one_sigma_lo, one_sigma_hi, two_sigma_hi
    
    def __sort_data(self, data):
        """
        Helper function to sort MeasurementID
        
        returns:
        @data: dataframe with sorted MeasurementID, where composite depth is sorted numeric not as string
        """
        data[['coreid','compositedepth']] = data['measurementid'].str.split(' ', n = 1, expand = True)
        data = data.astype(dtype = {'compositedepth' : float}).sort_values(by = ['coreid','compositedepth'], ignore_index = True)
        data.drop(['compositedepth','coreid'], axis = 1, inplace = True)
        return data 
    
    def results_agg(self):
        """
        Main function to aggregate data
        
        returns:
        @self.age_model_result_Bacon: dataframe holding the results from the aggregation 
        @self.Bacon_core_results: altered 10,000 iteration results from Bacon with MeasurementID and model name added
        """
        Bacon_core_results = self.Bacon_core_results
        Bacon_core_results.set_index('depth', inplace = True)
        Bacon_core_results.rename_axis('index', inplace = True)
        Bacon_core_results.dropna(axis = 0, inplace = True)
        dttp = self.dttp
        self.age_model_result_Bacon = Bacon_core_results.apply(self.__confidence_intervals, axis = 1, result_type='expand')
        self.age_model_result_Bacon.columns = ['modeloutput_median',
                                           'modeloutput_mean',
                                           'lower_2_sigma',
                                           'lower_1_sigma',
                                           'upper_1_sigma',
                                           'upper_2_sigma']
        self.age_model_result_Bacon = self.age_model_result_Bacon.astype(int)
        self.age_model_result_Bacon = self.age_model_result_Bacon.reset_index()
        self.age_model_result_Bacon = self.age_model_result_Bacon.rename(columns={"index": "measurementid"})
        self.age_model_result_Bacon = self.__sort_data(self.age_model_result_Bacon)
        self.age_model_result_Bacon.insert(7, 'model_name', 'Bacon', True)
        self.age_model_result_Bacon.insert(8, 'preselection', dttp, True)
        ###
        self.Bacon_core_results.reset_index(inplace = True)
        self.Bacon_core_results = self.Bacon_core_results.rename(columns={"index": "measurementid"})
        self.Bacon_core_results = self.__sort_data(self.Bacon_core_results)
        self.Bacon_core_results['model_name'] = 'Bacon'       
            
#### Clam
class AggDataClam(object):
    def __init__(self, clam_core_results, dttp):
        """
        parameters:
        @self.clam_core_results: dataframe with 10,000 iteration results from clam
        @self.dttp: value 'Yes' or 'No', if reservoir correction took place
        """
        self.clam_core_results = clam_core_results
        self.dttp = dttp
    
    def __confidence_intervals(self, g):
        """
        Helper function to get basic statistics (median, mean, 1-sigma range, 2-sigma range)
        
        returns:
        @median: median value of input data
        @mean:  mean value of input data
        @two_sigma_lo: lower boundary value of 2-sigma range of input data
        @one_sigma_lo: lower boundary value of 1-sigma range of input data
        @one_sigma_hi: upper boundary value of 1-sigma range of input data
        @two_sigma_hi: upper boundary value of 2-sigma range of input data
        """
        median = g.median()
        mean = g.mean()
        two_sigma_hi = g.quantile(q = 0.954, interpolation = 'nearest') 
        two_sigma_lo = g.quantile(q = 0.046, interpolation = 'nearest')
        one_sigma_hi = g.quantile(q = 0.683, interpolation = 'nearest') 
        one_sigma_lo = g.quantile(q = 0.317, interpolation = 'nearest')
        return median, mean, two_sigma_lo, one_sigma_lo, one_sigma_hi, two_sigma_hi
    
    def results_agg(self):
        """
        Main function to aggregate data
        
        returns:
        @self.age_model_result_clam: dataframe holding the results from the aggregation 
        @self.clam_core_results: altered iterations from clam with MeasurementID and model name added
        """
        clam_core_results = self.clam_core_results
        dttp = self.dttp
        if clam_core_results is None: #### This checks if there are results from clam
            clam_core_results = []
            self.age_model_result_clam = []
            print ('No age data available!')
        else:
            self.age_model_result_clam = clam_core_results.apply(self.__confidence_intervals, axis = 1, result_type='expand')
            self.age_model_result_clam.columns = ['modeloutput_median',
                                               'modeloutput_mean',
                                               'lower_2_sigma',
                                               'lower_1_sigma',
                                               'upper_1_sigma',
                                               'upper_2_sigma']
            self.age_model_result_clam = self.age_model_result_clam.astype(int)
            self.age_model_result_clam = self.age_model_result_clam.reset_index()
            self.age_model_result_clam = self.age_model_result_clam.rename(columns={"index": "measurementid"})
            #### This transforms the clam-specific MeasurementID into it's components
            self.age_model_result_clam[['coreid','depth_model_type']] = self.age_model_result_clam['measurementid'].str.split(' ', n = 1, expand = True)
            self.age_model_result_clam[['depth','model_name']] = self.age_model_result_clam['depth_model_type'].str.split('-', n = 1, expand = True)
            self.age_model_result_clam['model_name'] = self.age_model_result_clam['model_name'].str.replace('_',' ')
            self.age_model_result_clam.insert(8, 'preselection', dttp, True)
            self.age_model_result_clam['measurementid'] = self.age_model_result_clam['coreid'] + ' ' + self.age_model_result_clam['depth']
            self.age_model_result_clam = self.age_model_result_clam.astype(dtype = {'depth' : float}).sort_values(by = ['coreid','depth','model_name'], ignore_index = True)
            self.age_model_result_clam.drop(['coreid','depth','depth_model_type'], axis = 1, inplace = True)
            self.age_model_result_clam.reset_index(drop = True, inplace = True)
            self.age_model_result_clam = self.age_model_result_clam.reindex(['measurementid','modeloutput_median','modeloutput_mean',
                                                                             'lower_2_sigma','lower_1_sigma','upper_1_sigma','upper_2_sigma',
                                                                             'model_name', 'preselection'], axis = 1)
            #### This section checks if there were multiple results from clam
            multiple_entries = {}
            for i, r in self.age_model_result_clam.iterrows():
                if i == 0:
                    pass
                else:
                    if (self.age_model_result_clam.at[(i-1), 'measurementid'].split(' ')[0] == self.age_model_result_clam.at[i, 'measurementid'].split(' ')[0])                     and (self.age_model_result_clam.at[(i-1), 'model_name'] != self.age_model_result_clam.at[i, 'model_name']):
                        multiple_entries_coreid = self.age_model_result_clam.at[i, 'measurementid'].split(' ')[0]
                        multiple_entries[multiple_entries_coreid] = self.age_model_result_clam[self.age_model_result_clam.measurementid.str.contains(multiple_entries_coreid)]
            
            #### If there multiple entries, they are treated as one and statistics will be calculated from all results (10,000+)
            if bool(multiple_entries) == False:
                self.clam_core_results.reset_index(drop = True, inplace = True)
                self.clam_core_results['model_name'] = 'clam'
                self.clam_core_results['measurementid'] = self.age_model_result_clam['measurementid']
            else:
                list_of_keys = [*multiple_entries]
                new_combined_result_list = []
                for key in multiple_entries.keys():
                    combined_results = []
                    for unique_model_name in multiple_entries[key].model_name.unique():
                        combined_results.append(multiple_entries[key][multiple_entries[key].model_name.str.contains(unique_model_name)].reset_index(drop = True))
                    combined_results_df = pd.concat(combined_results, axis = 1)
                    index_results_df = combined_results_df['measurementid'].dropna(axis = 1)
                    index_results_df = index_results_df.loc[:,~index_results_df.columns.duplicated()]['measurementid']
                    combined_results_df = combined_results_df.set_index(index_results_df)
                    combined_results_df.drop(['measurementid','model_name'],axis = 1, inplace = True)
                    new_combined_results = pd.DataFrame(columns = ['measurementid', 'modeloutput_median', 'modeloutput_mean', 'lower_2_sigma',
                       'lower_1_sigma', 'upper_1_sigma', 'upper_2_sigma', 'model_name', 'preselection'])
                    new_combined_results['measurementid'] = index_results_df
                    new_combined_results['model_name'] = 'clam combined'
                    for column in combined_results_df.columns.unique():
                        if column == 'preselection':
                            new_combined_results['preselection'] = combined_results_df['preselection'].dropna(axis = 1).values
                        else:
                            new_combined_results[f'{column}'] = combined_results_df[f'{column}'].mean(axis = 1).values
                    new_combined_result_list.append(new_combined_results)
                new_combined_result_df = pd.concat(new_combined_result_list, axis = 0)
                self.age_model_result_clam = pd.concat([self.age_model_result_clam[~self.age_model_result_clam.measurementid.str.contains('|'.join(list_of_keys))], new_combined_result_df], axis = 0)
                self.age_model_result_clam.reset_index(drop = True, inplace = True)
                ###
                self.clam_core_results.reset_index(inplace = True)
                self.clam_core_results = self.clam_core_results.rename(columns={"index": "measurementid"})
                self.clam_core_results[['coreid','depth_model_type']] = self.clam_core_results['measurementid'].str.split(' ', n = 1, expand = True)
                self.clam_core_results[['depth','model_name']] = self.clam_core_results['depth_model_type'].str.split('-', n = 1, expand = True)
                self.clam_core_results['model_name'] = self.clam_core_results['model_name'].str.replace('_',' ')
                self.clam_core_results['measurementid'] = self.clam_core_results['coreid'] + ' ' + self.clam_core_results['depth']
                self.clam_core_results.drop(['coreid','depth','depth_model_type'], axis = 1, inplace = True)
                new_combined_result_list = []
                for key in multiple_entries.keys():
                    combined_results = []
                    for unique_model_name in multiple_entries[key].model_name.unique():
                        combined_results.append(self.clam_core_results[(self.clam_core_results.measurementid.str.contains(key))&(self.clam_core_results.model_name.str.contains(unique_model_name))].reset_index(drop = True))
                    combined_results_df = pd.concat(combined_results, axis = 1)
                    index_results_df = combined_results_df['measurementid'].dropna(axis = 1)
                    index_results_df = index_results_df.loc[:,~index_results_df.columns.duplicated()]['measurementid']
                    combined_results_df = combined_results_df.set_index(index_results_df)
                    combined_results_df.drop(['measurementid','model_name'],axis = 1, inplace = True) 
                    combined_results_df.columns = [f'V{i}' for i in range(1,len(combined_results_df.columns)+1)]
                    combined_results_df.reset_index(inplace = True)
                    combined_results_df['model_name'] = 'clam combined'
                    new_combined_result_list.append(combined_results_df)
                new_combined_result_df = pd.concat(new_combined_result_list, axis = 0)
                self.clam_core_results = pd.concat([self.clam_core_results[~self.clam_core_results.measurementid.str.contains('|'.join(list_of_keys))], new_combined_result_df], axis = 0)
                self.clam_core_results['model_name'] = 'clam'   

#### Reservoir
class AggDataReservoir(object):
    def __init__(self, results, surface_dates, verbose = 0):
        """
        parameters:
        @self.reservoir_core_results: dataframe with iteration results from quick calculating modeling software for uppermost layer
        @self.surface_dates: dataframe with surfaces dates for each CoreID, which corresponds to expedition year
        @self.verbose: If set to 1, messages will be printed whether an adjustment was not necessary; default value: 0
        """
        self.reservoir_core_results = results
        self.surface_dates = surface_dates
        self.verbose = verbose
    
    def __confidence_intervals(self, g):
        """
        Helper function to get basic statistics (median, mean, 1-sigma range, 2-sigma range)
        
        returns:
        @median: median value of input data
        @mean:  mean value of input data
        @two_sigma_lo: lower boundary value of 2-sigma range of input data
        @one_sigma_lo: lower boundary value of 1-sigma range of input data
        @one_sigma_hi: upper boundary value of 1-sigma range of input data
        @two_sigma_hi: upper boundary value of 2-sigma range of input data
        """
        median = g.median()
        mean = g.mean()
        two_sigma_hi = g.quantile(q = 0.954, interpolation = 'nearest') 
        two_sigma_lo = g.quantile(q = 0.046, interpolation = 'nearest')
        one_sigma_hi = g.quantile(q = 0.683, interpolation = 'nearest') 
        one_sigma_lo = g.quantile(q = 0.317, interpolation = 'nearest')
        return median, mean, two_sigma_lo, one_sigma_lo, one_sigma_hi, two_sigma_hi
    
    def results_agg(self):
        """
        Main function to aggregate data for uppermost layer and compare it to desired target year
        
        returns:
        @self.reservoir_values: dictionary with reservoir value and its error indexed by CoreID 
        """
        #### This section aggregates the iteration results and calculates basic statistics
        reservoir_core_results = self.reservoir_core_results
        verbose = self.verbose
        surface_dates = self.surface_dates
        reservoir_core_results.set_index('depth', inplace = True)
        reservoir_core_results.rename_axis('index', inplace = True)
        reservoir_core_results.dropna(axis = 0, inplace = True)
        self.age_model_result_reservoir = reservoir_core_results.apply(self.__confidence_intervals, axis = 1, result_type='expand')
        self.age_model_result_reservoir.columns = ['modeloutput_median',
                                           'modeloutput_mean',
                                           'lower_2_sigma',
                                           'lower_1_sigma',
                                           'upper_1_sigma',
                                           'upper_2_sigma']
        self.age_model_result_reservoir = self.age_model_result_reservoir.astype(int)
        self.age_model_result_reservoir = self.age_model_result_reservoir.reset_index()
        self.age_model_result_reservoir = self.age_model_result_reservoir.rename(columns={"index": "measurementid"})
        self.age_model_result_reservoir.insert(7, 'model_name', 'ReservoirCalculation', True)
        ####
        surface_comparison = surface_dates.merge(self.age_model_result_reservoir, on = ['measurementid'])
        surface_comparison = surface_comparison.astype(dtype = {'age': int,
                                                                'modeloutput_median': int,
                                                                'lower_2_sigma': int,
                                                                'upper_2_sigma': int})
        #### Compare calculated statistics with desired values and calculates the possible reservoir value
        self.reservoir_values = {}
        for i,r in surface_comparison.iterrows():
            if surface_comparison.at[i, 'modeloutput_mean'] <= surface_comparison.at[i, 'age']:
                if verbose == 1:
                    print(f"No adjustment needed for {surface_comparison.at[i, 'coreid']}")
                else:
                    pass
            elif surface_comparison.at[i, 'lower_2_sigma'] <= surface_comparison.at[i, 'age']:
                if verbose == 1:
                    print(f"No adjustment needed for {surface_comparison.at[i, 'coreid']}")
                else:
                    pass
            elif (surface_comparison.at[i, 'lower_2_sigma']/surface_comparison.at[i, 'age']) > 0.1:
                if verbose == 1:
                    print(f"No adjustment needed for {surface_comparison.at[i, 'coreid']}")
                else:
                    pass
            else:
                R_age_value = surface_comparison.at[i, 'age'] + surface_comparison.at[i, 'modeloutput_mean']
                left_error = surface_comparison.at[i,'modeloutput_mean'] - surface_comparison.at[i,'lower_2_sigma']
                right_error = surface_comparison.at[i,'upper_2_sigma'] - surface_comparison.at[i,'modeloutput_mean']
                if left_error == right_error:
                    R_error_value = left_error
                elif left_error > right_error:
                    R_error_value = left_error
                else:
                    R_error_value = right_error
                self.reservoir_values[surface_comparison.at[i, 'coreid']] = [R_age_value, R_error_value]
                print(f"Reservoir value of {R_age_value} years and an error of {R_error_value} years was calculated for {surface_comparison.at[i, 'coreid']} ")
        
    def add_reservoir(self, all_ages, which = None):
        """
        Main function to either add reservoir values to all data points, to only bulk samples or disregard the results 
        
        parameters:
        @self.all_ages: dataframe with all age determination data
        @self.which: string either 'all' (for 'all samples'), 'bulk' (for 'only bulk samples'), or 'without' ('if no reservoir values should be added'); default value: None
        
        returns:
        @self.all_ages: altered dataframe with all age determiantion data plus added reservoir values
        """
        self.all_ages = all_ages
        if self.reservoir_values:
            if which is None:
                self.which = input("Would you like to add the reservoir values to all samples ('all'), to only bulk samples ('bulk'), or disregard the values ('without')? ")
            ####
            if self.which == 'all':
                for key in self.reservoir_values.keys():
                    for i, r in self.all_ages.iterrows():
                        if (self.all_ages.at[i, 'coreid'] == key) and ('14C' in self.all_ages.at[i, 'material_category']):
                            self.all_ages.at[i, 'reservoir_age'] = float(self.all_ages.at[i, 'reservoir_age']) + float(self.reservoir_values[key][0])
                            self.all_ages.at[i, 'reservoir_error'] = float(self.all_ages.at[i, 'reservoir_error']) + float(self.reservoir_values[key][1])
                    self.dttp = 'Yes' ## Needs to be more sophisticated for multiple sediment cores, to answer which core had a transformation
                if bool(self.reservoir_values) == False:
                    self.dttp = 'No' 
            elif self.which == 'bulk':
                for key in self.reservoir_values.keys():
                    for i, r in self.all_ages.iterrows():
                        if (self.all_ages.at[i, 'coreid'] == key) and ('14C sediment' in self.all_ages.at[i, 'material_category']):
                            self.all_ages.at[i, 'reservoir_age'] = float(self.all_ages.at[i, 'reservoir_age']) + float(self.reservoir_values[key][0])
                            self.all_ages.at[i, 'reservoir_error'] = float(self.all_ages.at[i, 'reservoir_error']) + float(self.reservoir_values[key][1])
                    self.dttp = 'Yes' ## Needs to be more sophisticated for multiple sediment cores, to answer which core had a transformation
                if bool(self.reservoir_values) == False:
                    self.dttp = 'No' 
            else:
                self.dttp = 'No' 
        else:
            self.dttp = 'No' 
        ### Check for logic, if age and reservoir effect are smaller than current date - this is important for Bchron
        for i, r in self.all_ages.iterrows():
            if ((float(self.all_ages.at[i, 'age']) - float(self.all_ages.at[i, 'reservoir_age'])) < (1950 - datetime.datetime.now().year)) and (self.all_ages.at[i,'compositedepth'] <= 1):
                self.all_ages.at[i, 'reservoir_age'] = float(self.all_ages.at[i, 'age']) - float(self.all_ages[(self.all_ages.coreid == self.all_ages.at[i, 'coreid'])&(self.all_ages.labid.str.contains('_Surface'))]['age'])
                self.all_ages.at[i, 'reservoir_error'] = 0
            elif ((float(self.all_ages.at[i, 'age']) - float(self.all_ages.at[i, 'reservoir_age'])) < (1950 - datetime.datetime.now().year)) and (self.all_ages.at[i,'compositedepth'] > 1):
                self.all_ages.at[i, 'reservoir_age'] = 0
                self.all_ages.at[i, 'reservoir_error'] = 0
            else:
                pass
            
        return self.all_ages
