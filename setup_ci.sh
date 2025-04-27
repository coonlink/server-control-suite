#!/bin/bash
# Setup script for CI environment

echo "Setting up CI environment for Server Control Suite"

# Update pip to latest version
python -m pip install --upgrade pip

# Install pylint first to ensure it's available
pip install pylint==2.17.0

# Install specific version of python-telegram-bot
pip install python-telegram-bot==13.7

# Install other dependencies if requirements.txt exists
if [ -f requirements.txt ]; then
    echo "Installing dependencies from requirements.txt"
    pip install -r requirements.txt
fi

# Verify installations
echo "Installed packages:"
pip list

echo "CI environment setup complete" 