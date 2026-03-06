@echo off
REM Emtech EoAT Workbench Wizard - Update Script
REM Pulls the latest version from the repository
REM
REM HOW TO USE:
REM   1. Open File Explorer and navigate to your EEWW application folder
REM      (the folder containing main.py, runEEWW.bat, etc.)
REM   2. Double-click this file (updateEEWW.bat)
REM   3. Follow the on-screen prompts
REM
REM FIRST-TIME SETUP (if you received EEWW as a zip file):
REM   You need to clone the repository instead. Open a Command Prompt and run:
REM     git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git
REM   Then use that folder going forward.

echo ============================================
echo  EEWW Update Check
echo ============================================
echo.

REM Check if git is available
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git is not installed on this computer.
    echo.
    echo To install Git:
    echo   1. Go to https://git-scm.com/download/win
    echo   2. Download and run the installer
    echo   3. Use all default options during installation
    echo   4. Close and reopen this script after installing
    echo.
    pause
    exit /b 1
)

REM Check if this is a git repo
git rev-parse --git-dir >nul 2>nul
if errorlevel 1 (
    echo ERROR: This folder was not set up with Git.
    echo.
    echo This usually means EEWW was copied or unzipped rather than
    echo cloned from the repository. To fix this:
    echo.
    echo   1. Open a Command Prompt
    echo   2. Navigate to where you want the app, for example:
    echo        cd C:\Users\%USERNAME%\Downloads
    echo   3. Run this command:
    echo        git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git
    echo   4. Use the new folder from now on:
    echo        C:\Users\%USERNAME%\Downloads\emtech-eoat-workbench-wizard
    echo.
    echo Your existing workflows and output files will NOT be affected.
    echo You can copy your workflows/ and output/ folders into the new location.
    echo.
    pause
    exit /b 1
)

echo Current version:
git log -1 --format="  Commit: %%h  Date: %%ci  %%s"
echo.

echo Checking for updates...
git fetch origin
if errorlevel 1 (
    echo.
    echo ERROR: Could not connect to the update server.
    echo.
    echo Possible causes:
    echo   - No internet connection
    echo   - VPN not connected (if required by your network)
    echo   - GitHub is temporarily unavailable
    echo.
    echo Try again later or check your network connection.
    echo.
    pause
    exit /b 1
)

REM Check if there are updates
git diff --quiet HEAD origin/main
if errorlevel 1 (
    echo.
    echo Updates available! Changes:
    git log HEAD..origin/main --format="  - %%s"
    echo.
    set /p confirm="Apply updates? (Y/N): "
    if /i "%confirm%"=="Y" (
        git pull origin main
        if errorlevel 1 (
            echo.
            echo ERROR: Update failed.
            echo.
            echo This can happen if files were manually edited.
            echo Contact your administrator for help.
            echo.
            pause
            exit /b 1
        )
        echo.
        echo Update complete! New version:
        git log -1 --format="  Commit: %%h  Date: %%ci  %%s"

        REM Update dependencies if requirements changed
        if exist venv (
            echo.
            echo Updating dependencies...
            call venv\Scripts\activate
            pip install -r requirements.txt --quiet
            deactivate
        )
    ) else (
        echo Update skipped.
    )
) else (
    echo Already up to date!
)

echo.
pause
