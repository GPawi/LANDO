### Script to run Bacon via hamstr in LANDO ###
suppressPackageStartupMessages({
  library(hamstr)
  library(rbacon)
  library(hamstrbacon)
  library(rintcal)
  library(tidyverse)
  library(parallel)
  library(foreach)
  library(rngtools)
  library(doRNG)
  library(doSNOW)
  library(ff)
  library(ffbase)
  library(data.table)
  library(stringr)
})

try(Bacon.cleanup(), silent = TRUE)

Bacon_Frame <- as.data.table(Bacon_Frame)
CoreLengths <- as.data.table(CoreLengths)

# Determine system memory in MB and set "thick" accordingly
mem_mb <- as.numeric(system("awk '/MemTotal/ {print $2}' /proc/meminfo", intern = TRUE)) / 1024
if (!rbacon.change.thick) {
  if (mem_mb > 16000) {
    thick_val <- 1
    message("Detected >16GB RAM: using thick = 1")
  } else {
    thick_val <- 5
    message("Detected <=16GB RAM: using thick = 5")
  }
} else {
  thick_val <- 5
}

## Interpolation function
interpolate_bacon_output_ff <- function(info, depth_seq = NULL) {
  # Try to load output from file if missing
  if (is.null(info$output)) {
    out_file <- list.files(file.path(info$coredir, info$core), pattern = "\\.out$", full.names = TRUE)
    if (length(out_file) == 1) {
      posterior <- tryCatch({
        as.matrix(read.table(out_file, header = FALSE))
      }, error = function(e) NULL)
      if (is.null(posterior)) stop("Could not read Bacon output from .out file.")
      info$output <- posterior
    } else {
      stop("No Bacon output available in memory or file.")
    }
  }

  # Check the structure of the posterior
  posterior <- info$output
  if (ncol(posterior) < 3) stop("Bacon output is malformed or incomplete.")

  thick <- info$thick
  d.min <- info$d.min
  d.max <- info$d.max
  core_id <- info$core  # new

  if (is.null(depth_seq)) {
    depth_seq <- seq(d.min, d.max, by = 1)
  }

  # Age accumulation per iteration
  cum_ages <- apply(posterior[, 1:(ncol(posterior) - 2)], 1, cumsum)
  elbows <- d.min + (seq_len(nrow(cum_ages)) - 1) * thick

  interpolated <- lapply(seq_len(ncol(cum_ages)), function(i) {
    stats::approx(x = elbows, y = cum_ages[, i], xout = depth_seq, rule = 2)$y
  })

  interpolated_mat <- do.call(cbind, interpolated)
  colnames(interpolated_mat) <- paste0("iter_", seq_len(ncol(interpolated_mat)))

  # 🧠 Replace "depth" with combined label BEFORE conversion
  core_depth_labels <- paste(core_id, depth_seq)
  ff_interpolated <- ff::as.ffdf(data.frame(depth = factor(core_depth_labels), interpolated_mat))

  return(ff_interpolated)
}

### New function
lando_bacon <- function(core_id, depths, ages, errors,
                        cc = 1, delta.R = 0, delta.STD = 0,
                        thick = 5, d.min = NA, d.max = NA,
                        acc.shape = 1.5, acc.mean = 20,
                        mem.strength = 10, mem.mean = 0.5,
                        ssize = 4000, burnin = 1000,
                        suggest = FALSE, accept.suggestions = TRUE,
                        coredir = tempdir(),
                        runname = "",
                        ...) {
  
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
    cc = cc,
    delta.R = delta.R,
    delta.STD = delta.STD
  )

  utils::write.csv(dets, file = file.path(core_path, paste0(core_id, ".csv")),
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
    ...
  )
  dev.off()

  return(info)
}

# Shared function for running Bacon
Bacon_parallel <- function(i, Bacon_Frame, CoreIDs) {
  core_id <- CoreIDs[[i]]
  core_selection <- Bacon_Frame %>% filter(str_detect(id, paste0("^", core_id, " ")))
  clength <- CoreLengths %>% filter(coreid == core_id)

  retry <- 0
  max_retry <- 5
  current_ssize <- ssize
  success <- FALSE

  while (retry < max_retry && !success) {
    message(sprintf("Running Bacon for core %s (attempt %d, ssize = %d)", core_id, retry + 1, current_ssize))

    run <- tryCatch({
      lando_bacon(
        core_id = core_id,
        depths = core_selection$depth,
        ages = core_selection$obs_age,
        errors = core_selection$obs_err,
        cc = core_selection$cc,
        delta.R = core_selection$delta_R,
        delta.STD = core_selection$delta_STD,
        d.max = clength$corelength,
        acc.shape = acc.shape,
        acc.mean = acc.mean,
        mem.strength = mem.strength,
        mem.mean = mem.mean,
        ssize = current_ssize,
        thick = thick_val,
        suggest = rbacon.change.acc.mean,
        accept.suggestions = rbacon.change.acc.mean,
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

    age.mods.interp <- tryCatch(
      interpolate_bacon_output_ff(run, depth_seq = seq(0, clength$corelength, by = 1)),
      error = function(e) {
        message(sprintf("❌ Bacon error on attempt %d: %s", retry + 1, e$message))
        NULL
      }
    )

    if (is.null(age.mods.interp)) {
      retry <- retry + 1
      current_ssize <- ceiling(current_ssize * 1.5)
      next
    }

    iter_cols <- grep("^iter_", names(age.mods.interp), value = TRUE)
    achieved_iters <- length(iter_cols)

    if (achieved_iters >= 10000) {
      success <- TRUE
    } else {
      retry <- retry + 1
      needed_iters <- 10000 - achieved_iters
      current_ssize <- ceiling(current_ssize + needed_iters * 2.5)
      message(sprintf("Retry %d: only %d iterations. Increasing ssize to %d",
                      retry, achieved_iters, current_ssize))
    }
  }

  if (!success) {
    stop(sprintf("❌ Failed to generate ≥10001 iterations for core %s after %d attempts", core_id, max_retry))
  }

  # Convert ffdf to regular data.frame for final transformation
  out <- as.data.frame(age.mods.interp)

  message(sprintf("✅ Done with core %s — number %d of %d", core_id, i, length(CoreIDs)))
  
  unlink(run$coredir, recursive = TRUE, force = TRUE)

  return(out)

}


# --- SINGLE CORE (Treated as parallel with 1 worker) ---
if (length(CoreIDs) == 1) {
  options(fftempdir = "src/temp/ff")

  cl <- makeCluster(1, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  clusterExport(cl, c("Bacon_Frame", "CoreIDs", "acc.shape", "acc.mean",
                      "mem.strength", "mem.mean", "ssize", "CoreLengths",
                      "hamstr_bacon", "Bacon_parallel", "thick_val"))

  seed <- 210329

  Bacon_core_results <- foreach(i = 1,
                                .combine = bind_rows,
                                .options.RNG = seed,
                                .multicombine = TRUE,
                                .inorder = TRUE) %dorng% {
    suppressPackageStartupMessages({
      library(tidyverse)
      library(rintcal)
      library(rbacon)
      library(hamstr)
      library(hamstrbacon)
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
  registerDoSEQ()

  try(Bacon.cleanup(), silent = TRUE)

  return(Bacon_core_results)

} else {
  # --- MULTI-CORE EXECUTION ---
  options(fftempdir = "src/temp/ff")

  no_cores <- min(length(CoreIDs), detectCores(logical = TRUE))
  cl <- makeCluster(no_cores, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  clusterExport(cl, c("Bacon_Frame", "CoreIDs", "acc.shape", "acc.mean",
                      "mem.strength", "mem.mean", "ssize", "CoreLengths",
                      "hamstr_bacon", "Bacon_parallel", "thick_val"))

  seed <- 210329
  seq_id_all <- seq_along(CoreIDs)

  Bacon_core_results <- foreach(i = seq_id_all,
                                .combine = bind_rows,
                                .options.RNG = seed,
                                .multicombine = TRUE,
                                .inorder = FALSE) %dorng% {
    suppressPackageStartupMessages({
      library(tidyverse)
      library(rintcal)
      library(rbacon)
      library(hamstr)
      library(hamstrbacon)
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
  registerDoSEQ()

  try(Bacon.cleanup(), silent = TRUE)

  return(Bacon_core_results)
}
