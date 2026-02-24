@echo off
REM Emtech EoAT Workbench Wizard - Easy Launch Script
REM This script automatically sets up and runs the application

echo Starting Emtech EoAT Workbench Wizard...
echo.

REM Check if virtual environment exists
if not exist venv (
    echo First-time setup: Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo Please ensure Python 3.7+ is installed and in your PATH.
        pause
        exit /b 1
    )
    
    echo Activating virtual environment...
    call venv\Scripts\activate
    
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
    
    echo.
    echo Setup complete!
    echo.
) else (
    REM Virtual environment exists, just activate it
    call venv\Scripts\activate
)

REM Run the application
echo Launching application...
python main.py

REM Deactivate when done
deactivate
