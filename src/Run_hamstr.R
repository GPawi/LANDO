### Script to run hamstr in LANDO ###

# ---- Load libraries ----
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

# ---- Helper to calibrate dates with Bchron ----
calibrate_ages <- function(df) {
  df <- df %>%
    mutate(across(c(ages, ageSds), as.integer))

  cal <- BchronCalibrate(
    ages = df$ages,
    ageSds = df$ageSds,
    calCurves = df$calCurves,
    allowOutside = TRUE
  )

  suppressWarnings({
    df$ages_calib <- sapply(cal, \(x) hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["mean"])
    df$ages_calib_Sds <- sapply(cal, \(x) hamstr:::SummariseEmpiricalPDF(x$ageGrid, x$densities)["sd"])
  })

  return(df)
}

# ---- Hamstr runner for one core ----
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
    stan_sampler_args = list(iter = iter, control = list(max_treedepth = 15))
  )

  pred <- predict(fit, depth = seq(top_depth, bottom_depth, by = 1)) |>
    as.data.frame() |>
    mutate(depth = paste(core_id, depth, sep = " ")) |>
    pivot_wider(names_from = iter, values_from = age)

  pred <- pred[, 1:min(ncol(pred), 10001)]  # Limit columns
  message(sprintf("✅ Done with core: %s", core_id))
  return(pred)
}

# ---- Run block ----
hamstr_Frame <- hamstr_Frame |>
  mutate(across(everything(), \(x) type.convert(x, as.is = TRUE))) |>
  calibrate_ages()

if (length(CoreIDs) == 1) {
  hamstr_core_results <- run_hamstr_for_core(CoreIDs[[1]], hamstr_Frame, CoreLengths)
} else {
  n_cores <- min(detectCores(logical = TRUE), length(CoreIDs))
  cl <- makeCluster(n_cores, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  # Wrapped safe runner with libraries loaded inside
  run_safe_hamstr <- function(i) {
    suppressPackageStartupMessages({
      library(hamstr)
      library(Bchron)
      library(tidyverse)
    })

    core_id <- CoreIDs[[i]]
    tryCatch(
      run_hamstr_for_core(core_id, hamstr_Frame, CoreLengths),
      error = function(e) {
        message(sprintf("⚠️ Error in core %s: %s", core_id, e$message))
        NULL
      }
    )
  }

  hamstr_core_results <- foreach(i = seq_along(CoreIDs),
                                 .combine = bind_rows,
                                 .options.RNG = 20201224) %dorng% {
    run_safe_hamstr(i)
  }

  stopCluster(cl)
  registerDoSEQ()
}

return(hamstr_core_results)
