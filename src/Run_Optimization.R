### Script to find lithological changes through independet proxy data
## Load libraries
suppressPackageStartupMessages(c(library('forecast')
                                 ,library('changepoint')
                                 ,library('sets')
                                 ,library('parallel')
                                 ,library('stats')
                                 ,library('foreach')
                                 ,library('doSNOW')
                                 ))

### Functions taken and adaped by Holloway et al. 2021
##########
obs_pres_seg_proc <- function(obs_pres){
  
  seg_no  <- array(0,length(obs_pres))
  ini_seg <- 1
  
  for (ii in 1:length(obs_pres)){
    if(ii < length(obs_pres)){
      if ((obs_pres[ii] == TRUE) & (obs_pres[ii+1] == TRUE)){
        seg_no[ii] <- ini_seg
      } else if ((obs_pres[ii] == TRUE) & (obs_pres[ii+1] == FALSE)){
        seg_no[ii] <- ini_seg
        ini_seg    <- ini_seg+1  
      } else if ((obs_pres[ii] == FALSE) & (obs_pres[ii+1] == FALSE)){
        seg_no[ii] <- 0
      } else if ((obs_pres[ii] == FALSE) & (obs_pres[ii+1] == TRUE)){
        seg_no[ii] <- 0
      }
    } else {
      if(obs_pres[ii] == TRUE){
        seg_no[ii] <- ini_seg
      } else {
        seg_no[ii] <- 0
      }
    }
  }
  
  return(seg_no)
  
  #Close the function. 
} 

#Function to calculate summary stats for each segment (mean,sd,min and max)
seg_sumstats_fun <- function(df_row,x_tseries_orig,sumstat_proc){
  
  #Find the number of segments.
  nseg <- length(df_row)-1
  
  #Set blank variable to hold mean.
  tmpstat <- NULL
  
  #Loop over segments and determine mean.
  for(ll in 1:nseg){
    if ((!is.na(df_row[ll]) == TRUE) & (!is.na(df_row[ll+1]) == TRUE)){
      tmpstat[ll] <- eval(parse(text=paste(sumstat_proc,'(x_tseries_orig[(df_row[ll]+1):(df_row[ll+1])])',sep='')))
    } else {
      tmpstat[ll] <- NA
    }
  }
  
  return(tmpstat)
  
}

#Define a function that bootstraps the cpts for each segment.
#The function also returns the summary stats of each segment from the 
#resulting cpt location for each sample. 
cpt_boot <- function(seg_1,seg_2,cpt_method){
  
  #Gernerate new samples for each segment with replacement.      
  seg_1_boot <- sample(seg_1, length(seg_1), replace=T)
  seg_2_boot <- sample(seg_2, length(seg_2), replace=T)
  
  #Now estimate the new changepoint (fix at 1 using AMOC).
  #Also need to define this based on chosen cpt method.
  if (cpt_method == 'mean'){
    cpt_samp <- cpt.mean(c(seg_1_boot,seg_2_boot), method='AMOC', penalty='MBIC')
  } else if (cpt_method == 'variance'){
    cpt_samp <- cpt.var(c(seg_1_boot,seg_2_boot), method='AMOC', penalty='MBIC')
  } else if (cpt_method == 'mean+variance'){
    cpt_samp <- cpt.meanvar(c(seg_1_boot,seg_2_boot), method='AMOC', penalty='MBIC')
  } 
  
  return(cpts(cpt_samp))
  
  #Close the bootstrap function.    
}

#This based on the bootstrap method employed in the mosum package. 
#Essentially the time series is split into segments a each changepoint and sampled to the
#left anf right of each fitted changepoint. The AMOC method is then used to estimate the new location based
#on the new sample. confidence intervals are estimated for a chosen level for each cpt.    
cpts_confint <- function(x_series,
                         x_series_orig,
                         x_cpts,
                         N_reps,
                         n_cpts,
                         cpt_method){
  
  #First use the identified cpts to set upper and lower bnds for each 
  #segment.
  #Just use the length of the AR tseries (x_series) here.
  #Need to start from zero as segments are defined by +1
  #to end of previous seg. At start this is 0.
  x_cpts_segs_bnds <- c(0,x_cpts[1:length(x_cpts)],length(x_series))
  
  #Find the number of segments in the data to be processed.
  x_nseg <- n_cpts+1
  
  #Create a data frame to hold the summary of each segment.
  #This will also hold the summary of the changepoint locations at the start and end of each segment.
  cpts_CI_all <- data.frame(seg_lwr=as.integer(rep(NA,x_nseg)),
                            seg_lwr.ci.left=as.integer(rep(NA,x_nseg)),
                            seg_lwr.ci.right=as.integer(rep(NA,x_nseg)),
                            seg_upr=as.integer(rep(NA,x_nseg)),
                            seg_upr.ci.left=as.integer(rep(NA,x_nseg)),
                            seg_upr.ci.right=as.integer(rep(NA,x_nseg)),
                            is_cpt_lwr=as.character(rep('',x_nseg)),
                            is_cpt_upr=as.character(rep('',x_nseg)),
                            seg_mean=as.numeric(rep(NA,x_nseg)),
                            seg_mean.ci.left=as.numeric(rep(NA,x_nseg)),
                            seg_mean.ci.right=as.numeric(rep(NA,x_nseg)),
                            seg_sd=as.numeric(rep(NA,x_nseg)),
                            seg_sd.ci.left=as.numeric(rep(NA,x_nseg)),
                            seg_sd.ci.right=as.numeric(rep(NA,x_nseg)),
                            stringsAsFactors = FALSE
  )
  
  
  #Now loop over the changepoints and estimate the confidence intervals based on bootstrap sample.
  #Create a matrix to hold the boostrap cpt locations.
  cpt_samp_matrix              <- matrix(0,nrow=N_reps,ncol=n_cpts+2)
  cpt_samp_matrix[,1]                     <- 0
  cpt_samp_matrix[,ncol(cpt_samp_matrix)] <- length(x_series_orig)
  
  #Loop over the number of desired reps and bootstrap cpts.
  for(mm in 1:N_reps){
    
    summary_cpts <- numeric()
    
    #Bootstrap each cpt location. 
    for (ll in 1:n_cpts){
      
      #Get the segments for the current sample.
      #If the 1st cpt.
      if((ll == 1) & (n_cpts > 1)){
        x1_l <- 1
        x1_r <- x_cpts[ll]
        x2_l <- x_cpts[ll]+1
        x2_r <- x_cpts[ll+1]
        #if the last cpt.
      } else if ((ll > 1) & (ll == n_cpts)){
        x1_l <- x_cpts[ll-1]+1
        x1_r <- x_cpts[ll]
        x2_l <- x_cpts[ll]+1
        x2_r <- length(x_series)
        #Case where there is only 1 cpt in the segment.
      } else if ((ll == 1) & (n_cpts == 1)){
        x1_l <- 1
        x1_r <- x_cpts[ll]
        x2_l <- x_cpts[ll]+1
        x2_r <- length(x_series)
        #If any other cpt.
      } else {
        x1_l <- x_cpts[ll-1]+1
        x1_r <- x_cpts[ll]
        x2_l <- x_cpts[ll]+1
        x2_r <- x_cpts[ll+1]
      }
      
      #Extract the segments from the time series.       
      seg_1_proc <- x_series[x1_l:x1_r]
      seg_2_proc <- x_series[x2_l:x2_r]
      
      #Bootstrap the cpt locations.
      summary_cpts_tmp <- cpt_boot(seg_1_proc,seg_2_proc,
                                   cpt_method)
      if (length(summary_cpts_tmp) > 0){
        summary_cpts <- append(summary_cpts,(summary_cpts_tmp+(x1_l-1)))
      } else {
        summary_cpts   <- append(summary_cpts,NA)
      }
      
      
      #Close loop around cpts.
    }
    
    #Append the bootstrapped cpts locations to the master array.
    cpt_samp_matrix[mm,2:(ncol(cpt_samp_matrix)-1)] <- summary_cpts
    
    #Close the loop around the number of samples.
  }
  
  #Get the segment means,sd,min and max.
  #Returned matrix seems to be flipped to transpose to get 
  #correct orientation.
  cpt_samp_segmeans <- t(apply(cpt_samp_matrix,1,seg_sumstats_fun,x_series_orig,'mean'))
  cpt_samp_segsds   <- t(apply(cpt_samp_matrix,1,seg_sumstats_fun,x_series_orig,'sd'))
  
  #Get the segment means for the original set of cpts.
  x_seg_means_orig <- seg_sumstats_fun(x_cpts_segs_bnds,x_series_orig,'mean')
  x_seg_sds_orig   <- seg_sumstats_fun(x_cpts_segs_bnds,x_series_orig,'sd')
  
  #Loop over segments and calculate CIs of upper/lower ends + sumstats
  for (nn in 1:nrow(cpts_CI_all)){
    
    #Populate the master array.
    if (nn == 1){
      #Fix the lower bounds at 1 for the first segment.
      #This requires adding one to the lowest segment start (0).
      #This is because of the way the segment means are calculated.
      cpts_CI_all$seg_lwr[nn]          <- x_cpts_segs_bnds[nn]+1
      cpts_CI_all$seg_lwr.ci.left[nn]  <- x_cpts_segs_bnds[nn]+1
      cpts_CI_all$seg_lwr.ci.right[nn] <- x_cpts_segs_bnds[nn]+1
      cpts_CI_all$is_cpt_lwr[nn]       <- 'NO'
      cpts_CI_all$seg_upr[nn]          <- x_cpts_segs_bnds[nn+1]
      cpts_CI_all$seg_upr.ci.left[nn]  <- quantile(cpt_samp_matrix[,nn+1],c(0.025,0.975),type=1,na.rm=TRUE)[1]
      cpts_CI_all$seg_upr.ci.right[nn] <- quantile(cpt_samp_matrix[,nn+1],c(0.025,0.975),type=1,na.rm=TRUE)[2]
      cpts_CI_all$is_cpt_upr[nn]       <- 'YES'
    } else if (nn == length(x_cpts_segs_bnds)-1){
      cpts_CI_all$seg_lwr[nn]          <- x_cpts_segs_bnds[nn]
      cpts_CI_all$seg_lwr.ci.left[nn]  <- quantile(cpt_samp_matrix[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[1]
      cpts_CI_all$seg_lwr.ci.right[nn] <- quantile(cpt_samp_matrix[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[2]
      cpts_CI_all$is_cpt_lwr[nn]       <- 'YES'
      cpts_CI_all$seg_upr[nn]          <- x_cpts_segs_bnds[nn+1]
      cpts_CI_all$seg_upr.ci.left[nn]  <- x_cpts_segs_bnds[nn+1]
      cpts_CI_all$seg_upr.ci.right[nn] <- x_cpts_segs_bnds[nn+1]
      cpts_CI_all$is_cpt_upr[nn]       <- 'NO'
    } else {  
      cpts_CI_all$seg_lwr[nn]          <- x_cpts_segs_bnds[nn]
      cpts_CI_all$seg_lwr.ci.left[nn]  <- quantile(cpt_samp_matrix[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[1]
      cpts_CI_all$seg_lwr.ci.right[nn] <- quantile(cpt_samp_matrix[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[2]
      cpts_CI_all$is_cpt_lwr[nn]       <- 'YES'
      cpts_CI_all$seg_upr[nn]          <- x_cpts_segs_bnds[nn+1]
      cpts_CI_all$seg_upr.ci.left[nn]  <- quantile(cpt_samp_matrix[,nn+1],c(0.025,0.975),type=1,na.rm=TRUE)[1]
      cpts_CI_all$seg_upr.ci.right[nn] <- quantile(cpt_samp_matrix[,nn+1],c(0.025,0.975),type=1,na.rm=TRUE)[2]
      cpts_CI_all$is_cpt_upr[nn]       <- 'YES'
      #Close the if statement.
    }
    #Get the segment sumstats.
    #Means
    cpts_CI_all$seg_mean[nn]           <- x_seg_means_orig[nn]
    cpts_CI_all$seg_mean.ci.left[nn]   <- quantile(cpt_samp_segmeans[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[1]
    cpts_CI_all$seg_mean.ci.right[nn]  <- quantile(cpt_samp_segmeans[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[2]
    #SDs
    cpts_CI_all$seg_sd[nn]           <- x_seg_sds_orig[nn]
    cpts_CI_all$seg_sd.ci.left[nn]   <- quantile(cpt_samp_segsds[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[1]
    cpts_CI_all$seg_sd.ci.right[nn]  <- quantile(cpt_samp_segsds[,nn],c(0.025,0.975),type=1,na.rm=TRUE)[2]
    #Close loop around segments.    
  }
  
  #Pass out the results.
  return(cpts_CI_all)
  
  #Close the function.
}

cpts_currts_CI <- function(data_in_proc,
                           min_seg_proc,
                           CPT_METHOD_PROC,
                           N_reps_proc,
                           ts_type){
  
  #Get the proxy and age depth model time series.
  if (ts_type == 'OBS'){
    obs_tseries            <- ts(data_in_proc$value)
    proc_tseries           <- ts(data_in_proc$value)
    mod_dates_plt          <- data_in_proc$compositedepth
  } else if (ts_type == 'MOD'){
    #obs_tseries            <- ts(data_in_proc$SR_mean)
    #proc_tseries           <- ts(data_in_proc$SR_mean)
    #mod_dates_plt          <- data_in_proc$modeloutput_median
    obs_tseries            <- ts(data_in_proc$modeloutput_median)
    proc_tseries           <- ts(data_in_proc$modeloutput_median)
    mod_dates_plt          <- data_in_proc$modeloutput_median
  }
  
  #Find out where we have data present.
  obs_pres_logicals      <- (!is.na(obs_tseries))
  
  #Get the segment ids.
  obs_seg_no <- obs_pres_seg_proc(obs_pres_logicals)
  
  #Find the individual number of segments.
  obs_pres_segs <- sort(unique(obs_seg_no[which(obs_seg_no > 0)]))
  
  #Set up blank data frames to hold the changpoints over all segs and their confidence intervals.
  cpts_CI_site_currts <- data.frame(seg_lwr=as.integer(),
                                    seg_lwr.ci.left=as.integer(),
                                    seg_lwr.ci.right=as.integer(),
                                    seg_upr=as.integer(),
                                    seg_upr.ci.left=as.integer(),
                                    seg_upr.ci.right=as.integer(),
                                    is_cpt_lwr=as.character(),
                                    is_cpt_upr=as.character(),
                                    seg_mean=as.numeric(),
                                    seg_mean.ci.left=as.numeric(),
                                    seg_mean.ci.right=as.numeric(),
                                    seg_sd=as.numeric(),
                                    seg_sd.ci.left=as.numeric(),
                                    seg_sd.ci.right=as.numeric(),
                                    stringsAsFactors = FALSE
  )
  
  #Loop over the segments and identify the changepoints for that segment.
  for (kk in 1:length(obs_pres_segs)){
    
    #Calculate the % we are through all segments to show on progress bar.
    pct_proc <- 100.0*(kk/length(obs_pres_segs))
    
    #Find the current segment length.
    curr_seg_ids <- which(obs_seg_no == obs_pres_segs[kk])
    
    #If the seg length is above the minimum then find the changepoints.
    if (length(curr_seg_ids) > min_seg_proc){
      
      #Extract the current segment for both model and obs tseries.
      curr_seg_proc_ts <- proc_tseries[curr_seg_ids]
      
      #Fit the chosen AR model to smooth out seasonlity.
      #This is set in the UI for each time series.
      ##/// newly added ///##
      fit <- auto.arima(curr_seg_proc_ts, stepwise = FALSE, approximation = FALSE, parallel = TRUE, seasonal = FALSE)
      a_order <- arimaorder(fit)
      ##/// newly added ///##
      ts_arima <- arima(curr_seg_proc_ts,c(a_order[[1]],a_order[[2]],a_order[[3]]),method='CSS-ML')
      
      #Get the changepoints for the current segment.
      #Use the chosen CPT_METHOD to dermine location of changepoints.
      if (CPT_METHOD_PROC == "mean"){
        curr_seg_cpts_ts <- cpt.mean(residuals(ts_arima),method='PELT',penalty='MBIC', minseglen = min_seg_proc*0.50)
      } else if (CPT_METHOD_PROC == "variance"){
        curr_seg_cpts_ts <- cpt.var(residuals(ts_arima),method='PELT',penalty='MBIC', minseglen = min_seg_proc*0.50)
      } else if (CPT_METHOD_PROC == "mean+variance"){
        curr_seg_cpts_ts <- cpt.meanvar(residuals(ts_arima),method='PELT',penalty='MBIC', minseglen = min_seg_proc*0.50)
      } 
      
      
      #Check to see if there are any changepoints - of there are append to the main array.
      #Also compute the cpts CIs if any exist.
      if (ncpts(curr_seg_cpts_ts) > 0){
        curr_seg_CI_ts  <- cpts_confint(residuals(ts_arima),
                                        curr_seg_proc_ts,
                                        cpts(curr_seg_cpts_ts),
                                        N_reps_proc,
                                        ncpts(curr_seg_cpts_ts),
                                        CPT_METHOD_PROC)
        
        #As the segment processing code works on individual
        #segments need to add the base id to cpts locations
        #to make sure they are correct.
        
        #Use column names to get correct cols to correct
        seg_lwr_cols  <- grepl("seg_lwr",names(curr_seg_CI_ts))
        seg_upr_cols  <- grepl("seg_upr",names(curr_seg_CI_ts))
        seg_cols_corr <- which((seg_lwr_cols == TRUE) |
                                 (seg_upr_cols == TRUE))
        curr_seg_CI_ts[,seg_cols_corr] <- curr_seg_CI_ts[,seg_cols_corr] + (curr_seg_ids[1]-1)
        
        cpts_CI_site_currts <- rbind(cpts_CI_site_currts,curr_seg_CI_ts)
        
      } else if (ncpts(curr_seg_cpts_ts) == 0) {
        if (CPT_METHOD_PROC == "mean"){
          curr_seg_cpts_ts <- cpt.mean(curr_seg_proc_ts,method='PELT',penalty='MBIC', minseglen = min_seg_proc*0.50)
        } else if (CPT_METHOD_PROC == "variance"){
          curr_seg_cpts_ts <- cpt.var(curr_seg_proc_ts,method='PELT',penalty='MBIC', minseglen = min_seg_proc*0.50)
        } else if (CPT_METHOD_PROC == "mean+variance"){
          curr_seg_cpts_ts <- cpt.meanvar(curr_seg_proc_ts,method='PELT',penalty='MBIC', minseglen = min_seg_proc*0.50)
        } 
        
        curr_seg_CI_ts  <- cpts_confint(curr_seg_proc_ts,
                                        curr_seg_proc_ts,
                                        cpts(curr_seg_cpts_ts),
                                        N_reps_proc,
                                        ncpts(curr_seg_cpts_ts),
                                        CPT_METHOD_PROC)
        
        #As the segment processing code works on individual
        #segments need to add the base id to cpts locations
        #to make sure they are correct.
        
        #Use column names to get correct cols to correct
        seg_lwr_cols  <- grepl("seg_lwr",names(curr_seg_CI_ts))
        seg_upr_cols  <- grepl("seg_upr",names(curr_seg_CI_ts))
        seg_cols_corr <- which((seg_lwr_cols == TRUE) |
                                 (seg_upr_cols == TRUE))
        curr_seg_CI_ts[,seg_cols_corr] <- curr_seg_CI_ts[,seg_cols_corr] + (curr_seg_ids[1]-1)
        
        cpts_CI_site_currts <- rbind(cpts_CI_site_currts,curr_seg_CI_ts)
        
      } 
      #Close the check over segment length.
    }
    #Close loop over segments.
  }
  if(ncpts(curr_seg_cpts_ts) > 0){
    #Pick out the original cpts along with their CIS.
    cpts_CI_summary <- cpts_CI_site_currts[which(cpts_CI_site_currts$is_cpt_upr == 'YES'),which(seg_upr_cols == TRUE)]
    #Rename the columns names for output.
    names(cpts_CI_summary) <- c('cpt','ci.left','ci.right')
    
    #Ensure that there is a confidence interval and if not, then add one centimeter to the right side (older age)
    for (i in 1:nrow(cpts_CI_summary)) {
      if ((cpts_CI_summary[i,]$cpt == cpts_CI_summary[i,]$ci.left)&(cpts_CI_summary[i,]$cpt == cpts_CI_summary[i,]$ci.right)) {
        cpts_CI_summary[i,]$ci.right = cpts_CI_summary[i,]$ci.right+1
      }
    }
    
    #Append the dates timings of the changepoint to the data frame.    
    if (ts_type == 'MOD'){
      cpts_CI_summary$Modeloutput_Median       <- mod_dates_plt[cpts_CI_summary$cpt]
      cpts_CI_summary$Modeloutput_Median_left  <- mod_dates_plt[cpts_CI_summary$ci.left]    
      cpts_CI_summary$Modeloutput_Median_right <- mod_dates_plt[cpts_CI_summary$ci.right]
      
      #Also add the segment upper/lower dates.
      cpts_CI_site_currts$seg_lwr_Modeloutput_Median       <- mod_dates_plt[cpts_CI_site_currts$seg_lwr]
      cpts_CI_site_currts$seg_lwr_Modeloutput_Median_left  <- mod_dates_plt[cpts_CI_site_currts$seg_lwr.ci.left]
      cpts_CI_site_currts$seg_lwr_Modeloutput_Median_right <- mod_dates_plt[cpts_CI_site_currts$seg_lwr.ci.right]
      cpts_CI_site_currts$seg_upr_Modeloutput_Median       <- mod_dates_plt[cpts_CI_site_currts$seg_upr]
      cpts_CI_site_currts$seg_upr_Modeloutput_Median_left  <- mod_dates_plt[cpts_CI_site_currts$seg_upr.ci.left]
      cpts_CI_site_currts$seg_upr_Modeloutput_Median_right <- mod_dates_plt[cpts_CI_site_currts$seg_upr.ci.right]
      
    } else if (ts_type == 'OBS'){
      cpts_CI_summary$Composite_Depth       <- mod_dates_plt[cpts_CI_summary$cpt]
      cpts_CI_summary$Composite_Depth_left  <- mod_dates_plt[cpts_CI_summary$ci.left]    
      cpts_CI_summary$Composite_Depth_right <- mod_dates_plt[cpts_CI_summary$ci.right]
      
      #Also add the segment upper/lower dates.
      cpts_CI_site_currts$seg_lwr_Composite_Depth       <- mod_dates_plt[cpts_CI_site_currts$seg_lwr]
      cpts_CI_site_currts$seg_lwr_Composite_Depth_left  <- mod_dates_plt[cpts_CI_site_currts$seg_lwr.ci.left]
      cpts_CI_site_currts$seg_lwr_Composite_Depth_right <- mod_dates_plt[cpts_CI_site_currts$seg_lwr.ci.right]
      cpts_CI_site_currts$seg_upr_Composite_Depth       <- mod_dates_plt[cpts_CI_site_currts$seg_upr]
      cpts_CI_site_currts$seg_upr_Composite_Depth_left  <- mod_dates_plt[cpts_CI_site_currts$seg_upr.ci.left]
      cpts_CI_site_currts$seg_upr_Composite_Depth_right <- mod_dates_plt[cpts_CI_site_currts$seg_upr.ci.right]
    }
    
    
    #Pass out the results
    return(list(seg_summary=cpts_CI_site_currts,cpt_summary=cpts_CI_summary))
  } else {
    print('No change point detected - retry with other settings')
    return(list(seg_summary=0,cpt_summary=0))
  }
  #Close the function.      
}

cpts_insct_siml <- function(fuzzy_int_1,
                            fuzzy_int_2){
  
  #To conserve speed set the universe to be the max/min of the 2 cpts being compared.
  fuzzy_uni_min <- min(fuzzy_int_1$Composite_Depth_left,fuzzy_int_2$ci.left)
  fuzzy_uni_max <- max(fuzzy_int_1$Composite_Depth_right,fuzzy_int_2$ci.right)
  
  #Convert the intervals into fuzzy numbers.
  fuzzy_num_1 <- fuzzy_triangular_gset(corners=c(fuzzy_int_1$Composite_Depth_left,
                                                 fuzzy_int_1$Composite_Depth,fuzzy_int_1$Composite_Depth_right),
                                       universe=seq(fuzzy_uni_min,fuzzy_uni_max,0.1))
  
  fuzzy_num_2 <- fuzzy_triangular_gset(corners=c(fuzzy_int_2$ci.left,
                                                 fuzzy_int_2$cpt,fuzzy_int_2$ci.right),
                                       universe=seq(fuzzy_uni_min,fuzzy_uni_max,0.1))
  
  return(gset_similarity(fuzzy_num_1,fuzzy_num_2))
  
}

cpts_currts_eval <- function(data_in_proc_obs,
                             data_in_proc_mod,
                             cpts_CI_site_obs,
                             cpts_CI_site_mod){
  
  mat_df_1               <- merge(data_in_proc_mod, data_in_proc_obs, on = 'compositedepth')[, c('compositedepth','value')]
  if (dim(mat_df_1)[1] == 0) {
    mat_df_2 <- data.frame(approx(data_in_proc_mod$compositedepth, data_in_proc_mod$modeloutput_median, xout = data_in_proc_obs$compositedepth))
    names(mat_df_2) <- c('compositedepth', 'modeloutput_median')
    mat_df_1 <- data_in_proc_obs
  } else {
    mat_df_2               <- merge(mat_df_1, data_in_proc_mod, on = 'compositedepth')[, c('compositedepth','modeloutput_median')]
  }
  obs_tseries            <- ts(mat_df_1$value)
  mod_tseries            <- ts(mat_df_2$modeloutput_median)
  
  #Now compute the overlap for each observed changepoint assuming the obs cpts are truth.
  #First Use the CIs to find the cpts that overlap.
  cpts_overlap <- matrix(1,nrow=nrow(cpts_CI_site_obs),ncol=nrow(cpts_CI_site_mod))
  
  for (aa in 1:nrow(cpts_CI_site_obs)){
    for (bb in 1:nrow(cpts_CI_site_mod)){
      
      ci_overlap <- cbind(cpts_CI_site_obs$Composite_Depth_left[aa] - cpts_CI_site_mod$ci.right[bb], cpts_CI_site_obs$Composite_Depth_right[aa] - cpts_CI_site_mod$ci.right[bb], 
                          cpts_CI_site_obs$Composite_Depth_right[aa] - cpts_CI_site_mod$ci.left[bb])
      
      if ((ci_overlap[,1] > 0 & ci_overlap[,2] > 0 & ci_overlap[,3] > 0) |
          (ci_overlap[,1] < 0 & ci_overlap[,2] < 0 & ci_overlap[,3] < 0)){
        
        cpts_overlap[aa,bb] <- 0  #I.e. Cis do not overlap.
      }
    }
  }
  
  #Find all model cpts that intercept the CIs of each obs cpt.
  obs_cpt_insct <- list()
  for (cc in 1:nrow(cpts_overlap)){
    cpts_insct <- which(cpts_overlap[cc,] == 1)
    if (length(cpts_insct) != 0){
      obs_cpt_insct[[cc]] <- cpts_insct
    } else {
      obs_cpt_insct[[cc]] <- 0
    }
  }  
  
  cpts_fuzzy_eval   <-   list()
  obs_cpt_insct_max <- numeric()
  
  for (dd in 1:length(obs_cpt_insct)){
    
    if ((length(obs_cpt_insct[[dd]]) == 1) & (obs_cpt_insct[[dd]][1] != 0)){
      cpts_fuzzy_eval[[dd]] <- cpts_insct_siml(cpts_CI_site_obs[dd,],cpts_CI_site_mod[obs_cpt_insct[[dd]][1],])
      obs_cpt_insct_max[dd] <- obs_cpt_insct[[dd]][1]
    } else if ((length(obs_cpt_insct[[dd]]) == 1) & (obs_cpt_insct[[dd]][1] == 0)){
      cpts_fuzzy_eval[[dd]] <- 0
      obs_cpt_insct_max[dd] <- 0
    } else if (length(obs_cpt_insct[[dd]]) > 1){
      temp_fuzzy_eval <- numeric()
      for (ee in 1:length(obs_cpt_insct[[dd]])){
        temp_fuzzy_eval[ee] <- cpts_insct_siml(cpts_CI_site_obs[dd,],cpts_CI_site_mod[obs_cpt_insct[[dd]][ee],])
      }
      cpts_fuzzy_eval[[dd]] <- temp_fuzzy_eval
      obs_cpt_insct_max[dd] <- obs_cpt_insct[[dd]][which.max(temp_fuzzy_eval)]
    }
  }
  
  #Find the unique list of maximum intersections.
  #This gives the model cpt ind that has maximum intersection with each obs cpt.
  #There will be duplicates here where more than one model cpt intersects. 
  rep_cpt <- unique(obs_cpt_insct_max[obs_cpt_insct_max != 0])
  
  #Find the max intserctions to each obs cpt.
  #Set the duplicates to 0.
  obs_wgts_max <- numeric(length=length(obs_cpt_insct_max))
  for (yy in 1:length(rep_cpt)){
    obs_ind_mlt <- which(obs_cpt_insct_max == rep_cpt[yy])
    #If we have a single location having max intersect just populate with that value.
    #If we have more than one find the maxium score and that gives the max intersect.
    if (length(obs_ind_mlt) == 1){
      obs_wgts_max[obs_ind_mlt] <- rep_cpt[yy]
    } else if (length(obs_ind_mlt) > 1){
      obs_ind_max <- obs_ind_mlt[which.max(unlist(cpts_fuzzy_eval)[which(unlist(obs_cpt_insct) == rep_cpt[yy])])]
      obs_wgts_max[obs_ind_max] <- rep_cpt[yy]
    }
  }
  
  #Where we dont have maximum intersections there might be another cpt that does intersect to a lesser extent.
  #Check for these.
  
  #Find the remaining points to check for alternative intsersections
  obs_ind_rmn <- which(obs_wgts_max == 0)
  
  #Get the corresponding alternatives from the main list.
  obs_alt_check <- obs_cpt_insct[obs_ind_rmn]
  
  #Now loop over the remaining alternative intserctions (if any) and identify.
  #This code accounts for the fact that the only available insection may be a cpt that has already been taken by the maxima.
  if (length(obs_alt_check) > 0){
    for (xx in 1:length(obs_alt_check)){
      curr_alt <- obs_alt_check[[xx]]
      curr_alt_rmn <- curr_alt[!(curr_alt %in% obs_wgts_max)]  #strips out the maxima already taken.
      if (length(curr_alt_rmn) > 0){
        obs_alt_check[[xx]] <- curr_alt_rmn
      } else {
        obs_alt_check[[xx]] <- 0
      }
    }
  }
  
  #Now map the alternatives back into the main array.
  obs_wgts_max[obs_ind_rmn] <- unlist(obs_alt_check)
  
  #Extract the corresponding intersection weights.
  cpts_wgts_val <- numeric()
  for (zz in 1:length(obs_wgts_max)){
    if (obs_wgts_max[zz] == 0){
      cpts_wgts_val[zz] <- 0
    } else {
      cpts_wgts_val[zz] <- cpts_fuzzy_eval[[zz]][which(obs_cpt_insct[[zz]] == obs_wgts_max[zz])]
    }
  }
  
  #Create an output data frame to write to table.
  cpts_mod_eval_metrics <- data.frame(obs_cpt_no=1:length(obs_wgts_max),mod_cpt_insct=obs_wgts_max,cpt_eval_score=cpts_wgts_val)
   
  #Also get the summed changepoint evaluation metric.
  SUMM_CPTS_EVAL <- sum(cpts_mod_eval_metrics$cpt_eval_score)
  
  #Normalise the changepoint evaluation metric to 0-1 scale. 
  MOD_CPTS_EVAL <- SUMM_CPTS_EVAL/length(cpts_mod_eval_metrics$cpt_eval_score)
  CORRECT_CPTS_EVAL <- MOD_CPTS_EVAL * (sum(cpts_mod_eval_metrics$cpt_eval_score != 0)/length(cpts_mod_eval_metrics$cpt_eval_score))
  
  #Add all the metrics to a summary data.frames.
  mod_tseries_stats <- data.frame(CORRECT_CPTS_EVAL=CORRECT_CPTS_EVAL, NORMALIZED_CPT_METRIC=MOD_CPTS_EVAL)
  
  #Pass out the results.
  cpts_proc_out <- list(cpts_mod_eval_metrics=cpts_mod_eval_metrics,mod_tseries_stats=mod_tseries_stats)
  return(cpts_proc_out)
  
  #Close the function.
}
##########

if (length(CoreIDs) == 1) {
  i = 1
  ### Calculations
  ### Select data/sediment cores from dictionaries that has proxy data
  coreid <- names(proxy_ts)[i]
  core_models <- c(dict_model_name[[coreid]])
  core_data <- dict_SR_median_age[[coreid]]
  core_proxy <- proxy_ts[[coreid]]
  ### Initialize core-specific result variables
  core_result_list <- list()
  core_fitting_values <- c()
  ### Calculate change points with confidence intervals for each model
  for (m in core_models) {
    CI_for_TS <- cpts_currts_CI(core_data[[m]], curr_minseg, curr_cptmethod, curr_nreps, 'MOD')
    core_result_list[[m]] <- CI_for_TS$cpt_summar
  }
  ### Calculate change point within the proxy data
  CI_for_TS <- cpts_currts_CI(core_proxy, curr_minseg, curr_cptmethod, curr_nreps, 'OBS')
  core_result_list[['Proxy']] <- CI_for_TS$cpt_summary
  ### Compare the fitting between the proxy data and the models
  for (m in core_models){
    suppressWarnings({
      eval_value <- cpts_currts_eval(core_proxy, core_data[[m]], core_result_list[['Proxy']], core_result_list[[m]])
    })
    core_fitting_values[m] <- eval_value$mod_tseries_stats$CORRECT_CPTS_EVAL
  }
  ### Use CoreID to assign core-specific results to overall results
  core_fitting_values <- list(core_fitting_values)
  names(core_fitting_values) <- coreid
  core_result_list <- setNames(list(core_result_list), coreid)
  core_optimization_result <- c(core_result_list, core_fitting_values)
  return(core_optimization_result)
  
} else{
  ### Calculations
  optimization_parallel = function(...){
    ### Select data/sediment cores from dictionaries that has proxy data
    coreid <- names(proxy_ts)[i]
    core_models <- c(dict_model_name[[coreid]])
    core_data <- dict_SR_median_age[[coreid]]
    core_proxy <- proxy_ts[[coreid]]
    ### Initialize core-specific result variables
    core_result_list <- list()
    core_fitting_values <- c()
    ### Calculate change points with confidence intervals for each model
    for (m in core_models) {
      CI_for_TS <- cpts_currts_CI(core_data[[m]], curr_minseg, curr_cptmethod, curr_nreps, 'MOD')
      core_result_list[[m]] <- CI_for_TS$cpt_summar
    }
    ### Calculate change point within the proxy data
    CI_for_TS <- cpts_currts_CI(core_proxy, curr_minseg, curr_cptmethod, curr_nreps, 'OBS')
    core_result_list[['Proxy']] <- CI_for_TS$cpt_summary
    ### Compare the fitting between the proxy data and the models
    for (m in core_models){
      suppressWarnings({
        eval_value <- cpts_currts_eval(core_proxy, core_data[[m]], core_result_list[['Proxy']], core_result_list[[m]])
        })
      core_fitting_values[m] <- eval_value$mod_tseries_stats$CORRECT_CPTS_EVAL
    }
    ### Use CoreID to assign core-specific results to overall results
    core_fitting_values <- list(core_fitting_values)
    names(core_fitting_values) <- coreid
    core_result_list <- setNames(list(core_result_list), coreid)
    core_optimization_result <- c(core_result_list, core_fitting_values)
    return(core_optimization_result)
    }
  
  ### Initialize cluster
  no_cores <- detectCores(logical = TRUE)
  if (no_cores < length(names(proxy_ts))) {
    cl = makeCluster(no_cores*0.8, outfile = "", autoStop = TRUE)
    } else {cl = makeCluster(length(names(proxy_ts)), outfile = "", autoStop = TRUE)} 
  registerDoSNOW(cl)
  seed <- 211109
  
  ## Give data to cluster
  seq_id_all <- 1:length(names(proxy_ts))
  clusterExport(cl,list('dict_SR_median_age','dict_model_name','proxy_ts')) 
  
  ## Run function in parallel in cluster
  optimization_result <- foreach(i = seq_id_all
                                 ,.combine = 'c'
                                 ,.multicombine = TRUE
                                 ,.maxcombine = 1000       
                                 ,.options.RNG=seed
                               ) %dorng% {
                                 suppressPackageStartupMessages(c(library('forecast'),
                                                                  library('tseries'),
                                                                  library('lubridate'),
                                                                  library('changepoint'),
                                                                  library('dplyr'),
                                                                  library('DescTools'),
                                                                  library('sets'),
                                                                  library('FuzzyNumbers'),
                                                                  library('Metrics'),
                                                                  library('knitr'),
                                                                  library('maptools'),
                                                                  library('raster')))
                                 tryCatch(
                                   optimization_parallel(i, dict_SR_median_age, dict_model_name, proxy_ts)
                                   ,error = function(e){
                                     message(sprintf(" Caught an error in task %d! (%s)", i, names(proxy_ts)[i]))
                                     print(e)
                                   }
                                 )  
                               }
  
  stopCluster(cl)
  rm(list = "cl")
  gc()
  registerDoSEQ()
}

result_list <- list()
fitting_values <- list()
for (i in 1:length(optimization_result)){
  if ((i %% 2) == 0){
    fitting_values <- c(fitting_values, optimization_result[i])
  } else {
    result_list <- c(result_list, optimization_result[i])
  }
}

return(result_list)
return(fitting_values)