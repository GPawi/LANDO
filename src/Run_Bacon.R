### Script to run Bacon via hamstr in LANDO ###
suppressMessages(suppressPackageStartupMessages({
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
  library(furrr)
}))

try(Bacon.cleanup(), silent = TRUE)

Bacon_Frame <- as.data.table(Bacon_Frame)
CoreLengths <- as.data.table(CoreLengths)

# --- Internal parallel Bacon run ---
run_parallel_bacon_chunks <- function(core_id, core_selection, clength, total_ssize, nchunks) {
  ssize_each <- ceiling(total_ssize / nchunks)
  seeds <- sample(1e6:9e6, nchunks)

  future::plan(future::multisession, workers = nchunks)

  runs <- furrr::future_map2(seeds, seq_len(nchunks), function(seed, i) {
    message(sprintf("Running Bacon chunk %d/%d with ssize = %d, seed = %d", i, nchunks, ssize_each, seed))

    run <- hamstr_bacon(
      id = core_selection$id,
      depth = core_selection$depth,
      obs_age = core_selection$obs_age,
      obs_err = core_selection$obs_err,
      cc = core_selection$cc,
      delta.R = core_selection$delta_R,
      delta.STD = core_selection$delta_STD,
      d.max = clength$corelength,
      acc.shape = acc.shape,
      acc.mean = acc.mean,
      mem.strength = mem.strength,
      mem.mean = mem.mean,
      ssize = ssize_each,
      seed = seed,
      thick = 1,
      suggest = rbacon.change.acc.mean,
      accept.suggestions = rbacon.change.acc.mean
    )

    out_file <- list.files(run$info$output[["dir"]], pattern = "\\.out$", full.names = TRUE)
    data.table::fread(out_file, header = FALSE)
  })

  combined <- rbindlist(runs)
  return(combined)
}

# --- Shared function for running Bacon (multi-core) ---
Bacon_parallel <- function(i, Bacon_Frame, CoreIDs) {
  core_id <- CoreIDs[[i]]
  core_selection <- Bacon_Frame[str_detect(id, paste0("^", core_id, " "))]
  clength <- CoreLengths[coreid == core_id]

  retry <- 0
  max_retry <- 5
  current_ssize <- ssize
  success <- FALSE

  while (retry < max_retry && !success) {
    message(sprintf("Running Bacon for core %s (attempt %d, ssize = %d)", core_id, retry + 1, current_ssize))

    run <- hamstr_bacon(
      id = core_selection$id,
      depth = core_selection$depth,
      obs_age = core_selection$obs_age,
      obs_err = core_selection$obs_err,
      cc = core_selection$cc,
      delta.R = core_selection$delta_R,
      delta.STD = core_selection$delta_STD,
      d.max = clength$corelength,
      acc.shape = acc.shape,
      acc.mean = acc.mean,
      mem.strength = mem.strength,
      mem.mean = mem.mean,
      ssize = current_ssize,
      thick = 1,
      suggest = rbacon.change.acc.mean,
      accept.suggestions = rbacon.change.acc.mean
    )

    age.mods.interp <- as.ffdf(predict(run, depth = seq(0, clength$corelength, by = 1)))
    achieved_iters <- max(age.mods.interp$iter, na.rm = TRUE)

    if (achieved_iters >= 10001) {
      success <- TRUE
    } else {
      retry <- retry + 1
      needed_iters <- 10001 - achieved_iters
      current_ssize <- ceiling(current_ssize + (needed_iters * 2.5))
      message(sprintf("Retry %d: only %d iterations. Increasing ssize to %d", retry, achieved_iters, current_ssize))
    }
  }

  if (!success) {
    stop(sprintf("❌ Failed to generate ≥10001 iterations for core %s after %d attempts", core_id, max_retry))
  }

  age.mods.interp$depth <- as.character.ff(age.mods.interp$depth)
  age.mods.interp$depth <- ff(paste(core_id, age.mods.interp$depth))
  out <- pivot_wider(as.data.frame(age.mods.interp), names_from = iter, values_from = age)

  message(sprintf("✅ Done with core %s — number %d of %d", core_id, i, length(CoreIDs)))
  return(out)
}

# --- SINGLE CORE (Internal parallel) ---
if (length(CoreIDs) == 1) {
  i <- 1
  core_id <- CoreIDs[[i]]
  core_selection <- Bacon_Frame[str_detect(id, paste0("^", core_id, " "))]
  clength <- CoreLengths[coreid == core_id]

  retry <- 0
  max_retry <- 5
  current_ssize <- ssize
  success <- FALSE

  while (retry < max_retry && !success) {
    posterior <- run_parallel_bacon_chunks(core_id, core_selection, clength, total_ssize = current_ssize, nchunks = 3)
    posterior$depth <- seq(0, clength$corelength, length.out = nrow(posterior))
    posterior_long <- melt(posterior, id.vars = "depth", variable.name = "iter", value.name = "age")
    posterior_long$depth <- paste(core_id, as.character(posterior_long$depth))

    achieved_iters <- length(unique(posterior_long$iter))
    if (achieved_iters >= 10001) {
      success <- TRUE
    } else {
      retry <- retry + 1
      needed_iters <- 10001 - achieved_iters
      current_ssize <- ceiling(current_ssize + (needed_iters * 2.5))
      message(sprintf("Retry %d: only %d iterations. Increasing ssize to %d", retry, achieved_iters, current_ssize))
    }
  }

  if (!success) {
    stop(sprintf("❌ Failed to generate ≥10001 iterations for core %s after %d attempts", core_id, max_retry))
  }

  Bacon_core_results <- pivot_wider(posterior_long, names_from = iter, values_from = age)
  return(Bacon_core_results)

} else {
  # --- MULTI-CORE EXECUTION ---
  options(fftempdir = "src/temp/ff")
  no_cores <- min(length(CoreIDs), detectCores(logical = TRUE))
  cl <- makeCluster(no_cores, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  clusterExport(cl, c("Bacon_Frame", "CoreIDs", "acc.shape", "acc.mean",
                      "mem.strength", "mem.mean", "ssize", "CoreLengths",
                      "hamstr_bacon", "Bacon_parallel"))

  seed <- 210329
  seq_id_all <- seq_along(CoreIDs)

  Bacon_core_results <- foreach(i = seq_id_all,
                                .combine = bind_rows,
                                .options.RNG = seed,
                                .multicombine = TRUE,
                                .inorder = FALSE) %dorng% {
    suppressMessages(suppressPackageStartupMessages({
      library(tidyverse)
      library(rintcal)
      library(rbacon)
      library(hamstr)
      library(hamstrbacon)
      library(ff)
      library(ffbase)
      library(foreach)
      library(rngtools)
    }))

    tryCatch(Bacon_parallel(i, Bacon_Frame, CoreIDs), error = function(e) {
      message(sprintf("⚠️ Error in core %s: %s", CoreIDs[[i]], e$message))
      NULL
    })
  }

  stopCluster(cl)
  registerDoSEQ()

  return(Bacon_core_results)
}
