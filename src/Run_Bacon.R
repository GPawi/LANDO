### Script to run Bacon via hamstr in LANDO ###

## Load libraries
suppressPackageStartupMessages({
  library(hamstr)
  library(rbacon)
  library(hamstrbacon)
  library(IntCal)
  library(tidyverse)
  library(parallel)
  library(foreach)
  library(doRNG)
  library(doSNOW)
  library(ff)
  library(ffbase)
})

# Clean wrapper for Bacon2 that avoids passing unsupported args
hamstr_bacon <- function(id, depth, obs_age, obs_err, ..., MinAge = NULL, MaxAge = NULL) {
  core <- unique(str_extract(id, "^[^ ]+"))
  if (length(core) != 1) stop("Multiple core IDs detected. Only one at a time is allowed.")

  coredir <- "Bacon_runs"
  dir.create(file.path(coredir, core), recursive = TRUE, showWarnings = FALSE)

  dets <- data.frame(
    ID = seq_along(depth),
    age = obs_age,
    error = obs_err,
    depth = depth
  )
  write.csv(dets, file = file.path(coredir, core, paste0(core, ".csv")), row.names = FALSE, quote = FALSE)

  args <- list(...)
  args$core <- core
  args$coredir <- coredir
  args$MinAge = numeric(0)
  args$MaxAge = numeric(0)

  # Filter to only allowed arguments in Bacon2()
  bacon2_args <- names(formals(hamstrbacon:::Bacon2))
  args <- args[names(args) %in% bacon2_args]

  # Drop NULLs
  args <- args[!vapply(args, is.null, logical(1))]

  # Workaround: forcibly remove MinAge/MaxAge if they’re still in args
  args <- args[!names(args) %in% c("MinAge", "MaxAge")]

  do.call(hamstrbacon:::Bacon2, args)
}

# Preprocess to extract core name
Bacon_Frame <- Bacon_Frame %>%
  mutate(core_clean = str_extract(id, "^[^ ]+")) %>%
  mutate(across(c(obs_age, obs_err, delta_R, delta_STD), as.integer))

# --- SINGLE CORE RUN ---
if (length(CoreIDs) == 1) {
  i <- 1
  core_id <- CoreIDs[[i]]

  core_selection <- Bacon_Frame %>% filter(core_clean == core_id)
  clength <- CoreLengths %>% filter(str_detect(coreid, core_id))

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
    MinAge = numeric(0),
    MaxAge = numeric(0),
    ssize = ssize,
    thick = 1,
    bacon.change.thick = TRUE
  )

  age.mods.interp <- predict(run, depth = seq(0, clength$corelength, by = 1))
  while (max(age.mods.interp$iter) < 10001) {
    diff_iter <- 10001 - (max(age.mods.interp$iter) - min(age.mods.interp$iter))
    new_ssize <- ceiling(ssize + (diff_iter * 2.5))
    message(sprintf("Not enough iterations in core %s — retrying with ssize = %d", core_id, new_ssize))

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
      ssize = new_ssize,
      thick = 1,
      bacon.change.thick = TRUE
    )

    age.mods.interp <- predict(run, depth = seq(0, clength$corelength, by = 1))
  }

  result <- as.data.frame(age.mods.interp) %>%
    mutate(depth = paste(core_id, as.character(factor(depth)))) %>%
    pivot_wider(names_from = iter, values_from = age)

  message(sprintf("Done with core %s", core_id))
  return(result)
} else {
  # --- MULTI-CORE RUN ---
  options(fftempdir = "src/temp/ff")

  Bacon_parallel <- function(i, Bacon_Frame, CoreIDs) {
    core_id <- CoreIDs[[i]]
    core_selection <- Bacon_Frame %>% filter(str_detect(id, CoreIDs[[i]]))
    clength <- CoreLengths %>% filter(str_detect(coreid, CoreIDs[[i]]))

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
      ssize = ssize,
      thick = 1,
      bacon.change.thick = TRUE
    )

    age.mods.interp <- as.ffdf(predict(run, depth = seq(0, clength$corelength, by = 1)))
    while (max(age.mods.interp$iter) < 10001) {
      diff_iter <- 10001 - (max(age.mods.interp$iter) - min(age.mods.interp$iter))
      new_ssize <- ceiling(ssize + (diff_iter * 2.5))
      message(sprintf("Retrying core %s with ssize = %d", CoreIDs[[i]], new_ssize))

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
        ssize = new_ssize,
        thick = 1,
        bacon.change.thick = TRUE
      )

      age.mods.interp <- as.ffdf(predict(run, depth = seq(0, clength$corelength, by = 1)))
    }

    age.mods.interp$depth <- as.character.ff(age.mods.interp$depth)
    age.mods.interp$depth <- ff(paste(CoreIDs[[i]], age.mods.interp$depth))
    out <- pivot_wider(as.data.frame(age.mods.interp), names_from = iter, values_from = age)
    message(sprintf("Done with core %s — number %d of %d", CoreIDs[[i]], i, length(CoreIDs)))
    return(out)
  }

  # Setup cluster
  no_cores <- min(length(CoreIDs), detectCores(logical = TRUE))
  cl <- makeCluster(no_cores, outfile = "", autoStop = TRUE)
  registerDoSNOW(cl)

  Bacon_Frame <- Bacon_Frame %>%
    mutate_all(type.convert, as.is = TRUE) %>%
    mutate_at(c("obs_age", "obs_err", "delta_R", "delta_STD"), as.integer)

  clusterExport(cl, c("Bacon_Frame", "CoreIDs", "acc.shape", "acc.mean",
                      "mem.strength", "mem.mean", "ssize", "CoreLengths",
                      "hamstr_bacon", "Bacon_parallel"))

  seed <- 210329
  seq_id_all <- 1:length(CoreIDs)

  Bacon_core_results <- foreach(i = seq_id_all,
                                .combine = dplyr::bind_rows,
                                .options.RNG = seed,
                                .multicombine = TRUE,
                                .maxcombine = 1000,
                                .inorder = FALSE) %dorng% {
    suppressPackageStartupMessages({
      library(tidyverse)
      library(IntCal)
      library(rbacon)
      library(hamstr)
      library(hamstrbacon)
      library(ff)
      library(ffbase)
    })

    tryCatch(Bacon_parallel(i, Bacon_Frame, CoreIDs), error = function(e) {
      message(sprintf("⚠️ Error in task %d (%s): %s", i, CoreIDs[[i]], e$message))
      NULL
    })
  }

  stopCluster(cl)
  registerDoSEQ()
  return(Bacon_core_results)
}