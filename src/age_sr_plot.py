#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module within LANDO to plot data of age-depth model results

Author: Gregor Pfalz
github: GPawi
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.legend_handler import HandlerBase
from matplotlib.text import Text
import seaborn as sns
import os
import datetime
import copy
import math

class PlotAgeSR(object):
    def __init__(self, plot_data, coreid, dttp):
        """
        parameters:
        @self.model_plot_data: dictionary with aggregated age and sedimentation rate results indexed by modeling software
        @self.coreid: list of CoreIDs used within the LANDO environmen
        @self.dttp: value 'Yes' or 'No', if reservoir correction took place
        """
        self.model_plot_data = copy.deepcopy(plot_data)
        self.coreid = coreid
        self.dttp = dttp
        
    def __prep_for_plot(self, data, input_type = 'SR'):
        """
        Helper function to split MeasurementID into CoreID and composite depth and 
        ensuring the correct data type is assigned to each column
        
        returns:
        @data: dataframe with new columns 'coreid' and 'compositedepth', sorted by both columns 
        and assigning float as column type for numeric columns
        """
        data[['coreid','compositedepth']] = data['measurementid'].str.split(' ', n = 1, expand = True)
        if input_type == 'age':
            data = data.astype(dtype = {'compositedepth': float,
                                        'modeloutput_mean': float,
                                        'modeloutput_median': float,
                                        'lower_1_sigma': float,
                                        'upper_1_sigma': float,
                                        'lower_2_sigma': float,
                                        'upper_2_sigma': float})
        else: 
            data = data.astype(dtype = {'compositedepth': float,
                                        'SR_median': float,
                                        'SR_mean': float,
                                        'SR_lower_2_sigma': float,
                                        'SR_lower_1_sigma': float,
                                        'SR_upper_1_sigma': float,
                                        'SR_upper_2_sigma': float})
            
        data = data.sort_values(by = ['coreid','compositedepth'], ignore_index = True)
        
        return data
    
    def __frame_prep(self):
        """
        Function to move data from self.model_plot_data dictionary into lists to allowing plotting the data 
        
        returns:
        @self.age_data: list with all age-depth models results
        @self.SR_data: list with all sedimentation rate results
        @self.calib_dates: calibrated age determination data will be moved into its own variable
        @self.model_name_list: list with model names without extra specification (this is important, 
        especially if clam is used)
        """
        model_plot_data = self.model_plot_data
        self.age_data = []
        self.SR_data = []
        ###
        for key in model_plot_data.keys():
            if key == 'Undatable':
                self.Un_Age_data = self.__prep_for_plot(model_plot_data.get(key)[0], 'age')
                self.Un_SR_data = self.__prep_for_plot(model_plot_data.get(key)[1], 'SR')
                self.Un_SR_data.replace(0, np.nan, inplace = True)
                self.Un_SR_data['compositedepth'] = self.Un_SR_data['compositedepth'].replace(np.nan, 0)
                if len(self.coreid) == 1:
                    self.Un_Age_data = self.Un_Age_data[self.Un_Age_data.coreid.str.contains(self.coreid[0])]
                    self.Un_SR_data = self.Un_SR_data[self.Un_SR_data.coreid.str.contains(self.coreid[0])]
                self.age_data.append(self.Un_Age_data)
                self.SR_data.append(self.Un_SR_data)
            elif key == 'Bchron':
                self.Bc_Age_data = self.__prep_for_plot(model_plot_data.get(key)[0], 'age')
                self.Bc_SR_data = self.__prep_for_plot(model_plot_data.get(key)[1], 'SR')
                self.Bc_SR_data.replace(0, np.nan, inplace = True)
                self.Bc_SR_data['compositedepth'] = self.Bc_SR_data['compositedepth'].replace(np.nan, 0)
                if len(self.coreid) == 1:
                    self.Bc_Age_data = self.Bc_Age_data[self.Bc_Age_data.coreid.str.contains(self.coreid[0])]
                    self.Bc_SR_data = self.Bc_SR_data[self.Bc_SR_data.coreid.str.contains(self.coreid[0])]
                self.age_data.append(self.Bc_Age_data)
                self.SR_data.append(self.Bc_SR_data)
            elif key == 'hamstr':
                self.ha_Age_data = self.__prep_for_plot(model_plot_data.get(key)[0], 'age')
                self.ha_SR_data = self.__prep_for_plot(model_plot_data.get(key)[1], 'SR')
                self.ha_SR_data.replace(0, np.nan, inplace = True)
                self.ha_SR_data['compositedepth'] = self.ha_SR_data['compositedepth'].replace(np.nan, 0)
                if len(self.coreid) == 1:
                    self.ha_Age_data = self.ha_Age_data[self.ha_Age_data.coreid.str.contains(self.coreid[0])]
                    self.ha_SR_data = self.ha_SR_data[self.ha_SR_data.coreid.str.contains(self.coreid[0])]
                self.age_data.append(self.ha_Age_data)
                self.SR_data.append(self.ha_SR_data)
            elif key == 'Bacon':
                self.Ba_Age_data = self.__prep_for_plot(model_plot_data.get(key)[0], 'age')
                self.Ba_SR_data = self.__prep_for_plot(model_plot_data.get(key)[1], 'SR')
                self.Ba_SR_data.replace(0, np.nan, inplace = True)
                self.Ba_SR_data['compositedepth'] = self.Ba_SR_data['compositedepth'].replace(np.nan, 0)
                if len(self.coreid) == 1:
                    self.Ba_Age_data = self.Ba_Age_data[self.Ba_Age_data.coreid.str.contains(self.coreid[0])]
                    self.Ba_SR_data = self.Ba_SR_data[self.Ba_SR_data.coreid.str.contains(self.coreid[0])]
                self.age_data.append(self.Ba_Age_data)
                self.SR_data.append(self.Ba_SR_data)
            elif key == 'OxCal':
                self.Ox_Age_data = self.__prep_for_plot(model_plot_data.get(key)[0], 'age')
                self.Ox_SR_data = self.__prep_for_plot(model_plot_data.get(key)[1], 'SR')
                self.Ox_SR_data.replace(0, np.nan, inplace = True)
                self.Ox_SR_data['compositedepth'] = self.Ox_SR_data['compositedepth'].replace(np.nan, 0)
                if len(self.coreid) == 1:
                    self.Ox_Age_data = self.Ox_Age_data[self.Ox_Age_data.coreid.str.contains(self.coreid[0])]
                    self.Ox_SR_data = self.Ox_SR_data[self.Ox_SR_data.coreid.str.contains(self.coreid[0])]
                self.age_data.append(self.Ox_Age_data)
                self.SR_data.append(self.Ox_SR_data)
            elif key == 'clam':
                if not all(model_plot_data.get(key)[0]) == True: # in case, no suitable model was found for clam
                    print ('Note: clam cannot be added to plot')
                elif type(model_plot_data.get(key)[0]) == list: # in case, no suitable model was found for clam
                    print ('Note: clam cannot be added to plot')
                elif model_plot_data.get(key)[0].empty == True:
                    print ('Note: clam cannot be added to plot')
                else:
                    self.cl_Age_data = self.__prep_for_plot(model_plot_data.get(key)[0], 'age')
                    self.cl_SR_data = self.__prep_for_plot(model_plot_data.get(key)[1], 'SR')
                    self.cl_Age_data['model_name'] = self.cl_Age_data['model_name'].str.replace('T', 'Type ')
                    self.cl_Age_data['model_name'] = self.cl_Age_data['model_name'].str.replace('S', 'Smooth 0.')
                    self.cl_SR_data.replace(0, np.nan, inplace = True)
                    self.cl_SR_data['compositedepth'] = self.cl_SR_data['compositedepth'].replace(np.nan, 0)
                    if len(self.coreid) == 1:
                        self.cl_Age_data = self.cl_Age_data[self.cl_Age_data.coreid.str.contains(self.coreid[0])]
                        self.cl_SR_data = self.cl_SR_data[self.cl_SR_data.coreid.str.contains(self.coreid[0])]
                        if self.cl_Age_data.empty == True or self.cl_SR_data.empty == True:
                            continue
                    self.age_data.append(self.cl_Age_data)
                    self.SR_data.append(self.cl_SR_data)
            elif key == 'calib_dates':
                self.calib_dates = model_plot_data.get(key)
                self.calib_dates[['coreid','compositedepth']] = self.calib_dates['id'].str.split(' ', n = 1, expand = True)
                self.calib_dates['compositedepth'] = self.calib_dates['compositedepth'].astype(np.float32)
                if len(self.coreid) == 1:
                    self.calib_dates = self.calib_dates[self.calib_dates.coreid.str.contains(self.coreid[0])]
            else:
                raise Exception(f'There is an error in the model name')
        
        self.model_name_list = [self.age_data[x].model_name.unique()[0].split(' ')[0] for x in range(len(self.age_data))]
            
                
    def __combine_age_df(self):
        """
        Function to combine both the age-depth results from age-depth modeling software as well as the results from
        sedimentation rate calculation from all age-depth modeling software into one semi-informed model
        
        returns:
        @self.age_SR_core_dict: dictionary containing the combined models (age-depth and sedimentation rate) 
        indexed by the individual CoreID
        @self.combine_age_df: main dataframe holding the combined age-depth models from all models for all sediment
        cores
        @self.combine_SR_df: main dataframe holding the combined sedimentation rates from all models for all
        sediment cores
        """
        model_plot_data = self.model_plot_data
        self.age_SR_core_dict = {}
        for core in self.coreid:
            combine_age = []
            combine_SR = []
            for key in model_plot_data.keys():
                if key == 'calib_dates':
                    pass
                elif type(model_plot_data.get(key)[0]) == list:
                    pass
                elif model_plot_data.get(key)[0].empty == True:
                    pass
                elif core not in model_plot_data[key][0]['coreid'].unique():
                    continue                
                else:
                    if self.sigma_range == '1sigma':
                        age_core_selection = model_plot_data[key][0][model_plot_data[key][0].coreid.str.contains(core)]
                        sedi_core_selection = model_plot_data[key][1][model_plot_data[key][1].coreid.str.contains(core)]
                        combine_age.append(age_core_selection.astype(dtype = {'compositedepth': float})                                      .sort_values(by = ['coreid','compositedepth'], ignore_index = True)                                      [['measurementid','modeloutput_mean','lower_1_sigma','upper_1_sigma']]                                      .rename({'modeloutput_mean': f'{key}_mean', 'lower_1_sigma': f'{key}_l_1_sigma', 'upper_1_sigma': f'{key}_u_1_sigma'}, axis='columns'))
                        combine_SR.append(sedi_core_selection.astype(dtype = {'compositedepth': float})                                           .sort_values(by = ['coreid','compositedepth'], ignore_index = True)                                           [['measurementid','SR_mean', 'SR_lower_1_sigma','SR_upper_1_sigma']]                                           .rename({'SR_mean': f'{key}_SR_mean', 'SR_lower_1_sigma': f'{key}_SR_l_1_sigma', 'SR_upper_1_sigma': f'{key}_SR_u_1_sigma'}, axis='columns'))
                    else:
                        age_core_selection = model_plot_data[key][0][model_plot_data[key][0].coreid.str.contains(core)]
                        sedi_core_selection = model_plot_data[key][1][model_plot_data[key][1].coreid.str.contains(core)]
                        combine_age.append(age_core_selection.astype(dtype = {'compositedepth': float})                                      .sort_values(by = ['coreid','compositedepth'], ignore_index = True)                                      [['measurementid','modeloutput_mean','lower_2_sigma','upper_2_sigma']]                                      .rename({'modeloutput_mean': f'{key}_mean', 'lower_2_sigma': f'{key}_l_2_sigma', 'upper_2_sigma': f'{key}_u_2_sigma'}, axis='columns'))
                        combine_SR.append(sedi_core_selection.astype(dtype = {'compositedepth': float})                                           .sort_values(by = ['coreid','compositedepth'], ignore_index = True)                                           [['measurementid','SR_mean', 'SR_lower_2_sigma','SR_upper_2_sigma']]                                           .rename({'SR_mean': f'{key}_SR_mean', 'SR_lower_2_sigma': f'{key}_SR_l_2_sigma', 'SR_upper_2_sigma': f'{key}_SR_u_2_sigma'}, axis='columns'))
            
            #### This is to check if there are results for the CoreID, otherwise this core will be skipped
            if not combine_age:
                continue
            #### This section combines all age-depth model results and finds the maximum and minimum age 
            #### as well as the weighted mean age and adds each result per sediment core to the dictionary
            combine_age_df = pd.concat(combine_age, axis = 1)
            index_age_df = pd.DataFrame(combine_age_df['measurementid']).dropna(axis = 1)
            index_age_df = index_age_df.loc[:,~index_age_df.columns.duplicated()]['measurementid']
            combine_age_df = combine_age_df.set_index(index_age_df)
            combine_age_df.drop('measurementid',axis = 1, inplace = True)
            all_age_mean_core = combine_age_df.filter(regex='mean')
            self.weighted_mean_core_age = []
            for i in range(len(all_age_mean_core)):
                self.weighted_mean_core_age.append(sum(all_age_mean_core.iloc[i,:].dropna()*(1/len(all_age_mean_core.iloc[i,:].dropna()))))
            combine_age_df['Max_age'] = combine_age_df.max(axis=1)
            combine_age_df['Min_age'] = combine_age_df.min(axis=1)
            combine_age_df.reset_index(inplace = True)
            combine_age_df = combine_age_df[['measurementid','Max_age','Min_age']].copy()
            combine_age_df['Weighted_mean_age'] = self.weighted_mean_core_age
            combine_age_df[['coreid','compositedepth']] = combine_age_df['measurementid'].str.split(' ', n = 1, expand = True)
            combine_age_df['compositedepth'] = combine_age_df['compositedepth'].astype(np.float32)
            self.age_SR_core_dict.setdefault(core,[]).append(combine_age_df)
            
            #### This section combines all results the sedimentation rate (SR) calculation and finds 
            #### the maximum and minimum SR as well as the weighted mean SR and adds each result per 
            #### sediment core to the dictionary - this might be redundant and could be fit into one function later
            combine_SR_df = pd.concat(combine_SR, axis = 1)
            combine_SR_df.replace(0, np.nan, inplace = True)
            index_SR_df = pd.DataFrame(combine_SR_df['measurementid']).dropna(axis = 1)
            index_SR_df = index_SR_df.loc[:,~index_SR_df.columns.duplicated()]['measurementid']
            combine_SR_df = combine_SR_df.set_index(index_SR_df)
            combine_SR_df.drop('measurementid',axis = 1, inplace = True)
            all_SR_mean_core = combine_SR_df.filter(regex='mean')
            self.weighted_mean_core_SR = []
            for i in range(len(all_SR_mean_core)):
                if len(all_SR_mean_core.iloc[i,:].dropna()) > 1:
                    self.weighted_mean_core_SR.append(sum(all_SR_mean_core.iloc[i,:].dropna()*(1/len(all_SR_mean_core.iloc[i,:].dropna()))))
                elif len(all_SR_mean_core.iloc[i,:].dropna()) == 1:
                    self.weighted_mean_core_SR.append(sum(all_SR_mean_core.iloc[i,:].dropna()))
                else:
                    self.weighted_mean_core_SR.append(np.nan)
            mean_cols = [col for col in combine_SR_df.columns if 'mean' in col]
            combine_SR_df = combine_SR_df[combine_SR_df.columns.drop(mean_cols)]
            combine_SR_df['Max_SR'] = combine_SR_df.max(axis=1)
            combine_SR_df['Min_SR'] = combine_SR_df.min(axis=1)
            combine_SR_df.reset_index(inplace = True)
            combine_SR_df = combine_SR_df[['measurementid','Max_SR','Min_SR']].copy()
            combine_SR_df['Weighted_mean_SR'] = self.weighted_mean_core_SR
            combine_SR_df[['coreid','compositedepth']] = combine_SR_df['measurementid'].str.split(' ', n = 1, expand = True)
            combine_SR_df['compositedepth'] = combine_SR_df['compositedepth'].astype(np.float32)
            self.age_SR_core_dict.setdefault(core,[]).append(combine_SR_df)
        
        #### All results from the dictionary are now added to the two main return dataframes
        self.combine_age_df = pd.DataFrame(columns = combine_age_df.columns)
        self.combine_SR_df = pd.DataFrame(columns = combine_SR_df.columns)
        for key in self.age_SR_core_dict.keys():
            self.combine_age_df = pd.concat([self.combine_age_df, self.age_SR_core_dict[key][0]], ignore_index=True)
            self.combine_SR_df = pd.concat([self.combine_SR_df, self.age_SR_core_dict[key][1]], ignore_index=True)
        self.combine_age_df = self.combine_age_df.astype(dtype = {'Max_age' : float,
                                                                  'Min_age' : float,
                                                                  'Weighted_mean_age' : float})
        
    def __SR_median_age(self):
        """
        Function to combine the median age with the median sedimentation rate per sediment core
        
        returns:
        @self.dict_SR_median_age: unbinned sedimentation rates against median age per sediment core 
        and per modeling software 
        @self.dict_binned_SR_median_age: binned sedimentation rates against median age per sediment core 
        and per modeling software
        @self.combine_SR_median_age: binned combined sedimentation rates against median age 
        from all modeling software per sediment core
        """
        if len(self.coreid) == 1:
            self.dict_SR_median_age = {}
            self.dict_model_name = {}
            model_merge_dict = {}
            for core in self.coreid:
                for i in range(len(self.model_name_list)):
                    model_name = self.model_name_list[i]
                    left_df = self.model_plot_data[model_name][1][self.model_plot_data[model_name][1].coreid.str.contains(core)].copy()
                    right_df = self.model_plot_data[model_name][0][self.model_plot_data[model_name][0].coreid.str.contains(core)].copy()
                    left_df.replace(0, np.nan, inplace = True)
                    left_df['compositedepth'] = left_df['compositedepth'].replace(np.nan, 0)
                    merge_frame = pd.merge(left = left_df, right = right_df, on = ['measurementid','coreid','compositedepth'])
                    merge_frame = merge_frame.astype(dtype = {'compositedepth': float})
                    model_merge_dict[model_name] = merge_frame[['SR_median','modeloutput_median','compositedepth']]
                self.dict_SR_median_age[core] = model_merge_dict
                self.dict_model_name[core] = self.model_name_list
        else:
            self.list_SR_median_age = []
            self.list_binned_SR_median_age = []
            for i in range(len(self.model_name_list)):
                model_name = self.model_name_list[i]
                self.left_df = self.model_plot_data[model_name][1].copy()
                self.right_df = self.model_plot_data[model_name][0].copy()
                if model_name == 'clam':
                    self.right_df['model_name'] = self.right_df.model_name.str.split(' ',expand = True)[0]
                self.left_df.replace(0, np.nan, inplace = True)
                self.left_df['compositedepth'] = self.left_df['compositedepth'].replace(np.nan, 0)
                merge_frame = pd.merge(left = self.left_df, right = self.right_df, on = ['measurementid','coreid','compositedepth','model_name'])
                merge_frame = merge_frame.astype(dtype = {'compositedepth': float,
                                                          'modeloutput_median': float,
                                                          'SR_median': float,
                                                          'SR_upper_1_sigma': float,
                                                          'SR_lower_1_sigma': float,
                                                          'SR_upper_2_sigma': float,
                                                          'SR_lower_2_sigma': float})
                merge_frame = merge_frame[['SR_median',
                                           'SR_upper_1_sigma',
                                           'SR_lower_1_sigma',
                                           'SR_upper_2_sigma',
                                           'SR_lower_2_sigma',
                                           'modeloutput_median',
                                           'compositedepth',
                                           'coreid',
                                           'model_name'
                                          ]]
                self.list_SR_median_age.append(merge_frame)
                
                #### This section is dedicated to the binning of results for each model
                self.model_frame = pd.DataFrame(columns = ['Binned_mid_age', 'SR_median', 'SR_upper_1_sigma', 'SR_lower_1_sigma', 'SR_upper_2_sigma', 'SR_lower_2_sigma', 'coreid', 'model_name'])
                for core in self.coreid:
                    sliced_merge_frame = merge_frame[merge_frame.coreid.str.contains(core)]
                    if len(sliced_merge_frame.index) != 0:
                        sliced_merge_frame = sliced_merge_frame.drop(['compositedepth','coreid','model_name'], axis = 1).set_index('modeloutput_median')
                        if sliced_merge_frame.index.min() != 0:
                            lower_limit = rounddown(sliced_merge_frame.index.min(),self.bin_size)
                        else:
                            lower_limit = 0
                        upper_limit = roundup(sliced_merge_frame.index.max(),self.bin_size)
                        bins = range(lower_limit, upper_limit, self.bin_size)
                        dict_boundaries = {}
                        for i in range(len(bins)):
                            if bins[i] != lower_limit:
                                dict_boundaries[(bins[i-1], bins[i])] = sliced_merge_frame.index[(sliced_merge_frame.index.values <= bins[i]) & (sliced_merge_frame.index.values > bins[i-1])].values
                        new_frame = pd.DataFrame(columns = ['modeloutput_median', 'SR_median', 'SR_upper_1_sigma', 'SR_lower_1_sigma', 'SR_upper_2_sigma', 'SR_lower_2_sigma'])
                        for key in dict_boundaries:
                            bin_slice = sliced_merge_frame[sliced_merge_frame.index.isin(dict_boundaries[key])]
                            if len(bin_slice) > 0:
                                curr_loc = len(new_frame)
                                new_frame.loc[curr_loc] = (bin_slice.reset_index()*(1/len(bin_slice))).sum()
                                new_frame.at[curr_loc, 'modeloutput_median'] = int((key[0]+key[1])/2)
                        new_frame = new_frame.rename(columns={"modeloutput_median": "Binned_mid_age"})
                        new_frame['coreid'] = core
                        new_frame['model_name'] = model_name
                        new_frame.replace(0, np.nan, inplace = True)
                        self.model_frame = pd.concat([self.model_frame, new_frame], axis = 0)
                    else:
                        pass
                self.list_binned_SR_median_age.append(self.model_frame)
            ####
            self.df_SR_median_age = pd.concat(self.list_SR_median_age, axis = 0) 
            self.df_SR_median_age = self.df_SR_median_age.sort_values(by = ['coreid','compositedepth','model_name'], ignore_index = True)
            self.dict_SR_median_age = {}
            self.dict_model_name = {}
            for core in self.coreid:
                core_slice = self.df_SR_median_age[self.df_SR_median_age.coreid == core]
                self.dict_model_name[core] = list(core_slice.model_name.unique())
                model_merge_dict = {}
                for model in core_slice.model_name.unique():
                    model_merge_dict[model] = core_slice[core_slice.model_name == model]
                self.dict_SR_median_age[core] = model_merge_dict
            
            ####
            self.df_binned_SR_median_age = pd.concat(self.list_binned_SR_median_age, axis = 0) 
            self.df_binned_SR_median_age = self.df_binned_SR_median_age.sort_values(by = ['coreid','Binned_mid_age'], ignore_index = True)
                        
            #### This section is dedicated to the binning of the combined model results
            if self.only_combined == True:
                self.df_binned_combine_SR_median_age = pd.DataFrame(columns = ['Binned_mid_age', 'Weighted_SR_median', 'SR_upper_1_sigma', 'SR_lower_1_sigma', 'SR_upper_2_sigma', 'SR_lower_2_sigma', 'coreid'])
                for core in self.coreid:
                    if core in self.df_binned_SR_median_age.coreid.unique():
                        core_slice = self.df_binned_SR_median_age[self.df_binned_SR_median_age.coreid == core]
                        new_frame = pd.DataFrame()
                        if self.sigma_range == '1sigma':
                            new_frame[['SR_lower_1_sigma']] = core_slice.groupby('Binned_mid_age').min()[['SR_lower_1_sigma']]
                            new_frame[['SR_upper_1_sigma']] = core_slice.groupby('Binned_mid_age').max()[['SR_upper_1_sigma']]
                        elif self.sigma_range == '2sigma':
                            new_frame[['SR_lower_2_sigma']] = core_slice.groupby('Binned_mid_age').min()[['SR_lower_2_sigma']]
                            new_frame[['SR_upper_2_sigma']] = core_slice.groupby('Binned_mid_age').max()[['SR_upper_2_sigma']]
                        else:
                            new_frame[['SR_lower_1_sigma','SR_lower_2_sigma']] = core_slice.groupby('Binned_mid_age').min()[['SR_lower_1_sigma', 'SR_lower_2_sigma']]
                            new_frame[['SR_upper_1_sigma','SR_upper_2_sigma']] = core_slice.groupby('Binned_mid_age').max()[['SR_upper_1_sigma', 'SR_upper_2_sigma']]
                        df_weight_slice = core_slice[['Binned_mid_age','SR_median']].set_index('Binned_mid_age')
                        list_weighted_SR = []
                        for i in df_weight_slice.index.unique():
                            if len(df_weight_slice.loc[i]) > 1:
                                list_weighted_SR.append((df_weight_slice.loc[i]*(1/len(df_weight_slice.loc[i]))).groupby('Binned_mid_age').sum())
                            else:
                                list_weighted_SR.append(df_weight_slice.loc[[i]])
                        df_weighted_SR = pd.concat(list_weighted_SR, axis = 0)
                        new_frame = pd.concat([df_weighted_SR, new_frame], axis = 1)
                        new_frame.reset_index(drop=False, inplace = True)
                        new_frame['coreid'] = core
                        new_frame = new_frame.rename(columns={"SR_median":"Weighted_SR_median"})
                        self.df_binned_combine_SR_median_age = pd.concat([self.df_binned_combine_SR_median_age, new_frame], axis = 0)
                
                self.df_binned_combine_SR_median_age = self.df_binned_combine_SR_median_age.sort_values(by = ['coreid','Binned_mid_age'], ignore_index = True)
           
            
    def plot_graph(self, orig_dir, sigma_range = 'both', # General options
                   bin_size = 1000, xlim_max = None, number_col = 7, reduce_plot_axis = False, # Multi-plot options
                   only_combined = False, save = False, for_color_blind = False, as_jpg = False): # Addtional plotting options
        """
        Main function to plot data for single core and multi-core case
        
        parameters:
        @self.orig_dir: original directory where LANDO was launched, so that plots can be saved to the folder "output_figures"
        @self.sigma_range: sigma range that should be shown in the plot - the options are: 'both', '1sigma', '2sigma', and None
        @self.bin_size: this argument only works for the multi-core case; defines the bin size in years; default value: 1000
        @self.xlim_max: this argument only works for the multi-core case; defines the maximum age range in years to be plotted; default value: None
        @self.number_col: only works for the multi-core case; defines the number of columns to plot; default value: 7
        @self.reduce_plot_axis: only works for the multi-core case; reduces the number that are plotted on the axis; default value: False
        @self.only_combined: argument to decide if only combined model should be plotted; default value: False
        @self.save: argument to decide if plot should be saved to location given in orig_dir; default value: False
        @self.for_color_blind: argument to transform plot to be suitable for people with color vision deficiency; default value: False
        @self.as_jpg: argument to plot grafics as .jpg (default is .pdf), which works best for color-blind plot; default value: False
        
        returns:
        Main output plot from LANDO
        """
        self.orig_dir = orig_dir
        self.sigma_range = sigma_range
        self.bin_size = bin_size
        self.xlim_max = xlim_max
        self.number_col = number_col
        self.reduce_plot_axis = reduce_plot_axis
        self.only_combined = only_combined
        self.save = save
        self.for_color_blind = for_color_blind
        self.as_jpg = as_jpg
        os.chdir(self.orig_dir)
        
        #####################################################
        #### This is the section for the single core case####
        #####################################################
        if len(self.coreid) == 1:
            #### Changing the look of the graphic
            SMALL_SIZE = 8
            MEDIUM_SIZE = 13
            BIGGER_SIZE = 18
            plt.rcdefaults()
            plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
            plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
            plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
            plt.rc('hatch', linewidth = 1.5)
            plt.rcParams["xtick.top"] = plt.rcParams["xtick.labeltop"] = True
            plt.rcParams["xtick.bottom"] = plt.rcParams["xtick.labelbottom"] = False
            model_color = {'Undatable' : '#0571b0',
                           'Bchron' : 'green',
                           'hamstr' : '#ca0020',
                           'Bacon' : '#842bd7',
                           'clam' : '#C59534',
                           'all' : '#6a6a6a'}
            
            linestyles_model = {'Undatable' : 'solid',
                               'Bchron' : 'dashed',
                               'hamstr' : 'dashdot',
                               'Bacon' : 'dotted',#(0, (3, 5, 1, 5, 1, 5)),
                               'clam' : 'solid'}
            
            hatch_model = {'Undatable' : '//',
                           'Bchron' : '\\\\',
                           'hamstr' : '-',
                           'Bacon' : '.',
                           'clam' : '+o'}
            
            marker_model = {'Undatable' : '.',
                           'Bchron' : None,
                           'hamstr' : None,
                           'Bacon' : None,
                           'clam' : '3'}
            
            marker_dates = {'14C terrestrial fossil': 's',
                            '14C sediment': 'o',
                            '14C marine fossil': 'D',
                            'other': 'v',
                            'tephra': 'P',
                            'tie point': 'X',
                            'paleomag': '*',
                            'U/Th': 'H'}
            ##################################################
            #### This calls the main functions from above ####
            ##################################################
            self.__frame_prep()
            if self.only_combined == True:
                self.__combine_age_df()
            self.__SR_median_age()
            ################################################## 
            
            fig = plt.figure(figsize=(12,7))
            
            #### This plots the main age-depth plot
            ax1 = fig.add_subplot(1,4,(1,3))
            ax1.invert_yaxis()
            
            if self.only_combined == True:
                ax1.plot('Weighted_mean_age', 'compositedepth', data = self.combine_age_df, color = model_color['all'], label = 'Weighted mean age', linestyle='dashed')
                if self.sigma_range == 'both':
                    ax1.fill_betweenx(self.combine_age_df['compositedepth'], self.combine_age_df['Max_age'], self.combine_age_df['Min_age'], alpha = .3, color = model_color['all'], label = f'2{chr(948)} uncertainty')
                elif self.sigma_range == '1sigma':
                    ax1.fill_betweenx(self.combine_age_df['compositedepth'], self.combine_age_df['Max_age'], self.combine_age_df['Min_age'], alpha = .3, color = model_color['all'], label = f'1{chr(948)} uncertainty')
                elif self.sigma_range == '2sigma':
                    ax1.fill_betweenx(self.combine_age_df['compositedepth'], self.combine_age_df['Max_age'], self.combine_age_df['Min_age'], alpha = .3, color = model_color['all'], label = f'2{chr(948)} uncertainty')
                else:
                    pass
            else:
                if self.for_color_blind == True: #### This changes the plot to be suitable for people with color vision deficiency
                    for data in self.age_data:
                        line, = ax1.plot('modeloutput_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax1, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], linewidth = 2, marker = marker_model[data['model_name'].unique()[0].split(' ')[0]], markevery = 20)
                        if self.sigma_range == 'both':
                            ax1.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                            ax1.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '1sigma':
                            ax1.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '2sigma':
                            ax1.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        else:
                            pass
                else:
                    for data in self.age_data:
                        ax1.plot('modeloutput_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax1, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        if self.sigma_range == 'both':
                            ax1.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                            ax1.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '1sigma':
                            ax1.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '2sigma':
                            ax1.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        else:
                            pass
            
            ### Adding different symbols for different material category   
            # 14C terrestrial - 's' - square;
            # 14C sediment - 'o' - circle;
            # 14C marine - 'D' - diamond;
            # other - 'v' - triangle (down);
            # tephra - 'P' - plus (filled);
            # tie point - 'X' - X (filled);
            # paleomag - '*' - star; 
            # U/Th - 'H' - hexagon
            for category in self.calib_dates.material_category.unique():
                ax1.errorbar(x='ages_calib', y='compositedepth', xerr = 'ages_calib_Sds', data = self.calib_dates[self.calib_dates.material_category.str.contains(category)], color = 'black', marker = marker_dates[category], linestyle = 'None', linewidth=1, markerfacecolor= 'none', markeredgecolor = 'black', label = category)
                           
            ax1.set_ylabel('Composite Depth [cm]')
            ax1.xaxis.set_label_position('top')
            ax1.set_xlabel('Calibrated Age [cal yr BP]', labelpad = 10)
            
            #### This adds hatches to the plot to be suitable for people with color vision deficiency
            if self.for_color_blind == True and self.only_combined == False:
                self.patch_legend = []
                for data in self.age_data:
                    patch = mpatches.Patch(color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], alpha = 0.3, hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]], label = data['model_name'].unique()[0])
                    self.patch_legend.append(patch)
                self.handles, self.labels = ax1.get_legend_handles_labels()
                self.new_handles = list(zip(self.patch_legend, self.handles))
                self.new_handles.append(self.handles[-1])
                plt.legend(self.new_handles, self.labels, handler_map={line : HandlerLine2D(marker_pad = 0)})
            else:
                plt.legend()
            
            #### This plots the sedimentation rate plot
            ax2 = fig.add_subplot(144)
            ax2.invert_yaxis()
            
            if self.only_combined == True:
                ax2.plot('Weighted_mean_SR', 'compositedepth', data = self.combine_SR_df, color = model_color['all'], linestyle='dashed')
                ax2.fill_betweenx(self.combine_SR_df['compositedepth'], self.combine_SR_df['Max_SR'], self.combine_SR_df['Min_SR'], alpha = .3, color = model_color['all'], label = 'Combined output')
            else:
                if self.for_color_blind == True: #### This changes the plot to be suitable for people with color vision deficiency
                    for data in self.SR_data:
                        ax2.plot('SR_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax2, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], marker = marker_model[data['model_name'].unique()[0].split(' ')[0]], markevery = 20)
                        if self.sigma_range == 'both':
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '1sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '2sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        else:
                            pass
                else:
                    for data in self.SR_data:
                        ax2.plot('SR_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax2, color = model_color[data['model_name'].unique()[0]])
                        if self.sigma_range == 'both':
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]])
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]])
                        elif self.sigma_range == '1sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]])
                        elif self.sigma_range == '2sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]])
                        else:
                            pass
            
            ax2.xaxis.set_label_position('top')
            ax2.set_xscale('log')
            ax2.xaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y)))
            ax2.set_xlabel('Sedimentation Rate [cm/yr]', labelpad = 10)
            ax2.yaxis.set_ticks_position('right')
            ax2.yaxis.set_label_position('right')
            ax2.set_ylabel('Composite Depth [cm]', rotation = -90, labelpad = 20)
    
            #### This adds the header to the plot and saves the plot
            if self.dttp == 'No':
                ax1.set_title(f'Age Models - {self.coreid[0]}', loc = 'center', pad = (10), fontsize = BIGGER_SIZE, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_without_RC_{self.coreid[0]}_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_without_RC_{self.coreid[0]}_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            else:
                ax1.set_title(f'Reservoir Corrected Age Models - {self.coreid[0]}', loc = 'center', pad = (10), fontsize = BIGGER_SIZE, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_with_RC_{self.coreid[0]}_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif  self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_with_RC_{self.coreid[0]}_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            plt.show()
        else:
            ####################################################
            #### This is the section for the multi-core case####
            ####################################################
            #### Changing the look of the graphic
            SMALL_SIZE = 8
            MEDIUM_SIZE = 13
            BIGGER_SIZE = 18
            plt.rcdefaults()
            plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
            plt.rc('xtick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
            plt.rc('ytick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
            plt.rc('hatch', linewidth = 1.5)
            plt.rcParams['xtick.major.size'] =  plt.rcParams['ytick.major.size'] = 10
            plt.rcParams['xtick.major.width'] = plt.rcParams['ytick.major.width'] = 2
            plt.rcParams['xtick.minor.size'] =  plt.rcParams['ytick.minor.size'] = 5
            plt.rcParams['xtick.minor.width'] = plt.rcParams['ytick.minor.width'] = 1
            plt.rcParams["xtick.top"] = plt.rcParams["xtick.labeltop"] = False
            plt.rcParams["xtick.bottom"] = plt.rcParams["xtick.labelbottom"] = True
            model_color = {'Undatable' : '#0571b0',
                           'Bchron' : 'green',
                           'hamstr' : '#ca0020',
                           'Bacon' : '#842bd7',
                           'clam' : '#C59534',
                           'all' : '#6a6a6a'}
            
            linestyles_model = {'Undatable' : 'solid',
                               'Bchron' : 'dashed',
                               'hamstr' : 'dashdot',
                               'Bacon' : 'dotted',#(0, (3, 5, 1, 5, 1, 5)),
                               'clam' : 'solid'}
            
            hatch_model = {'Undatable' : '//',
                           'Bchron' : '\\\\',
                           'hamstr' : '-',
                           'Bacon' : '.',
                           'clam' : '+o'}
            
            marker_model = {'Undatable' : '.',
                           'Bchron' : None,
                           'hamstr' : None,
                           'Bacon' : None,
                           'clam' : '3'}
            
            class TextHandler(HandlerBase):
                def create_artists(self, legend,tup ,xdescent, ydescent,
                                   width, height, fontsize,trans):
                    tx = Text(width/2.,height/2,tup[0], fontsize=fontsize,
                              ha="center", va="center", color=tup[1], fontweight="bold")
                    return [tx]
                
            if (len(self.coreid)/self.number_col) > 4:
                labelsize_axis = 2*BIGGER_SIZE
                fontsize_legend = 20
                titlesize_legend = 24
            else:
                labelsize_axis = BIGGER_SIZE
                fontsize_legend = SMALL_SIZE
                titlesize_legend = MEDIUM_SIZE
            ##################################################
            #### This calls the main functions from above ####
            ##################################################
            self.__frame_prep()
            if self.only_combined == True:
                self.__combine_age_df()
            self.__SR_median_age()
            ##################################################
            
            #### This plots the combined binned sedimentation rate versus median age for all sediment cores
            if self.only_combined == True:
                g = sns.relplot(
                    data=self.df_binned_combine_SR_median_age,
                    x="Binned_mid_age", y="Weighted_SR_median", 
                    col="coreid", color = 'grey',
                    kind="line", linestyle = '--',  
                    linewidth=4, zorder=5,
                    col_wrap = self.number_col
                )
                self.core_legend = {}
                core_counter = 1
                for coreid, ax in g.axes_dict.items():
                    if self.sigma_range == '1sigma':
                        ax.fill_between(x = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].Binned_mid_age, 
                                        y1 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_upper_1_sigma, 
                                        y2 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_lower_1_sigma, 
                                        alpha = .3,
                                        color = 'grey', label = 'Combined Output')
                    else:
                        ax.fill_between(x = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].Binned_mid_age, 
                                        y1 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_upper_2_sigma, 
                                        y2 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_lower_2_sigma, 
                                        alpha = .3,
                                        color = 'grey', label = 'Combined Output')
                    #### Create a dictionary that holds the number and coreid, e.g., {1: 'PG1234', 2: 'EN20155'}
                    self.core_legend[core_counter] = coreid
                    #### This adds the title as an annotation within the plot
                    ax.text(.8, .85, core_counter, transform=ax.transAxes, fontweight="bold", fontsize = BIGGER_SIZE)
                    ax.set_yscale('log')
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y)))
                    core_counter += 1
                
                g.set_titles('')
                g.set_axis_labels("","")
                #### Set limits
                self.xlim_min = int(1950 - datetime.datetime.now().year)
                self.ylim_min = 0.001
                self.ylim_max = None
                g.set(ylim=(self.ylim_min, self.ylim_max))
                g.set(xlim=(self.xlim_min, self.xlim_max))
                g.tight_layout()
                
                #### Reduce the number that are shown in the plot
                if self.reduce_plot_axis == True:
                    value_x_tick = range(0, self.xlim_max + int(self.xlim_max/4), int(self.xlim_max/4))
                    new_x_tick_labels = ['' if (value != 0) and (value != self.xlim_max) and (value != int(self.xlim_max/2)) else value for value in value_x_tick]
                    for ax in g.axes.flat:
                        value_y_tick = ax.get_yticks()
                        new_y_tick_labels = ['' if (value != self.ylim_min) and (value != (self.ylim_min*100)) and (value != (self.ylim_min*10000)) else value for value in value_y_tick]
                        ax.yaxis.set_major_locator(ticker.FixedLocator(value_y_tick))
                        ax.yaxis.set_major_formatter(ticker.FixedFormatter(new_y_tick_labels))
                        ax.set_xticks(ticks=value_x_tick)
                        ax.set_xticklabels(labels=new_x_tick_labels)
                        
                #### Get a costumized legend
                self.ids = [*self.core_legend]
                self.handles_c = [(i, 'black') for i in self.ids]
                self.labels_c = [self.core_legend[number] for number in self.core_legend.keys()]
                g.fig.legend(handles=self.handles_c, labels=self.labels_c, handler_map={tuple : TextHandler()}, fontsize = fontsize_legend, loc = 'center right', bbox_to_anchor = (1.1, 0.5), title = 'CoreID', title_fontsize = titlesize_legend)
                g.fig.text(.5, -0.02, 'Median Ages [cal yr BP]', transform=g.fig.transFigure, horizontalalignment='center', fontsize = labelsize_axis, fontweight = 'bold')
                g.fig.text(-0.01, .5, 'Median Sedimentation Rate [cm/yr]', transform=g.fig.transFigure, ha='center', va='center', fontsize = labelsize_axis, fontweight = 'bold', rotation = 'vertical')
                
            else:
                #### This plots the binned sedimentation rate versus median age for all sediment cores from all models
                g = sns.relplot(
                    data=self.df_binned_SR_median_age,
                    x="Binned_mid_age", y="SR_median", 
                    col="coreid", hue="model_name",
                    kind="line", palette=model_color, 
                    linewidth=4, zorder=5,
                    col_wrap = self.number_col,
                    legend = False
                )
                self.patch_legend = []
                for model_name in self.model_name_list:
                    patch = mpatches.Patch(color = model_color[model_name], label = model_name)
                    self.patch_legend.append(patch)
                g.fig.legend(handles = self.patch_legend, labels = self.model_name_list, title = 'Software', loc = 'lower right', bbox_to_anchor = (1.1, 0), fontsize = fontsize_legend, title_fontsize = titlesize_legend)
                self.core_legend = {}
                core_counter = 1                
                for coreid, ax in g.axes_dict.items():
                    for model_name in self.model_name_list:
                        if self.sigma_range == 'both':
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_1_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_1_sigma, 
                                            alpha = .3,
                                            color = model_color[model_name])
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_2_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_2_sigma, 
                                            alpha = .1,
                                            color = model_color[model_name])
                        
                        elif self.sigma_range == '1sigma':
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_1_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_1_sigma, 
                                            alpha = .3,
                                            color = model_color[model_name])
                        
                        elif self.sigma_range == '2sigma':
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_2_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_2_sigma, 
                                            alpha = .1,
                                            color = model_color[model_name])
                        else:
                            pass
                    
                    #### Create a dictionary that holds the number and coreid, e.g., {1: 'PG1234', 2: 'EN20155'}
                    self.core_legend[core_counter] = coreid
                    #### This adds the title as an annotation within the plot
                    ax.text(.8, .85, core_counter, transform=ax.transAxes, fontweight="bold", fontsize = BIGGER_SIZE)
                    ax.set_yscale('log')
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y)))
                    core_counter += 1
                
                g.set_titles('')
                g.set_axis_labels("","")
                #### Set limits
                self.xlim_min = int(1950 - datetime.datetime.now().year)
                self.ylim_min = 0.001
                self.ylim_max = None
                g.set(ylim=(self.ylim_min, self.ylim_max))
                g.set(xlim=(self.xlim_min, self.xlim_max))
                g.tight_layout()
                
                #### Reduce the number that are shown in the plot
                if self.reduce_plot_axis == True:
                    value_x_tick = range(0, self.xlim_max + int(self.xlim_max/4), int(self.xlim_max/4))
                    new_x_tick_labels = ['' if (value != 0) and (value != self.xlim_max) and (value != int(self.xlim_max/2)) else value for value in value_x_tick]
                    for ax in g.axes.flat:
                        value_y_tick = ax.get_yticks()
                        new_y_tick_labels = ['' if (value != self.ylim_min) and (value != (self.ylim_min*100)) and (value != (self.ylim_min*10000)) else value for value in value_y_tick]
                        ax.yaxis.set_major_locator(ticker.FixedLocator(value_y_tick))
                        ax.yaxis.set_major_formatter(ticker.FixedFormatter(new_y_tick_labels))
                        ax.set_xticks(ticks=value_x_tick)
                        ax.set_xticklabels(labels=new_x_tick_labels)
                        
                #### Get a costumized legend
                self.ids = [*self.core_legend]
                self.handles_c = [(i, 'black') for i in self.ids]
                self.labels_c = [self.core_legend[number] for number in self.core_legend.keys()]
                g.fig.legend(handles=self.handles_c, labels=self.labels_c, handler_map={tuple : TextHandler()}, fontsize = fontsize_legend, loc = 'center right', bbox_to_anchor = (1.1, 0.5), title = 'CoreID', title_fontsize = titlesize_legend)
                g.fig.text(.5, -0.02, 'Median Ages [cal yr BP]', transform=g.fig.transFigure, horizontalalignment='center', fontsize = labelsize_axis, fontweight = 'bold')
                g.fig.text(-0.01, .5, 'Median Sedimentation Rate [cm/yr]', transform=g.fig.transFigure, ha='center', va='center', fontsize = labelsize_axis, fontweight = 'bold', rotation = 'vertical')
            
            #### This adds the header to the plot and saves the plot
            if self.dttp == 'No':
                g.fig.suptitle('Age Models - Multicore', y = 1.02, ha = 'center', fontsize = labelsize_axis, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_without_RC_multicore_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_without_RC_multicore_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            else:
                g.fig.suptitle('Reservoir Corrected Age Models - Multicore', y = 1.02, ha = 'center', fontsize = labelsize_axis, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_with_RC_multicore_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif  self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_with_RC_multicore_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            
            plt.show()
        
    def plot_optimized_graph(self, optimization_values, fitting_values, proxy, proxy_data, orig_dir, # General input
                             sigma_range = 'both', inclusion_threshold = 0.1, show_fitting_models = False, # General options
                             bin_size = 1000, xlim_max = None, number_col = 7, reduce_plot_axis = False, # Multi-plot options
                             only_combined = False, save = False, for_color_blind = False, as_jpg = False): # Addtional plotting options
        """
        Main function to plot optimized version for critical single core case
        
        parameters:
        @self.optimization_values: resulting list with all the results from the optimization process for proxy and modeling software
        @self.fitting_values: list with values how the modeling software fits with the proxy data  
        @self.proxy: string with name of proxy that will be plotted underneath the proxy-derived lithology
        @self.proxy_data: time series with proxy data to be plotted within the proxy-derived lithology
        @self.orig_dir: original directory where LANDO was launched, so that plots can be saved to the folder "output_figures"
        @self.sigma_range: sigma range that should be shown in the plot - the options are: 'both', '1sigma', '2sigma', and None
        @self.inclusion_threshold: threshold of fitting values to be plotted; default value: 0.1
        @self.show_fitting_models: argument to decide if only fitting age-depth models should be plotted; default value: False
        @self.bin_size: this argument only works for the multi-core case; defines the bin size in years; default value: 1000
        @self.xlim_max: this argument only works for the multi-core case; defines the maximum age range in years to be plotted; default value: None
        @self.number_col: only works for the multi-core case; defines the number of columns to plot; default value: 7
        @self.reduce_plot_axis: only works for the multi-core case; reduces the number that are plotted on the axis; default value: False
        @self.only_combined: argument to decide if only combined model should be plotted; default value: False
        @self.save: argument to decide if plot should be saved to location given in orig_dir; default value: False
        @self.for_color_blind: argument to transform plot to be suitable for people with color vision deficiency; default value: False
        @self.as_jpg: argument to plot grafics as .jpg (default is .pdf), which works best for color-blind plot; default value: False
        
        returns:
        Optimized output plot from LANDO
        """
        self.optimization_values = optimization_values
        self.fitting_values = fitting_values
        self.proxy = proxy
        self.proxy_data = proxy_data
        self.orig_dir = orig_dir
        self.sigma_range = sigma_range
        self.inclusion_threshold = inclusion_threshold
        self.show_fitting_models = show_fitting_models
        self.bin_size = bin_size
        self.xlim_max = xlim_max
        self.number_col = number_col
        self.reduce_plot_axis = reduce_plot_axis
        self.only_combined = only_combined
        self.save = save
        self.for_color_blind = for_color_blind
        self.as_jpg = as_jpg
        os.chdir(self.orig_dir)
        
        #####################################################
        #### This is the section for the single core case####
        #####################################################
        if len(self.coreid) == 1:
            #### Changing the look of the graphic
            SMALL_SIZE = 8
            MEDIUM_SIZE = 13
            BIGGER_SIZE = 18
            plt.rcdefaults()
            plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
            plt.rc('xtick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
            plt.rc('ytick', labelsize=MEDIUM_SIZE)    # fontsize of the tick labels
            plt.rc('hatch', linewidth = 1.5)
            plt.rcParams["xtick.top"] = plt.rcParams["xtick.labeltop"] = True
            plt.rcParams["xtick.bottom"] = plt.rcParams["xtick.labelbottom"] = False
            model_color = {'Undatable' : '#0571b0',
                           'Bchron' : 'green',
                           'hamstr' : '#ca0020',
                           'Bacon' : '#842bd7',
                           'clam' : '#C59534',
                           'all' : '#6a6a6a'}
            
            linestyles_model = {'Undatable' : 'solid',
                               'Bchron' : 'dashed',
                               'hamstr' : 'dashdot',
                               'Bacon' : 'dotted',#(0, (3, 5, 1, 5, 1, 5)),
                               'clam' : 'solid'}
            
            hatch_model = {'Undatable' : '//',
                           'Bchron' : '\\\\',
                           'hamstr' : '-',
                           'Bacon' : '.',
                           'clam' : '+o'}
            
            marker_model = {'Undatable' : '.',
                           'Bchron' : None,
                           'hamstr' : None,
                           'Bacon' : None,
                           'clam' : '3'}
            
            marker_dates = {'14C terrestrial fossil': 's',
                            '14C sediment': 'o',
                            '14C marine fossil': 'D',
                            'other': 'v',
                            'tephra': 'P',
                            'tie point': 'X',
                            'paleomag': '*',
                            'U/Th': 'H'}
            ##################################################
            #### This calls the main functions from above ####
            ##################################################
            self.c_fitting_values = self.fitting_values[self.coreid[0]]
            self.c_optimization_values = self.optimization_values[self.coreid[0]]
            if self.show_fitting_models == True: #### This if statement ensures that no data will be deleted if only excluded models are shown
                self.excluded_models = [self.c_fitting_values.index[i] for i in range(len(self.c_fitting_values)) if self.c_fitting_values[i] <= self.inclusion_threshold]
                for i in self.excluded_models:
                    self.model_plot_data.pop(i)
            self.__frame_prep()
            if self.only_combined == True:
                self.__combine_age_df()
            self.__SR_median_age()
            ##################################################
            
            fig = plt.figure(figsize=(14,7))
            
            #### This plots the main age-depth plot
            ax2 = fig.add_subplot(1,7,(2,6))
            ax2.invert_yaxis()
            
            if self.only_combined == True:
                ax2.plot('Weighted_mean_age', 'compositedepth', data = self.combine_age_df, color = model_color['all'], label = 'Weighted mean age', linestyle='dashed')
                if self.sigma_range == 'both':
                    ax2.fill_betweenx(self.combine_age_df['compositedepth'], self.combine_age_df['Max_age'], self.combine_age_df['Min_age'], alpha = .3, color = model_color['all'], label = f'2{chr(948)} uncertainty')
                elif self.sigma_range == '1sigma':
                    ax2.fill_betweenx(self.combine_age_df['compositedepth'], self.combine_age_df['Max_age'], self.combine_age_df['Min_age'], alpha = .3, color = model_color['all'], label = f'1{chr(948)} uncertainty')
                elif self.sigma_range == '2sigma':
                    ax2.fill_betweenx(self.combine_age_df['compositedepth'], self.combine_age_df['Max_age'], self.combine_age_df['Min_age'], alpha = .3, color = model_color['all'], label = f'2{chr(948)} uncertainty')
                else:
                    pass
            else:
                if self.for_color_blind == True:
                    for data in self.age_data:
                        line, = ax2.plot('modeloutput_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax2, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], linewidth = 2, marker = marker_model[data['model_name'].unique()[0].split(' ')[0]], markevery = 20)
                        if self.sigma_range == 'both':
                            ax2.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                            ax2.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '1sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '2sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        else:
                            pass
                else:
                    for data in self.age_data:
                        ax2.plot('modeloutput_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax2, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        if self.sigma_range == 'both':
                            ax2.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                            ax2.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '1sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['upper_1_sigma'], data['lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '2sigma':
                            ax2.fill_betweenx(data['compositedepth'], data['upper_2_sigma'], data['lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0].split(' ')[0]])
                        else:
                            pass
            
            ### Adding different symbols for different material category   
            # 14C terrestrial - 's' - square;
            # 14C sediment - 'o' - circle;
            # 14C marine - 'D' - diamond;
            # other - 'v' - triangle (down);
            # tephra - 'P' - plus (filled);
            # tie point - 'X' - X (filled);
            # paleomag - '*' - star; 
            # U/Th - 'H' - hexagon
            for category in self.calib_dates.material_category.unique():
                ax2.errorbar(x='ages_calib', y='compositedepth', xerr = 'ages_calib_Sds', data = self.calib_dates[self.calib_dates.material_category.str.contains(category)], color = 'black', marker = marker_dates[category], linestyle = 'None', linewidth=1, markerfacecolor= 'none', markeredgecolor = 'black', label = category)
            
            ax2.xaxis.set_label_position('top')
            ax2.set_xlabel('Calibrated Age [cal yr BP]', labelpad = 10)
            ax2.set_yticklabels([])
            
            #### This adds hatches to the plot to be suitable for people with color vision deficiency
            if self.for_color_blind == True and self.only_combined == False:
                self.patch_legend = []
                for data in self.age_data:
                    patch = mpatches.Patch(color = model_color[data['model_name'].unique()[0].split(' ')[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], alpha = 0.3, hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]], label = data['model_name'].unique()[0])
                    self.patch_legend.append(patch)
                self.handles, self.labels = ax2.get_legend_handles_labels()
                self.new_handles = list(zip(self.patch_legend, self.handles))
                self.new_handles.append(self.handles[-1])
                plt.legend(self.new_handles, self.labels, handler_map={line : HandlerLine2D(marker_pad = 0)})
            else:
                plt.legend()
            
            #### This plots the proxy derived lithology on the left side 
            ax1 = fig.add_subplot(171)
            ax1.invert_yaxis()
            ax1.plot('value','compositedepth', data = self.proxy_data[self.coreid[0]], color = 'black')
            ax1.set_ylabel('Composite Depth [cm]')
            ax1.xaxis.set_label_position('top')
            ax1.set_xlabel(f'Proxy-derived \n Lithology', labelpad = 10)
            ax1.set_xticklabels([])
            ax1.set_xticks([])
            ax1.set_ylim(ax2.get_ylim())
            
            #### This plots the sedimentation rate plot 
            ax3 = fig.add_subplot(177)
            ax3.invert_yaxis()
            
            if self.only_combined == True:
                ax3.plot('Weighted_mean_SR', 'compositedepth', data = self.combine_SR_df, color = model_color['all'], linestyle='dashed')
                ax3.fill_betweenx(self.combine_SR_df['compositedepth'], self.combine_SR_df['Max_SR'], self.combine_SR_df['Min_SR'], alpha = .3, color = model_color['all'], label = 'Combined output')
            else:
                if self.for_color_blind == True:
                    for data in self.SR_data:
                        ax3.plot('SR_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax3, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], marker = marker_model[data['model_name'].unique()[0].split(' ')[0]], markevery = 20)
                        if self.sigma_range == 'both':
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '1sigma':
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        elif self.sigma_range == '2sigma':
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]], linestyle = linestyles_model[data['model_name'].unique()[0].split(' ')[0]], hatch = hatch_model[data['model_name'].unique()[0].split(' ')[0]])
                        else:
                            pass
                else:
                    for data in self.SR_data:
                        ax3.plot('SR_median', 'compositedepth', data = data, label = data['model_name'].unique()[0], axes = ax3, color = model_color[data['model_name'].unique()[0]])
                        if self.sigma_range == 'both':
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]])
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]])
                        elif self.sigma_range == '1sigma':
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_1_sigma'], data['SR_lower_1_sigma'], alpha = .3, color = model_color[data['model_name'].unique()[0]])
                        elif self.sigma_range == '2sigma':
                            ax3.fill_betweenx(data['compositedepth'], data['SR_upper_2_sigma'], data['SR_lower_2_sigma'], alpha = .1, color = model_color[data['model_name'].unique()[0]])
                        else:
                            pass
            
            ax3.xaxis.set_label_position('top')
            ax3.set_xscale('log')
            ax3.xaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y)))
            ax3.set_xlabel('Sedimentation Rate [cm/yr]', labelpad = 10)
            ax3.yaxis.set_ticks_position('right')
            ax3.yaxis.set_label_position('right')
            ax3.set_ylabel('Composite Depth [cm]', rotation = -90, labelpad = 20)
    
            #### This adds the lithological boundaries to all three plots
            ax1_min = ax1.get_xlim()[1]
            ax1_max = ax1.get_xlim()[0]
            ax2_min = ax2.get_xlim()[1]
            ax2_max = ax2.get_xlim()[0]
            ax3_min = ax3.get_xlim()[1]
            ax3_max = ax3.get_xlim()[0]
            ax1.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth'], xmin = ax1_min, xmax =ax1_max, linewidth=2, color = 'black')
            ax1.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth_left'], xmin = ax1_min, xmax = ax1_max, linewidth=0.5, color = 'black', linestyle = 'dashed')
            ax1.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth_right'], xmin = ax1_min, xmax = ax1_max, linewidth=0.5, color = 'black', linestyle = 'dashed')
            ax2.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth'], xmin = ax2_min-(0.05*ax2_min), xmax = ax2_max-(0.5*ax2_max), linewidth=1, color = 'black')
            ax2.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth_left'], xmin = ax2_min-(0.05*ax2_min), xmax = ax2_max-(0.5*ax2_max), linewidth=0.5, color = 'black', linestyle = 'dashed')
            ax2.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth_right'], xmin = ax2_min-(0.05*ax2_min), xmax = ax2_max-(0.5*ax2_max), linewidth=0.5, color = 'black', linestyle = 'dashed')
            ax3.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth'], xmin = ax3_min, xmax = ax3_max, linewidth=1, color = 'black')
            ax3.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth_left'], xmin = ax3_min, xmax = ax3_max, linewidth=0.5, color = 'black', linestyle = 'dashed')
            ax3.hlines(y = self.c_optimization_values['Proxy']['Composite_Depth_right'], xmin = ax3_min, xmax = ax3_max, linewidth=0.5, color = 'black', linestyle = 'dashed')
        
            #### This adds the name of the proxy underneath the proxy-derived lithology
            ax1.text(x = ((ax1_min + ax1_max)/2), y = (ax1.get_ylim()[0] * 1.05), s = proxy[self.coreid[0]], ha = 'center', fontsize = BIGGER_SIZE)
            
            #### This adds the fitting values of each individual modeling software underneath all plots
            if self.show_fitting_models == True:
                self.org_fitting_values = copy.deepcopy(self.c_fitting_values)
                self.c_fitting_values = self.c_fitting_values[~self.c_fitting_values.index.isin(self.excluded_models)]
            info_string = ""
            for i in range(len(self.c_fitting_values)):
                info_string += f"{self.c_fitting_values.index[i]}: {round(self.c_fitting_values[i], 4)}"
                if i != len(self.c_fitting_values)-1:
                    info_string += ", "
            ax2.text(x = ((ax2_min + ax2_max)/2), y = (ax2.get_ylim()[0] * 1.05), s = info_string, ha = 'center')
            if self.show_fitting_models == True:
                self.c_fitting_values = self.org_fitting_values
        
            #### This adds the header to the plot and saves the plot
            if self.dttp == 'No':
                ax2.set_title(f'Optimized Age Models - {self.coreid[0]}', loc = 'center', pad = (10), fontsize = BIGGER_SIZE, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/optimized_age_models_without_RC_{self.coreid[0]}_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/optimized_age_models_without_RC_{self.coreid[0]}_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            else:
                ax2.set_title(f'Reservoir Corrected Optimized Age Models - {self.coreid[0]}', loc = 'center', pad = (10), fontsize = BIGGER_SIZE, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/optimized_age_models_with_RC_{self.coreid[0]}_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif  self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/optimized_age_models_with_RC_{self.coreid[0]}_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            plt.show()
        else:
            ####################################################
            #### This is the section for the multi-core case####
            ####################################################
            #### Changing the look of the graphic
            SMALL_SIZE = 8
            MEDIUM_SIZE = 13
            BIGGER_SIZE = 18
            plt.rcdefaults()
            plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
            plt.rc('xtick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
            plt.rc('ytick', labelsize=BIGGER_SIZE)    # fontsize of the tick labels
            plt.rc('hatch', linewidth = 1.5)
            plt.rcParams['xtick.major.size'] =  plt.rcParams['ytick.major.size'] = 10
            plt.rcParams['xtick.major.width'] = plt.rcParams['ytick.major.width'] = 2
            plt.rcParams['xtick.minor.size'] =  plt.rcParams['ytick.minor.size'] = 5
            plt.rcParams['xtick.minor.width'] = plt.rcParams['ytick.minor.width'] = 1
            plt.rcParams["xtick.top"] = plt.rcParams["xtick.labeltop"] = False
            plt.rcParams["xtick.bottom"] = plt.rcParams["xtick.labelbottom"] = True
            model_color = {'Undatable' : '#0571b0',
                           'Bchron' : 'green',
                           'hamstr' : '#ca0020',
                           'Bacon' : '#842bd7',
                           'clam' : '#C59534',
                           'all' : '#6a6a6a'}
            
            linestyles_model = {'Undatable' : 'solid',
                               'Bchron' : 'dashed',
                               'hamstr' : 'dashdot',
                               'Bacon' : 'dotted',#(0, (3, 5, 1, 5, 1, 5)),
                               'clam' : 'solid'}
            
            hatch_model = {'Undatable' : '//',
                           'Bchron' : '\\\\',
                           'hamstr' : '-',
                           'Bacon' : '.',
                           'clam' : '+o'}
            
            marker_model = {'Undatable' : '.',
                           'Bchron' : None,
                           'hamstr' : None,
                           'Bacon' : None,
                           'clam' : '3'}
            
            class TextHandler(HandlerBase):
                def create_artists(self, legend,tup ,xdescent, ydescent,
                                   width, height, fontsize,trans):
                    tx = Text(width/2.,height/2,tup[0], fontsize=fontsize,
                              ha="center", va="center", color=tup[1], fontweight="bold")
                    return [tx]
                
            if (len(self.coreid)/self.number_col) > 4:
                labelsize_axis = 2*BIGGER_SIZE
                fontsize_legend = 20
                titlesize_legend = 24
            else:
                labelsize_axis = BIGGER_SIZE
                fontsize_legend = SMALL_SIZE
                titlesize_legend = MEDIUM_SIZE
            ##################################################
            #### This calls the main functions from above ####
            ##################################################
            if self.show_fitting_models == True: #### This if statement ensures that no data will be deleted if only excluded models are shown
                for core in self.fitting_values.keys():
                    excluded_models = [key for key in fitting_values[core].keys() if fitting_values[core][key] <= self.inclusion_threshold]
                    for model in excluded_models:
                        self.model_plot_data[model][0].drop(self.model_plot_data[model][0][self.model_plot_data[model][0].measurementid.str.contains(core)].index, inplace = True)
                        self.model_plot_data[model][1].drop(self.model_plot_data[model][1][self.model_plot_data[model][1].measurementid.str.contains(core)].index, inplace = True)
                        #self.model_plot_data[model][0].drop(self.model_plot_data[model][0][self.model_plot_data[model][0]['coreid'] == core].index, inplace = True)
                        #self.model_plot_data[model][1].drop(self.model_plot_data[model][1][self.model_plot_data[model][1]['coreid'] == core].index, inplace = True)
            self.__frame_prep()
            if self.only_combined == True:
                self.__combine_age_df()
            self.__SR_median_age()
            ##################################################
            #### This plots the combined binned sedimentation rate versus median age for all sediment cores
            if self.only_combined == True:
                g = sns.relplot(
                    data=self.df_binned_combine_SR_median_age,
                    x="Binned_mid_age", y="Weighted_SR_median", 
                    col="coreid", color = 'grey',
                    kind="line", linestyle = '--',  
                    linewidth=4, zorder=5,
                    col_wrap = self.number_col
                )
                self.core_legend = {}
                core_counter = 1
                for coreid, ax in g.axes_dict.items():
                    if self.sigma_range == '1sigma':
                        ax.fill_between(x = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].Binned_mid_age, 
                                        y1 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_upper_1_sigma, 
                                        y2 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_lower_1_sigma, 
                                        alpha = .3,
                                        color = 'grey', label = 'Combined Output')
                    else:
                        ax.fill_between(x = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].Binned_mid_age, 
                                        y1 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_upper_2_sigma, 
                                        y2 = self.df_binned_combine_SR_median_age[(self.df_binned_combine_SR_median_age['coreid'] == coreid)].SR_lower_2_sigma, 
                                        alpha = .3,
                                        color = 'grey', label = 'Combined Output')
                    #### Create a dictionary that holds the number and coreid, e.g., {1: 'PG1234', 2: 'EN20155'}
                    self.core_legend[core_counter] = coreid
                    #### This adds the title as an annotation within the plot
                    ax.text(.8, .85, core_counter, transform=ax.transAxes, fontweight="bold", fontsize = BIGGER_SIZE)
                    if coreid in self.proxy:
                        ax.text(.8, .8, self.proxy[coreid], transform=ax.transAxes, fontweight="bold", fontsize = BIGGER_SIZE)
                    ax.set_yscale('log')
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y)))
                    core_counter += 1
                
                g.set_titles('')
                g.set_axis_labels("","")
                #### Set limits
                self.xlim_min = int(1950 - datetime.datetime.now().year)
                self.ylim_min = 0.001
                self.ylim_max = None
                g.set(ylim=(self.ylim_min, self.ylim_max))
                g.set(xlim=(self.xlim_min, self.xlim_max))
                g.tight_layout()
                
                #### Reduce the number that are shown in the plot
                if self.reduce_plot_axis == True:
                    value_x_tick = range(0, self.xlim_max + int(self.xlim_max/4), int(self.xlim_max/4))
                    new_x_tick_labels = ['' if (value != 0) and (value != self.xlim_max) and (value != int(self.xlim_max/2)) else value for value in value_x_tick]
                    for ax in g.axes.flat:
                        value_y_tick = ax.get_yticks()
                        new_y_tick_labels = ['' if (value != self.ylim_min) and (value != (self.ylim_min*100)) and (value != (self.ylim_min*10000)) else value for value in value_y_tick]
                        ax.yaxis.set_major_locator(ticker.FixedLocator(value_y_tick))
                        ax.yaxis.set_major_formatter(ticker.FixedFormatter(new_y_tick_labels))
                        ax.set_xticks(ticks=value_x_tick)
                        ax.set_xticklabels(labels=new_x_tick_labels)
                        
                #### Get a costumized legend
                self.ids = [*self.core_legend]
                self.handles_c = [(i, 'black') for i in self.ids]
                self.labels_c = [self.core_legend[number] for number in self.core_legend.keys()]
                g.fig.legend(handles=self.handles_c, labels=self.labels_c, handler_map={tuple : TextHandler()}, fontsize = fontsize_legend, loc = 'center right', bbox_to_anchor = (1.1, 0.5), title = 'CoreID', title_fontsize = titlesize_legend)
                g.fig.text(.5, -0.02, 'Median Ages [cal yr BP]', transform=g.fig.transFigure, horizontalalignment='center', fontsize = labelsize_axis, fontweight = 'bold')
                g.fig.text(-0.01, .5, 'Median Sedimentation Rate [cm/yr]', transform=g.fig.transFigure, ha='center', va='center', fontsize = labelsize_axis, fontweight = 'bold', rotation = 'vertical')
                
            else:
                #### This plots the binned sedimentation rate versus median age for all sediment cores from all models
                g = sns.relplot(
                    data=self.df_binned_SR_median_age,
                    x="Binned_mid_age", y="SR_median", 
                    col="coreid", hue="model_name",
                    kind="line", palette=model_color, 
                    linewidth=4, zorder=5,
                    col_wrap = self.number_col,
                    legend = False
                )
                self.patch_legend = []
                for model_name in self.model_name_list:
                    patch = mpatches.Patch(color = model_color[model_name], label = model_name)
                    self.patch_legend.append(patch)
                g.fig.legend(handles = self.patch_legend, labels = self.model_name_list, title = 'Software', loc = 'lower right', bbox_to_anchor = (1.1, 0), fontsize = fontsize_legend, title_fontsize = titlesize_legend)
                self.core_legend = {}
                core_counter = 1                
                for coreid, ax in g.axes_dict.items():
                    for model_name in self.model_name_list:
                        if self.sigma_range == 'both':
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_1_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_1_sigma, 
                                            alpha = .3,
                                            color = model_color[model_name])
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_2_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_2_sigma, 
                                            alpha = .1,
                                            color = model_color[model_name])
                        
                        elif self.sigma_range == '1sigma':
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_1_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_1_sigma, 
                                            alpha = .3,
                                            color = model_color[model_name])
                        
                        elif self.sigma_range == '2sigma':
                            ax.fill_between(x = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].Binned_mid_age, 
                                            y1 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_upper_2_sigma, 
                                            y2 = self.df_binned_SR_median_age[(self.df_binned_SR_median_age['coreid'] == coreid) & (self.df_binned_SR_median_age['model_name'] == model_name)].SR_lower_2_sigma, 
                                            alpha = .1,
                                            color = model_color[model_name])
                        else:
                            pass
                    
                    #### Create a dictionary that holds the number and coreid, e.g., {1: 'PG1234', 2: 'EN20155'}
                    self.core_legend[core_counter] = coreid
                    #### This adds the title as an annotation within the plot
                    ax.text(.8, .85, core_counter, transform=ax.transAxes, fontweight="bold", fontsize = BIGGER_SIZE)
                    if coreid in self.proxy:
                        ax.text(.8, .8, self.proxy[coreid], transform=ax.transAxes, fontweight="bold", fontsize = BIGGER_SIZE)
                    ax.set_yscale('log')
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: '{:g}'.format(y)))
                    core_counter += 1
                
                g.set_titles('')
                g.set_axis_labels("","")
                #### Set limits
                self.xlim_min = int(1950 - datetime.datetime.now().year)
                self.ylim_min = 0.001
                self.ylim_max = None
                g.set(ylim=(self.ylim_min, self.ylim_max))
                g.set(xlim=(self.xlim_min, self.xlim_max))
                g.tight_layout()
                
                #### Reduce the number that are shown in the plot
                if self.reduce_plot_axis == True:
                    value_x_tick = range(0, self.xlim_max + int(self.xlim_max/4), int(self.xlim_max/4))
                    new_x_tick_labels = ['' if (value != 0) and (value != self.xlim_max) and (value != int(self.xlim_max/2)) else value for value in value_x_tick]
                    for ax in g.axes.flat:
                        value_y_tick = ax.get_yticks()
                        new_y_tick_labels = ['' if (value != self.ylim_min) and (value != (self.ylim_min*100)) and (value != (self.ylim_min*10000)) else value for value in value_y_tick]
                        ax.yaxis.set_major_locator(ticker.FixedLocator(value_y_tick))
                        ax.yaxis.set_major_formatter(ticker.FixedFormatter(new_y_tick_labels))
                        ax.set_xticks(ticks=value_x_tick)
                        ax.set_xticklabels(labels=new_x_tick_labels)
                        
                #### Get a costumized legend
                self.ids = [*self.core_legend]
                self.handles_c = [(i, 'black') for i in self.ids]
                self.labels_c = [self.core_legend[number] for number in self.core_legend.keys()]
                g.fig.legend(handles=self.handles_c, labels=self.labels_c, handler_map={tuple : TextHandler()}, fontsize = fontsize_legend, loc = 'center right', bbox_to_anchor = (1.1, 0.5), title = 'CoreID', title_fontsize = titlesize_legend)
                g.fig.text(.5, -0.02, 'Median Ages [cal yr BP]', transform=g.fig.transFigure, horizontalalignment='center', fontsize = labelsize_axis, fontweight = 'bold')
                g.fig.text(-0.01, .5, 'Median Sedimentation Rate [cm/yr]', transform=g.fig.transFigure, ha='center', va='center', fontsize = labelsize_axis, fontweight = 'bold', rotation = 'vertical')
            
            #### This adds the header to the plot and saves the plot
            if self.dttp == 'No':
                g.fig.suptitle('Age Models - Multicore', y = 1.02, ha = 'center', fontsize = labelsize_axis, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_without_RC_multicore_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_without_RC_multicore_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            else:
                g.fig.suptitle('Reservoir Corrected Age Models - Multicore', y = 1.02, ha = 'center', fontsize = labelsize_axis, fontweight = 'bold')
                if self.save == True and self.as_jpg == False:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_with_RC_multicore_{date}.pdf', dpi = 600, bbox_inches = 'tight')
                elif  self.save == True and self.as_jpg == True:
                    date = f"{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}"
                    plt.savefig(f'output_figures/age_models_with_RC_multicore_{date}.jpg', dpi = 600, bbox_inches = 'tight')
                else:
                    pass
            
            plt.show()

def roundup(x, bin_size):
    """
    Helper function to round up the edge of age-depth result according to the bin size
    """
    return int(math.ceil(x / bin_size)) * bin_size
def rounddown(x, bin_size):
    """
    Helper function to round down the edge of age-depth result according to the bin size
    """
    return int(math.floor(x / bin_size)) * bin_size
