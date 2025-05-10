#!/bin/bash
# Cryptobot Firewall Configuration Script for Linux/macOS
# This script configures firewall rules to protect the Cryptobot application

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
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

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    log "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    log "Warning: .env file not found. Using default values."
    # Set default values
    AUTH_SERVICE_PORT="8000"
    STRATEGY_SERVICE_PORT="8010"
    BACKTEST_SERVICE_PORT="8020"
    TRADE_SERVICE_PORT="8030"
    DATA_SERVICE_PORT="8001"
    DB_PORT="5432"
    REDIS_PORT="6379"
fi

log "Starting firewall configuration for Cryptobot..."

# Configure firewall based on OS
if [[ "$OS" == "linux" ]]; then
    # Check which firewall is available (ufw, firewalld, or iptables)
    if command_exists ufw; then
        log "Configuring UFW firewall..."
        
        # Check if UFW is active
        if ! ufw status | grep -q "Status: active"; then
            log "Enabling UFW firewall..."
            sudo ufw --force enable
        fi
        
        # Allow SSH to prevent lockout
        log "Allowing SSH connections..."
        sudo ufw allow ssh
        
        # Allow service ports
        log "Allowing Cryptobot service ports..."
        sudo ufw allow $AUTH_SERVICE_PORT/tcp
        sudo ufw allow $STRATEGY_SERVICE_PORT/tcp
        sudo ufw allow $BACKTEST_SERVICE_PORT/tcp
        sudo ufw allow $TRADE_SERVICE_PORT/tcp
        sudo ufw allow $DATA_SERVICE_PORT/tcp
        
        # Allow web interface port (default: 3000)
        sudo ufw allow 3000/tcp
        
        # Restrict database and Redis access to localhost only
        log "Restricting database and Redis access to localhost only..."
        sudo ufw deny $DB_PORT/tcp
        sudo ufw deny $REDIS_PORT/tcp
        sudo ufw allow from 127.0.0.1 to any port $DB_PORT
        sudo ufw allow from 127.0.0.1 to any port $REDIS_PORT
        
        # Reload firewall
        sudo ufw reload
        
        log "UFW firewall configured successfully"
        
    elif command_exists firewall-cmd; then
        log "Configuring firewalld..."
        
        # Check if firewalld is running
        if ! systemctl is-active --quiet firewalld; then
            log "Starting firewalld..."
            sudo systemctl start firewalld
            sudo systemctl enable firewalld
        fi
        
        # Allow SSH to prevent lockout
        log "Allowing SSH connections..."
        sudo firewall-cmd --permanent --add-service=ssh
        
        # Allow service ports
        log "Allowing Cryptobot service ports..."
        sudo firewall-cmd --permanent --add-port=$AUTH_SERVICE_PORT/tcp
        sudo firewall-cmd --permanent --add-port=$STRATEGY_SERVICE_PORT/tcp
        sudo firewall-cmd --permanent --add-port=$BACKTEST_SERVICE_PORT/tcp
        sudo firewall-cmd --permanent --add-port=$TRADE_SERVICE_PORT/tcp
        sudo firewall-cmd --permanent --add-port=$DATA_SERVICE_PORT/tcp
        
        # Allow web interface port (default: 3000)
        sudo firewall-cmd --permanent --add-port=3000/tcp
        
        # Restrict database and Redis access to localhost only
        log "Restricting database and Redis access to localhost only..."
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="127.0.0.1" port protocol="tcp" port="'$DB_PORT'" accept'
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="127.0.0.1" port protocol="tcp" port="'$REDIS_PORT'" accept'
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="0.0.0.0/0" port protocol="tcp" port="'$DB_PORT'" drop'
        sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="0.0.0.0/0" port protocol="tcp" port="'$REDIS_PORT'" drop'
        
        # Reload firewall
        sudo firewall-cmd --reload
        
        log "firewalld configured successfully"
        
    elif command_exists iptables; then
        log "Configuring iptables..."
        
        # Create a temporary file for iptables rules
        TEMP_RULES=$(mktemp)
        
        # Basic policies
        echo "*filter" > $TEMP_RULES
        echo ":INPUT DROP [0:0]" >> $TEMP_RULES
        echo ":FORWARD DROP [0:0]" >> $TEMP_RULES
        echo ":OUTPUT ACCEPT [0:0]" >> $TEMP_RULES
        
        # Allow established connections
        echo "-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT" >> $TEMP_RULES
        
        # Allow loopback
        echo "-A INPUT -i lo -j ACCEPT" >> $TEMP_RULES
        
        # Allow SSH to prevent lockout
        echo "-A INPUT -p tcp --dport 22 -j ACCEPT" >> $TEMP_RULES
        
        # Allow service ports
        echo "-A INPUT -p tcp --dport $AUTH_SERVICE_PORT -j ACCEPT" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $STRATEGY_SERVICE_PORT -j ACCEPT" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $BACKTEST_SERVICE_PORT -j ACCEPT" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $TRADE_SERVICE_PORT -j ACCEPT" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $DATA_SERVICE_PORT -j ACCEPT" >> $TEMP_RULES
        
        # Allow web interface port (default: 3000)
        echo "-A INPUT -p tcp --dport 3000 -j ACCEPT" >> $TEMP_RULES
        
        # Restrict database and Redis access to localhost only
        echo "-A INPUT -p tcp --dport $DB_PORT -s 127.0.0.1 -j ACCEPT" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $REDIS_PORT -s 127.0.0.1 -j ACCEPT" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $DB_PORT -j DROP" >> $TEMP_RULES
        echo "-A INPUT -p tcp --dport $REDIS_PORT -j DROP" >> $TEMP_RULES
        
        # Commit changes
        echo "COMMIT" >> $TEMP_RULES
        
        # Apply rules
        sudo iptables-restore < $TEMP_RULES
        
        # Save rules for persistence
        if command_exists iptables-save; then
            if command_exists netfilter-persistent; then
                sudo netfilter-persistent save
            elif [ -d "/etc/iptables" ]; then
                sudo iptables-save > /etc/iptables/rules.v4
            elif [ -d "/etc/sysconfig" ]; then
                sudo iptables-save > /etc/sysconfig/iptables
            else
                sudo iptables-save > /etc/iptables.rules
                # Add restore to network interfaces if file exists
                if [ -f "/etc/network/interfaces" ]; then
                    if ! grep -q "iptables-restore" /etc/network/interfaces; then
                        echo "pre-up iptables-restore < /etc/iptables.rules" | sudo tee -a /etc/network/interfaces
                    fi
                fi
            fi
        fi
        
        # Clean up
        rm $TEMP_RULES
        
        log "iptables configured successfully"
    else
        log "Error: No supported firewall found. Please install and configure a firewall manually."
        exit 1
    fi
    
elif [[ "$OS" == "macos" ]]; then
    log "Configuring macOS firewall..."
    
    # Enable firewall
    log "Enabling macOS firewall..."
    sudo defaults write /Library/Preferences/com.apple.alf globalstate -int 1
    
    # Allow signed applications
    sudo defaults write /Library/Preferences/com.apple.alf allowsignedenabled -int 1
    
    # Stealth mode (don't respond to ICMP ping requests)
    sudo defaults write /Library/Preferences/com.apple.alf stealthenabled -int 1
    
    # Restart firewall
    sudo launchctl unload /System/Library/LaunchDaemons/com.apple.alf.agent.plist
    sudo launchctl load /System/Library/LaunchDaemons/com.apple.alf.agent.plist
    
    log "macOS firewall configured successfully"
    log "Note: For port-specific rules on macOS, consider using the pf firewall or a third-party firewall application."
fi

log "Firewall configuration completed successfully!"
exit 0