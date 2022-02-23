### Script to define reservoir values with hamstr in LANDO ###
## Load libraries
suppressPackageStartupMessages(c(library('hamstr'),
                                 library('rstan'),
                                 library('Bchron'),
                                 library('tidyverse'),
                                 library('parallel'),
                                 library('foreach'),
                                 library('doSNOW'),
                                 library('doRNG')))
set.seed(20201224)

### Parallel add - RC parallel

RC_parallel <- function(...) {
  if (parallel::detectCores() >= 3) options(mc.cores = 3)
  core_selection <- RC_Frame %>% filter(str_detect(id, RC_CoreIDs[[i]]))
  clength <- RC_CoreLengths %>% filter(str_detect(coreid, RC_CoreIDs[[i]]))
  suppressWarnings(hamstr_fitting <- hamstr(depth = core_selection$position,
                           obs_age = core_selection$ages_calib,
                           obs_err = core_selection$ages_calib_Sds,
                           top_depth = 0,
                           bottom_depth = clength$corelength,
                           K = K, #c(10, 10),
                           iter = 2000)) # 2000
  age.mods.interp <- hamstr:::predict.hamstr_fit(hamstr_fitting,depth = 0)
  result_individual_core <- as.data.frame(age.mods.interp)
  result_individual_core$depth <- factor(result_individual_core$depth) 
  result_individual_core$depth <- paste(RC_CoreIDs[[i]], result_individual_core$depth)
  result_individual_core <- spread(result_individual_core, iter, age)
  message(sprintf("Done with core number: %d out of %d", i, length(RC_CoreIDs)))
  return (result_individual_core)
}


## Parallel add - Initialize cluster
no_cores <- detectCores(logical = TRUE)
if ((no_cores/4) < length(RC_CoreIDs)) {
  cl <- makeCluster((no_cores/4), outfile = "", autoStop = TRUE)
  } else {cl <- makeCluster(length(RC_CoreIDs), outfile = "", autoStop = TRUE)} 
registerDoSNOW(cl)
seed <- 210330


## Load data and calibrate

RC_Frame = RC_Frame %>%
    mutate_all(type.convert, as.is = TRUE) %>%
    mutate_at(c("ages", "ageSds"), as.integer)
cal.ages = BchronCalibrate(ages = RC_Frame$ages, ageSds = RC_Frame$ageSds, calCurves = RC_Frame$calCurves, allowOutside = TRUE)
suppressWarnings({RC_Frame$ages_calib <- sapply(cal.ages, function(x){
    hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"]
  })
  
RC_Frame$ages_calib_Sds <- sapply(cal.ages, function(x){
    hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"]
  })})


## Parallel add - cluster export data
seq_id_all <- 1:length(RC_CoreIDs)
clusterExport(cl,list('RC_parallel','RC_Frame','RC_CoreIDs', 'RC_CoreLengths'))


## Run hamstr and prepare output

reservoir_core_results <- foreach(i = seq_id_all 
                              #,.combine='rbind'
                              ,.combine=dplyr::bind_rows
                              ,.multicombine = TRUE
                              ,.maxcombine = 1000
                              ,.inorder = FALSE
                              ,.packages=c('tidyverse', 'hamstr', 'rstan', 'foreach', 'parallel')
                              ,.options.RNG=seed
                              
) %dorng% {
  tryCatch(
    RC_parallel(i, RC_Frame, RC_CoreIDs)
     ,error = function(e){
      message(sprintf(" Caught an error in task %d! (%s)", i, RC_CoreIDs[[i]]))
      print(e)
    }
  )
}

stopCluster(cl)
rm(list = "cl")
gc()
registerDoSEQ()

return(reservoir_core_results)
