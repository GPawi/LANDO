### LANDO Clam runner script — stable double parallelization with clean logging and reduced memory ###

suppressPackageStartupMessages({
  library(clam)
  library(tidyverse)
  library(data.table)
  library(parallel)
  library(doParallel)
  library(foreach)
  library(R.devices)
})

# Ensure numeric types
clam_Frame <- clam_Frame %>% mutate(across(c(`14C_age`, cal_age, error, reservoir, depth, thickness), as.numeric))
CoreLengths <- CoreLengths %>% mutate(corelength = as.integer(corelength))
seq_id_all <- seq_along(CoreIDs)

# Outer loop (%do% for visibility)
clam_core_results <- foreach(core = seq_id_all, .combine = dplyr::bind_rows) %do% {

  suppressPackageStartupMessages({
    library(clam)
    library(tidyverse)
    library(data.table)
    library(R.devices)
  })

  core_id <- CoreIDs[[core]]
  message(sprintf("🌍 Starting core %s (%d of %d)", core_id, core, length(CoreIDs)))

  core_selection <- clam_Frame %>% filter(str_detect(lab_ID, core_id))
  clength <- CoreLengths %>% filter(coreid == core_id)
  core_max <- clength$corelength
  date_max <- floor(max(core_selection$depth, na.rm = TRUE))

  types <- types_curve
  poly_degree <- poly_degree_curve
  smoothness <- smoothness_curve
  n_depths <- length(unique(core_selection$depth))
  if (n_depths < 4) types <- types[!types %in% 2]
  if (n_depths < 6) types <- types[!types %in% c(4, 5)]
  poly_degree <- poly_degree[poly_degree < n_depths]

  shared_dir <- file.path(tempdir(), paste0("clam_", core_id))
  dir.create(file.path(shared_dir, core_id), recursive = TRUE, showWarnings = FALSE)

  write.csv(core_selection %>%
              select(lab_ID, `14C_age`, cal_age, error, reservoir, depth, thickness),
            file = file.path(shared_dir, core_id, paste0(core_id, ".csv")),
            row.names = FALSE, quote = FALSE)

  model_tasks <- list()
  for (type in types) {
    if (type %in% c(1, 3)) {
      model_tasks <- c(model_tasks, list(list(type = type, smooth = NULL, dmax = core_max)))
    } else if (type == 2) {
      model_tasks <- c(model_tasks, lapply(poly_degree, function(d) list(type = type, smooth = d, dmax = core_max)))
    } else if (type %in% c(4, 5)) {
      dmax_val <- ifelse(type == 5, date_max, core_max)
      model_tasks <- c(model_tasks, lapply(smoothness, function(s) list(type = type, smooth = s, dmax = dmax_val)))
    }
  }

  # Parallel inner loop
  inner_cl <- makeCluster(floor(detectCores(logical = TRUE) * 0.8), outfile = "")
  registerDoParallel(inner_cl)

  model_results <- tryCatch({
    foreach(task = model_tasks, .combine = dplyr::bind_rows, .errorhandling = "remove") %dopar% {
      suppressPackageStartupMessages({
        library(clam)
        library(tidyverse)
        library(R.devices)
      })

      type <- task$type
      smooth <- task$smooth
      dmax <- task$dmax

      label <- if (type == 2) sprintf("clam type %d degree %d", type, smooth)
               else if (type %in% c(4, 5)) sprintf("clam type %d smoothing %.1f", type, smooth)
               else sprintf("clam type %d", type)

      clam_output <- capture.output(suppressMessages(suppressWarnings(
        R.devices::suppressGraphics({
          clam(core = core_id, coredir = shared_dir, type = type, smooth = smooth,
               its = 10000, dmin = 0, dmax = dmax,
               plotpdf = FALSE, plotpng = FALSE, plotname = FALSE)
        })
      )), type = "output")

      # Parse fit value directly from output
      fit_line <- clam_output[grepl("Fit \\(-log, lower is better\\):", clam_output)]
      fit_val <- if (length(fit_line) > 0) {
        as.numeric(sub(".*Fit \\(-log, lower is better\\):\\s*", "", fit_line[1]))
      } else {
        NA_real_
      }

      cm_range <- 0:floor(dmax)
      chron_matrix <- tryCatch(as.data.frame(chron[, seq_len(min(10000, ncol(chron)))]),
                               error = function(e) NULL)

      if (is.null(chron_matrix) || nrow(chron_matrix) != length(cm_range)) {
        message(sprintf("⚠️ Invalid chron output for %s — %s", core_id, label))
        return(tibble(model_label = label, core_id = core_id, depth_cm = NA_real_, fit = fit_val))
      }

      message(sprintf("📏 Fit for %s — %s: %s", core_id, label, format(fit_val, digits = 5)))

      chron_matrix <- chron_matrix %>%
        mutate(model_label = label,
               core_id = core_id,
               depth_cm = cm_range,
               fit = fit_val) %>%
        relocate(model_label, core_id, depth_cm, fit)

      if (exists("chron", envir = .GlobalEnv)) rm("chron", envir = .GlobalEnv)
      message(sprintf("✅ Finished core %s — %s", core_id, label))
      gc()
      return(chron_matrix)
    }
  }, error = function(e) {
    message(sprintf("❌ Inner loop failed for core %s: %s", core_id, conditionMessage(e)))
    return(NULL)
  })

  stopCluster(inner_cl)
  registerDoSEQ()

  if (exists("best_fit") && isTRUE(best_fit) &&
      !is.null(model_results) && "fit" %in% colnames(model_results)) {

    valid_models <- model_results %>% filter(!is.na(fit), is.finite(fit))

    if (nrow(valid_models) > 0) {
      best <- valid_models %>% slice_min(fit, n = 1)
      message(sprintf("🏆 Selected best-fit model for core %s — %s", core_id, best$model_label[1]))
      model_results <- best
    } else {
      message(sprintf("⚠️ No valid models found for core %s — all fits were NA or infinite", core_id))
      model_results <- tibble()
    }
  }

  unlink(shared_dir, recursive = TRUE, force = TRUE)
  return(model_results)
}

# Return final results
return(clam_core_results)