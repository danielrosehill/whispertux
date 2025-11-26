#!/bin/bash
# Build and install WhisperTux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building and installing WhisperTux..."

# Build the package
"$SCRIPT_DIR/build-deb.sh"

# Find the built package
DEB_FILE=$(ls -t "$SCRIPT_DIR"/whispertux_*.deb 2>/dev/null | head -1)

if [ -z "$DEB_FILE" ]; then
    echo "Error: No .deb file found after build"
    exit 1
fi

# Install
echo "Installing $DEB_FILE..."
sudo dpkg -i "$DEB_FILE"

# Install any missing dependencies
sudo apt-get install -f -y

echo ""
echo "WhisperTux installed successfully!"
echo "Run 'whispertux' to start the application."
