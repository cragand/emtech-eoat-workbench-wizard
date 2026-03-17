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
    
    REM Try to install pyzbar for barcode scanning (optional)
    echo.
    echo Installing optional barcode scanning support...
    pip install pyzbar>nul 2>&1
    python -c "from pyzbar import pyzbar" >nul 2>&1
    if errorlevel 1 (
        echo NOTE: Camera-based barcode/QR scanning is not available on this system.
        echo       USB handheld barcode scanners will still work.
        echo       The app will work fine without camera-based scanning.
        echo       To enable it, install the ZBar library from:
        echo       https://sourceforge.net/projects/zbar/files/zbar/0.10/
    ) else (
        echo Barcode/QR scanning support installed successfully.
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
