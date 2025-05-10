#!/bin/bash
# Cryptobot Auth Service Installation Script for Linux/macOS

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
SERVICE_DIR="/opt/cryptobot/services/auth"
log "Creating service directory at $SERVICE_DIR"
mkdir -p "$SERVICE_DIR"

# Copy service files
log "Copying auth service files..."
cp -r ./auth/* "$SERVICE_DIR/"

# Install dependencies
log "Installing auth service dependencies..."
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
    log "Error: requirements.txt not found for auth service."
    exit 1
fi

# Create service configuration
log "Setting up auth service configuration..."
CONFIG_DIR="/etc/cryptobot/auth"
mkdir -p "$CONFIG_DIR"

# Check if config file exists from Phase 3
if [ -f "./config/auth_service_config.json" ]; then
    cp "./config/auth_service_config.json" "$CONFIG_DIR/config.json"
    log "Copied configuration from Phase 3 setup."
else
    log "Warning: Configuration file from Phase 3 not found. Using default configuration."
    # Create a default config file
    cat > "$CONFIG_DIR/config.json" << EOF
{
    "service_name": "auth",
    "host": "0.0.0.0",
    "port": 8000,
    "log_level": "info",
    "database": {
        "host": "localhost",
        "port": 5432,
        "username": "cryptobot",
        "password": "changeme",
        "database": "cryptobot"
    },
    "redis": {
        "host": "localhost",
        "port": 6379,
        "password": "",
        "db": 0
    },
    "jwt": {
        "secret_key": "CHANGE_THIS_TO_A_SECURE_SECRET",
        "algorithm": "HS256",
        "access_token_expire_minutes": 30
    },
    "email": {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "sender_email": "noreply@example.com",
        "sender_password": "changeme"
    }
}
EOF
    log "Created default configuration. Please update with secure values."
fi

# Create a symbolic link to the configuration
ln -sf "$CONFIG_DIR/config.json" "$SERVICE_DIR/config.json"

# Set up systemd service for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log "Setting up systemd service for auth service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/cryptobot-auth.service << EOF
[Unit]
Description=Cryptobot Auth Service
After=network.target postgresql.service redis.service

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

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable cryptobot-auth.service
    
    log "Auth service has been installed and configured as a systemd service."
    log "To start the service, run: sudo systemctl start cryptobot-auth.service"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Create launchd plist for macOS
    log "Setting up launchd service for auth service..."
    
    # Create launchd plist file
    cat > ~/Library/LaunchAgents/com.cryptobot.auth.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.auth</string>
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
    <string>/tmp/cryptobot-auth.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cryptobot-auth.err</string>
</dict>
</plist>
EOF

    log "Auth service has been installed and configured as a launchd service."
    log "To start the service, run: launchctl load ~/Library/LaunchAgents/com.cryptobot.auth.plist"
fi

# Create a simple script to run the service manually
cat > "$SERVICE_DIR/run_service.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
python3 main.py
EOF

chmod +x "$SERVICE_DIR/run_service.sh"

log "Auth service installation completed successfully!"
log "You can manually start the service by running: $SERVICE_DIR/run_service.sh"

exit 0