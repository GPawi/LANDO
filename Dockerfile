# Step 1: Base image with Python, R, Jupyter, and Conda
FROM jupyter/datascience-notebook:python-3.11

# Set working directory inside the container
WORKDIR /home/jovyan/work

# Copy your code into the container
COPY . /home/jovyan/work

# Install SoS and its Python kernel
RUN pip install sos sos-notebook \
    && python3 -m sos_notebook.install

# Downgrade to JupyterLab 3.x to support jupyterlab-sos
RUN pip install "jupyterlab<4" \
    && pip install jupyterlab-sos

# Install R kernel (IRkernel) and register with Jupyter
RUN R -e "install.packages('IRkernel', repos='https://cloud.r-project.org')" \
    && R -e "IRkernel::installspec()"

# Change the USER
USER root

# Install Octave runtime (without dev tools)
RUN apt-get update && apt-get install -y octave

# ⬇️ COPY prebuilt Octave packages from the builder
COPY --from=octave-pkg-builder /opt/octave-pkgs /usr/share/octave/packages

# Let Octave know where to find the installed packages
ENV OCTAVE_PATH="/usr/share/octave/packages"

# Change USER back
USER $NB_UID

# Launch JupyterLab and open LANDO.ipynb
CMD ["start-notebook.sh", "--NotebookApp.default_url=/lab/tree/LANDO.ipynb"]
