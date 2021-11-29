#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module to calculate sedimentation rate from the results of age-depth modeling process

Author: Gregor Pfalz
github: GPawi
"""

import numpy as np
import pandas as pd
import os
import dask
import dask.distributed
from dask.distributed import Client , LocalCluster
import joblib
import multiprocessing
dask.config.set({"distributed.comm.timeouts.tcp": "90s"})


class CalculateSediRate(object):
    def __init__(self, agg, model, coreid, mode):
        """
        parameters:
        @self.agg: object containing the results from the aggregation function
        @self.coreids: list of CoreIDs used within the LANDO environment
        @self.mode: string of mode that should be used for sedimentation rate calculation; options are 'naive',
        'move_three', and 'move_five' 
        @self.model: string of name of model that the aggregation object is coming from
        @self.core_results: model-specific 10,000 iteration results with MeasurementID and model name added
        """
        self.agg = agg
        self.coreid = coreid
        self.mode = mode
        self.model = model
        if self.model == 'Undatable':
            self.core_results = agg.Undatable_core_results
        elif self.model == 'Bchron':
            self.core_results = agg.Bchron_core_results
        elif self.model == 'hamstr':
            self.core_results = agg.hamstr_core_results
        elif self.model == 'Bacon':
            self.core_results = agg.Bacon_core_results
        elif self.model == 'OxCal':
            self.core_results = agg.OxCal_core_results
        elif self.model == 'clam':
            self.core_results = agg.clam_core_results        
        else: 
            raise Exception(f'Please specify the model that you are using')
    
    def __prep_for_par(self, data):
        """
        Helper function to prepare dataframe to work in parallel
        
        returns:
        @data: dataframe sorted by MeasurementID, where composite depth is sorted numeric not as string
        and index set to multiindex consisting of MeasurementID, model name and CoreID
        """
        data[['coreid','compositedepth']] = data['measurementid'].str.split(' ', n = 1, expand = True)
        data = data.astype(dtype = {'compositedepth' : float}).sort_values(by = ['coreid', 'compositedepth'], ignore_index = True)
        data.drop(['compositedepth'], axis = 1, inplace = True)
        data = data.set_index(['measurementid','model_name','coreid'])
        return data    

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
    
    def __sed_rate(self, core_results, mode):
        """
        Helper function to calculate sedimentation rate based on the mode selected
        
        parameters:
        @core_results: model-specific 10,000 iteration results with MeasurementID and model name added
        @mode: string of mode that should be used for sedimentation rate calculation; options are 'naive',
        'move_three', and 'move_five' 
        
        returns:
        @sed_frame: numpy array with 10,000 results from the sedimentation rate calculation
        """
        ages = core_results.copy()
        core_results.reset_index(inplace = True)
        #####
        sed_frame = pd.DataFrame()
        sedimentation_rate = []
        for i in range(len(ages)):       
            try:        
                if mode == 'naive':          ## ('naive') - Naive approach: sedimentation rate(x) = (depth(x)-depth(x-1)) / (age(x)-age(x-1))
                    sedimentation_step = pd.DataFrame(np.asarray([1/(ages.iloc[i+1] - ages.iloc[i])], dtype = np.float64))
                    if sedimentation_step.mean().min() < 0:
                        sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                    sed_frame = pd.concat([sed_frame,sedimentation_step])
        
                elif mode == 'move_three':   ## ('move_three') - Moving average over three depths: sedimentation rate(x) = (depth(x+1)-depth(x-1)) / (age(x+1)-age(x-1))
                    sedimentation_step = pd.DataFrame(np.asarray([2/(ages.iloc[i+1] - ages.iloc[i-1])], dtype = np.float64))
                    if sedimentation_step.mean().min() < 0:
                        sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                    sed_frame = pd.concat([sed_frame,sedimentation_step])
    
                elif mode == 'move_five':    ## ('move_five') - Moving average over five depths: sedimentation rate(x) = (depth(x+2)-depth(x-2)) / (age(x+2)-age(x-2))
                    sedimentation_step = pd.DataFrame(np.asarray([4/(ages.iloc[i+2] - ages.iloc[i-2])], dtype = np.float64))
                    if sedimentation_step.mean().min() < 0:
                        sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                    sed_frame = pd.concat([sed_frame,sedimentation_step])
                
                else: 
                    sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                    sed_frame = pd.concat([sed_frame,sedimentation_step])
    
            except:
                sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                sed_frame = pd.concat([sed_frame,sedimentation_step])
        ####
        sed_frame.reset_index(drop = True, inplace = True)
        sed_frame.replace([np.inf, -np.inf], 0, inplace=True)
        sed_frame = sed_frame.apply(self.__confidence_intervals, axis = 1, result_type='expand')
        sed_frame[['measurementid','model_name']] = core_results[['measurementid','model_name']]
        sed_frame['SR_mode'] = mode
        
        return sed_frame.to_numpy()
    
    def __split_list(self, original_list):
        """
        Helper function to split list of CoreID into two lists
        
        returns:
        two lists containing the original list split by its half
        """
        half = len(original_list)//2
        return original_list[:half], original_list[half:]

    
    def __SR_multi(self):
        """
        Helper function to calculate sedimentation rates in parallel for multiple sediment cores
        
        returns:
        @Out_p: dataframe containing the summarizing statistics from the sedimentation rate calculation for multiple cores
        """
        core_results = self.core_results
        coreid = self.coreid
        mode = self.mode
        ###
        par_df = self.__prep_for_par(core_results)
        ###
        with LocalCluster(scheduler_port = 0) as cluster, Client(cluster, timeout="90s") as client:
            try:
                #### This section splits calculation into two parts, if number of sediment cores is bigger than twice the available number of threads
                if len(coreid) > 2*multiprocessing.cpu_count(): 
                    coreid_split_1, coreid_split_2 = self.__split_list(coreid)
                    ###
                    par_df_1 = par_df[par_df.index.get_level_values('coreid').isin(coreid_split_1)]
                    par_df_2 = par_df[par_df.index.get_level_values('coreid').isin(coreid_split_2)]
                    ###
                    print(f'Calculating first batch with {len(coreid_split_1)} sediment cores')
                    with joblib.parallel_backend('dask'):
                        self.out1 = joblib.Parallel(n_jobs = -1, verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df_1[par_df_1.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid_split_1)
                    print(f'Calculating second batch with {len(coreid_split_2)} sediment cores')
                    with joblib.parallel_backend('dask'):
                        self.out2 = joblib.Parallel(n_jobs = -1, verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df_2[par_df_2.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid_split_2)
                    ###
                    self.out = self.out1 + self.out2
                
                #### This section splits calculation into four parts, if number of sediment cores is bigger than four times the available number of threads    
                elif len(coreid) > 4*multiprocessing.cpu_count():
                    split_A, split_B = self.__split_list(coreid)
                    coreid_split_1, coreid_split_2 = self.__split_list(split_A)
                    coreid_split_3, coreid_split_4 = self.__split_list(split_B)
                    ###
                    par_df_1 = par_df[par_df.index.get_level_values('coreid').isin(coreid_split_1)]
                    par_df_2 = par_df[par_df.index.get_level_values('coreid').isin(coreid_split_2)]
                    par_df_3 = par_df[par_df.index.get_level_values('coreid').isin(coreid_split_3)]
                    par_df_4 = par_df[par_df.index.get_level_values('coreid').isin(coreid_split_4)]
                    ###
                    print(f'Calculating first batch with {len(coreid_split_1)} sediment cores')
                    with joblib.parallel_backend('dask'):
                        self.out1 = joblib.Parallel(n_jobs = -1, verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df_1[par_df_1.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid_split_1)
                    print(f'Calculating second batch with {len(coreid_split_2)} sediment cores')
                    with joblib.parallel_backend('dask'):
                        self.out2 = joblib.Parallel(n_jobs = -1, verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df_2[par_df_2.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid_split_2)
                    print(f'Calculating third batch with {len(coreid_split_2)} sediment cores')     
                    with joblib.parallel_backend('dask'):
                        self.out3 = joblib.Parallel(n_jobs = -1, verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df_3[par_df_3.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid_split_3)
                    print(f'Calculating fourth batch with {len(coreid_split_4)} sediment cores')
                    with joblib.parallel_backend('dask'):
                        self.out4 = joblib.Parallel(n_jobs = -1, verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df_4[par_df_4.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid_split_4)
                    ###
                    self.out = self.out1 + self.out2 + self.out3 + self.out4
                
                else:
                    with joblib.parallel_backend('dask'):
                        self.out = joblib.Parallel(verbose=100)(
                            joblib.delayed(sed_rate_multi)(par_df[par_df.index.get_level_values('coreid') == i].dropna(axis = 1), mode = mode)
                            for i in coreid)
            except: 
                print('Caught an error - restart jupyter notebook!')
                self.out = []
        ###
        if not self.out:
            Out_p = []
        else:
            Out_p = pd.DataFrame()
            for i in range(len(self.out)):
                partial = pd.DataFrame(self.out[i])
                Out_p = pd.concat([Out_p,partial], ignore_index = True)
            Out_p.columns = ['SR_median',
                             'SR_mean',
                             'SR_lower_2_sigma',
                             'SR_lower_1_sigma',
                             'SR_upper_1_sigma',
                             'SR_upper_2_sigma',
                             'measurementid',
                             'model_name',
                             'SR_mode']
        return Out_p

    
    def calculating_SR(self):
        """
        Main function that calls helper functions and creates variable based on model name for summarized statistics of sedimentation rate
        
        returns:
        @self.SR_model_result_{self.model}: dataframe containing the summarizing statistics from the sedimentation rate calculation
        """
        coreid = self.coreid
        core_results = self.core_results
        mode = self.mode
        if core_results is None:
            Out_p = []
            print ('No sedimentation rate data available!')
        else:
            if len(coreid) > 1:
                Out_p = self.__SR_multi()
            else:
                Out_p = pd.DataFrame(self.__sed_rate(self.__prep_for_par(core_results), mode), columns = ['SR_median',
                                                                                                         'SR_mean',
                                                                                                         'SR_lower_2_sigma',
                                                                                                         'SR_lower_1_sigma',
                                                                                                         'SR_upper_1_sigma',
                                                                                                         'SR_upper_2_sigma',
                                                                                                         'measurementid',
                                                                                                         'model_name',
                                                                                                         'SR_mode'])
        if self.model == 'Undatable':
            self.SR_model_result_Undatable = Out_p
        elif self.model == 'Bchron':
            self.SR_model_result_Bchron = Out_p
        elif self.model == 'hamstr':
            self.SR_model_result_hamstr = Out_p
        elif self.model == 'Bacon':
            self.SR_model_result_Bacon = Out_p
        elif self.model == 'OxCal':
            self.SR_model_result_OxCal = Out_p
        elif self.model == 'clam':
            self.SR_model_result_clam = Out_p       
        else: 
            raise Exception(f'Please specify the model that you are using')  
            
def sed_rate_multi(core_results, mode):
    """
    Helper function to work with dask to calculate sedimentation rate based on the mode selected
    
    parameters:
    @core_results: model-specific 10,000 iteration results with MeasurementID and model name added
    @mode: string of mode that should be used for sedimentation rate calculation; options are 'naive',
    'move_three', and 'move_five' 
    
    returns:
    @sed_frame: numpy array with 10,000 results from the sedimentation rate calculation
    """
    ages = core_results.copy()
    core_results.reset_index(inplace = True)
    #####
    sed_frame = pd.DataFrame()
    sedimentation_rate = []
    for i in range(len(ages)):       
        try:        
            if mode == 'naive':          ## ('naive') - Naive approach: sedimentation rate(x) = (depth(x)-depth(x-1)) / (age(x)-age(x-1))
                sedimentation_step = pd.DataFrame(np.asarray([1/(ages.iloc[i+1] - ages.iloc[i])], dtype = np.float64))
                if sedimentation_step.mean().min() < 0:
                    sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                sed_frame = pd.concat([sed_frame,sedimentation_step])
    
            elif mode == 'move_three':   ## ('move_three') - Moving average over three depths: sedimentation rate(x) = (depth(x+1)-depth(x-1)) / (age(x+1)-age(x-1))
                sedimentation_step = pd.DataFrame(np.asarray([2/(ages.iloc[i+1] - ages.iloc[i-1])], dtype = np.float64))
                if sedimentation_step.mean().min() < 0:
                    sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                sed_frame = pd.concat([sed_frame,sedimentation_step])
    
            elif mode == 'move_five':    ## ('move_five') - Moving average over five depths: sedimentation rate(x) = (depth(x+2)-depth(x-2)) / (age(x+2)-age(x-2))
                sedimentation_step = pd.DataFrame(np.asarray([4/(ages.iloc[i+2] - ages.iloc[i-2])], dtype = np.float64))
                if sedimentation_step.mean().min() < 0:
                    sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                sed_frame = pd.concat([sed_frame,sedimentation_step])
            
            else: 
                sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
                sed_frame = pd.concat([sed_frame,sedimentation_step])
    
        except:
            sedimentation_step = pd.DataFrame(np.asarray([[0] * len(ages.columns)], dtype = np.float64))
            sed_frame = pd.concat([sed_frame,sedimentation_step])
    ####
    sed_frame.reset_index(drop = True, inplace = True)
    sed_frame.replace([np.inf, -np.inf], 0, inplace=True)
    sed_frame = sed_frame.apply(confidence_intervals_multi, axis = 1, result_type='expand')
    sed_frame[['measurementid','model_name']] = core_results[['measurementid','model_name']]
    sed_frame['SR_mode'] = mode
    
    return sed_frame.to_numpy()

def confidence_intervals_multi( g):
    """
    Helper function to work with dask to get basic statistics (median, mean, 1-sigma range, 2-sigma range)
    
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
