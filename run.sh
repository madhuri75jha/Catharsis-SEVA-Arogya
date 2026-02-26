#!/bin/bash

# SEVA Arogya - Flask Application Runner

echo "Starting SEVA Arogya Flask Application..."
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the application
echo "Starting Flask server..."
echo "Access the application at: http://localhost:5000"
python app.py
