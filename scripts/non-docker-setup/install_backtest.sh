#!/bin/bash
# Cryptobot Backtest Service Installation Script for Linux/macOS

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

# Create service directory if it doesn't exist
SERVICE_DIR="/opt/cryptobot/services/backtest"
log "Creating service directory at $SERVICE_DIR"
mkdir -p "$SERVICE_DIR"

# Copy service files
log "Copying backtest service files..."
cp -r ./backtest/* "$SERVICE_DIR/"

# Install dependencies
log "Installing backtest service dependencies..."
if [ -f "$SERVICE_DIR/requirements.txt" ]; then
    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        log "Warning: Not running in a virtual environment. It's recommended to activate the virtual environment first."
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Please activate the virtual environment and try again."
            exit 1
        fi
    fi
    
    pip install -r "$SERVICE_DIR/requirements.txt"
else
    log "Warning: requirements.txt not found for backtest service. Using project requirements."
    pip install -r "./requirements.txt"
fi

# Create service configuration
log "Setting up backtest service configuration..."
CONFIG_DIR="/etc/cryptobot/backtest"
mkdir -p "$CONFIG_DIR"

# Check if config file exists from Phase 3
if [ -f "./config/backtest_service_config.json" ]; then
    cp "./config/backtest_service_config.json" "$CONFIG_DIR/config.json"
    log "Copied configuration from Phase 3 setup."
else
    log "Warning: Configuration file from Phase 3 not found. Using default configuration."
    # Create a default config file
    cat > "$CONFIG_DIR/config.json" << EOF
{
    "service_name": "backtest",
    "host": "0.0.0.0",
    "port": 8002,
    "log_level": "info",
    "database": {
        "host": "localhost",
        "port": 5432,
        "username": "cryptobot",
        "password": "changeme",
        "database": "cryptobot"
    },
    "auth_service": {
        "url": "http://localhost:8000",
        "api_key": "CHANGE_THIS_TO_A_SECURE_API_KEY"
    },
    "data_service": {
        "url": "http://localhost:8003"
    },
    "strategy_service": {
        "url": "http://localhost:8001"
    },
    "results_dir": "/var/lib/cryptobot/backtest_results"
}
EOF
    log "Created default configuration. Please update with secure values."
fi

# Create a symbolic link to the configuration
ln -sf "$CONFIG_DIR/config.json" "$SERVICE_DIR/config.json"

# Create results directory
RESULTS_DIR="/var/lib/cryptobot/backtest_results"
mkdir -p "$RESULTS_DIR"

# Set up systemd service for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log "Setting up systemd service for backtest service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/cryptobot-backtest.service << EOF
[Unit]
Description=Cryptobot Backtest Service
After=network.target postgresql.service cryptobot-auth.service cryptobot-strategy.service

[Service]
User=cryptobot
Group=cryptobot
WorkingDirectory=$SERVICE_DIR
ExecStart=$(which python3) $SERVICE_DIR/main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=$SERVICE_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Create cryptobot user and group if they don't exist
    if ! id -u cryptobot &>/dev/null; then
        log "Creating cryptobot user and group..."
        useradd -r -s /bin/false cryptobot
    fi

    # Set proper permissions
    chown -R cryptobot:cryptobot "$SERVICE_DIR"
    chown -R cryptobot:cryptobot "$CONFIG_DIR"
    chown -R cryptobot:cryptobot "$RESULTS_DIR"

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable cryptobot-backtest.service
    
    log "Backtest service has been installed and configured as a systemd service."
    log "To start the service, run: sudo systemctl start cryptobot-backtest.service"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Create launchd plist for macOS
    log "Setting up launchd service for backtest service..."
    
    # Create launchd plist file
    cat > ~/Library/LaunchAgents/com.cryptobot.backtest.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.backtest</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$SERVICE_DIR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$SERVICE_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$SERVICE_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cryptobot-backtest.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cryptobot-backtest.err</string>
</dict>
</plist>
EOF

    log "Backtest service has been installed and configured as a launchd service."
    log "To start the service, run: launchctl load ~/Library/LaunchAgents/com.cryptobot.backtest.plist"
fi

# Create a simple script to run the service manually
cat > "$SERVICE_DIR/run_service.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
python3 main.py
EOF

chmod +x "$SERVICE_DIR/run_service.sh"

log "Backtest service installation completed successfully!"
log "You can manually start the service by running: $SERVICE_DIR/run_service.sh"

exit 0