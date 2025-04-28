# install_r_packages.R

# Set options
options(build_vignettes = FALSE)
options(timeout = max(600, getOption("timeout")))

# Standard CRAN repo
cran_repo <- "https://cran.r-project.org"

# Install CRAN packages (excluding arrow for now)
cran_pkgs <- c(
  "changepoint", "DescTools", "devtools",
  "doParallel", "doRNG", "doSNOW", "dplyr", "ff", "foreach", "forecast",
  "FuzzyNumbers", "IntCal", "knitr", "lubridate",
  "Metrics", "plyr", "R.devices", "raster", "remotes",
  "rstan", "sets", "tidyverse", "tseries", "clam"
)

install.packages(cran_pkgs, repos = cran_repo)

# Optional: Confirm installed versions
if (requireNamespace("clam", quietly = TRUE)) {
  message("Installed clam version: ", as.character(packageVersion("clam")))
}
if (requireNamespace("arrow", quietly = FALSE)) {
  message("Installed arrow version: ", as.character(packageVersion("arrow")))
}