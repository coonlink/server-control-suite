#!/bin/bash
# Setup script for CI environment

set -e  # Exit immediately if a command exits with a non-zero status

echo "Setting up CI environment for Server Control Suite"

# Update pip to latest version
python -m pip install --upgrade pip

# Install pylint first to ensure it's available
echo "Installing pylint..."
pip install pylint==2.17.0

# Verify pylint installation
if command -v pylint &> /dev/null; then
    echo "Pylint installed successfully"
    pylint --version
else
    echo "WARNING: Pylint installation may have failed"
fi

# Install specific version of python-telegram-bot
echo "Installing python-telegram-bot..."
pip install python-telegram-bot==13.7

# Install other dependencies if requirements.txt exists
if [ -f requirements.txt ]; then
    echo "Installing dependencies from requirements.txt"
    cat requirements.txt
    pip install -r requirements.txt || echo "WARNING: Some dependencies could not be installed"
fi

# Install additional testing dependencies
echo "Installing flake8 for basic syntax checking..."
pip install flake8

# Verify pylint configuration
if [ -f .pylintrc ]; then
    echo "Found pylint configuration (.pylintrc)"
else
    echo "WARNING: No pylint configuration file found. Using default settings."
fi

# Verify installations
echo "Installed packages:"
pip list

echo "CI environment setup complete"