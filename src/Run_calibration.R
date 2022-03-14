### Script to calibrate dates for LANDO ###
## Load libraries
suppressPackageStartupMessages(c(library('hamstr'),
                                 library('rstan'),
                                 library('Bchron'),
                                 library('tidyverse')))

## Load data and calibrate

calib_Frame = calib_Frame %>%
  mutate_all(type.convert,as.is = TRUE) %>%
  mutate_at(c("ages", "ageSds"), as.integer)
cal.ages = BchronCalibrate(ages = calib_Frame$ages, ageSds = calib_Frame$ageSds, calCurves = calib_Frame$calCurves, allowOutside = TRUE)
suppressWarnings({
  calib_Frame$ages_calib <- sapply(cal.ages, function(x){
    hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"]
  })
  
  calib_Frame$ages_calib_Sds <- sapply(cal.ages, function(x){
    hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"]
  })})

calib_dates = calib_Frame[, c(1, 7:9)]
return(calib_dates)