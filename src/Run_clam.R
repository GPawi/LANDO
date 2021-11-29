### Script to run clam in LANDO ###
## Load libraries
suppressPackageStartupMessages(c(library('IntCal')
                                 ,library('clam')
                                 ,library('R.devices')
                                 ,library('tidyverse')
                                 ,library('foreach')
                                 ,library('parallel')
                                 ,library('doParallel')
                                 ,library('doSNOW')
                                 ))

## Initialize cluster
no_cores = detectCores(logical = TRUE)
cl = makeCluster(no_cores*0.8, outfile = "", autoStop = TRUE)
registerDoSNOW(cl)

## Load data and give it to the cluster
seq_id_all <- 1:length(CoreIDs)
clam_Frame <- clam_Frame %>% mutate_at("depth", as.double)
CoreLengths <- CoreLengths %>% mutate_at("corelength", as.integer)
clusterExport(cl,list('clam_Frame','CoreLengths'))

## Run function in parallel in cluster
clam_core_results <- foreach(core = seq_id_all
                   ,.combine='rbind'
                   #,.combine=dplyr::bind_rows
                   ,.multicombine = TRUE
                   ,.maxcombine = 1000
                   ,.packages=c('tidyverse', 'foreach', 'parallel', 'clam')) %do% {
                     ### Prepare input from each sediment core
                     core_selection <- clam_Frame %>% filter(str_detect(lab_ID, CoreIDs[[core]]))
                     clength <- CoreLengths %>% filter(str_detect(coreid, CoreIDs[[core]]))
                     date_max <- plyr::round_any(max(core_selection$depth), 1, f = floor)
                     core_max <- clength$corelength
                     ### Initial attributes
                     types <- types_curve
                     smoothness <- smoothness_curve
                     poly_degree <- poly_degree_curve
                     search_rev <- "!!! Too many models with age reversals!!!"
                     search_fit <- "  Fit \\(-log, lower is better\\): "
                     ####
                     tmpdir <- tempdir()
                     dirbase <- basename(tmpdir)
                     dirnm <- dirname(tmpdir) 
                     datfl <- tempfile(tmpdir = tmpdir)
                     fl <- paste0(tmpdir, "//", dirbase, ".csv")
                     utils::write.csv(core_selection,
                                      file = fl,
                                      row.names = FALSE, quote = FALSE)
                     ## Take limits for each methods into account
                     if (length(unique(core_selection$depth)) < 4) {
                       types <- 1:3
                     }
                     if (poly_degree[length(poly_degree)] >= length(unique(core_selection$depth))) {
                       poly_degree <- 1:(length(unique(core_selection$depth))-1)
                     }
                     ###############################################################
                     result_types <- foreach(type = types
                                             ,.combine='rbind'
                                             #,.combine=dplyr::bind_rows
                                             ,.multicombine = TRUE
                                             ,.maxcombine = 1000
                                             ,.packages=c('tidyverse', 'foreach', 'parallel', 'clam')) %dopar% {
                                               ## Type 1 & Type 3
                                               if (type == 1 || type == 3){
                                                 suppressWarnings(R.devices::suppressGraphics({
                                                   z <- capture.output(clam(core=dirbase, coredir=dirnm, type = type, 
                                                                            its = 20000, dmin = 0, dmax = core_max, 
                                                                            plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
                                                 }))
                                                 fit <- subset(z, grepl((gsub("[\\]", "", search_fit)), z, fixed = TRUE) == TRUE)
                                                 fit <- as.numeric(sub(search_fit, "", as.character(fit)))
                                                 if (any(grepl(search_rev, z, fixed = TRUE)) == TRUE) {
                                                   message(sprintf('%s : Too many models with age reversals with type %d', CoreIDs[[core]], type))
                                                   
                                                 } else if (fit == 'Inf' & best_fit == TRUE) {
                                                   message(sprintf('%s : Inf in model fit; model with type %d will be discarded', CoreIDs[[core]], type))
                                                 } else {
                                                   chron_model <- as.data.frame(chron[, 1:10000]) 
                                                   mid <- outer(CoreIDs[[core]], seq(0, core_max, by = 1), paste)
                                                   row.names(chron_model) <- outer(mid, sprintf('-clam_T%d', type), paste0)
                                                   chron_model$fit <- fit
                                                   return (chron_model)
                                                 }
                                               } 
                                               ## Type 2 with different degrees of polynomial degree
                                               else if (type == 2) {
                                                 result_2nd <- foreach(degree = poly_degree
                                                                       ,.combine='rbind'
                                                                       #,.combine=dplyr::bind_rows
                                                                       ,.multicombine = TRUE
                                                                       ,.maxcombine = 1000
                                                                       ,.packages=c('tidyverse', 'foreach', 'parallel', 'clam')) %dopar% {
                                                                         for (poly_d in degree){
                                                                           suppressWarnings(R.devices::suppressGraphics({
                                                                             z <- capture.output(clam(core=dirbase, coredir=dirnm, type = type, smooth = poly_d, 
                                                                                                      its = 20000, dmin = 0, dmax = core_max, 
                                                                                                      plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
                                                                           }))
                                                                           fit <- subset(z, grepl((gsub("[\\]", "", search_fit)), z, fixed = TRUE) == TRUE)
                                                                           fit <- as.numeric(sub(search_fit, "", as.character(fit)))
                                                                           if (any(grepl(search_rev, z, fixed = TRUE)) == TRUE) {
                                                                             message(sprintf('%s : Too many models with age reversals with type %d and degree of %d', CoreIDs[[core]], type, poly_d))
                                                                           } else if (fit == 'Inf' & best_fit == TRUE) {
                                                                             message(sprintf('%s : Inf in model fit; model with type %d and degree of %d will be discarded', CoreIDs[[core]], type, poly_d))
                                                                           } else {
                                                                             chron_model <- as.data.frame(chron[, 1:10000])
                                                                             mid <- outer(CoreIDs[[core]], seq(0, core_max, by = 1), paste)
                                                                             row.names(chron_model) <- outer(mid, sprintf('-clam_T%d_D%d', type, poly_d), paste0)
                                                                             chron_model$fit <- fit
                                                                             return (chron_model)
                                                                           }                 
                                                                         }
                                                                       }
                                                 if (best_fit == TRUE){
                                                   result_2nd <- result_2nd[result_2nd$fit == min(result_2nd$fit),]
                                                 }
                                                 return (result_2nd)
                                               } 
                                               ## Type 4 with different smoothness
                                               else if (type == 4) {
                                                 result_4th <- foreach(s = smoothness
                                                                       ,.combine='rbind'
                                                                       #,.combine=dplyr::bind_rows
                                                                       ,.multicombine = TRUE
                                                                       ,.maxcombine = 1000
                                                                       ,.packages=c('tidyverse', 'foreach', 'parallel', 'clam')) %dopar% {
                                                                         for (smo1 in s){
                                                                           suppressWarnings(R.devices::suppressGraphics({ 
                                                                             z <- capture.output(clam(core=dirbase, coredir=dirnm, type = type, smooth = smo1, 
                                                                                                      its = 20000, dmin = 0, dmax = core_max, 
                                                                                                      plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
                                                                           }))
                                                                           fit <- subset(z, grepl((gsub("[\\]", "", search_fit)), z, fixed = TRUE) == TRUE)
                                                                           fit <- as.numeric(sub(search_fit, "", as.character(fit)))
                                                                           if (any(grepl(search_rev, z, fixed = TRUE)) == TRUE) {
                                                                             message(sprintf('%s : Too many models with age reversals with type %d and smooth of %.1f', CoreIDs[[core]], type, smo1))
                                                                           } else if (fit == 'Inf' & best_fit == TRUE) {
                                                                             message(sprintf('%s : Inf in model fit; model with type %d and smooth of %.1f will be discarded', CoreIDs[[core]], type, smo1))
                                                                           } else {
                                                                             chron_model <- as.data.frame(chron[, 1:10000])
                                                                             mid <- outer(CoreIDs[[core]], seq(0, core_max, by = 1), paste)
                                                                             row.names(chron_model) <- outer(mid, sprintf('-clam_T%d_S%d', type, as.integer(smo1*10)), paste0)
                                                                             chron_model$fit <- fit
                                                                             return (chron_model)
                                                                           }
                                                                         }
                                                                       }
                                                 if (best_fit == TRUE){
                                                   result_4th <- result_4th[result_4th$fit == min(result_4th$fit),]
                                                 }
                                                 return (result_4th)
                                               }
                                               ## Type 5 with different smoothness 
                                               else {
                                                 result_5th <- foreach(k = smoothness
                                                                       ,.combine='rbind'
                                                                       #,.combine=dplyr::bind_rows
                                                                       ,.multicombine = TRUE
                                                                       ,.maxcombine = 1000
                                                                       ,.packages=c('tidyverse', 'foreach', 'parallel', 'clam')
                                                                       ,.errorhandling = 'remove') %dopar% {
                                                                         for (smo2 in k){
                                                                           suppressWarnings(R.devices::suppressGraphics({ 
                                                                             z <- capture.output(clam(core=dirbase, coredir=dirnm, type = type, smooth = smo2, 
                                                                                                      its = 20000, dmin = 0, dmax = date_max, 
                                                                                                      plotpdf = FALSE, plotpng = FALSE, plotname = FALSE))
                                                                           }))
                                                                           fit <- subset(z, grepl((gsub("[\\]", "", search_fit)), z, fixed = TRUE) == TRUE)
                                                                           fit <- as.numeric(sub(search_fit, "", as.character(fit)))
                                                                           if (any(grepl(search_rev, z, fixed = TRUE)) == TRUE) {
                                                                             message(sprintf('%s : Too many models with age reversals with type %d and smooth of %.1f', CoreIDs[[core]], type, smo2))
                                                                           } else if (fit == 'Inf' & best_fit == TRUE) {
                                                                             message(sprintf('%s : Inf in model fit; model with type %d and smooth of %.1f will be discarded', CoreIDs[[core]], type, smo2))
                                                                           } else {
                                                                             chron_model <- as.data.frame(chron[, 1:10000])
                                                                             mid <- outer(CoreIDs[[core]], seq(0, date_max, by = 1), paste)
                                                                             row.names(chron_model) <- outer(mid, sprintf('-clam_T%d_S%d', type, as.integer(smo2*10)), paste0)
                                                                             chron_model$fit <- fit
                                                                             return (chron_model)
                                                                           }
                                                                         }
                                                                       }
                                                 if (best_fit == TRUE){
                                                   result_5th <- result_5th[result_5th$fit == min(result_5th$fit),]
                                                 }
                                                 return (result_5th)
                                               }
                                               ########################################
                                             }
                     message(sprintf(" Done with core %s - Number %d out of %d", CoreIDs[[core]], core, length(CoreIDs)))
                     if (best_fit == TRUE){
                       if (is.null(result_types)){
                         message(sprintf("No suitable best fit model found for core %s", CoreIDs[[core]]))
                       } else {
                         result_types <- result_types[result_types$fit == min(result_types$fit),]
                       }
                     }
                     return (result_types)
                   }

stopCluster(cl)
rm(list = "cl")
gc()
registerDoSEQ()

clam_core_results$fit <- NULL
return (clam_core_results)