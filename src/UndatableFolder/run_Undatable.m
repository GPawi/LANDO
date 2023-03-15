function [] = run_Undatable(CoreID_array,xfactor,bootpc)
%Rebuild library
pkg rebuild
%Load packages
warning('off', 'all')
pkg load statistics
pkg load dataframe
%For loop to execute different CoreIDs
for i=1:length(CoreID_array)
    coreid_array_txt = strcat(CoreID_array{i}, '.txt');
    undatable(coreid_array_txt, 10^4, xfactor, bootpc, 'plotme',0, 'printme',0);
endfor