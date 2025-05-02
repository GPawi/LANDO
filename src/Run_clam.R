### LANDO Clam runner script — robust, adaptive, full chron output, best-fit optional ###

# Load libraries
suppressPackageStartupMessages({
  library(rice)
  library(rintcal)
  library(clam)
  library(R.devices)
  library(tidyverse)
  library(data.table)
  library(future)
  library(furrr)
})

# Set parallel plan
plan(multisession, workers = floor(availableCores(logical = TRUE) * 0.8))

# Inputs (assumes clam_Frame, CoreLengths, CoreIDs, types_curve, poly_degree_curve, smoothness_curve, best_fit are defined)
clam_Frame <- clam_Frame %>% mutate(across(c(depth, thickness), as.numeric))
CoreLengths <- CoreLengths %>% mutate(corelength = as.integer(corelength))
seq_id_all <- seq_along(CoreIDs)

# Chron extractor
extract_chron_full <- function(core_id, cm_range, model_label, fit) {
  ncols <- ncol(chron)
  chron_matrix <- as.data.frame(chron[, seq_len(min(20000, ncols))])
  rownames(chron_matrix) <- NULL
  chron_matrix <- chron_matrix %>%
    mutate(
      model_label = model_label,
      core_id = core_id,
      depth_cm = cm_range,
      fit = fit
    ) %>%
    relocate(model_label, core_id, depth_cm, fit)
  return(chron_matrix)
}

# Main execution
clam_core_results <- future_map_dfr(seq_id_all, function(core) {
  core_id <- CoreIDs[[core]]

  core_selection <- clam_Frame %>%
    filter(str_detect(lab_ID, core_id)) %>%
    mutate(across(everything(), ~as.numeric(as.character(.))))

  clength <- CoreLengths %>% filter(coreid == core_id)
  core_max <- clength$corelength
  date_max <- plyr::round_any(max(core_selection$depth, na.rm = TRUE), 1, f = floor)

  n_depths <- length(unique(core_selection$depth))
  types <- types_curve
  poly_degree <- poly_degree_curve
  smoothness <- smoothness_curve

  if (n_depths < 4) types <- types[!types %in% c(2)]
  if (n_depths < 6) types <- types[!types %in% c(4, 5)]
  poly_degree <- poly_degree[poly_degree < n_depths]
  if (length(poly_degree) == 0) types <- types[types != 2]

  # Temp folder
  shared_dir <- file.path(tempdir(), paste0("clam_shared_", core_id))
  dir.create(shared_dir, showWarnings = FALSE)
  core_dir <- file.path(shared_dir, core_id)
  dir.create(core_dir, showWarnings = FALSE)

  input_file <- file.path(core_dir, paste0(core_id, ".csv"))
  core_selection %>%
    select(lab_ID, `14C_age`, cal_age, error, reservoir, depth, thickness) %>%
    write.csv(file = input_file, row.names = FALSE, quote = FALSE, na = "")

  # Runner
  run_clam_model <- function(type, smooth = NULL, dmax) {
    suppressWarnings(R.devices::suppressGraphics({
      clam(core = core_id, coredir = shared_dir, type = type, smooth = smooth,
           its = 20000, dmin = 0, dmax = dmax,
           plotpdf = FALSE, plotpng = FALSE, plotname = FALSE)
    }))

    if (!exists("chron", inherits = TRUE)) {
      label <- if (!is.null(smooth)) {
        if (type == 2) sprintf("type %d degree %d", type, smooth)
        else sprintf("type %d smooth %.1f", type, smooth)
      } else sprintf("type %d", type)
      cat(sprintf("❌ Clam couldn’t create a chron for core %s — %s\n", core_id, label))
      return(NULL)
    }

    cm_range <- 0:floor(dmax)
    ncols <- ncol(chron)
    chron_matrix <- tryCatch(as.data.frame(chron[, seq_len(min(20000, ncols))]), error = function(e) NULL)

    if (is.null(chron_matrix) || nrow(chron_matrix) != length(cm_range)) {
      label <- if (!is.null(smooth)) {
        if (type == 2) sprintf("type %d degree %d", type, smooth)
        else sprintf("type %d smooth %.1f", type, smooth)
      } else sprintf("type %d", type)
      cat(sprintf("❌ Clam couldn’t match depth range for core %s — %s\n", core_id, label))
      return(NULL)
    }

    model_label <- paste0("clam_T", type,
                          if (!is.null(smooth)) {
                            if (type == 2) sprintf("_D%d", smooth)
                            else sprintf("_S%d", as.integer(smooth * 10))
                          } else "")
    fit_value <- tryCatch(get("fit", envir = parent.env(environment())), error = function(e) NA_real_)

    cat(sprintf("✅ Finished core %s — %s\n", core_id, model_label))
    chron_df <- extract_chron_full(core_id, cm_range, model_label, fit_value)
    rm(list = "chron", envir = .GlobalEnv)
    return(chron_df)
  }

  # Collect all results
  all_results <- list()
  for (type in types) {
    if (type %in% c(1, 3)) {
      all_results <- c(all_results, list(run_clam_model(type, dmax = core_max)))
    } else if (type == 2) {
      all_results <- c(all_results, lapply(poly_degree, function(d) run_clam_model(type, smooth = d, dmax = core_max)))
    } else if (type == 4) {
      all_results <- c(all_results, lapply(smoothness, function(s) run_clam_model(type, smooth = s, dmax = core_max)))
    } else if (type == 5) {
      all_results <- c(all_results, lapply(smoothness, function(k) run_clam_model(type, smooth = k, dmax = date_max)))
    }
  }

  all_results <- compact(all_results)

  if (best_fit && length(all_results) > 1 && all(sapply(all_results, function(x) "fit" %in% colnames(x)))) {
    fits <- sapply(all_results, function(x) x$fit[1])
    valid_fits <- which(!is.na(fits) & is.finite(fits))
  
    if (length(valid_fits) == 0) {
      warning(sprintf("⚠️ No valid fits for core %s — returning all models instead.", core_id))
      result_types <- rbindlist(all_results, fill = TRUE)
    } else {
      best_idx <- valid_fits[which.min(fits[valid_fits])]
      result_types <- all_results[[best_idx]]
    }
  } else {
    result_types <- rbindlist(all_results, fill = TRUE)
  }

  unlink(shared_dir, recursive = TRUE, force = TRUE)
  return(result_types)

}, .options = furrr_options(seed = TRUE))

# Cleanup
plan(sequential)
gc()

clam_core_results