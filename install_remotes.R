# install_remotes.R
.libPaths("/opt/conda/lib/R/library")

Sys.setenv(R_REMOTES_NO_ERRORS_FROM_WARNINGS = "true")
options(build_vignettes = FALSE)

# Ensure 'remotes' is installed
if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes", repos = "https://cloud.r-project.org")
}

# Install GitHub packages with correct settings
pkgs <- list(
  list(repo = "edwindj/ffbase", subdir = "pkg"),
  list(repo = "earthsystemdiagnostics/hamstr"),
  list(repo = "earthsystemdiagnostics/hamstrbacon"),
  list(repo = "Maarten14C/rbacon"),
  list(repo = "Maarten14C/clam", ref = "v2.3.9")
)

for (pkg in pkgs) {
  tryCatch({
    if (!is.null(pkg$subdir)) {
      remotes::install_github(pkg$repo, subdir = pkg$subdir, upgrade = "never")
    } else if (!is.null(pkg$ref)) {
      remotes::install_github(pkg$repo, ref = pkg$ref, upgrade = "never")
    } else {
      remotes::install_github(pkg$repo, upgrade = "never")
    }
  }, error = function(e) {
    message("Failed to install: ", pkg$repo, "\n", e$message)
  })
}
