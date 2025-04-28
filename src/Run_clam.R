### Script to run clam in LANDO (future version - fixed!) ###

# Load libraries
suppressPackageStartupMessages({
  library(rice)
  library(rintcal)
  library(clam)
  library(R.devices)
  library(tidyverse)
  library(future)
  library(furrr)
})

# Initialize future plan
no_cores <- availableCores(logical = TRUE)
plan(multisession, workers = floor(no_cores * 0.8))

# Prepare data
seq_id_all <- seq_along(CoreIDs)
clam_Frame <- clam_Frame %>% mutate(across(c(depth, thickness), as.numeric))
CoreLengths <- CoreLengths %>% mutate(corelength = as.integer(corelength))

# Define helper function
run_clam_type <- function(type, core_id, smooth = NULL, dmax, core_selection, core_max, date_max) {
  # Worker-local temp dir
  worker_tmpdir <- tempfile(pattern = paste0("clam_", core_id, "_"))
  dir.create(worker_tmpdir, showWarnings = FALSE)

  # Important: core-specific subdirectory
  core_subdir <- file.path(worker_tmpdir, core_id)
  dir.create(core_subdir, showWarnings = FALSE)

  # File path inside core folder
  input_file <- file.path(core_subdir, paste0(core_id, ".csv"))

  # Write the clam input file
  core_selection %>%
    select(lab_ID, `14C_age`, cal_age, error, reservoir, depth, thickness) %>%
    write.csv(file = input_file, row.names = FALSE, quote = FALSE, na = "")

  # Now run clam
  tmpfile <- tempfile(tmpdir = worker_tmpdir)
  sink(tmpfile)
  suppressWarnings(suppressMessages(
    suppressPackageStartupMessages(
      R.devices::suppressGraphics({
        clam(core = core_id, coredir = worker_tmpdir, type = type, smooth = smooth,
             its = 20000, dmin = 0, dmax = dmax,
             plotpdf = FALSE, plotpng = FALSE, plotname = FALSE)
      })
    )
  ))
  sink()

  # Read clam output
  out_file <- file.path(core_subdir, paste0(core_id, ".out"))
  if (!file.exists(out_file)) {
    cat(sprintf("⚠️  No output found for core %s, type %d\n", core_id, type))
    return(Inf)
  }

  z <- readLines(out_file)

  if (any(grepl("!!! Too many models with age reversals!!!", z))) {
    cat(sprintf("⚠️  Too many models with age reversals for core %s, type %d\n", core_id, type))
    return(Inf)
  }

  fit_line <- subset(z, grepl("  Fit (-log, lower is better): ", z))
  if (length(fit_line) > 0) {
    fit <- as.numeric(sub("  Fit (-log, lower is better): ", "", fit_line))
    if (is.infinite(fit)) {
      cat(sprintf("⚠️  Inf model fit for core %s, type %d\n", core_id, type))
      return(Inf)
    } else {
      cat(sprintf("✅ Successfully ran core %s, type %d (fit = %.2f)\n", core_id, type, fit))
      return(fit)
    }
  } else {
    cat(sprintf("⚠️  No fit information for core %s, type %d\n", core_id, type))
    return(Inf)
  }
}

# Run over cores
clam_core_results <- future_map_dfr(seq_id_all, function(core) {

  core_id <- CoreIDs[[core]]

  # Core preparation
  core_selection <- clam_Frame %>%
    filter(str_detect(lab_ID, core_id)) %>%
    mutate(
      `14C_age` = ifelse(`14C_age` == "", NA, as.numeric(`14C_age`)),
      cal_age = ifelse(cal_age == "", NA, as.numeric(cal_age)),
      error = as.numeric(error),
      reservoir = as.numeric(reservoir),
      depth = as.numeric(depth),
      thickness = as.numeric(thickness)
    )
  clength <- CoreLengths %>% filter(coreid == core_id)
  date_max <- plyr::round_any(max(core_selection$depth, na.rm = TRUE), 1, f = floor)
  core_max <- clength$corelength

  types <- types_curve
  smoothness <- smoothness_curve
  poly_degree <- poly_degree_curve

  if (length(unique(core_selection$depth)) < 4) {
    types <- types[types != 2]
  }
  if (any(poly_degree >= length(unique(core_selection$depth)))) {
    poly_degree <- 1:(length(unique(core_selection$depth)) - 1)
  }

  # Run types
  result_types <- map_dfr(types, function(type) {

    if (type %in% c(1, 3)) {
      fit <- run_clam_type(type, core_id, dmax = core_max, core_selection = core_selection, core_max = core_max, date_max = date_max)
      if (fit != Inf) {
        chron_model <- as.data.frame(chron[, 1:10000])
        mid <- outer(core_id, seq(0, core_max, by = 1), paste)
        rownames(chron_model) <- outer(mid, sprintf('-clam_T%d', type), paste0)
        chron_model$fit <- fit
        return(chron_model)
      }
    }
    else if (type == 2) {
      map_dfr(poly_degree, function(degree) {
        fit <- run_clam_type(type, core_id, smooth = degree, dmax = core_max, core_selection = core_selection, core_max = core_max, date_max = date_max)
        if (fit != Inf) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(core_id, seq(0, core_max, by = 1), paste)
          rownames(chron_model) <- outer(mid, sprintf('-clam_T2_D%d', degree), paste0)
          chron_model$fit <- fit
          return(chron_model)
        }
      })
    }
    else if (type == 4) {
      map_dfr(smoothness, function(s) {
        fit <- run_clam_type(type, core_id, smooth = s, dmax = core_max, core_selection = core_selection, core_max = core_max, date_max = date_max)
        if (fit != Inf) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(core_id, seq(0, core_max, by = 1), paste)
          rownames(chron_model) <- outer(mid, sprintf('-clam_T4_S%d', as.integer(s * 10)), paste0)
          chron_model$fit <- fit
          return(chron_model)
        }
      })
    }
    else if (type == 5) {
      map_dfr(smoothness, function(k) {
        fit <- run_clam_type(type, core_id, smooth = k, dmax = date_max, core_selection = core_selection, core_max = core_max, date_max = date_max)
        if (fit != Inf) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(core_id, seq(0, date_max, by = 1), paste)
          rownames(chron_model) <- outer(mid, sprintf('-clam_T5_S%d', as.integer(k * 10)), paste0)
          chron_model$fit <- fit
          return(chron_model)
        }
      })
    }
  })

  cat(sprintf("✅ Finished core %s — %d of %d\n", core_id, core, length(CoreIDs)))

  if (best_fit && !is.null(result_types)) {
    result_types <- result_types[result_types$fit == min(result_types$fit), ]
  }

  return(result_types)

}, .options = furrr_options(seed = TRUE))

# Final cleanup
plan(sequential)
gc()

clam_core_results$fit <- NULL
return(clam_core_results)