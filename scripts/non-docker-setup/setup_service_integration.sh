#!/bin/bash
# Cryptobot Service Integration Setup Script for Linux/macOS

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

# Configuration directories
AUTH_CONFIG_DIR="/etc/cryptobot/auth"
STRATEGY_CONFIG_DIR="/etc/cryptobot/strategy"
BACKTEST_CONFIG_DIR="/etc/cryptobot/backtest"
TRADE_CONFIG_DIR="/etc/cryptobot/trade"
DATA_CONFIG_DIR="/etc/cryptobot/data"
MCP_CONFIG_DIR="/etc/cryptobot/mcp"

# Check if all configuration files exist
if [ ! -f "$AUTH_CONFIG_DIR/config.json" ] || \
   [ ! -f "$STRATEGY_CONFIG_DIR/config.json" ] || \
   [ ! -f "$BACKTEST_CONFIG_DIR/config.json" ] || \
   [ ! -f "$TRADE_CONFIG_DIR/config.json" ] || \
   [ ! -f "$DATA_CONFIG_DIR/config.json" ] || \
   [ ! -f "$MCP_CONFIG_DIR/config.json" ]; then
    log "Error: One or more service configuration files are missing."
    log "Please run the service installation scripts first."
    exit 1
fi

log "Setting up service integration and communication..."

# Generate API keys for inter-service communication
generate_api_key() {
    # Generate a random 32-character API key
    openssl rand -hex 16
}

# Update configuration files with API keys for inter-service communication
log "Generating and configuring API keys for inter-service communication..."

# Generate API keys
AUTH_API_KEY=$(generate_api_key)
STRATEGY_API_KEY=$(generate_api_key)
BACKTEST_API_KEY=$(generate_api_key)
TRADE_API_KEY=$(generate_api_key)
DATA_API_KEY=$(generate_api_key)

# Update Auth Service config
log "Updating Auth Service configuration..."
AUTH_CONFIG_FILE="$AUTH_CONFIG_DIR/config.json"
TMP_FILE=$(mktemp)
jq ".api_keys = {
    \"strategy_service\": \"$STRATEGY_API_KEY\",
    \"backtest_service\": \"$BACKTEST_API_KEY\",
    \"trade_service\": \"$TRADE_API_KEY\",
    \"data_service\": \"$DATA_API_KEY\"
}" "$AUTH_CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$AUTH_CONFIG_FILE"

# Update Strategy Service config
log "Updating Strategy Service configuration..."
STRATEGY_CONFIG_FILE="$STRATEGY_CONFIG_DIR/config.json"
TMP_FILE=$(mktemp)
jq ".auth_service.api_key = \"$STRATEGY_API_KEY\" |
    .backtest_service.url = \"http://localhost:8002\" |
    .data_service.url = \"http://localhost:8003\"" "$STRATEGY_CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$STRATEGY_CONFIG_FILE"

# Update Backtest Service config
log "Updating Backtest Service configuration..."
BACKTEST_CONFIG_FILE="$BACKTEST_CONFIG_DIR/config.json"
TMP_FILE=$(mktemp)
jq ".auth_service.api_key = \"$BACKTEST_API_KEY\" |
    .strategy_service.url = \"http://localhost:8001\" |
    .data_service.url = \"http://localhost:8003\"" "$BACKTEST_CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$BACKTEST_CONFIG_FILE"

# Update Trade Service config
log "Updating Trade Service configuration..."
TRADE_CONFIG_FILE="$TRADE_CONFIG_DIR/config.json"
TMP_FILE=$(mktemp)
jq ".auth_service.api_key = \"$TRADE_API_KEY\" |
    .strategy_service.url = \"http://localhost:8001\" |
    .data_service.url = \"http://localhost:8003\" |
    .mcp_services = {
        \"router\": \"http://localhost:8010\",
        \"exchange_gateway\": \"http://localhost:8011\",
        \"paper_trading\": \"http://localhost:8012\"
    }" "$TRADE_CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$TRADE_CONFIG_FILE"

# Update Data Service config
log "Updating Data Service configuration..."
DATA_CONFIG_FILE="$DATA_CONFIG_DIR/config.json"
TMP_FILE=$(mktemp)
jq ".auth_service.api_key = \"$DATA_API_KEY\"" "$DATA_CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$DATA_CONFIG_FILE"

# Update MCP Services config
log "Updating MCP Services configuration..."
MCP_CONFIG_FILE="$MCP_CONFIG_DIR/config.json"
TMP_FILE=$(mktemp)
jq ".auth_service = {
    \"url\": \"http://localhost:8000\",
    \"api_key\": \"$AUTH_API_KEY\"
} |
.strategy_service = {
    \"url\": \"http://localhost:8001\"
} |
.backtest_service = {
    \"url\": \"http://localhost:8002\"
} |
.trade_service = {
    \"url\": \"http://localhost:8004\"
} |
.data_service = {
    \"url\": \"http://localhost:8003\"
}" "$MCP_CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$MCP_CONFIG_FILE"

# Create a service discovery file
log "Creating service discovery configuration..."
SERVICE_DISCOVERY_FILE="/etc/cryptobot/service_discovery.json"
cat > "$SERVICE_DISCOVERY_FILE" << EOF
{
    "services": {
        "auth": {
            "host": "localhost",
            "port": 8000,
            "url": "http://localhost:8000",
            "api_key": "$AUTH_API_KEY"
        },
        "strategy": {
            "host": "localhost",
            "port": 8001,
            "url": "http://localhost:8001",
            "api_key": "$STRATEGY_API_KEY"
        },
        "backtest": {
            "host": "localhost",
            "port": 8002,
            "url": "http://localhost:8002",
            "api_key": "$BACKTEST_API_KEY"
        },
        "data": {
            "host": "localhost",
            "port": 8003,
            "url": "http://localhost:8003",
            "api_key": "$DATA_API_KEY"
        },
        "trade": {
            "host": "localhost",
            "port": 8004,
            "url": "http://localhost:8004",
            "api_key": "$TRADE_API_KEY"
        },
        "mcp_router": {
            "host": "localhost",
            "port": 8010,
            "url": "http://localhost:8010"
        },
        "exchange_gateway": {
            "host": "localhost",
            "port": 8011,
            "url": "http://localhost:8011"
        },
        "paper_trading": {
            "host": "localhost",
            "port": 8012,
            "url": "http://localhost:8012"
        }
    },
    "communication": {
        "protocol": "http",
        "timeout": 30,
        "retry_attempts": 3,
        "retry_delay": 2
    }
}
EOF

# Set proper permissions
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Create cryptobot user and group if they don't exist
    if ! id -u cryptobot &>/dev/null; then
        log "Creating cryptobot user and group..."
        useradd -r -s /bin/false cryptobot
    fi

    # Set proper permissions
    chown cryptobot:cryptobot "$SERVICE_DISCOVERY_FILE"
    chmod 600 "$SERVICE_DISCOVERY_FILE"
    
    # Set permissions for all config files
    chown -R cryptobot:cryptobot "$AUTH_CONFIG_DIR"
    chown -R cryptobot:cryptobot "$STRATEGY_CONFIG_DIR"
    chown -R cryptobot:cryptobot "$BACKTEST_CONFIG_DIR"
    chown -R cryptobot:cryptobot "$TRADE_CONFIG_DIR"
    chown -R cryptobot:cryptobot "$DATA_CONFIG_DIR"
    chown -R cryptobot:cryptobot "$MCP_CONFIG_DIR"
fi

# Create symbolic links to the service discovery file in each service directory
ln -sf "$SERVICE_DISCOVERY_FILE" "/opt/cryptobot/services/auth/service_discovery.json"
ln -sf "$SERVICE_DISCOVERY_FILE" "/opt/cryptobot/services/strategy/service_discovery.json"
ln -sf "$SERVICE_DISCOVERY_FILE" "/opt/cryptobot/services/backtest/service_discovery.json"
ln -sf "$SERVICE_DISCOVERY_FILE" "/opt/cryptobot/services/trade/service_discovery.json"
ln -sf "$SERVICE_DISCOVERY_FILE" "/opt/cryptobot/services/data/service_discovery.json"
ln -sf "$SERVICE_DISCOVERY_FILE" "/opt/cryptobot/services/mcp/service_discovery.json"

# Create a health check script
log "Creating health check script..."
HEALTH_CHECK_SCRIPT="/opt/cryptobot/scripts/health_check.sh"
mkdir -p "$(dirname "$HEALTH_CHECK_SCRIPT")"
cat > "$HEALTH_CHECK_SCRIPT" << 'EOF'
#!/bin/bash
# Cryptobot Services Health Check Script

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if a service is running
check_service() {
    local service_name=$1
    local url=$2
    
    log "Checking $service_name service..."
    if curl -s -o /dev/null -w "%{http_code}" "$url/health" | grep -q "200"; then
        log "$service_name service is running."
        return 0
    else
        log "$service_name service is not responding."
        return 1
    fi
}

# Check all services
log "Starting health check for all Cryptobot services..."

# Load service discovery configuration
SERVICE_DISCOVERY_FILE="/etc/cryptobot/service_discovery.json"
if [ ! -f "$SERVICE_DISCOVERY_FILE" ]; then
    log "Error: Service discovery configuration file not found."
    exit 1
fi

# Check core services
check_service "Auth" "http://localhost:8000"
check_service "Strategy" "http://localhost:8001"
check_service "Backtest" "http://localhost:8002"
check_service "Data" "http://localhost:8003"
check_service "Trade" "http://localhost:8004"

# Check MCP services
check_service "MCP Router" "http://localhost:8010"
check_service "Exchange Gateway" "http://localhost:8011"
check_service "Paper Trading" "http://localhost:8012"

log "Health check completed."
EOF

chmod +x "$HEALTH_CHECK_SCRIPT"

# Create a service restart script
log "Creating service restart script..."
RESTART_SCRIPT="/opt/cryptobot/scripts/restart_services.sh"
cat > "$RESTART_SCRIPT" << 'EOF'
#!/bin/bash
# Cryptobot Services Restart Script

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to restart a systemd service
restart_service() {
    local service_name=$1
    
    log "Restarting $service_name service..."
    if systemctl restart "$service_name"; then
        log "$service_name service restarted successfully."
        return 0
    else
        log "Failed to restart $service_name service."
        return 1
    fi
}

# Restart all services in the correct order
log "Restarting all Cryptobot services..."

# Restart core services
restart_service "cryptobot-auth.service"
sleep 5
restart_service "cryptobot-data.service"
sleep 5
restart_service "cryptobot-strategy.service"
sleep 5
restart_service "cryptobot-backtest.service"
sleep 5
restart_service "cryptobot-trade.service"
sleep 5

# Restart MCP services
restart_service "cryptobot-mcp-router.service"
sleep 5
restart_service "cryptobot-exchange-gateway.service"
sleep 5
restart_service "cryptobot-paper-trading.service"

log "All services have been restarted."
EOF

chmod +x "$RESTART_SCRIPT"

# Create a macOS version of the restart script if needed
if [[ "$OSTYPE" == "darwin"* ]]; then
    MACOS_RESTART_SCRIPT="/opt/cryptobot/scripts/restart_services_macos.sh"
    cat > "$MACOS_RESTART_SCRIPT" << 'EOF'
#!/bin/bash
# Cryptobot Services Restart Script for macOS

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to restart a launchd service
restart_service() {
    local service_name=$1
    
    log "Restarting $service_name service..."
    launchctl unload "$service_name"
    sleep 2
    if launchctl load "$service_name"; then
        log "$service_name service restarted successfully."
        return 0
    else
        log "Failed to restart $service_name service."
        return 1
    fi
}

# Restart all services in the correct order
log "Restarting all Cryptobot services..."

# Restart core services
restart_service "~/Library/LaunchAgents/com.cryptobot.auth.plist"
sleep 5
restart_service "~/Library/LaunchAgents/com.cryptobot.data.plist"
sleep 5
restart_service "~/Library/LaunchAgents/com.cryptobot.strategy.plist"
sleep 5
restart_service "~/Library/LaunchAgents/com.cryptobot.backtest.plist"
sleep 5
restart_service "~/Library/LaunchAgents/com.cryptobot.trade.plist"
sleep 5

# Restart MCP services
restart_service "~/Library/LaunchAgents/com.cryptobot.mcp-router.plist"
sleep 5
restart_service "~/Library/LaunchAgents/com.cryptobot.exchange-gateway.plist"
sleep 5
restart_service "~/Library/LaunchAgents/com.cryptobot.paper-trading.plist"

log "All services have been restarted."
EOF

    chmod +x "$MACOS_RESTART_SCRIPT"
fi

log "Service integration setup completed successfully!"
log "The services are now configured to communicate with each other."
log "You can use the following scripts to manage the services:"
log "  - Health check: $HEALTH_CHECK_SCRIPT"
log "  - Restart services: $RESTART_SCRIPT"

if [[ "$OSTYPE" == "darwin"* ]]; then
    log "  - Restart services (macOS): $MACOS_RESTART_SCRIPT"
fi

exit 0