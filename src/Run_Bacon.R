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
  if (is.null(depth_seq)) {
    depth_seq <- seq(info$d.min, info$d.max, by = 1)
  }

  # Load Bacon output into info$output if not already present
  if (is.null(info$output)) {
    out_file <- list.files(file.path(info$coredir, info$core), pattern = "\\.out$", full.names = TRUE)
    if (length(out_file) == 1) {
      info$output <- tryCatch({
        as.matrix(read.table(out_file, header = FALSE))
      }, error = function(e) stop("❌ Could not read Bacon .out file: ", e$message))
    } else {
      stop("❌ No .out file found in: ", file.path(info$coredir, info$core))
    }
  }

  # Safety check
  if (is.null(info$output)) stop("❌ Bacon model 'info$output' is missing (no .out file loaded).")

  n_iter <- nrow(info$output)
  n_depths <- length(depth_seq)

  # Loop through all depths and extract MCMC age estimates
  message(sprintf("⏳ Extracting ages at %d depths × %d iterations", n_depths, n_iter))
  age_matrix <- matrix(NA_real_, nrow = n_depths, ncol = n_iter)
  for (i in seq_len(n_depths)) {
    d <- depth_seq[i]
    age_matrix[i, ] <- tryCatch({
      Bacon.Age.d(
        d = d,
        set = info,
        its = info$output,
        BCAD = info$BCAD,
        na.rm = FALSE
      )
    }, error = function(e) {
      warning(sprintf("⚠️ Bacon.Age.d() failed at depth %.2f: %s", d, e$message))
      rep(NA_real_, n_iter)
    })
  }

  colnames(age_matrix) <- paste0("iter_", seq_len(ncol(age_matrix)))

  # Return as ffdf
  core_depth_labels <- paste(info$core, depth_seq)
  ff_interpolated <- ff::as.ffdf(data.frame(depth = factor(core_depth_labels), age_matrix))

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
      retry <- retry + 1
      current_ssize <- ceiling(current_ssize * 1.5)
      next
    }

    iter_cols <- grep("^iter_", names(age.mods.interp), value = TRUE)
    if (length(iter_cols) >= 10000) {
      success <- TRUE
    } else {
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
