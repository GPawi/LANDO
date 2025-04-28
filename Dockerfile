# Step 1: Base image with Python, R, Jupyter, and Conda
FROM jupyter/datascience-notebook:python-3.11

# Set working directory inside the container
WORKDIR /home/jovyan/work

# Copy your code into the container
COPY . /home/jovyan/work

# Install SoS, Octave kernel, and JupyterLab UI
RUN pip install \
    sos \
    sos-r \
    sos-python \
    sos-matlab \
    ipysheet \
    ipyfilechooser \
    psycopg2-binary \
    sos-notebook \
    octave_kernel \
    metakernel \
    jupyterlab-sos \
    setuptools \
    "jupyterlab<4.1" && \
    # Install SoS and language kernels
    python3 -m sos_notebook.install --sys-prefix

# Set library environment
ENV R_LIBS_SITE=/opt/conda/lib/R/library
ENV LD_LIBRARY_PATH=/opt/conda/lib:/opt/conda/lib/R/lib:/usr/local/lib

# Register the R kernel
RUN R -e "install.packages('IRkernel', repos='https://cloud.r-project.org')" && \
    R -e "IRkernel::installspec(user = FALSE)"

# Install shared R + Python data exchange libraries via conda (Arrow, Feather)
RUN mamba install -y -c conda-forge \
    r-arrow \
    pyarrow \
    feather-format

# Copy pre-installed R packages from builder stage
COPY --from=r-lib-builder /opt/conda/lib/R/library /opt/conda/lib/R/library

# Switch to root for system-level installations
USER root

# Install dev tools and system libraries
RUN apt-get update && apt-get install -y \
    build-essential gfortran \
    libcurl4-openssl-dev libssl-dev libxml2-dev \
    libhdf5-openmpi-103 libglpk40 libreadline8 \
    libfftw3-double3 libfftw3-3 libfftw3-single3 libgraphicsmagick++-q16-12 \
    libcholmod3 libamd2 libcolamd2 libccolamd2 libcxsparse3 \
    libsuitesparseconfig5 libumfpack5 libspqr2 libarpack2 libqrupdate1 \
    libgl2ps1.4 libopenblas0 libglu1-mesa libgl1 libx11-6 \
    libfontconfig1 libfreetype6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Ensure compiler works (for diagnosing build errors)
RUN echo 'int main() { return 0; }' > test.cpp && g++ test.cpp -o test && ./test && echo "C++ compiler works"

# Set compiler flags for R builds
RUN mkdir -p /etc/R && \
    echo 'CC = /usr/bin/gcc' >> /etc/R/Makevars && \
    echo 'CXX = /usr/bin/g++' >> /etc/R/Makevars && \
    echo 'CXX11 = /usr/bin/g++' >> /etc/R/Makevars && \
    echo 'CXX14 = /usr/bin/g++' >> /etc/R/Makevars && \
    echo 'CXX17 = /usr/bin/g++' >> /etc/R/Makevars && \
    echo 'CXX20 = /usr/bin/g++' >> /etc/R/Makevars && \
    echo 'CXXFLAGS = -O2 -pipe -march=native -mtune=native' >> /etc/R/Makevars && \
    echo 'CXX11FLAGS = $(CXXFLAGS)' >> /etc/R/Makevars && \
    echo 'CXX14FLAGS = $(CXXFLAGS)' >> /etc/R/Makevars && \
    echo 'CXX17FLAGS = $(CXXFLAGS)' >> /etc/R/Makevars && \
    echo 'CXX20FLAGS = $(CXXFLAGS)' >> /etc/R/Makevars

# Lock arrow and stringi to prevent accidental reinstall
RUN chmod -R a-w /opt/conda/lib/R/library/arrow || true && \
    chmod -R a-w /opt/conda/lib/R/library/stringi || true

# Set optional R install behaviors (disable source fallback)
RUN echo 'options(install.packages.check.source = "no")' >> /home/jovyan/.Rprofile && \
    echo 'options(pkgType = "binary")' >> /home/jovyan/.Rprofile && \
    echo '.libPaths("/opt/conda/lib/R/library")' >> /home/jovyan/.Rprofile

# Add IntCal20 calibration curves with proper filenames
RUN mkdir -p /opt/conda/lib/R/library/IntCal/extdata && \
    curl -sSL https://intcal.org/IntCal20Files/intcal20.14c -o /opt/conda/lib/R/library/IntCal/extdata/3Col_intcal20.14C && \
    curl -sSL https://intcal.org/IntCal20Files/marine20.14c -o /opt/conda/lib/R/library/IntCal/extdata/3Col_marine20.14C && \
    curl -sSL https://intcal.org/IntCal20Files/shcal20.14c -o /opt/conda/lib/R/library/IntCal/extdata/3Col_shcal20.14C && \
    curl -sSL https://intcal.org/IntCal20Files/constcal20.14c -o /opt/conda/lib/R/library/IntCal/extdata/3Col_constcal20.14C

# Ensure old version is gone
RUN rm -f /usr/bin/octave /usr/bin/octave-cli

# Install runtime libs needed for Octave 8.3.0
RUN apt-get update && apt-get install -y \
    libhdf5-openmpi-103 libglpk40 libcurl4-openssl-dev libreadline8 \
    libfftw3-double3 libfftw3-3 libfftw3-single3 libgraphicsmagick++-q16-12 \
    libcholmod3 libamd2 libcolamd2 libccolamd2 libcxsparse3 \
    libsuitesparseconfig5 libumfpack5 libspqr2 libarpack2 libqrupdate1 \
    libgl2ps1.4 libopenblas0 libglu1-mesa libgl1 libx11-6 \
    libfontconfig1 libfreetype6 libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Copy full Octave binary + packages from builder
COPY --from=octave-pkg-builder /usr/local /usr/local
#COPY --from=octave-pkg-builder /opt/octave-pkgs /usr/share/octave/packages

# Let Octave know where to find the installed packages
ENV OCTAVE_EXECUTABLE=/usr/local/bin/octave
#ENV OCTAVE_PATH=/usr/share/octave/packages

# Rebuild INDEX files for each copied package
RUN for d in /usr/local/share/octave/packages/*; do \
      if [ -d "$d" ]; then \
        octave --eval "pkg rebuild('${d}')" || true; \
      fi; \
    done

# Set default Octave package directory
RUN echo "pkg prefix('/usr/local/share/octave/packages'); pkg local_list('/usr/local/share/octave/octave_packages');" > /usr/local/share/octave/site/m/startup/octaverc

# Set persistent Octave path for iser
RUN echo "addpath('/src/UndatableFolder')" >> /home/jovyan/.octaverc && \
    chown jovyan:users /home/jovyan/.octaverc

# Back to notebook user
USER $NB_UID
