#!/bin/bash
# Build script for CryptoBot macOS DMG package
#
# This script builds a DMG package for CryptoBot using create-dmg.
# It requires the application bundle to be built first using build_macos_app.sh.
#
# Usage:
#   ./build_macos_dmg.sh [options]
#
# Options:
#   --clean     Clean dist directory before building
#   --test      Open the DMG after building to verify it works
#
# Example:
#   ./build_macos_dmg.sh --clean

# Exit on error
set -e

# Parse arguments
CLEAN=0
TEST=0

for arg in "$@"; do
  case $arg in
    --clean)
      CLEAN=1
      shift
      ;;
    --test)
      TEST=1
      shift
      ;;
    *)
      # Unknown option
      echo "Unknown option: $arg"
      exit 1
      ;;
  esac
done

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
DMG_CONTENTS_DIR="$DIST_DIR/dmg_contents"
DMG_FILE="$DIST_DIR/CryptoBot-1.0.0.dmg"
APP_DIR="$DIST_DIR/CryptoBot.app"
LAUNCHER_APP_DIR="$DIST_DIR/CryptoBot Launcher.app"

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Output header
echo "===================================================="
echo "CryptoBot macOS DMG Package Build Script"
echo "===================================================="
echo "Project root: $PROJECT_ROOT"
echo "Distribution directory: $DIST_DIR"
echo "DMG contents directory: $DMG_CONTENTS_DIR"
echo "DMG file: $DMG_FILE"
echo "===================================================="

# Check if the application bundle exists
if [ ! -d "$APP_DIR" ]; then
  echo "Application bundle not found. Please run build_macos_app.sh first."
  exit 1
fi

# Clean dist directory if requested
if [ $CLEAN -eq 1 ]; then
  echo "Cleaning DMG file if it exists..."
  if [ -f "$DMG_FILE" ]; then
    rm -f "$DMG_FILE"
  fi
  echo "Cleaned DMG file."
fi

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
  echo "create-dmg not found. Installing..."
  if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
  brew install create-dmg
  echo "create-dmg installed."
fi

# Create DMG package
echo "Creating DMG package..."

# Ensure DMG contents directory exists
if [ ! -d "$DMG_CONTENTS_DIR" ]; then
  echo "DMG contents directory not found. Creating..."
  mkdir -p "$DMG_CONTENTS_DIR"
  cp -R "$APP_DIR" "$DMG_CONTENTS_DIR/"
  cp -R "$LAUNCHER_APP_DIR" "$DMG_CONTENTS_DIR/"
  ln -sf /Applications "$DMG_CONTENTS_DIR/Applications"
  echo "DMG contents directory created."
fi

# Create a background image for the DMG if it doesn't exist
if [ ! -f "$DMG_CONTENTS_DIR/.background/background.png" ]; then
  echo "Creating background image for the DMG..."
  mkdir -p "$DMG_CONTENTS_DIR/.background"
  
  # Create a simple background image using SVG and convert to PNG
  cat > "$DMG_CONTENTS_DIR/.background/background.svg" << EOF
<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
  <rect width="600" height="400" fill="#1a1a1a"/>
  <text x="300" y="200" font-family="Arial" font-size="48" text-anchor="middle" fill="#ffffff">CryptoBot</text>
  <text x="300" y="250" font-family="Arial" font-size="24" text-anchor="middle" fill="#ffffff">Drag to Applications folder to install</text>
</svg>
EOF

  # Convert SVG to PNG
  if command -v convert &> /dev/null; then
    convert -background none "$DMG_CONTENTS_DIR/.background/background.svg" "$DMG_CONTENTS_DIR/.background/background.png"
  else
    echo "ImageMagick not found. Installing..."
    brew install imagemagick
    convert -background none "$DMG_CONTENTS_DIR/.background/background.svg" "$DMG_CONTENTS_DIR/.background/background.png"
  fi
  
  echo "Background image created."
fi

# Create a DMG file
echo "Creating DMG file..."
create-dmg \
  --volname "CryptoBot Installer" \
  --volicon "static/favicon.ico" \
  --background "$DMG_CONTENTS_DIR/.background/background.png" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "CryptoBot.app" 150 190 \
  --icon "CryptoBot Launcher.app" 300 190 \
  --icon "Applications" 450 190 \
  --hide-extension "CryptoBot.app" \
  --hide-extension "CryptoBot Launcher.app" \
  --app-drop-link 450 190 \
  --no-internet-enable \
  "$DMG_FILE" \
  "$DMG_CONTENTS_DIR"

echo "DMG file created: $DMG_FILE"

# Create a post-installation script
echo "Creating post-installation script..."
mkdir -p "$DIST_DIR/scripts"
cat > "$DIST_DIR/scripts/post_install.sh" << EOF
#!/bin/bash
# Post-installation script for CryptoBot

# Create necessary directories
mkdir -p "\$HOME/Library/Application Support/CryptoBot/data"
mkdir -p "\$HOME/Library/Application Support/CryptoBot/logs"

# Copy default configuration if it doesn't exist
if [ ! -f "\$HOME/Library/Application Support/CryptoBot/config.json" ]; then
  cp "/Applications/CryptoBot.app/Contents/Resources/config/default_config.json" "\$HOME/Library/Application Support/CryptoBot/config.json"
fi

# Set permissions
chmod -R 755 "/Applications/CryptoBot.app"
chmod -R 755 "/Applications/CryptoBot Launcher.app"

echo "Post-installation tasks completed."
EOF

chmod +x "$DIST_DIR/scripts/post_install.sh"
echo "Post-installation script created."

# Copy the post-installation script to the DMG contents
cp "$DIST_DIR/scripts/post_install.sh" "$DMG_CONTENTS_DIR/"
echo "Post-installation script copied to DMG contents."

# Test the DMG if requested
if [ $TEST -eq 1 ]; then
  echo "Testing DMG..."
  open "$DMG_FILE"
  echo "DMG test started."
fi

# Output summary
echo "===================================================="
echo "Build Summary"
echo "===================================================="
echo "DMG file: $DMG_FILE"
echo "===================================================="
echo "Build completed successfully!"