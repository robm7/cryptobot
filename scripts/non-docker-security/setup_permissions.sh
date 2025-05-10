#!/bin/bash
# Cryptobot User Permissions Configuration Script for Linux/macOS
# This script sets up proper user permissions for the Cryptobot application

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    log "Detected Linux operating system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    log "Detected macOS operating system"
else
    log "Error: Unsupported operating system. This script is for Linux and macOS only."
    exit 1
fi

# Get current user and group
CURRENT_USER=$(whoami)
CURRENT_GROUP=$(id -gn)

log "Starting user permissions configuration for Cryptobot..."
log "Current user: $CURRENT_USER"
log "Current group: $CURRENT_GROUP"

# Create a dedicated group for Cryptobot if it doesn't exist
CRYPTOBOT_GROUP="cryptobot"
if [[ "$OS" == "linux" ]]; then
    if ! getent group $CRYPTOBOT_GROUP > /dev/null; then
        log "Creating cryptobot group..."
        sudo groupadd $CRYPTOBOT_GROUP
    else
        log "Cryptobot group already exists"
    fi
elif [[ "$OS" == "macos" ]]; then
    if ! dscl . -read /Groups/$CRYPTOBOT_GROUP > /dev/null 2>&1; then
        log "Creating cryptobot group..."
        sudo dscl . -create /Groups/$CRYPTOBOT_GROUP
        sudo dscl . -create /Groups/$CRYPTOBOT_GROUP PrimaryGroupID 600
    else
        log "Cryptobot group already exists"
    fi
fi

# Add current user to cryptobot group
log "Adding current user to cryptobot group..."
if [[ "$OS" == "linux" ]]; then
    sudo usermod -a -G $CRYPTOBOT_GROUP $CURRENT_USER
elif [[ "$OS" == "macos" ]]; then
    sudo dscl . -append /Groups/$CRYPTOBOT_GROUP GroupMembership $CURRENT_USER
fi

# Create necessary directories if they don't exist
log "Creating necessary directories..."
mkdir -p logs
mkdir -p data
mkdir -p config
mkdir -p config/security
mkdir -p config/ssl

# Set ownership and permissions for directories
log "Setting ownership and permissions for directories..."

# Set ownership
sudo chown -R $CURRENT_USER:$CRYPTOBOT_GROUP .

# Set base directory permissions
find . -type d -exec chmod 750 {} \;

# Set permissions for sensitive directories
chmod 700 config/security
chmod 700 config/ssl

# Set permissions for log directory
chmod 770 logs

# Set permissions for data directory
chmod 770 data

# Set file permissions
log "Setting file permissions..."

# Set base file permissions
find . -type f -exec chmod 640 {} \;

# Make scripts executable
find scripts -name "*.sh" -exec chmod 750 {} \;
find scripts -name "*.py" -exec chmod 750 {} \;

# Set permissions for sensitive files
if [ -f .env ]; then
    chmod 600 .env
fi

if [ -f config/security/security_config.json ]; then
    chmod 600 config/security/security_config.json
fi

# Set permissions for SSL certificates if they exist
if [ -d config/ssl ]; then
    find config/ssl -name "*.key" -exec chmod 600 {} \;
    find config/ssl -name "*.pem" -exec chmod 640 {} \;
    find config/ssl -name "*.crt" -exec chmod 640 {} \;
fi

# Set special permissions for specific directories
log "Setting special permissions for specific directories..."

# Database directory (if exists)
if [ -d database ]; then
    chmod 700 database
fi

# Set permissions for Python virtual environment (if exists)
if [ -d venv ]; then
    chmod 750 venv
    find venv -type d -exec chmod 750 {} \;
    find venv -type f -exec chmod 640 {} \;
    find venv/bin -type f -exec chmod 750 {} \;
fi

# Set ACLs for better permission management if available
if [[ "$OS" == "linux" ]] && command -v setfacl > /dev/null; then
    log "Setting up ACLs for better permission management..."
    
    # Set default ACLs for new files and directories
    setfacl -R -d -m g:$CRYPTOBOT_GROUP:rwX data
    setfacl -R -d -m g:$CRYPTOBOT_GROUP:rwX logs
    
    # Set ACLs for existing files and directories
    setfacl -R -m g:$CRYPTOBOT_GROUP:rwX data
    setfacl -R -m g:$CRYPTOBOT_GROUP:rwX logs
elif [[ "$OS" == "macos" ]] && command -v chmod > /dev/null; then
    log "Setting up ACLs for better permission management..."
    
    # Set ACLs for directories
    chmod -R +a "group:$CRYPTOBOT_GROUP allow list,add_file,search,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,file_inherit,directory_inherit" data
    chmod -R +a "group:$CRYPTOBOT_GROUP allow list,add_file,search,add_subdirectory,delete_child,readattr,writeattr,readextattr,writeextattr,readsecurity,file_inherit,directory_inherit" logs
fi

# Create a secure umask configuration
log "Creating secure umask configuration..."
if [[ "$OS" == "linux" ]]; then
    # Add secure umask to .bashrc if not already present
    if ! grep -q "umask 027" ~/.bashrc; then
        echo "# Cryptobot secure umask" >> ~/.bashrc
        echo "umask 027" >> ~/.bashrc
    fi
    
    # Add secure umask to .profile if not already present
    if ! grep -q "umask 027" ~/.profile; then
        echo "# Cryptobot secure umask" >> ~/.profile
        echo "umask 027" >> ~/.profile
    fi
elif [[ "$OS" == "macos" ]]; then
    # Add secure umask to .bash_profile if not already present
    if ! grep -q "umask 027" ~/.bash_profile 2>/dev/null; then
        echo "# Cryptobot secure umask" >> ~/.bash_profile
        echo "umask 027" >> ~/.bash_profile
    fi
    
    # Add secure umask to .zshrc if not already present (macOS Catalina and later use zsh by default)
    if ! grep -q "umask 027" ~/.zshrc 2>/dev/null; then
        echo "# Cryptobot secure umask" >> ~/.zshrc
        echo "umask 027" >> ~/.zshrc
    fi
fi

# Create a systemd service file with proper permissions if on Linux
if [[ "$OS" == "linux" ]] && [ -d /etc/systemd/system ]; then
    log "Creating systemd service files with proper permissions..."
    
    # Create service files
    cat > cryptobot-auth.service << EOL
[Unit]
Description=Cryptobot Auth Service
After=network.target postgresql.service redis.service

[Service]
User=$CURRENT_USER
Group=$CRYPTOBOT_GROUP
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python auth/main.py
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=cryptobot-auth
Environment="PATH=$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$(pwd)/.env
UMask=0027

[Install]
WantedBy=multi-user.target
EOL

    # Copy service file to systemd directory
    sudo cp cryptobot-auth.service /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/cryptobot-auth.service
    
    # Clean up
    rm cryptobot-auth.service
    
    # Reload systemd
    sudo systemctl daemon-reload
fi

# Create a launchd service file with proper permissions if on macOS
if [[ "$OS" == "macos" ]]; then
    log "Creating launchd service files with proper permissions..."
    
    # Create service files
    mkdir -p ~/Library/LaunchAgents
    
    cat > ~/Library/LaunchAgents/com.cryptobot.auth.plist << EOL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.auth</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(pwd)/venv/bin/python</string>
        <string>$(pwd)/auth/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$(pwd)/venv/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$(pwd)/logs/auth.log</string>
    <key>StandardErrorPath</key>
    <string>$(pwd)/logs/auth.error.log</string>
</dict>
</plist>
EOL

    # Set proper permissions
    chmod 644 ~/Library/LaunchAgents/com.cryptobot.auth.plist
fi

log "User permissions configuration completed successfully!"
log "Note: You may need to log out and log back in for group membership changes to take effect."
exit 0