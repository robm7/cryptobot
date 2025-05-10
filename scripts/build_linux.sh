#!/bin/bash
# Build script for Cryptobot Linux executable
#
# This script builds a standalone Linux executable for Cryptobot using PyInstaller.
# It handles dependency management, packaging, and creates both a directory-based
# and a single-file executable.
#
# Usage:
#   ./build_linux.sh [options]
#
# Options:
#   --clean     Clean build and dist directories before building
#   --optimize  Optimize the build for size using UPX
#   --test      Run the executable after building to verify it works
#
# Example:
#   ./build_linux.sh --clean --optimize

# Exit on error
set -e

# Parse arguments
CLEAN=0
OPTIMIZE=0
TEST=0

for arg in "$@"; do
  case $arg in
    --clean)
      CLEAN=1
      shift
      ;;
    --optimize)
      OPTIMIZE=1
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
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
SPEC_FILE="$PROJECT_ROOT/pyinstaller_config.spec"
VENV_DIR="$PROJECT_ROOT/venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
DEV_REQUIREMENTS_FILE="$PROJECT_ROOT/requirements-dev.txt"

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Output header
echo "===================================================="
echo "Cryptobot Linux Build Script"
echo "===================================================="
echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo "Distribution directory: $DIST_DIR"
echo "Spec file: $SPEC_FILE"
echo "===================================================="

# Clean build and dist directories if requested
if [ $CLEAN -eq 1 ]; then
  echo "Cleaning build and dist directories..."
  if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
  fi
  if [ -d "$DIST_DIR" ]; then
    rm -rf "$DIST_DIR"
  fi
  echo "Cleaned build and dist directories."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
  echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "Virtual environment activated."

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"
pip install -r "$DEV_REQUIREMENTS_FILE"
pip install pyinstaller

if [ $OPTIMIZE -eq 1 ]; then
  # Install UPX for compression
  echo "Installing UPX for executable compression..."
  
  # Check if UPX is already installed
  if command -v upx &> /dev/null; then
    echo "UPX is already installed."
    UPX_PATH=$(command -v upx)
  else
    # Try to install UPX using package manager
    if command -v apt-get &> /dev/null; then
      echo "Installing UPX using apt..."
      sudo apt-get update
      sudo apt-get install -y upx
      UPX_PATH=$(command -v upx)
    elif command -v dnf &> /dev/null; then
      echo "Installing UPX using dnf..."
      sudo dnf install -y upx
      UPX_PATH=$(command -v upx)
    elif command -v yum &> /dev/null; then
      echo "Installing UPX using yum..."
      sudo yum install -y upx
      UPX_PATH=$(command -v upx)
    elif command -v pacman &> /dev/null; then
      echo "Installing UPX using pacman..."
      sudo pacman -S --noconfirm upx
      UPX_PATH=$(command -v upx)
    else
      echo "Could not install UPX automatically. Please install it manually."
      OPTIMIZE=0
    fi
  fi
  
  if [ $OPTIMIZE -eq 1 ]; then
    echo "UPX installed at: $UPX_PATH"
  fi
fi

echo "Dependencies installed."

# Run PyInstaller
echo "Building executable with PyInstaller..."
if [ $OPTIMIZE -eq 1 ]; then
  pyinstaller --clean "$SPEC_FILE" --upx-dir="$(dirname "$UPX_PATH")"
else
  pyinstaller --clean "$SPEC_FILE"
fi
echo "PyInstaller build completed."

# Verify the build
if [ -f "$DIST_DIR/cryptobot/cryptobot" ]; then
  echo "Directory-based executable built successfully."
else
  echo "Directory-based executable build failed!"
fi

if [ -f "$DIST_DIR/cryptobot_onefile" ]; then
  echo "Single-file executable built successfully."
else
  echo "Single-file executable build failed!"
fi

# Test the executable if requested
if [ $TEST -eq 1 ]; then
  echo "Testing executable..."
  EXECUTABLE="$DIST_DIR/cryptobot/cryptobot"
  if [ -f "$EXECUTABLE" ]; then
    "$EXECUTABLE" --help
    echo "Executable test completed."
  else
    echo "Executable not found for testing!"
  fi
fi

# Create a tarball of the directory-based executable
echo "Creating tarball archive..."
TARBALL="$DIST_DIR/cryptobot-linux.tar.gz"
if [ -f "$TARBALL" ]; then
  rm -f "$TARBALL"
fi
CRYPTOBOT_DIR="$DIST_DIR/cryptobot"
tar -czf "$TARBALL" -C "$DIST_DIR" "cryptobot"
echo "Tarball archive created: $TARBALL"

# Deactivate virtual environment
deactivate
echo "Virtual environment deactivated."

# Make executables executable
chmod +x "$DIST_DIR/cryptobot/cryptobot"
chmod +x "$DIST_DIR/cryptobot_onefile"

# Output summary
echo "===================================================="
echo "Build Summary"
echo "===================================================="
echo "Directory-based executable: $DIST_DIR/cryptobot/cryptobot"
echo "Single-file executable: $DIST_DIR/cryptobot_onefile"
echo "Tarball archive: $TARBALL"
echo "===================================================="
echo "Build completed successfully!"