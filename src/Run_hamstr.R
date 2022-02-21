### Script to run hamstr in LANDO ###
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

### Parallel add - hamstr parallel

hamstr_parallel <- function(...) {
  if (parallel::detectCores() >= 3) options(mc.cores = 3)
  core_selection <- hamstr_Frame %>% filter(str_detect(id, CoreIDs[[i]]))
  clength <- CoreLengths %>% filter(str_detect(coreid, CoreIDs[[i]]))
  hamstr_fitting <- hamstr(depth = core_selection$position,
                           obs_age = core_selection$ages_calib,
                           obs_err = core_selection$ages_calib_Sds,
                           top_depth = 0,
                           bottom_depth = clength$corelength,
                           K = K, #c(10, 10),
                           iter = 6667)
  age.mods.interp <- hamstr:::predict.hamstr_fit(hamstr_fitting,depth = seq(0,clength$corelength, by = 1))
  result_individual_core <- as.data.frame(age.mods.interp)
  result_individual_core$depth <- factor(result_individual_core$depth) 
  result_individual_core$depth <- paste(CoreIDs[[i]], result_individual_core$depth)
  result_individual_core <- spread(result_individual_core, iter, age)
  result_individual_core <- result_individual_core[, 1:10001]
  message(sprintf("Done with core number: %d out of %d", i, length(CoreIDs)))
  return (result_individual_core)
}


## Parallel add - Initialize cluster
no_cores <- detectCores(logical = TRUE)
if ((no_cores/4) < length(CoreIDs)) {
  cl <- makeCluster((no_cores/4), outfile = "", autoStop = TRUE)
  } else {cl <- makeCluster(length(CoreIDs), outfile = "", autoStop = TRUE)} 
registerDoSNOW(cl)
seed <- 210330


## Load data and calibrate

hamstr_Frame = hamstr_Frame %>%
    mutate_all(type.convert,as.is = TRUE) %>%
    mutate_at(c("ages", "ageSds"), as.integer)
cal.ages = BchronCalibrate(ages = hamstr_Frame$ages, ageSds = hamstr_Frame$ageSds, calCurves = hamstr_Frame$calCurves, allowOutside = TRUE)
suppressWarnings({
  hamstr_Frame$ages_calib <- sapply(cal.ages, function(x){
    hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"]
  })
  
  hamstr_Frame$ages_calib_Sds <- sapply(cal.ages, function(x){
    hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"]
  })})


## Parallel add - cluster export data
seq_id_all <- 1:length(CoreIDs)
clusterExport(cl,list('hamstr_parallel','hamstr_Frame','CoreIDs','CoreLengths'))


## Run hamstr and prepare output

hamstr_core_results <- foreach(i = seq_id_all 
                              #,.combine='rbind'
                              ,.combine=dplyr::bind_rows
                              ,.multicombine = TRUE
                              ,.maxcombine = 1000
                              ,.inorder = FALSE
                              ,.packages=c('tidyverse', 'hamstr', 'rstan', 'foreach', 'parallel')
                              ,.options.RNG=seed
                              
) %dorng% {
  tryCatch(
    hamstr_parallel(i, hamstr_Frame, CoreIDs)
     ,error = function(e){
      message(sprintf(" Caught an error in task %d! (%s)", i, CoreIDs[[i]]))
      print(e)
    }
  )
}

stopCluster(cl)
rm(list = "cl")
gc()
registerDoSEQ()

return(hamstr_core_results)
