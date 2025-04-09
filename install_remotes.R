# install_remotes.R

Sys.setenv(R_REMOTES_NO_ERRORS_FROM_WARNINGS = "true")
options(build_vignettes = FALSE)

if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes", repos = "https://cloud.r-project.org")
}

pkgs <- c(
  "edwindj/ffbase",
  "earthsystemdiagnostics/hamstr",
  "earthsystemdiagnostics/hamstrbacon",
  "Maarten14C/rbacon"
)

for (pkg in pkgs) {
  tryCatch({
    remotes::install_github(pkg, upgrade = "never")
  }, error = function(e) {
    message("Failed to install: ", pkg, "\n", e$message)
  })
}
