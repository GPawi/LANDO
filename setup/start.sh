#!/bin/bash

# Move into the directory this script is in
cd "$(dirname "$0")"

# Ensure tmp_host is created one level up
mkdir -p ../tmp_host

# Launch Docker Compose
docker-compose up
