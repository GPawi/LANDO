### LANDO Clam runner script — double parallelization with clean logging and robust combining ###

suppressPackageStartupMessages({
  library(clam)
  library(tidyverse)
  library(data.table)
  library(parallel)
  library(doParallel)
  library(foreach)
  library(R.devices)
})

# Initialize outer cluster
n_cores <- floor(detectCores(logical = TRUE) * 0.8)
cl <- makeCluster(n_cores, outfile = "")
registerDoParallel(cl)

# Inputs
clam_Frame <- clam_Frame %>% mutate(across(c(`14C_age`, cal_age, error, reservoir, depth, thickness), as.numeric))
CoreLengths <- CoreLengths %>% mutate(corelength = as.integer(corelength))
seq_id_all <- seq_along(CoreIDs)

# Outer loop over cores (use %do% so LANDO logs are visible)
clam_core_results <- foreach(core = seq_id_all,
                             .combine = dplyr::bind_rows, 
                             .multicombine = TRUE, 
                             .packages = c("clam", "tidyverse", "data.table")) %do% {

  suppressPackageStartupMessages({
      library(clam)
      library(tidyverse)
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
  dir.create(shared_dir, recursive = TRUE, showWarnings = FALSE)
  core_dir <- file.path(shared_dir, core_id)
  dir.create(core_dir, showWarnings = FALSE)

  input_file <- file.path(core_dir, paste0(core_id, ".csv"))
  core_selection %>%
    select(lab_ID, `14C_age`, cal_age, error, reservoir, depth, thickness) %>%
    write.csv(file = input_file, row.names = FALSE, quote = FALSE)

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

  # Inner parallel loop for model types (dopar)
  inner_cl <- makeCluster(4, outfile = "")
  registerDoParallel(inner_cl)

  model_results <- foreach(task = model_tasks, .combine = dplyr::bind_rows, .packages = c("clam", "tidyverse", "R.devices")) %dopar% {
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

    invisible(capture.output(
      suppressMessages(
        suppressWarnings(
          R.devices::suppressGraphics({
            clam(core = core_id, coredir = shared_dir, type = type, smooth = smooth,
                 its = 20000, dmin = 0, dmax = dmax,
                 plotpdf = FALSE, plotpng = FALSE, plotname = FALSE)
          })
        )
      ), type = "output"
    ))

    if (!exists("chron", inherits = TRUE)) {
      return(tibble(model_label = label, core_id = core_id, depth_cm = NA_real_, fit = NA_real_))
    }

    cm_range <- 0:floor(dmax)
    ncols <- ncol(chron)
    chron_matrix <- tryCatch(as.data.frame(chron[, seq_len(min(20000, ncols))]), error = function(e) NULL)
    if (is.null(chron_matrix) || nrow(chron_matrix) != length(cm_range)) {
      return(tibble(model_label = label, core_id = core_id, depth_cm = NA_real_, fit = NA_real_))
    }

    fit_val <- tryCatch(get("fit", envir = parent.env(environment())), error = function(e) NA_real_)
    chron_matrix <- chron_matrix %>%
      mutate(model_label = label,
             core_id = core_id,
             depth_cm = cm_range,
             fit = fit_val) %>%
      relocate(model_label, core_id, depth_cm, fit)

    rm(list = "chron", envir = .GlobalEnv)
    message(sprintf("✅ Finished core %s — %s", core_id, label))
    return(chron_matrix)
  }

  stopCluster(inner_cl)
  registerDoSEQ()

  message(sprintf("✅ Finished all models for core %s", core_id))

  unlink(shared_dir, recursive = TRUE, force = TRUE)

  if (best_fit && !is.null(model_results) && "fit" %in% colnames(model_results)) {
    best <- model_results %>% filter(!is.na(fit)) %>% slice_min(fit, n = 1)
    return(best)
  }

  return(model_results)
}

stopCluster(cl)
registerDoSEQ()
gc()

return(clam_core_results)
