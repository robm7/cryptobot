#!/bin/bash
# Cryptobot MCP Services Installation Script for Linux/macOS

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

# Create MCP services directory if it doesn't exist
MCP_DIR="/opt/cryptobot/services/mcp"
log "Creating MCP services directory at $MCP_DIR"
mkdir -p "$MCP_DIR"

# Copy MCP router
log "Copying MCP router..."
cp -r ./services/mcp/mcp_router.py "$MCP_DIR/"

# Install MCP services
log "Installing MCP services..."

# Exchange Gateway
log "Installing Exchange Gateway MCP service..."
EXCHANGE_GATEWAY_DIR="$MCP_DIR/exchange-gateway"
mkdir -p "$EXCHANGE_GATEWAY_DIR"
cp -r ./services/mcp/exchange-gateway/* "$EXCHANGE_GATEWAY_DIR/"

# Market Data
log "Installing Market Data MCP service..."
MARKET_DATA_DIR="$MCP_DIR/market-data"
mkdir -p "$MARKET_DATA_DIR"
cp -r ./services/mcp/market-data/* "$MARKET_DATA_DIR/"

# Order Execution
log "Installing Order Execution MCP service..."
ORDER_EXECUTION_DIR="$MCP_DIR/order-execution"
mkdir -p "$ORDER_EXECUTION_DIR"
cp -r ./services/mcp/order-execution/* "$ORDER_EXECUTION_DIR/"

# Paper Trading
log "Installing Paper Trading MCP service..."
PAPER_TRADING_DIR="$MCP_DIR/paper-trading"
mkdir -p "$PAPER_TRADING_DIR"
cp -r ./services/mcp/paper-trading/* "$PAPER_TRADING_DIR/"

# Portfolio Management
log "Installing Portfolio Management MCP service..."
PORTFOLIO_MGMT_DIR="$MCP_DIR/portfolio-management"
mkdir -p "$PORTFOLIO_MGMT_DIR"
cp -r ./services/mcp/portfolio-management/* "$PORTFOLIO_MGMT_DIR/"

# Reporting
log "Installing Reporting MCP service..."
REPORTING_DIR="$MCP_DIR/reporting"
mkdir -p "$REPORTING_DIR"
cp -r ./services/mcp/reporting/* "$REPORTING_DIR/"

# Risk Management
log "Installing Risk Management MCP service..."
RISK_MGMT_DIR="$MCP_DIR/risk-management"
mkdir -p "$RISK_MGMT_DIR"
cp -r ./services/mcp/risk-management/* "$RISK_MGMT_DIR/"

# Strategy Execution
log "Installing Strategy Execution MCP service..."
STRATEGY_EXEC_DIR="$MCP_DIR/strategy-execution"
mkdir -p "$STRATEGY_EXEC_DIR"
cp -r ./services/mcp/strategy-execution/* "$STRATEGY_EXEC_DIR/"

# Install dependencies for each MCP service
log "Installing dependencies for MCP services..."

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

# Install dependencies for Exchange Gateway
if [ -f "$EXCHANGE_GATEWAY_DIR/requirements.txt" ]; then
    log "Installing Exchange Gateway dependencies..."
    pip install -r "$EXCHANGE_GATEWAY_DIR/requirements.txt"
fi

# Install dependencies for Paper Trading
if [ -f "$PAPER_TRADING_DIR/requirements.txt" ]; then
    log "Installing Paper Trading dependencies..."
    pip install -r "$PAPER_TRADING_DIR/requirements.txt"
fi

# Install common dependencies for other MCP services
log "Installing common dependencies for MCP services..."
pip install pydantic fastapi uvicorn requests

# Create MCP configuration
log "Setting up MCP services configuration..."
CONFIG_DIR="/etc/cryptobot/mcp"
mkdir -p "$CONFIG_DIR"

# Check if config file exists from Phase 3
if [ -f "./config/mcp_services_config.json" ]; then
    cp "./config/mcp_services_config.json" "$CONFIG_DIR/config.json"
    log "Copied configuration from Phase 3 setup."
else
    log "Warning: Configuration file from Phase 3 not found. Using default configuration."
    # Create a default config file
    cat > "$CONFIG_DIR/config.json" << EOF
{
    "mcp_router": {
        "host": "0.0.0.0",
        "port": 8010,
        "log_level": "info"
    },
    "exchange_gateway": {
        "host": "0.0.0.0",
        "port": 8011,
        "log_level": "info",
        "supported_exchanges": ["binance", "kraken", "coinbase"],
        "api_keys_path": "/etc/cryptobot/mcp/api_keys.json"
    },
    "paper_trading": {
        "host": "0.0.0.0",
        "port": 8012,
        "log_level": "info",
        "initial_balance": 10000,
        "fee_rate": 0.001
    },
    "order_execution": {
        "retry_attempts": 3,
        "retry_delay": 2,
        "timeout": 30
    },
    "risk_management": {
        "max_open_trades": 5,
        "max_open_trades_per_pair": 1,
        "max_daily_drawdown_percent": 5,
        "stop_loss_percent": 2.5
    },
    "portfolio_management": {
        "rebalance_frequency": "daily",
        "target_allocation": {
            "BTC": 0.5,
            "ETH": 0.3,
            "other": 0.2
        }
    },
    "reporting": {
        "report_directory": "/var/lib/cryptobot/reports",
        "report_formats": ["json", "csv", "html"]
    }
}
EOF
    log "Created default configuration. Please update with secure values."
    
    # Create a default API keys file
    cat > "$CONFIG_DIR/api_keys.json" << EOF
{
    "binance": {
        "api_key": "YOUR_BINANCE_API_KEY",
        "api_secret": "YOUR_BINANCE_API_SECRET"
    },
    "kraken": {
        "api_key": "YOUR_KRAKEN_API_KEY",
        "api_secret": "YOUR_KRAKEN_API_SECRET"
    },
    "coinbase": {
        "api_key": "YOUR_COINBASE_API_KEY",
        "api_secret": "YOUR_COINBASE_API_SECRET",
        "passphrase": "YOUR_COINBASE_PASSPHRASE"
    }
}
EOF
    log "Created default API keys file. Please update with your actual API keys."
    chmod 600 "$CONFIG_DIR/api_keys.json"
fi

# Create a symbolic link to the configuration
ln -sf "$CONFIG_DIR/config.json" "$MCP_DIR/config.json"

# Create reports directory
REPORTS_DIR="/var/lib/cryptobot/reports"
mkdir -p "$REPORTS_DIR"

# Set up systemd service for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log "Setting up systemd service for MCP router..."
    
    # Create systemd service file for MCP router
    cat > /etc/systemd/system/cryptobot-mcp-router.service << EOF
[Unit]
Description=Cryptobot MCP Router Service
After=network.target cryptobot-auth.service cryptobot-strategy.service cryptobot-data.service cryptobot-trade.service

[Service]
User=cryptobot
Group=cryptobot
WorkingDirectory=$MCP_DIR
ExecStart=$(which python3) -m uvicorn mcp_router:app --host 0.0.0.0 --port 8010
Restart=always
RestartSec=10
Environment=PYTHONPATH=$MCP_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Create systemd service file for Exchange Gateway
    cat > /etc/systemd/system/cryptobot-exchange-gateway.service << EOF
[Unit]
Description=Cryptobot Exchange Gateway MCP Service
After=network.target cryptobot-mcp-router.service

[Service]
User=cryptobot
Group=cryptobot
WorkingDirectory=$EXCHANGE_GATEWAY_DIR
ExecStart=$(which python3) $EXCHANGE_GATEWAY_DIR/main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=$EXCHANGE_GATEWAY_DIR:$MCP_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Create systemd service file for Paper Trading
    cat > /etc/systemd/system/cryptobot-paper-trading.service << EOF
[Unit]
Description=Cryptobot Paper Trading MCP Service
After=network.target cryptobot-mcp-router.service

[Service]
User=cryptobot
Group=cryptobot
WorkingDirectory=$PAPER_TRADING_DIR
ExecStart=$(which python3) $PAPER_TRADING_DIR/main.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=$PAPER_TRADING_DIR:$MCP_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Create cryptobot user and group if they don't exist
    if ! id -u cryptobot &>/dev/null; then
        log "Creating cryptobot user and group..."
        useradd -r -s /bin/false cryptobot
    fi

    # Set proper permissions
    chown -R cryptobot:cryptobot "$MCP_DIR"
    chown -R cryptobot:cryptobot "$CONFIG_DIR"
    chown -R cryptobot:cryptobot "$REPORTS_DIR"
    chmod 600 "$CONFIG_DIR/api_keys.json"

    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable cryptobot-mcp-router.service
    systemctl enable cryptobot-exchange-gateway.service
    systemctl enable cryptobot-paper-trading.service
    
    log "MCP services have been installed and configured as systemd services."
    log "To start the services, run:"
    log "  sudo systemctl start cryptobot-mcp-router.service"
    log "  sudo systemctl start cryptobot-exchange-gateway.service"
    log "  sudo systemctl start cryptobot-paper-trading.service"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # Create launchd plist for macOS
    log "Setting up launchd services for MCP services..."
    
    # Create launchd plist file for MCP router
    cat > ~/Library/LaunchAgents/com.cryptobot.mcp-router.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.mcp-router</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>mcp_router:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8010</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$MCP_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$MCP_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cryptobot-mcp-router.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cryptobot-mcp-router.err</string>
</dict>
</plist>
EOF

    # Create launchd plist file for Exchange Gateway
    cat > ~/Library/LaunchAgents/com.cryptobot.exchange-gateway.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.exchange-gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$EXCHANGE_GATEWAY_DIR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$EXCHANGE_GATEWAY_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$EXCHANGE_GATEWAY_DIR:$MCP_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cryptobot-exchange-gateway.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cryptobot-exchange-gateway.err</string>
</dict>
</plist>
EOF

    # Create launchd plist file for Paper Trading
    cat > ~/Library/LaunchAgents/com.cryptobot.paper-trading.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.paper-trading</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$PAPER_TRADING_DIR/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PAPER_TRADING_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$PAPER_TRADING_DIR:$MCP_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/cryptobot-paper-trading.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cryptobot-paper-trading.err</string>
</dict>
</plist>
EOF

    log "MCP services have been installed and configured as launchd services."
    log "To start the services, run:"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.mcp-router.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.exchange-gateway.plist"
    log "  launchctl load ~/Library/LaunchAgents/com.cryptobot.paper-trading.plist"
fi

# Create simple scripts to run the services manually
cat > "$MCP_DIR/run_mcp_router.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
export PYTHONPATH=\$PYTHONPATH:\$(pwd)
python3 -m uvicorn mcp_router:app --host 0.0.0.0 --port 8010
EOF

cat > "$EXCHANGE_GATEWAY_DIR/run_service.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
export PYTHONPATH=\$PYTHONPATH:\$(pwd):\$(dirname "\$(pwd)")"
python3 main.py
EOF

cat > "$PAPER_TRADING_DIR/run_service.sh" << EOF
#!/bin/bash
cd "\$(dirname "\$0")"
export PYTHONPATH=\$PYTHONPATH:\$(pwd):\$(dirname "\$(pwd)")"
python3 main.py
EOF

chmod +x "$MCP_DIR/run_mcp_router.sh"
chmod +x "$EXCHANGE_GATEWAY_DIR/run_service.sh"
chmod +x "$PAPER_TRADING_DIR/run_service.sh"

log "MCP services installation completed successfully!"
log "You can manually start the services by running:"
log "  $MCP_DIR/run_mcp_router.sh"
log "  $EXCHANGE_GATEWAY_DIR/run_service.sh"
log "  $PAPER_TRADING_DIR/run_service.sh"

exit 0