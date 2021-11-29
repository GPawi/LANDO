function [] = run_Undatable(CoreIDs_df,xfactor,bootpc)
%Test for Undatable in Octave
%Load packages
pkg load statistics
pkg load dataframe
pkg load parallel
warning('off', 'all')
% Prepare Undatable 
coreid_array = cellstr(CoreIDs_df);
coreid_array_txt = strcat(coreid_array, '.txt');

%Run function in parallel
fun = @(id) undatable(id, 10^4, xfactor, bootpc, 'plotme',0, 'printme',0);
parcellfun (nproc, fun, coreid_array_txt);