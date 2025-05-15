#!/bin/bash

# Move into the directory *above* the script (the project root)
cd "$(dirname "$0")"

# Ensure tmp_host exists in project root
mkdir -p ./src/tmp_host

# Launch Docker Compose using the relative path to the YAML file
echo "🚀 Starting LANDO environment..."

MAX_RETRIES=5
RETRY_DELAY=4
COUNT=0
SUCCESS=0

while [[ $COUNT -lt $MAX_RETRIES ]]; do
  if docker-compose -f ./setup/docker-compose.yml up -d; then
    SUCCESS=1
    echo "⏳ Giving Jupyter a few seconds to start up..."
    sleep 5
    break
  else
    echo "⚠️ Docker Compose failed. Retrying in $RETRY_DELAY seconds... ($((COUNT+1))/$MAX_RETRIES)"
    sleep $RETRY_DELAY
    COUNT=$((COUNT+1))
  fi
done

if [[ $SUCCESS -ne 1 ]]; then
  echo "❌ LANDO could not be started. Is Docker running and is the image 'lando-full' built?"
  exit 1
fi

# Gracefully shut down container and clean up on Ctrl+C
trap 'echo "🧹 Stopping LANDO..."; 
      docker-compose -f ./setup/docker-compose.yml down; 
      echo "🧹 Cleaning up ..."; 
      rm -rf ./src/tmp_host; 
      rm -rf ./src/__pycache__; 
      rm -rf ./.ipynb_checkpoints; 
      exit 0' INT

# Open browser
echo "🚀 Opening LANDO in your browser..."
if command -v xdg-open &> /dev/null; then
  xdg-open http://localhost:8888/lab/tree/LANDO.ipynb
elif command -v open &> /dev/null; then
  open http://localhost:8888/lab/tree/LANDO.ipynb
else
  echo "🌐 Please open your browser and go to: http://localhost:8888/lab/tree/LANDO.ipynb"
fi

echo "✅ LANDO is running. Press Ctrl+C to stop."
while true; do sleep 60; done
