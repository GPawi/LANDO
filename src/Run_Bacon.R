### Script to run Bacon via hamstr in LANDO ###
## Load libraries
suppressPackageStartupMessages(c(library('hamstr')
                                 ,library('rbacon')
                                 ,library('hamstrbacon')
                                 ,library('IntCal')
                                 ,library('tidyverse')
                                 ,library('parallel')
                                 ,library('foreach')
                                 ,library('doRNG')
                                 ,library('doSNOW')
                                 ,library('ff')
                                 ,library('ffbase') 
                                 ))

options(fftempdir = "src/temp/ff")

## Function for run
Bacon_parallel <- function(...) {
  options(fftempdir = "src/temp/ff")
  core_selection <- Bacon_Frame %>% filter(str_detect(id, CoreIDs[[i]]))
  clength <- CoreLengths %>% filter(str_detect(coreid, CoreIDs[[i]]))
  run <- hamstr_bacon(id = core_selection$id,
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
  #age.mods.interp <- as.ffdf(hamstr:::predict.hamstr_bacon_fit(run, depth = seq(0,clength$corelength, by = 1)))
  age.mods.interp <- as.ffdf(predict(run, depth = seq(0,clength$corelength, by = 1)))
  rm(run)
  gc()
  while (max(age.mods.interp$iter) < 10001) {
    diff_iter <- 10001 - (max(age.mods.interp$iter) - min(age.mods.interp$iter))
    new_ssize <- ceiling(ssize + (diff_iter*2.5))
    message(sprintf("There are not enough of iterations in core %s - re-run with ssize = %d", CoreIDs[[i]], new_ssize))
    rm(age.mods.interp)
    run <- hamstr_bacon(id = core_selection$id,
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
    #age.mods.interp <- as.ffdf(hamstr:::predict.hamstr_bacon_fit(run, depth = seq(min(run$pars$d.min),clength$corelength, by = 1)))
    age.mods.interp <- as.ffdf(predict(run, depth = seq(0,clength$corelength, by = 1)))
    rm(run)
    gc()
  } 
  gc()
  age.mods.interp <- subset(age.mods.interp, iter < 10001)
  age.mods.interp$depth <- as.character.ff(age.mods.interp$depth)
  age.mods.interp$depth <- ff(paste(CoreIDs[[i]], levels(age.mods.interp[,]$depth)), levels = paste(CoreIDs[[i]], levels(age.mods.interp$depth)), length = length(age.mods.interp$depth))
  age.mods.interp <- pivot_wider(as.data.frame(age.mods.interp), names_from = iter, values_from = age)
  message(sprintf(" Done with core %s - Number %d out of %d", CoreIDs[[i]], i, length(CoreIDs)))
  return(age.mods.interp)
}

## Initialize cluster
no_cores <- detectCores(logical = TRUE)
if (no_cores < length(CoreIDs)) {
  cl <- makeCluster(no_cores*0.8, outfile = "", autoStop = TRUE)
  } else {cl <- makeCluster(length(CoreIDs), outfile = "", autoStop = TRUE)} 
registerDoSNOW(cl)
seed <- 210329

## Load data and give it to cluster
Bacon_Frame <- Bacon_Frame %>% 
  mutate_all(type.convert, as.is = TRUE) %>% 
  # mutate_if(is.factor, as.character) %>% #removed since "as.is = TRUE" was added
  mutate_at(c("obs_age", "obs_err","delta_R","delta_STD"), as.integer)
seq_id_all <- 1:length(CoreIDs)
clusterExport(cl,list('Bacon_parallel','Bacon_Frame','CoreIDs','acc.shape','acc.mean', 'mem.strength', 'mem.mean', 'ssize', 'CoreLengths'))

## Run function in parallel in cluster
Bacon_core_results <- foreach(i = seq_id_all 
                              #,.combine='rbind'
                              ,.combine=dplyr::bind_rows
                              ,.multicombine = TRUE
                              ,.maxcombine = 1000
                              ,.inorder = FALSE
                              ,.packages=c('tidyverse', 'IntCal', 'rbacon', 'hamstr', 'foreach', 'parallel','ff', 'ffbase', 'hamstrbacon')
                              ,.options.RNG=seed

) %dorng% {
  tryCatch(
    Bacon_parallel(i, Bacon_Frame, CoreIDs)
    ,error = function(e){
      message(sprintf(" Caught an error in task %d! (%s)", i, CoreIDs[[i]]))
      print(e)
    }
  )
}

stopCluster(cl)
rm(list = "cl")
gc()
registerDoSEQ()

return(Bacon_core_results)
