# Step 1: Base image with Python, R, Jupyter, and Conda
FROM jupyter/datascience-notebook:python-3.11

# Set working directory inside the container
WORKDIR /home/jovyan/work

# Copy your code into the container
COPY . /home/jovyan/work

# Install SoS, Octave kernel, and JupyterLab UI
RUN pip install sos sos-r sos-matlab ipysheet ipyfilechooser psycopg2-binary sos-notebook octave_kernel metakernel jupyterlab-sos "jupyterlab<4" &&     python3 -m sos_notebook.install 

# Set liberary environment
ENV R_LIBS_SITE=/opt/conda/lib/R/library

# Register the R kernel
RUN R -e "install.packages('IRkernel', repos='https://cloud.r-project.org')" &&     R -e "IRkernel::installspec(user = FALSE)"

# Set environment options for R
ENV RENV_CONFIG_DISABLE_CACHE=TRUE
ENV R_REMOTES_NO_ERRORS_FROM_WARNINGS=true
ENV RSPM=https://packagemanager.posit.co/cran/latest

# Install CRAN packages with fallback to source if binary not supported
RUN Rscript -e "options(repos = c(RSPM = 'https://packagemanager.posit.co/cran/latest'), build_vignettes = FALSE); install.packages(c(   'arrow','Bchron','changepoint','DescTools','devtools','doParallel','doRNG','doSNOW','dplyr','ff','foreach','forecast',   'FuzzyNumbers','IntCal','knitr','lubridate','maptools','Metrics','plyr','R.devices','raster','remotes',   'rstan','sets','tidyverse','tseries' ))"

# Install GitHub R packages (avoiding rebuilds and avoiding unwanted upgrades)
COPY install_remotes.R /tmp/install_remotes.R
RUN Rscript /tmp/install_remotes.R

# Switch to root for system-level installs
USER root

# Ensure old version is gone
RUN rm -f /usr/bin/octave /usr/bin/octave-cli

# Install runtime libs needed for Octave 8.3.0
RUN apt-get update && apt-get install -y     libhdf5-openmpi-103     libglpk40     libcurl4-openssl-dev     libreadline8     libfftw3-double3     libfftw3-3     libfftw3-single3     libgraphicsmagick++-q16-12     libcholmod3     libamd2     libcolamd2     libccolamd2     libcxsparse3     libsuitesparseconfig5     libumfpack5     libspqr2     libarpack2     libqrupdate1     libgl2ps1.4     libopenblas0     libglu1-mesa     libgl1     libx11-6     libfontconfig1     libfreetype6     libgomp1     && rm -rf /var/lib/apt/lists/*

# Copy full Octave binary + packages from builder
COPY --from=octave-pkg-builder /usr/local /usr/local
COPY --from=octave-pkg-builder /opt/octave-pkgs /usr/share/octave/packages

# Let Octave know where to find the installed packages
ENV OCTAVE_EXECUTABLE=/usr/local/bin/octave
ENV OCTAVE_PATH=/usr/share/octave/package

# Make sure R uses the correct library path inside the container
RUN echo '.libPaths("/opt/conda/lib/R/library")' >> /etc/R/Rprofile.site

# Back to notebook user
USER $NB_UID
