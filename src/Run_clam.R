### LANDO Clam runner script — double parallelization, live output, pre-calibrated dates (cc=0) ###

suppressPackageStartupMessages({
  library(clam)
  library(tidyverse)
  library(data.table)
  library(parallel)
  library(doParallel)
  library(foreach)
  library(R.devices)
})

# Ensure clam_Frame and calib_dates are data.tables
clam_Frame <- as.data.table(clam_Frame)

# Convert all fields to numeric as needed
clam_Frame <- clam_Frame %>%
  mutate(across(c(`14C_age`, cal_age, error, reservoir, depth, thickness), as.numeric))

CoreLengths <- CoreLengths %>% mutate(corelength = as.integer(corelength))
seq_id_all <- seq_along(CoreIDs)

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
  dir.create(shared_dir, recursive = TRUE, showWarnings = FALSE)

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

  n_workers <- floor(detectCores(logical = TRUE) * 0.8)
  inner_cl <- makeCluster(n_workers, outfile = "")
  registerDoParallel(inner_cl)

  model_results <- tryCatch({
  foreach(task = model_tasks, 
          .combine = dplyr::bind_rows, 
          .errorhandling = "pass") %dopar% {

      tryCatch({
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

        model_dir <- file.path(shared_dir, gsub("[^a-zA-Z0-9_]", "_", label))
        core_subdir <- file.path(model_dir, core_id)
        dir.create(core_subdir, recursive = TRUE, showWarnings = FALSE)

        write.csv(core_selection,
                  file = file.path(core_subdir, paste0(core_id, ".csv")),
                  row.names = FALSE, quote = FALSE)

        suppressGraphics({
          pdf(NULL)
          clam_output <- tryCatch({

            # Suppress cat/print output (stdout)
            invisible(capture.output({

              # Suppress message() output and capture it
              out <- capture.output({
                suppressWarnings({
                  result <- clam(
                    core = core_id,
                    coredir = model_dir,
                    type = type,
                    smooth = smooth,
                    its = 20000,
                    dmin = 0,
                    dmax = dmax,
                    plotpdf = FALSE,
                    plotpng = FALSE,
                    plotname = FALSE
                  )
                  message("✅ Clam call returned successfully.")
                })
              }, type = "message")

              # Write filtered messages
              cleaned_out <- stringr::str_subset(out, "^((?!extrapolating beyond dated levels, dangerous!|^NULL$).)*$")
              writeLines(cleaned_out, file.path(model_dir, "clam_output.txt"))

            }))  # <-- end of capture.output for cat()

            out  # Return message log

          }, error = function(e) {
            msg <- paste("❌ Clam run failed:", conditionMessage(e))
            message(msg)
            writeLines(msg, file.path(model_dir, "clam_error.txt"))
            return(character(0))
          })
          dev.off()
        })

        fit_line <- stringr::str_subset(clam_output, "Fit \\(-log, lower is better\\):")
        fit_val <- if (length(fit_line) > 0) {
          stringr::str_extract(fit_line[1], "[-+]?[0-9]*\\.?[0-9]+([eE][-+]?[0-9]+)?") %>% as.numeric()
        } else {
          NA_real_
        }

        reversal_warning <- any(stringr::str_detect(clam_output, "Age reversals occurred"))

        # Handle exclusion conditions
        if (is.na(fit_val) || !is.finite(fit_val)) {
          message(sprintf("⚠️ Excluding %s for %s due to NA or infinite fit value", label, core_id))
          gc()
          return(NULL)
        }
        if (reversal_warning) {
          message(sprintf("⚠️ Excluding %s for %s due to age reversal warning", label, core_id))
          gc()
          return(NULL)
        }

        cm_range <- 0:floor(dmax)

        chron_matrix <- tryCatch({
          df <- as.data.frame(chron[, seq_len(min(10000, ncol(chron)))])
          rownames(df) <- sprintf("%s %d-%s", core_id, cm_range, gsub("clam ", "clam_", label))
          df$fit <- fit_val
          df
        }, error = function(e) {
          message(sprintf("⚠️ Invalid chron output for %s — %s", core_id, label))
          return(NULL)
        })

        if (exists("chron", envir = .GlobalEnv)) rm("chron", envir = .GlobalEnv)

        message(sprintf("📏 Fit for %s — %s: %s", core_id, label, format(fit_val, digits = 5)))
        message(sprintf("✅ Finished core %s — %s", core_id, label))
        gc()

        if (is.null(chron_matrix)) {
          return(NULL)
        } else {
          return(chron_matrix)
        }
      }, error = function(e) {
        message(sprintf("❌ Worker error in core %s — %s: %s", core_id, label, conditionMessage(e)))
        return(NULL)
      })

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

      # Extract model label from row name
      label_out <- stringr::str_extract(rownames(best)[1], "clam_.*$")

      message(sprintf("🏆 Selected best-fit model for core %s — %s", core_id, label_out))
      model_results <- best
    } else {
      message(sprintf("⚠️ No valid models found for core %s — all fits were NA or infinite", core_id))
      model_results <- tibble()
    }
  }

  unlink(shared_dir, recursive = TRUE, force = TRUE)
  return(model_results)
}

# Final result
return(clam_core_results)
