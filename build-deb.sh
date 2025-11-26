#!/bin/bash
# Build Debian package for WhisperTux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
APP_DIR="$REPO_DIR/app"

# Package info
PKG_NAME="whispertux"
PKG_VERSION="1.0.0"
PKG_ARCH="all"
PKG_MAINTAINER="Daniel Rosehill <daniel@danielrosehill.co.il>"
PKG_DESCRIPTION="Voice dictation application for Linux using whisper.cpp"

# Build directory
BUILD_DIR="$SCRIPT_DIR/pkg-build"
DEB_DIR="$BUILD_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}"

echo "Building WhisperTux Debian package..."
echo "Version: $PKG_VERSION"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$DEB_DIR"

# Create directory structure
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/opt/whispertux"
mkdir -p "$DEB_DIR/usr/local/bin"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"

# Copy application files
cp -r "$APP_DIR/main.py" "$DEB_DIR/opt/whispertux/"
cp -r "$APP_DIR/src" "$DEB_DIR/opt/whispertux/"
cp -r "$APP_DIR/requirements.txt" "$DEB_DIR/opt/whispertux/"
cp -r "$APP_DIR/setup.py" "$DEB_DIR/opt/whispertux/"
cp -r "$APP_DIR/setup-venv.sh" "$DEB_DIR/opt/whispertux/"
cp -r "$APP_DIR/scripts" "$DEB_DIR/opt/whispertux/"

# Copy assets if they exist
if [ -d "$APP_DIR/assets" ]; then
    cp -r "$APP_DIR/assets" "$DEB_DIR/opt/whispertux/"
fi

# Copy icon
if [ -f "$APP_DIR/whispertux-main.png" ]; then
    cp "$APP_DIR/whispertux-main.png" "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/whispertux.png"
elif [ -f "$APP_DIR/assets/whispertux-main.png" ]; then
    cp "$APP_DIR/assets/whispertux-main.png" "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/whispertux.png"
fi

# Create launcher script
cat > "$DEB_DIR/usr/local/bin/whispertux" << 'EOF'
#!/bin/bash
# WhisperTux launcher

INSTALL_DIR="/opt/whispertux"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/whispertux"
VENV_DIR="$DATA_DIR/.venv"

# Ensure data directory exists
mkdir -p "$DATA_DIR"

# Check if venv exists, create if not
if [ ! -d "$VENV_DIR" ]; then
    echo "Setting up virtual environment..."
    if command -v uv &> /dev/null; then
        uv venv "$VENV_DIR"
        uv pip install --python "$VENV_DIR/bin/python" -r "$INSTALL_DIR/requirements.txt"
    else
        python3 -m venv "$VENV_DIR"
        "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    fi
fi

# Run the application
cd "$INSTALL_DIR"
exec "$VENV_DIR/bin/python" main.py "$@"
EOF
chmod 755 "$DEB_DIR/usr/local/bin/whispertux"

# Create desktop entry
cat > "$DEB_DIR/usr/share/applications/whispertux.desktop" << EOF
[Desktop Entry]
Name=WhisperTux
Comment=Voice dictation using whisper.cpp
Exec=/usr/local/bin/whispertux
Icon=whispertux
Terminal=false
Type=Application
Categories=Utility;Accessibility;
Keywords=voice;speech;dictation;transcription;whisper;
EOF

# Create control file
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: utils
Priority: optional
Architecture: $PKG_ARCH
Depends: python3 (>= 3.8), python3-venv, python3-tk, ydotool
Recommends: whisper-cpp
Maintainer: $PKG_MAINTAINER
Description: $PKG_DESCRIPTION
 WhisperTux is a voice dictation application that uses whisper.cpp for
 offline speech-to-text transcription. Press a shortcut key to start
 recording, speak, press again to stop, and text appears in the focused
 application.
EOF

# Create postinst script
cat > "$DEB_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

echo ""
echo "WhisperTux installed successfully!"
echo ""
echo "First-time setup:"
echo "  1. Run 'whispertux' to start the application"
echo "  2. The virtual environment will be created automatically"
echo "  3. Make sure ydotool daemon is running: systemctl --user start ydotool"
echo ""

exit 0
EOF
chmod 755 "$DEB_DIR/DEBIAN/postinst"

# Create postrm script
cat > "$DEB_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

case "$1" in
    purge|remove)
        # Note: User data in ~/.local/share/whispertux is preserved
        # Users can manually remove it if desired
        echo "Note: User data in ~/.local/share/whispertux has been preserved."
        echo "Remove manually if no longer needed."
        ;;
esac

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

exit 0
EOF
chmod 755 "$DEB_DIR/DEBIAN/postrm"

# Build the package
cd "$BUILD_DIR"
dpkg-deb --build --root-owner-group "$DEB_DIR"

# Move to build directory
mv "${DEB_DIR}.deb" "$SCRIPT_DIR/"

# Cleanup
rm -rf "$BUILD_DIR"

echo ""
echo "Package built successfully!"
echo "Output: $SCRIPT_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"
echo ""
echo "Install with: sudo dpkg -i $SCRIPT_DIR/${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"
