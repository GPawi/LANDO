### Script to run Bacon via hamstr in LANDO ###
suppressPackageStartupMessages({
  library(hamstr)
  library(rbacon)
  library(hamstrbacon)
  library(rintcal)
  library(tidyverse)
  library(parallel)
  library(foreach)
  library(doRNG)
  library(doSNOW)
  library(ff)
  library(ffbase)
  library(data.table)
  library(stringr)
})

Bacon.cleanup()

Bacon_Frame <- as.data.table(Bacon_Frame)
CoreLengths <- as.data.table(CoreLengths)

# --- SINGLE CORE EXECUTION ---
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
  message(sprintf("Running Bacon for core %s (attempt %d, ssize = %d)", core_id, retry + 1, current_ssize))

  withCallingHandlers({
      run <- hamstr_bacon(
        id = core_selection$id,
        depth = core_selection$depth,
        obs_age = core_selection$obs_age,
        obs_err = core_selection$obs_err,
        d.max = clength$corelength,
        cc = core_selection$cc,
        delta.R = core_selection$delta_R,
        delta.STD = core_selection$delta_STD,
        acc.shape = acc.shape,
        acc.mean = acc.mean,
        mem.strength = mem.strength,
        mem.mean = mem.mean,
        ssize = current_ssize,
        thick = 1,
        verbose = TRUE,
        suggest = rbacon.change.acc.mean,
        accept.suggestions = rbacon.change.acc.mean
      )
    }, warning = function(w) {
      if (grepl("longer object length is not a multiple", conditionMessage(w))) {
        invokeRestart("muffleWarning")
      }
    })

  age.mods.interp <- predict(run, depth = seq(0, clength$corelength, by = 1))
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

  age.mods.interp_dt <- as.data.table(age.mods.interp)
  age.mods.interp_dt[, depth := paste(core_id, as.character(depth))]
  Bacon_core_results <- dcast(age.mods.interp_dt, depth ~ iter, value.var = "age")

  message(sprintf("✅ Done with core %s", core_id))
  return(Bacon_core_results)

} else {

# --- MULTI-CORE EXECUTION ---
options(fftempdir = "src/temp/ff")

Bacon_parallel <- function(i, Bacon_Frame, CoreIDs) {
  core_id <- CoreIDs[[i]]
  core_selection <- Bacon_Frame %>% filter(str_detect(id, paste0("^", core_id, " ")))
  clength <- CoreLengths %>% filter(coreid == core_id)

  dets_file <- tempfile(fileext = ".csv")
  write.csv(core_selection, file = dets_file, row.names = FALSE)

  run <- hamstr_bacon(dets = dets_file,
                      d.max = clength$corelength,
                      acc.shape = acc.shape,
                      acc.mean = acc.mean,
                      mem.strength = mem.strength,
                      mem.mean = mem.mean,
                      ssize = ssize,
                      thick = 1)

  age.mods.interp <- as.ffdf(predict(run, depth = seq(0, clength$corelength, by = 1)))
  while (max(age.mods.interp$iter) < 10001) {
    diff_iter <- 10001 - (max(age.mods.interp$iter) - min(age.mods.interp$iter))
    new_ssize <- ceiling(ssize + (diff_iter * 2.5))
    message(sprintf("Retrying core %s with ssize = %d", core_id, new_ssize))

    run <- hamstr_bacon(dets = dets_file,
                        d.max = clength$corelength,
                        acc.shape = acc.shape,
                        acc.mean = acc.mean,
                        mem.strength = mem.strength,
                        mem.mean = mem.mean,
                        ssize = new_ssize,
                        thick = 1)

    age.mods.interp <- as.ffdf(predict(run, depth = seq(0, clength$corelength, by = 1)))
  }

  age.mods.interp$depth <- as.character.ff(age.mods.interp$depth)
  age.mods.interp$depth <- ff(paste(core_id, age.mods.interp$depth))
  out <- pivot_wider(as.data.frame(age.mods.interp), names_from = iter, values_from = age)

  message(sprintf("✅ Done with core %s — number %d of %d", core_id, i, length(CoreIDs)))
  return(out)
}

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
  suppressPackageStartupMessages({
    library(tidyverse)
    library(rintcal)
    library(rbacon)
    library(hamstr)
    library(hamstrbacon)
    library(ff)
    library(ffbase)
  })

  tryCatch(Bacon_parallel(i, Bacon_Frame, CoreIDs), error = function(e) {
    message(sprintf("⚠️ Error in core %s: %s", CoreIDs[[i]], e$message))
    NULL
  })
}

stopCluster(cl)
registerDoSEQ()

return(Bacon_core_results)
}