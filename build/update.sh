#!/bin/bash
# Update WhisperTux from git and rebuild/reinstall
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "Updating WhisperTux..."

# Pull latest changes
cd "$REPO_DIR"
echo "Pulling latest changes from git..."
git pull

# Rebuild the package
echo "Building Debian package..."
"$SCRIPT_DIR/build-deb.sh"

# Find the built package
DEB_FILE=$(ls -t "$SCRIPT_DIR"/whispertux_*.deb 2>/dev/null | head -1)

if [ -z "$DEB_FILE" ]; then
    echo "Error: No .deb file found after build"
    exit 1
fi

echo ""
echo "Package built: $DEB_FILE"
echo ""

# Ask to install
read -p "Install the updated package? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    sudo dpkg -i "$DEB_FILE"
    echo ""
    echo "WhisperTux updated and installed successfully!"
else
    echo "Package built but not installed."
    echo "Install manually with: sudo dpkg -i $DEB_FILE"
fi
