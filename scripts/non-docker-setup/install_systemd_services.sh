#!/bin/bash
# Script to install CryptoBot services as systemd services

# Set script to exit immediately if a command exits with a non-zero status
set -e

# Check if running with sudo/root privileges
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root or with sudo privileges."
    exit 1
fi

# Display banner
echo "========================================================"
echo "  Installing CryptoBot systemd services"
echo "========================================================"
echo ""

# Create cryptobot user if it doesn't exist
if ! id -u cryptobot &>/dev/null; then
    echo "Creating cryptobot user..."
    useradd -m -s /bin/bash cryptobot
    echo "User cryptobot created."
else
    echo "User cryptobot already exists."
fi

# Set installation directory
INSTALL_DIR="/opt/cryptobot"

# Create installation directory if it doesn't exist
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Creating installation directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    echo "Installation directory created."
else
    echo "Installation directory already exists."
fi

# Create logs directory
if [ ! -d "$INSTALL_DIR/logs" ]; then
    echo "Creating logs directory: $INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/logs"
    echo "Logs directory created."
else
    echo "Logs directory already exists."
fi

# Copy service files to systemd directory
echo "Copying systemd service files..."
cp config/non-docker/services/systemd/*.service /etc/systemd/system/
echo "Service files copied."

# Set permissions
echo "Setting permissions..."
chown -R cryptobot:cryptobot "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
echo "Permissions set."

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload
echo "Systemd reloaded."

# Enable services
echo "Enabling services..."
systemctl enable cryptobot-auth.service
systemctl enable cryptobot-data.service
systemctl enable cryptobot-strategy.service
systemctl enable cryptobot-backtest.service
systemctl enable cryptobot-trade.service
echo "Services enabled."

echo ""
echo "CryptoBot systemd services have been installed and enabled."
echo ""
echo "You can now start the services with the following commands:"
echo "- Start all services: systemctl start cryptobot-auth cryptobot-data cryptobot-strategy cryptobot-backtest cryptobot-trade"
echo "- Start individual service: systemctl start cryptobot-auth"
echo ""
echo "To check service status:"
echo "- Check all services: systemctl status cryptobot-*"
echo "- Check individual service: systemctl status cryptobot-auth"
echo ""
echo "To stop services:"
echo "- Stop all services: systemctl stop cryptobot-trade cryptobot-backtest cryptobot-strategy cryptobot-data cryptobot-auth"
echo "- Stop individual service: systemctl stop cryptobot-auth"
echo ""
echo "Service logs can be viewed with:"
echo "- journalctl -u cryptobot-auth"
echo ""