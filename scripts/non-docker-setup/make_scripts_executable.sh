#!/bin/bash
# Script to make all shell scripts executable

# Set script to exit immediately if a command exits with a non-zero status
set -e

# Display banner
echo "========================================================"
echo "  Making CryptoBot scripts executable"
echo "========================================================"
echo ""

# Make all shell scripts in the non-docker-setup directory executable
echo "Making startup scripts executable..."
chmod +x scripts/non-docker-setup/*.sh

# Make systemd service installation script executable
echo "Making systemd service installation script executable..."
if [ -f scripts/non-docker-setup/install_systemd_services.sh ]; then
    chmod +x scripts/non-docker-setup/install_systemd_services.sh
fi

# Make launchd service installation script executable
echo "Making launchd service installation script executable..."
if [ -f scripts/non-docker-setup/install_launchd_services.sh ]; then
    chmod +x scripts/non-docker-setup/install_launchd_services.sh
fi

echo ""
echo "All scripts are now executable."
echo ""
echo "You can now run the following commands:"
echo "- To start all services: ./scripts/non-docker-setup/start_all.sh"
echo "- To check service status: ./scripts/non-docker-setup/check_status.sh"
echo "- To stop all services: ./scripts/non-docker-setup/orchestrate_services.sh stop all"
echo ""