#!/bin/bash
# Script to install CryptoBot services as launchd services on macOS

# Set script to exit immediately if a command exits with a non-zero status
set -e

# Display banner
echo "========================================================"
echo "  Installing CryptoBot launchd services"
echo "========================================================"
echo ""

# Check if running on macOS
if [ "$(uname)" != "Darwin" ]; then
    echo "This script is intended to run on macOS only."
    exit 1
fi

# Set installation directory
INSTALL_DIR="/opt/cryptobot"

# Create installation directory if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating installation directory: $INSTALL_DIR"
    sudo mkdir -p "$INSTALL_DIR"
    echo "Installation directory created."
else
    echo "Installation directory already exists."
fi

# Create logs directory
if [ ! -d "$INSTALL_DIR/logs" ]; then
    echo "Creating logs directory: $INSTALL_DIR/logs"
    sudo mkdir -p "$INSTALL_DIR/logs"
    echo "Logs directory created."
else
    echo "Logs directory already exists."
fi

# Copy plist files to LaunchDaemons directory
echo "Copying launchd plist files..."
sudo cp config/non-docker/services/launchd/*.plist /Library/LaunchDaemons/
echo "Plist files copied."

# Set permissions
echo "Setting permissions..."
sudo chown -R root:wheel /Library/LaunchDaemons/com.cryptobot.*.plist
sudo chmod 644 /Library/LaunchDaemons/com.cryptobot.*.plist
sudo chown -R $(whoami):staff "$INSTALL_DIR"
sudo chmod -R 755 "$INSTALL_DIR"
echo "Permissions set."

# Load services
echo "Loading services..."
sudo launchctl load /Library/LaunchDaemons/com.cryptobot.auth.plist
sudo launchctl load /Library/LaunchDaemons/com.cryptobot.data.plist
sudo launchctl load /Library/LaunchDaemons/com.cryptobot.strategy.plist
sudo launchctl load /Library/LaunchDaemons/com.cryptobot.backtest.plist
sudo launchctl load /Library/LaunchDaemons/com.cryptobot.trade.plist
echo "Services loaded."

echo ""
echo "CryptoBot launchd services have been installed and loaded."
echo ""
echo "You can check service status with the following commands:"
echo "- Check all services: sudo launchctl list | grep cryptobot"
echo "- Check individual service: sudo launchctl list | grep com.cryptobot.auth"
echo ""
echo "To stop services:"
echo "- Stop all services:"
echo "  sudo launchctl unload /Library/LaunchDaemons/com.cryptobot.trade.plist"
echo "  sudo launchctl unload /Library/LaunchDaemons/com.cryptobot.backtest.plist"
echo "  sudo launchctl unload /Library/LaunchDaemons/com.cryptobot.strategy.plist"
echo "  sudo launchctl unload /Library/LaunchDaemons/com.cryptobot.data.plist"
echo "  sudo launchctl unload /Library/LaunchDaemons/com.cryptobot.auth.plist"
echo ""
echo "- Stop individual service: sudo launchctl unload /Library/LaunchDaemons/com.cryptobot.auth.plist"
echo ""
echo "Service logs can be found at: $INSTALL_DIR/logs/"
echo ""
echo "Note: Services will automatically start on system boot."
echo ""