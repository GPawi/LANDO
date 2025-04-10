# install_r_packages.R

# Set options
options(build_vignettes = FALSE)
options(timeout = max(600, getOption("timeout")))

# Standard CRAN repo
cran_repo <- "https://cran.r-project.org"

# Install CRAN packages (excluding arrow and clam for separate handling)
cran_pkgs <- c(
  "changepoint", "DescTools", "devtools",
  "doParallel", "doRNG", "doSNOW", "dplyr", "ff", "foreach", "forecast",
  "FuzzyNumbers", "IntCal", "knitr", "lubridate",
  "Metrics", "plyr", "R.devices", "raster", "remotes",
  "rstan", "sets", "tidyverse", "tseries"
)

install.packages(cran_pkgs, repos = cran_repo)

# Install arrow explicitly from CRAN (source)
#install.packages("arrow", repos = c(RSPM = "https://packagemanager.posit.co/cran/latest"), type = "binary")

# Install clam version 2.3.9 from CRAN archive
clam_url <- "https://cran.r-project.org/src/contrib/Archive/clam/clam_2.3.9.tar.gz"
install.packages(clam_url, repos = NULL, type = "source")

# Optional: confirm installed version
if (requireNamespace("clam", quietly = TRUE)) {
  message("Installed clam version: ", as.character(packageVersion("clam")))
}
if (requireNamespace("arrow", quietly = FALSE)) {
  message("Installed arrow version: ", as.character(packageVersion("arrow")))
}
