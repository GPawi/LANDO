#!/bin/bash

# ------------------------------
# LANDO Docker Entrypoint Script
# ------------------------------

# Move to project root
cd /home/jovyan/work

# Ensure tmp_host exists and clean other temporary folders
mkdir -p ./src/tmp_host
chmod 1777 ./src/tmp_host
rm -rf ./src/__pycache__ ./.ipynb_checkpoints

# Start JupyterLab without token, open LANDO notebook
echo "🚀 Starting JupyterLab..."
exec start-notebook.sh --NotebookApp.token='' --NotebookApp.default_url="/lab/tree/LANDO.ipynb"
