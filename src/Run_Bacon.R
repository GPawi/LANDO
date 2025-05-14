suppressPackageStartupMessages({
  library(rbacon)
  library(tidyverse)
  library(data.table)
  library(parallel)
  library(foreach)
  library(rngtools)
  library(doRNG)
  library(doSNOW)
  library(ff)
  library(ffbase)
})

# Cleanup before run
try(Bacon.cleanup(), silent = TRUE)

# Load and merge pre-calibrated ages
Bacon_Frame <- as.data.table(Bacon_Frame)
# Only merge if calibrated columns are missing
if (!("cal_median" %in% names(Bacon_Frame)) || !("cal_1sigma" %in% names(Bacon_Frame))) {
  calib_dates <- as.data.table(calib_dates)
  
  # Only merge if Bacon_Frame does not already include the calib columns
  Bacon_Frame <- merge(Bacon_Frame, calib_dates, by = "id", sort = FALSE)
  
  Bacon_Frame <- Bacon_Frame %>%
    rename(cal_median = ages_calib,
           cal_1sigma = ages_calib_Sds)
}

CoreLengths <- as.data.table(CoreLengths)

# Set thick value based on RAM
mem_mb <- as.numeric(system("awk '/MemTotal/ {print $2}' /proc/meminfo", intern = TRUE)) / 1024
thick_val <- if (!rbacon.change.thick && mem_mb > 16000) 1 else 5

# Interpolation function
interpolate_bacon_output_ff <- function(info, depth_seq = NULL) {
  # Load Bacon output if not already loaded
  if (is.null(info$output)) {
    out_file <- list.files(file.path(info$coredir, info$core), pattern = "\\.out$", full.names = TRUE)
    if (length(out_file) == 1) {
      posterior <- tryCatch({
        as.matrix(read.table(out_file, header = FALSE))
      }, error = function(e) NULL)
      if (is.null(posterior)) stop("❌ Could not read Bacon output from .out file.")
      info$output <- posterior
    } else {
      stop("❌ No Bacon output available in memory or file.")
    }
  }

  out_file <- list.files(file.path(info$coredir, info$core), pattern = "\\.out$", full.names = TRUE)
  posterior <- tryCatch({
    as.matrix(read.table(out_file, header = FALSE))
  }, error = function(e) stop("❌ Could not read Bacon output from .out file."))

  thick <- info$thick
  d.min <- info$d.min
  d.max <- info$d.max
  core_id <- info$core

  if (is.null(depth_seq)) {
    depth_seq <- seq(d.min, d.max, by = 1)
  }

  # Drop last two columns (metadata)
  raw <- posterior[, 1:(ncol(posterior) - 2)]
  ages_matrix <- t(raw)  # Transpose: now rows = depths, cols = iterations

  message(sprintf("✅ ages_matrix shape: %d depths × %d iterations", nrow(ages_matrix), ncol(ages_matrix)))

  # Load correct elbow depths from the .bacon file
  n_depths <- nrow(ages_matrix)
  elbows <- d.min + (seq_len(n_depths) - 1) * thick

  # Check alignment with raw posterior
  if (length(elbows) != nrow(ages_matrix)) {
    stop(sprintf("❌ Mismatch: %d elbow depths vs %d rows in posterior", length(elbows), nrow(ages_matrix)))
  }

  interpolated <- lapply(seq_len(ncol(ages_matrix)), function(i) {
    stats::approx(x = elbows, y = ages_matrix[, i], xout = depth_seq, rule = 2)$y
  })

  interpolated_mat <- do.call(cbind, interpolated)
  colnames(interpolated_mat) <- paste0("iter_", seq_len(ncol(interpolated_mat)))

  # Sanity check
  max_depth <- max(depth_seq)
  deepest_layer <- interpolated_mat[nrow(interpolated_mat), ]
  message("🔎 Interpolation check:")
  message(sprintf("Depth range: %.2f–%.2f cm", min(depth_seq), max_depth))
  message(sprintf("Deepest modeled age: min=%.1f, mean=%.1f, max=%.1f",
                  min(deepest_layer, na.rm = TRUE),
                  mean(deepest_layer, na.rm = TRUE),
                  max(deepest_layer, na.rm = TRUE)))
  if (max(deepest_layer, na.rm = TRUE) < 10000) {
    warning("⚠️ Deepest modeled age is <10,000 cal BP — check input ages or d.max")
  }

  # Return as ffdf
  core_depth_labels <- paste(core_id, depth_seq)
  ff_interpolated <- ff::as.ffdf(data.frame(depth = factor(core_depth_labels), interpolated_mat))

  return(ff_interpolated)
}

# Core Bacon runner
lando_bacon <- function(core_id, depths, ages, errors,
                        thick = thick_val, d.min = NA, d.max = NA,
                        acc.shape = 1.5, acc.mean = 20,
                        mem.strength = 10, mem.mean = 0.5,
                        ssize = 4000, burnin = 1000,
                        suggest = FALSE, accept.suggestions = TRUE,
                        coredir = tempdir(), runname = "") {
  try(Bacon.cleanup(), silent = TRUE)

  if (is.na(d.min)) d.min <- min(depths, na.rm = TRUE)
  if (is.na(d.max)) d.max <- max(depths, na.rm = TRUE)
  core_path <- file.path(coredir, core_id)
  dir.create(core_path, showWarnings = FALSE, recursive = TRUE)

  dets <- data.frame(
    id = core_id,
    age = ages,
    error = errors,
    depth = depths,
    cc = 0,
    delta.R = 0,
    delta.STD = 0
  )

  write.csv(dets, file = file.path(core_path, paste0(core_id, ".csv")),
            row.names = FALSE, quote = FALSE)

  pdf(NULL)
  info <- rbacon::Bacon(
    core = core_id,
    coredir = coredir,
    thick = thick,
    d.min = d.min,
    d.max = d.max,
    acc.shape = acc.shape,
    acc.mean = acc.mean,
    mem.strength = mem.strength,
    mem.mean = mem.mean,
    ssize = ssize,
    burnin = burnin,
    suggest = suggest,
    accept.suggestions = accept.suggestions,
    ask = FALSE,
    runname = runname,
    plot.pdf = FALSE,
    close.connections = TRUE,
    oldest.age = 10e6
  )
  dev.off()

  return(info)
}

# Parallel wrapper
Bacon_parallel <- function(i, Bacon_Frame, CoreIDs) {
  core_id <- CoreIDs[[i]]
  core_selection <- Bacon_Frame %>% filter(str_detect(id, paste0("^", core_id, " ")))
  clength <- CoreLengths %>% filter(coreid == core_id)

  retry <- 0
  max_retry <- 5
  current_ssize <- ssize
  success <- FALSE

  while (retry < max_retry && !success) {
    message(sprintf("Running Bacon for core %s (attempt %d)", core_id, retry + 1))
    run <- tryCatch({
      lando_bacon(
        core_id = core_id,
        depths = core_selection$depth,
        ages = core_selection$cal_median,
        errors = core_selection$cal_1sigma,
        d.max = as.numeric(clength$corelength[[1]]),
        acc.shape = acc.shape,
        acc.mean = acc.mean,
        mem.strength = mem.strength,
        mem.mean = mem.mean,
        ssize = current_ssize,
        thick = thick_val,
        suggest = rbacon.change.acc.mean,
        accept.suggestions = rbacon.change.acc.mean
      )
    }, error = function(e) {
      message(sprintf("❌ Bacon error on attempt %d: %s", retry + 1, e$message))
      NULL
    })

    if (is.null(run)) {
      message("I am culprit No.1")
      retry <- retry + 1
      current_ssize <- ceiling(current_ssize * 1.5)
      next
    }

    depth_max <- clength$corelength[[1]]
    age.mods.interp <- tryCatch(
      interpolate_bacon_output_ff(run, depth_seq = seq(0, depth_max, by = 1)),
      error = function(e) {
        message(sprintf("❌ Interpolation error: %s", e$message))
        NULL
      }
    )

    if (is.null(age.mods.interp)) {
      message("I am culprit No. 2")
      retry <- retry + 1
      current_ssize <- ceiling(current_ssize * 1.5)
      next
    }

    iter_cols <- grep("^iter_", names(age.mods.interp), value = TRUE)
    message(sprintf("✅ %d iterations achieved", length(iter_cols)))
    if (length(iter_cols) >= 10000) {
      success <- TRUE
    } else {
      message("I am culprit No. 3")
      retry <- retry + 1
      current_ssize <- ceiling(current_ssize + (10000 - length(iter_cols)) * 2.5)
    }
  }

  if (!success) stop(sprintf("❌ Bacon failed for core %s after %d attempts", core_id, max_retry))

  out <- as.data.frame(age.mods.interp)
  message(sprintf("✅ Done with core %s", core_id))
  unlink(run$coredir, recursive = TRUE, force = TRUE)
  return(out)
}

# --- Run in parallel or single core ---
options(fftempdir = "src/temp/ff")
seed <- 210329

if (length(CoreIDs) == 1) {
  cl <- makeCluster(1, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  Bacon_core_results <- foreach(i = 1,
                                .combine = bind_rows,
                                .options.RNG = seed) %dorng% {
    suppressPackageStartupMessages({
      library(tidyverse)
      library(rbacon)
      library(ff)
      library(ffbase)
      library(foreach)
      library(rngtools)
    })
    tryCatch(Bacon_parallel(i, Bacon_Frame, CoreIDs), error = function(e) {
      message(sprintf("⚠️ Error in core %s: %s", CoreIDs[[i]], e$message))
      NULL
    })
  }

  stopCluster(cl)
} else {
  no_cores <- min(length(CoreIDs), detectCores(logical = TRUE))
  cl <- makeCluster(no_cores, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  Bacon_core_results <- foreach(i = seq_along(CoreIDs),
                                .combine = bind_rows,
                                .options.RNG = seed) %dorng% {
    suppressPackageStartupMessages({
      library(tidyverse)
      library(rbacon)
      library(ff)
      library(ffbase)
      library(foreach)
      library(rngtools)
    })
    tryCatch(Bacon_parallel(i, Bacon_Frame, CoreIDs), error = function(e) {
      message(sprintf("⚠️ Error in core %s: %s", CoreIDs[[i]], e$message))
      NULL
    })
  }

  stopCluster(cl)
}

return(Bacon_core_results)
