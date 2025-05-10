#!/bin/bash
# Cryptobot Master Service Installation Script for Linux/macOS
# This script orchestrates the installation of all Cryptobot services

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if running with appropriate permissions
if [ "$EUID" -ne 0 ] && [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log "Warning: This script may require sudo privileges for some operations."
    log "If you encounter permission errors, please run with sudo."
    read -p "Continue without sudo? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Please run the script with sudo."
        exit 1
    fi
fi

# Display welcome message
log "Welcome to the Cryptobot Service Installation!"
log "This script will install and configure all Cryptobot services."
log "The installation process includes:"
log "1. Core services (auth, strategy, backtest, trade, data)"
log "2. MCP services"
log "3. Service integration and communication setup"
log ""
log "The installation process may take several minutes to complete."
log ""

read -p "Press Enter to continue or Ctrl+C to cancel..."

# Create a directory for logs
mkdir -p logs

# Step 1: Install Auth Service
log "Step 1: Installing Auth Service"
log "Running install_auth.sh..."
bash ./scripts/non-docker-setup/install_auth.sh 2>&1 | tee logs/install_auth.log

if [ $? -ne 0 ]; then
    log "Error: Auth service installation failed. Please check logs/install_auth.log for details."
    exit 1
fi

log "Auth service installation completed successfully!"

# Step 2: Install Data Service
log "Step 2: Installing Data Service"
log "Running install_data.sh..."
bash ./scripts/non-docker-setup/install_data.sh 2>&1 | tee logs/install_data.log

if [ $? -ne 0 ]; then
    log "Error: Data service installation failed. Please check logs/install_data.log for details."
    exit 1
fi

log "Data service installation completed successfully!"

# Step 3: Install Strategy Service
log "Step 3: Installing Strategy Service"
log "Running install_strategy.sh..."
bash ./scripts/non-docker-setup/install_strategy.sh 2>&1 | tee logs/install_strategy.log

if [ $? -ne 0 ]; then
    log "Error: Strategy service installation failed. Please check logs/install_strategy.log for details."
    exit 1
fi

log "Strategy service installation completed successfully!"

# Step 4: Install Backtest Service
log "Step 4: Installing Backtest Service"
log "Running install_backtest.sh..."
bash ./scripts/non-docker-setup/install_backtest.sh 2>&1 | tee logs/install_backtest.log

if [ $? -ne 0 ]; then
    log "Error: Backtest service installation failed. Please check logs/install_backtest.log for details."
    exit 1
fi

log "Backtest service installation completed successfully!"

# Step 5: Install Trade Service
log "Step 5: Installing Trade Service"
log "Running install_trade.sh..."
bash ./scripts/non-docker-setup/install_trade.sh 2>&1 | tee logs/install_trade.log

if [ $? -ne 0 ]; then
    log "Error: Trade service installation failed. Please check logs/install_trade.log for details."
    exit 1
fi

log "Trade service installation completed successfully!"

# Step 6: Install MCP Services
log "Step 6: Installing MCP Services"
log "Running install_mcp_services.sh..."
bash ./scripts/non-docker-setup/install_mcp_services.sh 2>&1 | tee logs/install_mcp_services.log

if [ $? -ne 0 ]; then
    log "Error: MCP services installation failed. Please check logs/install_mcp_services.log for details."
    exit 1
fi

log "MCP services installation completed successfully!"

# Step 7: Setup Service Integration
log "Step 7: Setting up Service Integration"
log "Running setup_service_integration.sh..."
bash ./scripts/non-docker-setup/setup_service_integration.sh 2>&1 | tee logs/setup_service_integration.log

if [ $? -ne 0 ]; then
    log "Error: Service integration setup failed. Please check logs/setup_service_integration.log for details."
    exit 1
fi

log "Service integration setup completed successfully!"

# Final steps and verification
log "Verifying installation..."

# Check if all service directories exist
SERVICE_DIRS=(
    "/opt/cryptobot/services/auth"
    "/opt/cryptobot/services/strategy"
    "/opt/cryptobot/services/backtest"
    "/opt/cryptobot/services/trade"
    "/opt/cryptobot/services/data"
    "/opt/cryptobot/services/mcp"
)

for dir in "${SERVICE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        log "Service directory $dir exists."
    else
        log "Warning: Service directory $dir does not exist."
    fi
done

# Check if all configuration files exist
CONFIG_FILES=(
    "/etc/cryptobot/auth/config.json"
    "/etc/cryptobot/strategy/config.json"
    "/etc/cryptobot/backtest/config.json"
    "/etc/cryptobot/trade/config.json"
    "/etc/cryptobot/data/config.json"
    "/etc/cryptobot/mcp/config.json"
    "/etc/cryptobot/service_discovery.json"
)

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        log "Configuration file $file exists."
    else
        log "Warning: Configuration file $file does not exist."
    fi
done

# Check if systemd services are installed (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    SYSTEMD_SERVICES=(
        "cryptobot-auth.service"
        "cryptobot-strategy.service"
        "cryptobot-backtest.service"
        "cryptobot-trade.service"
        "cryptobot-data.service"
        "cryptobot-mcp-router.service"
        "cryptobot-exchange-gateway.service"
        "cryptobot-paper-trading.service"
    )

    for service in "${SYSTEMD_SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "$service"; then
            log "Systemd service $service is installed."
        else
            log "Warning: Systemd service $service is not installed."
        fi
    done
fi

# Check if launchd services are installed (macOS only)
if [[ "$OSTYPE" == "darwin"* ]]; then
    LAUNCHD_SERVICES=(
        "~/Library/LaunchAgents/com.cryptobot.auth.plist"
        "~/Library/LaunchAgents/com.cryptobot.strategy.plist"
        "~/Library/LaunchAgents/com.cryptobot.backtest.plist"
        "~/Library/LaunchAgents/com.cryptobot.trade.plist"
        "~/Library/LaunchAgents/com.cryptobot.data.plist"
        "~/Library/LaunchAgents/com.cryptobot.mcp-router.plist"
        "~/Library/LaunchAgents/com.cryptobot.exchange-gateway.plist"
        "~/Library/LaunchAgents/com.cryptobot.paper-trading.plist"
    )

    for service in "${LAUNCHD_SERVICES[@]}"; do
        if [ -f "$service" ]; then
            log "Launchd service $service is installed."
        else
            log "Warning: Launchd service $service is not installed."
        fi
    done
fi

log "Service installation completed successfully!"
log ""
log "To start all services, you can use the following commands:"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log "  sudo systemctl start cryptobot-auth.service"
    log "  sudo systemctl start cryptobot-data.service"
    log "  sudo systemctl start cryptobot-strategy.service"
    log "  sudo systemctl start cryptobot-backtest.service"
    log "  sudo systemctl start cryptobot-trade.service"
    log "  sudo systemctl start cryptobot-mcp-router.service"
    log "  sudo systemctl start cryptobot-exchange-gateway.service"
    log "  sudo systemctl start cryptobot-paper-trading.service"
    log ""
    log "Or use the restart script:"
    log "  /opt/cryptobot/scripts/restart_services.sh"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.auth.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.data.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.strategy.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.backtest.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.trade.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.mcp-router.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.exchange-gateway.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.paper-trading.plist"
    log ""
    log "Or use the restart script:"
    log "  /opt/cryptobot/scripts/restart_services_macos.sh"
fi

log ""
log "To check the health of all services, run:"
log "  /opt/cryptobot/scripts/health_check.sh"
log ""
log "Thank you for installing Cryptobot services!"

exit 0