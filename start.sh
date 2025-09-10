#!/bin/bash

# Startup script for Render deployment
echo "Starting OANDA Trading Bot..."

# Set environment variables if not already set
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Create necessary directories
mkdir -p logs
mkdir -p data

# Start the application
python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1