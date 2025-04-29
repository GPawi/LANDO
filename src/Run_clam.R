### Script to run clam in LANDO (future parallel version, using a real shared folder!) ###

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

# Prepare shared folder (important: NOT tempdir)
shared_dir <- file.path(getwd(), "clam_shared")
dir.create(shared_dir, showWarnings = FALSE, recursive = TRUE)

# Prepare data
seq_id_all <- seq_along(CoreIDs)
clam_Frame <- clam_Frame %>% mutate(across(c(depth, thickness), as.numeric))
CoreLengths <- CoreLengths %>% mutate(corelength = as.integer(corelength))

# Write input CSVs for each core first
walk(seq_id_all, function(core) {
  core_id <- CoreIDs[[core]]

  # Core selection
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

  # Make core directory
  core_dir <- file.path(shared_dir, core_id)
  dir.create(core_dir, showWarnings = FALSE, recursive = TRUE)

  # Write the .csv file
  input_file <- file.path(core_dir, paste0(core_id, ".csv"))
  core_selection %>%
    select(lab_ID, `14C_age`, cal_age, error, reservoir, depth, thickness) %>%
    write.csv(file = input_file, row.names = FALSE, quote = FALSE, na = "")
})

# Define helper function
run_clam_type <- function(type, core_id, smooth = NULL, dmax) {
  core_dir <- file.path(shared_dir, core_id)
  input_file <- file.path(core_dir, paste0(core_id, ".csv"))

  if (!file.exists(input_file)) {
    cat(sprintf("⚠️  Input CSV missing for core %s\n", core_id))
    return(list(fit = Inf, smooth = smooth))
  }

  tmpfile <- tempfile(tmpdir = core_dir)
  sink(tmpfile)
  suppressWarnings(suppressMessages(
    suppressPackageStartupMessages(
      R.devices::suppressGraphics({
        clam(core = core_id, coredir = shared_dir, type = type, smooth = smooth,
             its = 20000, dmin = 0, dmax = dmax,
             plotpdf = FALSE, plotpng = FALSE, plotname = FALSE)
      })
    )
  ))
  sink()

  out_file <- file.path(core_dir, paste0(core_id, ".out"))
  if (!file.exists(out_file)) {
    cat(sprintf("⚠️  No output for core %s, type %d\n", core_id, type))
    return(list(fit = Inf, smooth = smooth))
  }

  z <- readLines(out_file)

  if (any(grepl("!!! Too many models with age reversals!!!", z))) {
    cat(sprintf("⚠️  Too many reversals for core %s, type %d\n", core_id, type))
    return(list(fit = Inf, smooth = smooth))
  }

  fit_line <- subset(z, grepl("  Fit (-log, lower is better): ", z))
  if (length(fit_line) > 0) {
    fit <- as.numeric(sub("  Fit (-log, lower is better): ", "", fit_line))
    if (is.infinite(fit)) {
      cat(sprintf("⚠️  Inf model fit for core %s, type %d\n", core_id, type))
      return(list(fit = Inf, smooth = smooth))
    } else {
      cat(sprintf("✅ Core %s type %d%s fit = %.2f\n",
                  core_id, type,
                  if (!is.null(smooth)) paste0(", smooth=", smooth) else "",
                  fit))
      return(list(fit = fit, smooth = smooth))
    }
  } else {
    cat(sprintf("⚠️  No fit found for core %s, type %d\n", core_id, type))
    return(list(fit = Inf, smooth = smooth))
  }
}

# Parallel modeling
clam_core_results <- future_map_dfr(seq_id_all, function(core) {
  core_id <- CoreIDs[[core]]

  core_selection <- clam_Frame %>%
    filter(str_detect(lab_ID, core_id))
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

  # Modeling
  result_types <- map_dfr(types, function(type) {
    if (type %in% c(1, 3)) {
      res <- run_clam_type(type, core_id, dmax = core_max)
      if (res$fit != Inf) {
        chron_model <- as.data.frame(chron[, 1:10000])
        mid <- outer(core_id, seq(0, core_max, by = 1), paste)
        rownames(chron_model) <- outer(mid, sprintf('-clam_T%d', type), paste0)
        chron_model$fit <- res$fit
        return(chron_model)
      }
    } else if (type == 2) {
      map_dfr(poly_degree, function(degree) {
        res <- run_clam_type(type, core_id, smooth = degree, dmax = core_max)
        if (res$fit != Inf) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(core_id, seq(0, core_max, by = 1), paste)
          rownames(chron_model) <- outer(mid, sprintf('-clam_T2_D%d', degree), paste0)
          chron_model$fit <- res$fit
          return(chron_model)
        }
      })
    } else if (type == 4) {
      map_dfr(smoothness, function(s) {
        res <- run_clam_type(type, core_id, smooth = s, dmax = core_max)
        if (res$fit != Inf) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(core_id, seq(0, core_max, by = 1), paste)
          rownames(chron_model) <- outer(mid, sprintf('-clam_T4_S%d', as.integer(s * 10)), paste0)
          chron_model$fit <- res$fit
          return(chron_model)
        }
      })
    } else if (type == 5) {
      map_dfr(smoothness, function(k) {
        res <- run_clam_type(type, core_id, smooth = k, dmax = date_max)
        if (res$fit != Inf) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(core_id, seq(0, date_max, by = 1), paste)
          rownames(chron_model) <- outer(mid, sprintf('-clam_T5_S%d', as.integer(k * 10)), paste0)
          chron_model$fit <- res$fit
          return(chron_model)
        }
      })
    }
  })

  cat(sprintf("✅ Finished core %s (%d of %d)\n", core_id, core, length(CoreIDs)))

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