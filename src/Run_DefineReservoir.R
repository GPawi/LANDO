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

if (length(RC_CoreIDs) == 1) {
  i = 1
  ## Load data and calibrate
  RC_Frame = RC_Frame %>%
    mutate(across(everything(), ~type.convert(.x, as.is = TRUE))) %>%
    mutate(across(c("ages", "ageSds"), as.integer))
  cal.ages = BchronCalibrate(ages = RC_Frame$ages, ageSds = RC_Frame$ageSds, calCurves = RC_Frame$calCurves, allowOutside = TRUE)
  suppressWarnings({
    RC_Frame$ages_calib <- sapply(cal.ages, function(x){
      hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"]
    })
    RC_Frame$ages_calib_Sds <- sapply(cal.ages, function(x){
      hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"]
    })
  })
  
  ## Do calculations
  if (parallel::detectCores() >= 3) options(mc.cores = 3)
  core_selection <- RC_Frame %>% filter(str_detect(id, RC_CoreIDs[[i]]))
  clength <- RC_CoreLengths %>% filter(str_detect(coreid, RC_CoreIDs[[i]]))
  hamstr_fitting <- hamstr(depth = core_selection$position,
                           obs_age = core_selection$ages_calib,
                           obs_err = core_selection$ages_calib_Sds,
                           top_depth = 0,
                           bottom_depth = clength$corelength,
                           min_age = -150,
                           K_fine = K_fine,
                           stan_sampler_args = list(iter = 2000))
  age.mods.interp <- predict(hamstr_fitting, depth = 0)
  result_individual_core <- as.data.frame(age.mods.interp)
  result_individual_core$depth <- paste(RC_CoreIDs[[i]], factor(result_individual_core$depth))
  reservoir_core_results <- tidyr::pivot_wider(result_individual_core, names_from = iter, values_from = age)
  message(sprintf("Done with core number: %d out of %d", i, length(RC_CoreIDs)))
  return(reservoir_core_results)
  
} else {
  RC_parallel <- function(...) {
    if (parallel::detectCores() >= 3) options(mc.cores = 3)
    core_selection <- RC_Frame %>% filter(str_detect(id, RC_CoreIDs[[i]]))
    clength <- RC_CoreLengths %>% filter(str_detect(coreid, RC_CoreIDs[[i]]))
    hamstr_fitting <- hamstr(depth = core_selection$position,
                             obs_age = core_selection$ages_calib,
                             obs_err = core_selection$ages_calib_Sds,
                             top_depth = 0,
                             bottom_depth = clength$corelength,
                             min_age = -150,
                             K_fine = K_fine,
                             stan_sampler_args = list(iter = 2000))
    age.mods.interp <- predict(hamstr_fitting, depth = 0)
    result_individual_core <- as.data.frame(age.mods.interp)
    result_individual_core$depth <- paste(RC_CoreIDs[[i]], factor(result_individual_core$depth))
    result_individual_core <- tidyr::pivot_wider(result_individual_core, names_from = iter, values_from = age)
    message(sprintf("Done with core number: %d out of %d", i, length(RC_CoreIDs)))
    return(result_individual_core)
  }

  no_cores <- detectCores(logical = TRUE)
  cl <- if ((no_cores / 4) < length(RC_CoreIDs)) {
    makeCluster((no_cores / 4), outfile = "", autoStop = TRUE)
  } else {
    makeCluster(length(RC_CoreIDs), outfile = "", autoStop = TRUE)
  }
  registerDoSNOW(cl)
  seed <- 210330

  RC_Frame = RC_Frame %>%
    mutate(across(everything(), \(x) type.convert(x, as.is = TRUE))) %>%
    mutate(across(c("ages", "ageSds"), as.integer))
  cal.ages = BchronCalibrate(ages = RC_Frame$ages, ageSds = RC_Frame$ageSds, calCurves = RC_Frame$calCurves, allowOutside = TRUE)
  suppressWarnings({
    RC_Frame$ages_calib <- sapply(cal.ages, function(x){
      hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"]
    })
    RC_Frame$ages_calib_Sds <- sapply(cal.ages, function(x){
      hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"]
    })
  })

  seq_id_all <- 1:length(RC_CoreIDs)
  clusterExport(cl, list('RC_parallel', 'RC_Frame', 'RC_CoreIDs', 'RC_CoreLengths'))

  reservoir_core_results <- foreach(i = seq_id_all,
                                    .combine = dplyr::bind_rows,
                                    .multicombine = TRUE,
                                    .maxcombine = 1000,
                                    .inorder = FALSE,
                                    .options.RNG = seed) %dorng% {
    suppressPackageStartupMessages(c(library('tidyverse'), 
                                     library('hamstr'), 
                                     library('rstan'), 
                                     library('foreach'), 
                                     library('parallel')))
    tryCatch(
      RC_parallel(i, RC_Frame, RC_CoreIDs),
      error = function(e) {
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
}
