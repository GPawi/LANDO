# Step 1: Base image with Python, R, Jupyter, and Conda
FROM jupyter/datascience-notebook:python-3.11

# Set working directory inside the container
WORKDIR /home/jovyan/work

# Copy your code into the container
COPY . /home/jovyan/work

# Install SoS, Octave kernel, and JupyterLab UI
RUN pip install sos sos-notebook octave_kernel metakernel jupyterlab-sos "jupyterlab<4" && \
    python3 -m sos_notebook.install 

# Install R kernel (IRkernel) and register with Jupyter
RUN R -e "install.packages('IRkernel', repos='https://cloud.r-project.org')" \
    && R -e "IRkernel::installspec()"

# Change the USER
USER root

# Copy full Octave binary + packages from builder
COPY --from=octave-pkg-builder /usr/bin/octave /usr/bin/octave
COPY --from=octave-pkg-builder /usr/lib /usr/lib
COPY --from=octave-pkg-builder /usr/libexec /usr/libexec
COPY --from=octave-pkg-builder /usr/share/octave /usr/share/octave
COPY --from=octave-pkg-builder /opt/octave-pkgs /usr/share/octave/packages

# Let Octave know where to find the installed packages
ENV OCTAVE_PATH="/usr/share/octave/packages"

# Change USER back
USER $NB_UID

# Launch JupyterLab and open LANDO.ipynb
CMD ["start-notebook.sh", "--NotebookApp.default_url=/lab/tree/LANDO.ipynb"]
