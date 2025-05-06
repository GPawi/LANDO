#!/bin/bash

# Move into the directory this script is in
cd "$(dirname "$0")"

# Ensure tmp_host is created one level up
mkdir -p ../tmp_host

# Launch Docker Compose in detached mode
echo "🚀 Starting LANDO environment..."
docker-compose -f ./setup/docker-compose.yml up -d

# Gracefully shut down container on Ctrl+C
trap 'echo \"🧹 Stopping LANDO...\"; docker-compose -f ./setup/docker-compose.yml down; exit 0' INT

# Open the user's browser
echo "🚀 Opening LANDO in your browser..."
if command -v xdg-open &> /dev/null; then
  xdg-open http://localhost:8888/lab/tree/LANDO.ipynb
elif command -v open &> /dev/null; then
  open http://localhost:8888/lab/tree/LANDO.ipynb
else
  echo "🌐 Please open your browser and go to: http://localhost:8888/lab/tree/LANDO.ipynb"
fi

# Keep the script running to capture Ctrl+C
echo "✅ LANDO is running. Press Ctrl+C to stop."
while true; do sleep 60; done