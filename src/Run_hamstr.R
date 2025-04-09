### Updated Script to Run hamstr in LANDO ###

suppressPackageStartupMessages({
  library(hamstr)
  library(rstan)
  library(Bchron)
  library(tidyverse)
  library(parallel)
  library(foreach)
  library(doSNOW)
  library(doRNG)
})

set.seed(20201224)

# Function to summarize Bchron calibration results
summarise_calibrated_ages <- function(cal.ages) {
  list(
    means = sapply(cal.ages, function(x) hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"]),
    sds   = sapply(cal.ages, function(x) hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"])
  )
}

# Main function for single or multi-core hamstr modeling
run_hamstr <- function(CoreIDs, hamstr_Frame, CoreLengths, K = c(10, 10)) {
  hamstr_Frame <- hamstr_Frame %>%
    mutate(across(everything(), type.convert, as.is = TRUE)) %>%
    mutate(across(c("ages", "ageSds"), as.integer))
  cal.ages <- BchronCalibrate(
    ages = hamstr_Frame$ages,
    ageSds = hamstr_Frame$ageSds,
    calCurves = hamstr_Frame$calCurves,
    allowOutside = TRUE
  )
  summaries <- summarise_calibrated_ages(cal.ages)
  hamstr_Frame$ages_calib <- summaries$means
  hamstr_Frame$ages_calib_Sds <- summaries$sds

  if (length(CoreIDs) == 1) {
    i <- 1
    core_selection <- filter(hamstr_Frame, str_detect(id, CoreIDs[[i]]))
    clength <- filter(CoreLengths, str_detect(coreid, CoreIDs[[i]]))
    fit <- hamstr(
      depth = core_selection$position,
      obs_age = core_selection$ages_calib,
      obs_err = core_selection$ages_calib_Sds,
      top_depth = 0,
      bottom_depth = clength$corelength,
      min_age = -150,
      K = K
    )
    interp <- hamstr:::predict.hamstr_fit(fit, depth = seq(0, clength$corelength, by = 1))
    df <- as.data.frame(interp)
    df$depth <- factor(df$depth)
    df$depth <- paste(CoreIDs[[i]], df$depth)
    df <- pivot_wider(df, names_from = iter, values_from = age)
    return(df[, 1:min(10001, ncol(df))])
  } else {
    hamstr_parallel <- function(i) {
      core_selection <- filter(hamstr_Frame, str_detect(id, CoreIDs[[i]]))
      clength <- filter(CoreLengths, str_detect(coreid, CoreIDs[[i]]))
      fit <- hamstr(
        depth = core_selection$position,
        obs_age = core_selection$ages_calib,
        obs_err = core_selection$ages_calib_Sds,
        top_depth = 0,
        bottom_depth = clength$corelength,
        min_age = -150,
        K = K
      )
      interp <- hamstr:::predict.hamstr_fit(fit, depth = seq(0, clength$corelength, by = 1))
      df <- as.data.frame(interp)
      df$depth <- factor(df$depth)
      df$depth <- paste(CoreIDs[[i]], df$depth)
      df <- pivot_wider(df, names_from = iter, values_from = age)
      return(df[, 1:min(10001, ncol(df))])
    }

    no_cores <- detectCores(logical = TRUE)
    cl <- makeCluster(min(length(CoreIDs), max(1, floor(no_cores / 4))), outfile = "", autoStop = TRUE)
    registerDoSNOW(cl)
    seed <- 210330
    clusterExport(cl, list("hamstr_parallel", "hamstr_Frame", "CoreIDs", "CoreLengths", "K"))

    results <- foreach(i = seq_along(CoreIDs), .combine = bind_rows, .options.RNG = seed) %dorng% {
      suppressPackageStartupMessages({
        library(tidyverse)
        library(hamstr)
        library(rstan)
        library(foreach)
        library(parallel)
      })
      tryCatch(
        hamstr_parallel(i),
        error = function(e) {
          message(sprintf("Error in core %d (%s): %s", i, CoreIDs[[i]], e$message))
          return(NULL)
        }
      )
    }

    stopCluster(cl)
    registerDoSEQ()
    return(results)
  }
}
