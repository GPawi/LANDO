suppressPackageStartupMessages({
  library(hamstr)
  library(Bchron)
  library(tidyverse)
  library(parallel)
  library(foreach)
  library(doSNOW)
  library(doRNG)
})

set.seed(20201224)

## ---- Helper to calibrate dates with Bchron ----
calibrate_ages <- function(df) {
  df <- df %>%
    mutate(across(c(ages, ageSds), as.integer))
  
  cal <- BchronCalibrate(
    ages = df$ages,
    ageSds = df$ageSds,
    calCurves = df$calCurves,
    allowOutside = TRUE
  )
  
  df$ages_calib <- sapply(cal, \(x) SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"])
  df$ages_calib_Sds <- sapply(cal, \(x) SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"])
  df
}

## ---- Single core runner ----
run_hamstr_for_core <- function(core_id, hamstr_Frame, CoreLengths,
                                K_fine = 100, iter = 6667,
                                min_age = -150, top_depth = 0) {
  core_data <- hamstr_Frame %>% filter(str_detect(id, core_id))
  clength <- CoreLengths %>% filter(str_detect(coreid, core_id))
  bottom_depth <- clength$corelength

  fit <- hamstr(
    depth = core_data$position,
    obs_age = core_data$ages_calib,
    obs_err = core_data$ages_calib_Sds,
    min_age = min_age,
    top_depth = top_depth,
    bottom_depth = bottom_depth,
    K_fine = K_fine,
    stan_sampler_args = list(iter = iter)
  )

  pred <- predict(fit, depth = seq(top_depth, bottom_depth, by = 1)) |>
    as.data.frame() |>
    mutate(depth = paste(core_id, depth, sep = "_")) |>
    pivot_wider(names_from = iter, values_from = age)

  return(pred)
}

## ---- Run section ----
hamstr_Frame <- hamstr_Frame |>
  mutate(across(everything(), type.convert)) |>
  calibrate_ages()

if (length(CoreIDs) == 1) {
  result <- run_hamstr_for_core(CoreIDs[[1]], hamstr_Frame, CoreLengths)
} else {
  no_cores <- min(parallel::detectCores(logical = TRUE), length(CoreIDs))
  cl <- makeCluster(no_cores, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)
  clusterExport(cl, c("hamstr_Frame", "CoreLengths", "CoreIDs", "run_hamstr_for_core"))

  result <- foreach(i = seq_along(CoreIDs), .combine = bind_rows, .options.RNG = 20201224) %dorng% {
    core_id <- CoreIDs[[i]]
    tryCatch(
      run_hamstr_for_core(core_id, hamstr_Frame, CoreLengths),
      error = function(e) {
        message(sprintf("⚠️ Error in core %s: %s", core_id, e$message))
        NULL
      }
    )
  }

  stopCluster(cl)
  registerDoSEQ()
}

return(result)
