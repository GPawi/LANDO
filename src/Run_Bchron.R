### Script to run Bchron in LANDO ###
## Load libraries
suppressPackageStartupMessages(c(library('tidyverse')
                                 ,library('Bchron')
                                 ,library('parallel')
                                 ,library('doParallel')
                                 ,library('foreach')
                                 ,library('doRNG')
                                 ,library('doSNOW')
                                 ))

## Function for run
Bchron_parallel = function(...) {
  core_selection <- Bchron_Frame %>% filter(str_detect(id, CoreIDs[[i]]))
  clength <- CoreLengths %>% filter(str_detect(coreid, CoreIDs[[i]]))
  run <- Bchronology(ages = core_selection$ages,
                    ageSds = core_selection$ageSds,
                    calCurves = core_selection$calCurves,
                    positions = core_selection$position,
                    positionThickness = core_selection$thickness,
                    ids = core_selection$id,
                    #jitterPositions = TRUE, #removed from Bchron 4.7.6
                    artificialThickness = 0.5,
                    iterations = 15000,  #iterations = 10000,
                    burn = 5000,        #burn = 2000,
                    thin = 1,            #thin = 8,
                    allowOutside = TRUE,
                    predictPositions = seq(0,clength$corelength, by = 1))
  result_individual_core <- as.data.frame(t(run$thetaPredict))
  row.names(result_individual_core) <- outer(CoreIDs[[i]], seq(0,clength$corelength, by = 1), paste)
  message(sprintf(" Done with core %s - Number %d out of %d", CoreIDs[[i]], i, length(CoreIDs)))
  return (result_individual_core)
}

## Initialize cluster
no_cores <- detectCores(logical = TRUE)
if (no_cores < length(CoreIDs)) {
  cl = makeCluster(no_cores*0.8, outfile = "", autoStop = TRUE)
  } else {cl = makeCluster(length(CoreIDs), outfile = "", autoStop = TRUE)} 
registerDoSNOW(cl)
seed <- 210308

## Load data and give it to cluster
Bchron_Frame <- Bchron_Frame %>%
    mutate_all(type.convert, as.is = TRUE) %>%
    mutate_at(c("ages", "ageSds"), as.integer)
seq_id_all <- 1:length(CoreIDs)
clusterExport(cl,list('Bchron_parallel','Bchron_Frame','CoreIDs','CoreLengths')) 


## Run function in parallel in cluster
Bchron_core_results <- foreach(i = seq_id_all 
                              ,.combine=dplyr::bind_rows
                              ,.multicombine = TRUE
                              ,.maxcombine = 1000
                              ,.inorder = FALSE
                              ,.packages=c('tidyverse'
                                           ,'Bchron'
                                           ,'foreach'
                                           ,'parallel'
                                           )
                              ,.options.RNG=seed
                              ) %dorng% {
                                tryCatch(
                                  Bchron_parallel(i, Bchron_Frame, CoreIDs)
                                         ,error = function(e){
                                           message(sprintf(" Caught an error in task %d! (%s)", i, CoreIDs[[i]]))
                                           print(e)
                                           }
                                )
                                }
## Stop cluster
stopCluster(cl)
rm(list = "cl")
gc()
registerDoSEQ()


return(Bchron_core_results)
