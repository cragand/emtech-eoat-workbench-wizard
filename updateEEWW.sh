#!/bin/bash
# Emtech EoAT Workbench Wizard - Update Script
# Pulls the latest version from the repository
#
# HOW TO USE:
#   1. Open a terminal and navigate to your EEWW application folder
#      (the folder containing main.py, runEEWW.sh, etc.)
#   2. Run: ./updateEEWW.sh
#   3. Follow the on-screen prompts
#
# FIRST-TIME SETUP (if you received EEWW as a zip file):
#   You need to clone the repository instead:
#     git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git
#   Then use that folder going forward.

echo "============================================"
echo " EEWW Update Check"
echo "============================================"
echo

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "ERROR: Git is not installed on this computer."
    echo
    echo "To install Git:"
    echo "  Ubuntu/Debian: sudo apt-get install git"
    echo "  Fedora/RHEL:   sudo dnf install git"
    echo "  macOS:         xcode-select --install"
    echo
    exit 1
fi

# Check if this is a git repo
if ! git rev-parse --git-dir &> /dev/null; then
    echo "ERROR: This folder was not set up with Git."
    echo
    echo "This usually means EEWW was copied or unzipped rather than"
    echo "cloned from the repository. To fix this:"
    echo
    echo "  1. Open a terminal"
    echo "  2. Navigate to where you want the app, for example:"
    echo "       cd ~/Downloads"
    echo "  3. Run this command:"
    echo "       git clone https://github.com/cragand/emtech-eoat-workbench-wizard.git"
    echo "  4. Use the new folder from now on:"
    echo "       ~/Downloads/emtech-eoat-workbench-wizard"
    echo
    echo "Your existing workflows and output files will NOT be affected."
    echo "You can copy your workflows/ and output/ folders into the new location."
    echo
    exit 1
fi

echo "Current version:"
git log -1 --format="  Commit: %h  Date: %ci  %s"
echo

echo "Checking for updates..."
if ! git fetch origin; then
    echo
    echo "ERROR: Could not connect to the update server."
    echo
    echo "Possible causes:"
    echo "  - No internet connection"
    echo "  - VPN not connected (if required by your network)"
    echo "  - GitHub is temporarily unavailable"
    echo
    echo "Try again later or check your network connection."
    exit 1
fi

# Check if there are updates
if ! git diff --quiet HEAD origin/main; then
    echo
    echo "Updates available! Changes:"
    git log HEAD..origin/main --format="  - %s"
    echo
    read -p "Apply updates? (Y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        if ! git pull origin main; then
            echo
            echo "ERROR: Update failed."
            echo
            echo "This can happen if files were manually edited."
            echo "Contact your administrator for help."
            exit 1
        fi
        echo
        echo "Update complete! New version:"
        git log -1 --format="  Commit: %h  Date: %ci  %s"

        # Update dependencies if venv exists
        if [ -d "venv" ]; then
            echo
            echo "Updating dependencies..."
            source venv/bin/activate
            pip install -r requirements.txt --quiet
            deactivate
        fi
    else
        echo "Update skipped."
    fi
else
    echo "Already up to date!"
fi

echo
