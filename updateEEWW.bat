@echo off
REM Emtech EoAT Workbench Wizard - Update Script
REM Pulls the latest version from the repository

echo ============================================
echo  EEWW Update Check
echo ============================================
echo.

REM Check if git is available
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: Git is not installed or not in your PATH.
    echo Please install Git from https://git-scm.com/
    pause
    exit /b 1
)

REM Check if this is a git repo
git rev-parse --git-dir >nul 2>nul
if errorlevel 1 (
    echo ERROR: This folder is not a git repository.
    echo Please contact your administrator.
    pause
    exit /b 1
)

echo Current version:
git log -1 --format="  Commit: %%h  Date: %%ci  %%s"
echo.

echo Checking for updates...
git fetch origin
if errorlevel 1 (
    echo ERROR: Could not reach the update server.
    echo Check your network connection and try again.
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
            echo ERROR: Update failed. You may have local changes.
            echo Contact your administrator for help.
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
