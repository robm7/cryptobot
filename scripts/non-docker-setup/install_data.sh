#!/bin/bash
# Cryptobot Data Service Installation Script for Linux/macOS

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
SERVICE_DIR="/opt/cryptobot/services/data"
log "Creating service directory at $SERVICE_DIR"
mkdir -p "$SERVICE_DIR"

# Copy service files
log "Copying data service files..."
cp -r ./data/* "$SERVICE_DIR/"

# Install dependencies
log "Installing data service dependencies..."
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
    log "Warning: requirements.txt not found for data service. Using project requirements."
    pip install -r "./requirements.txt"
fi

# Create service configuration
log "Setting up data service configuration..."
CONFIG_DIR="/etc/cryptobot/data"
mkdir -p "$CONFIG_DIR"

# Create data storage directory
DATA_DIR="/var/lib/cryptobot/data"
mkdir -p "$DATA_DIR"

# Check if config file exists from Phase 3
if [ -f "./config/data_service_config.json" ]; then
    cp "./config/data_service_config.json" "$CONFIG_DIR/config.json"
    log "Copied configuration from Phase 3 setup."
else
    log "Warning: Configuration file from Phase 3 not found. Using default configuration."
    # Create a default config file
    cat > "$CONFIG_DIR/config.json" << EOF
{
    "service_name": "data",
    "host": "0.0.0.0",
    "port": 8003,
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
    "data_storage": {
        "path": "/var/lib/cryptobot/data",
        "format": "parquet"
    },
    "exchange_settings": {
        "default_exchange": "binance",
        "retry_attempts": 3,
        "retry_delay": 2,
        "timeout": 30
    },
    "cache": {
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_db": 1,
        "ttl": 3600
    }
}
EOF
    log "Created default configuration. Please update with secure values."
fi

# Create a symbolic link to the configuration
ln -sf "$CONFIG_DIR/config.json" "$SERVICE_DIR/config.json"

# Set up systemd service for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log "Setting up systemd service for data service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/cryptobot-data.service << EOF
[Unit]
Description=Cryptobot Data Service
After=network.target postgresql.service redis.service cryptobot-auth.service

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
    chown -R cryptobot:cryptobot "$DATA_DIR"

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable cryptobot-data.service
    
    log "Data service has been installed and configured as a systemd service."
    log "To start the service, run: sudo systemctl start cryptobot-data.service"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Create launchd plist for macOS
    log "Setting up launchd service for data service..."
    
    # Create launchd plist file
    cat > ~/Library/LaunchAgents/com.cryptobot.data.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.data</string>
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
    <string>/tmp/cryptobot-data.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cryptobot-data.err</string>
</dict>
</plist>
EOF

    log "Data service has been installed and configured as a launchd service."
    log "To start the service, run: launchctl load ~/Library/LaunchAgents/com.cryptobot.data.plist"
fi

# Create a simple script to run the service manually
cat > "$SERVICE_DIR/run_service.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
python3 main.py
EOF

chmod +x "$SERVICE_DIR/run_service.sh"

log "Data service installation completed successfully!"
log "You can manually start the service by running: $SERVICE_DIR/run_service.sh"

exit 0