### Script to run clam in LANDO (updated for clam 2.6.2) ###

# Load libraries
suppressPackageStartupMessages({
  library(rice)
  library(rintcal)
  library(clam)
  library(R.devices)
  library(tidyverse)
  library(foreach)
  library(parallel)
  library(doParallel)
  library(doSNOW)
})

# Initialize cluster
no_cores <- detectCores(logical = TRUE)
cl <- makeCluster(floor(no_cores * 0.8), outfile = "", autoStop = TRUE)
registerDoSNOW(cl)

# Prepare data
seq_id_all <- seq_along(CoreIDs)
clam_Frame <- clam_Frame %>%
  mutate(across(c(depth, thickness), as.numeric))
CoreLengths <- CoreLengths %>%
  mutate(corelength = as.integer(corelength))
clusterExport(cl, list('clam_Frame', 'CoreLengths', 'CoreIDs', 'types_curve', 'smoothness_curve', 'poly_degree_curve', 'best_fit'))

# Parallel run over cores
clam_core_results <- foreach(core = seq_id_all, .combine = 'rbind', .multicombine = TRUE, .maxcombine = 1000) %dopar% {
  
  suppressPackageStartupMessages({
    library(rice)
    library(rintcal)
    library(clam)
    library(tidyverse)
  })
  
  # Core preparation
  core_selection <- clam_Frame %>% filter(str_detect(lab_ID, CoreIDs[[core]]))
  clength <- CoreLengths %>% filter(coreid == CoreIDs[[core]])
  date_max <- plyr::round_any(max(core_selection$depth, na.rm = TRUE), 1, f = floor)
  core_max <- clength$corelength
  
  # Attributes
  types <- types_curve
  smoothness <- smoothness_curve
  poly_degree <- poly_degree_curve
  search_rev <- "!!! Too many models with age reversals!!!"
  search_fit <- "  Fit (-log, lower is better): "
  
  # Setup temporary core directory
  tmpdir <- tempdir()
  dirbase <- basename(tmpdir)
  dirnm <- dirname(tmpdir)
  fl <- file.path(tmpdir, paste0(dirbase, ".csv"))
  
  # Write CSV (clam expects specific order)
  core_selection %>%
    select(lab_ID, `14C_age`, error, reservoir, depth, thickness) %>%
    write.csv(file = fl, row.names = FALSE, quote = FALSE)
  
  # Adjust modeling types if needed
  if (length(unique(core_selection$depth)) < 4) {
    types <- types[types != 2]  # No polynomial if too few points
  }
  if (any(poly_degree >= length(unique(core_selection$depth)))) {
    poly_degree <- 1:(length(unique(core_selection$depth)) - 1)
  }
  
  # --- Now run different types ---
  result_types <- foreach(type = types, .combine = 'rbind', .multicombine = TRUE, .maxcombine = 1000) %do% {
    
    if (type %in% c(1, 3)) {
      # Linear interpolation or smooth spline
      suppressWarnings(R.devices::suppressGraphics({
        z <- capture.output(clam(core = dirbase, coredir = dirnm, type = type,
                                 its = 20000, dmin = 0, dmax = core_max,
                                 plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
      }))
      fit <- as.numeric(sub(search_fit, "", subset(z, grepl(search_fit, z))))
      if (!any(grepl(search_rev, z)) && !is.infinite(fit)) {
        chron_model <- as.data.frame(chron[, 1:10000])
        mid <- outer(CoreIDs[[core]], seq(0, core_max, by = 1), paste)
        row.names(chron_model) <- outer(mid, sprintf('-clam_T%d', type), paste0)
        chron_model$fit <- fit
        return(chron_model)
      }
    }
    
    else if (type == 2) {
      # Polynomial fitting
      result_2nd <- foreach(degree = poly_degree, .combine = 'rbind', .multicombine = TRUE, .maxcombine = 1000) %do% {
        suppressWarnings(R.devices::suppressGraphics({
          z <- capture.output(clam(core = dirbase, coredir = dirnm, type = type, smooth = degree,
                                   its = 20000, dmin = 0, dmax = core_max,
                                   plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
        }))
        fit <- as.numeric(sub(search_fit, "", subset(z, grepl(search_fit, z))))
        if (!any(grepl(search_rev, z)) && !is.infinite(fit)) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(CoreIDs[[core]], seq(0, core_max, by = 1), paste)
          row.names(chron_model) <- outer(mid, sprintf('-clam_T2_D%d', degree), paste0)
          chron_model$fit <- fit
          return(chron_model)
        }
      }
      if (best_fit && !is.null(result_2nd)) {
        result_2nd <- result_2nd[result_2nd$fit == min(result_2nd$fit), ]
      }
      return(result_2nd)
    }
    
    else if (type == 4) {
      # Age-depth smooth spline
      result_4th <- foreach(s = smoothness, .combine = 'rbind', .multicombine = TRUE, .maxcombine = 1000) %do% {
        suppressWarnings(R.devices::suppressGraphics({
          z <- capture.output(clam(core = dirbase, coredir = dirnm, type = type, smooth = s,
                                   its = 20000, dmin = 0, dmax = core_max,
                                   plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
        }))
        fit <- as.numeric(sub(search_fit, "", subset(z, grepl(search_fit, z))))
        if (!any(grepl(search_rev, z)) && !is.infinite(fit)) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(CoreIDs[[core]], seq(0, core_max, by = 1), paste)
          row.names(chron_model) <- outer(mid, sprintf('-clam_T4_S%d', as.integer(s * 10)), paste0)
          chron_model$fit <- fit
          return(chron_model)
        }
      }
      if (best_fit && !is.null(result_4th)) {
        result_4th <- result_4th[result_4th$fit == min(result_4th$fit), ]
      }
      return(result_4th)
    }
    
    else if (type == 5) {
      # Stineman interpolation
      result_5th <- foreach(k = smoothness, .combine = 'rbind', .multicombine = TRUE, .maxcombine = 1000, .errorhandling = 'remove') %do% {
        suppressWarnings(R.devices::suppressGraphics({
          z <- capture.output(clam(core = dirbase, coredir = dirnm, type = type, smooth = k,
                                   its = 20000, dmin = 0, dmax = date_max,
                                   plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
        }))
        fit <- as.numeric(sub(search_fit, "", subset(z, grepl(search_fit, z))))
        if (!any(grepl(search_rev, z)) && !is.infinite(fit)) {
          chron_model <- as.data.frame(chron[, 1:10000])
          mid <- outer(CoreIDs[[core]], seq(0, date_max, by = 1), paste)
          row.names(chron_model) <- outer(mid, sprintf('-clam_T5_S%d', as.integer(k * 10)), paste0)
          chron_model$fit <- fit
          return(chron_model)
        }
      }
      if (best_fit && !is.null(result_5th)) {
        result_5th <- result_5th[result_5th$fit == min(result_5th$fit), ]
      }
      return(result_5th)
    }
  }
  
  message(sprintf("✅ Done with core %s — Number %d of %d", CoreIDs[[core]], core, length(CoreIDs)))
  
  if (best_fit && !is.null(result_types)) {
    result_types <- result_types[result_types$fit == min(result_types$fit), ]
  }
  return(result_types)
}

# Cleanup
stopCluster(cl)
rm(list = "cl")
gc()
registerDoSEQ()

clam_core_results$fit <- NULL
return(clam_core_results)