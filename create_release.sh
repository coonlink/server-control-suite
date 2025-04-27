#!/bin/bash
# Script to create a release zip file of the server-control-suite

# Stop on errors
set -e

# Default version if not provided
VERSION=${1:-"1.0.0"}

echo "Creating release package for Server Control Suite v$VERSION"

# Create directories
mkdir -p dist
rm -f dist/server-control-suite-$VERSION.zip

# Create a clean release directory
echo "Preparing release files..."
mkdir -p temp-release
cp -r *.py *.sh .pylintrc requirements.txt README.md .telegram_credentials.example temp-release/

# Remove any development or CI-specific files
rm -f temp-release/create_release.sh
rm -f temp-release/setup_ci.sh

# Create the zip file
echo "Creating zip archive..."
(cd temp-release && zip -r ../dist/server-control-suite-$VERSION.zip .)

# Cleanup
rm -rf temp-release

# Show contents and file size
echo "Release created successfully: dist/server-control-suite-$VERSION.zip"
echo "Contents:"
unzip -l dist/server-control-suite-$VERSION.zip
echo "Size: $(du -h dist/server-control-suite-$VERSION.zip | cut -f1)"

echo "Done!" 