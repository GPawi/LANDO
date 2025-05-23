# install_remotes.R

# Ensure packages go into the correct lib path inside Docker
.libPaths("/opt/conda/lib/R/library")

# Environment and install options
Sys.setenv(R_REMOTES_NO_ERRORS_FROM_WARNINGS = "true")
options(build_vignettes = FALSE)
options(timeout = max(600, getOption("timeout")))

# Ensure 'remotes' is installed
if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes", repos = "https://cloud.r-project.org")
}

# List of GitHub packages with optional 'subdir' or 'ref'
pkgs <- list(
  list(repo = "edwindj/ffbase", subdir = "pkg"),
  list(repo = "Maarten14C/rbacon"),
  list(repo = "andrewcparnell/Bchron"),
  list(repo = "earthsystemdiagnostics/hamstr"),
  list(repo = "earthsystemdiagnostics/hamstrbacon")
)

# Install each package, catching errors and preserving state
for (pkg in pkgs) {
  tryCatch({
    message("Installing: ", pkg$repo)
    
    if (!is.null(pkg$subdir)) {
      remotes::install_github(pkg$repo, subdir = pkg$subdir, upgrade = "never", quiet = FALSE)
    } else if (!is.null(pkg$ref)) {
      remotes::install_github(pkg$repo, ref = pkg$ref, upgrade = "never", quiet = FALSE)
    } else {
      remotes::install_github(pkg$repo, upgrade = "never", quiet = FALSE)
    }
    
    message("Successfully installed: ", pkg$repo)
  }, error = function(e) {
    message("Failed to install: ", pkg$repo, "\n", e$message)
  })
}
