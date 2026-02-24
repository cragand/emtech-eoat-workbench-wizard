#!/bin/bash
# Emtech EoAT Workbench Wizard - Easy Launch Script
# This script automatically sets up and runs the application

echo "Starting Emtech EoAT Workbench Wizard..."
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "First-time setup: Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "Please ensure Python 3.7+ is installed."
        exit 1
    fi
    
    echo "Activating virtual environment..."
    source venv/bin/activate
    
    echo "Installing dependencies..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies."
        exit 1
    fi
    
    echo
    echo "Setup complete!"
    echo
else
    # Virtual environment exists, just activate it
    source venv/bin/activate
fi

# Run the application
echo "Launching application..."
python main.py

# Deactivate when done
deactivate
