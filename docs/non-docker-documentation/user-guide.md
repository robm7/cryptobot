# User Guide

This guide provides detailed instructions on how to use the non-Docker version of Cryptobot, including the Quick Start Launcher, service configuration, management, monitoring, and updates.

## Table of Contents
- [Using the Quick Start Launcher](#using-the-quick-start-launcher)
- [Configuring Services](#configuring-services)
- [Managing Services](#managing-services)
- [Monitoring Service Health](#monitoring-service-health)
- [Updating the Application](#updating-the-application)

## Using the Quick Start Launcher

The Quick Start Launcher is a user-friendly interface to start and manage the CryptoBot application.

### Launching the Application

1. **Start the Quick Start Launcher**:
   - **Windows**: Start Menu > CryptoBot > CryptoBot Launcher
   - **macOS**: Applications > CryptoBot Launcher
   - **Linux**: Run `cryptobot-launcher` from the terminal or application menu

2. **Launcher Interface Overview**:
   - **Service Selection**: Checkboxes to select which services to start
   - **Configuration Options**: Dropdown menus for environment, profile, and log level
   - **Control Buttons**: Start, stop, and open dashboard buttons
   - **Service Status**: Status indicators for each service
   - **Log Display**: Real-time logs from all services

### Service Selection

The Quick Start Launcher allows you to select which services to start:

1. **Core Services**:
   - **Authentication Service**: Handles user authentication and API key management
   - **Strategy Service**: Manages trading strategies and signals
   - **Data Service**: Provides market data and historical prices
   - **Trade Service**: Executes trades and manages positions
   - **Backtest Service**: Runs strategy backtests on historical data

2. **MCP Services**:
   - **Exchange Gateway**: Provides a unified interface to multiple exchanges
   - **Market Data**: Collects and processes market data
   - **Order Execution**: Executes orders on exchanges
   - **Paper Trading**: Simulates trading without real money
   - **Portfolio Management**: Manages the portfolio and allocations
   - **Reporting**: Generates reports on performance
   - **Risk Management**: Manages risk and exposure
   - **Strategy Execution**: Executes trading strategies

3. **User Interface**:
   - **Dashboard**: Web interface for monitoring and control

### Configuration Options

The Quick Start Launcher provides several configuration options:

1. **Environment**:
   - **dev**: Development environment with debug features
   - **test**: Testing environment for running tests
   - **stage**: Staging environment for pre-production testing
   - **prod**: Production environment for live trading

2. **Profile**:
   - **default**: Standard configuration for non-Docker deployment
   - **minimal**: Minimal configuration with only essential services
   - **full**: Full configuration with all services

3. **Log Level**:
   - **DEBUG**: Detailed debugging information
   - **INFO**: General information about system operation
   - **WARNING**: Warning messages about potential issues
   - **ERROR**: Error messages about critical issues

### Starting and Stopping Services

1. **Starting Services**:
   - Select the services you want to start by checking the corresponding boxes
   - Configure the environment, profile, and log level as needed
   - Click the "Start Selected Services" button
   - The status of each service will be updated in the "Service Status" section

2. **Stopping Services**:
   - Click the "Stop All Services" button to stop all running services
   - Alternatively, you can stop individual services by clicking the "Stop" button next to each service

3. **Opening the Dashboard**:
   - Click the "Open in Browser" button to open the dashboard in your web browser
   - Alternatively, navigate to `http://localhost:8080` in your web browser

## Configuring Services

### Configuration Files

The main configuration file is located at:

- **Windows**: `%APPDATA%\CryptoBot\config.json`
- **macOS**: `~/Library/Application Support/CryptoBot/config.json`
- **Linux**: `/etc/cryptobot/config.json`

You can edit this file to customize CryptoBot's behavior. The configuration file is in JSON format and contains settings for all services.

### Example Configuration

```json
{
  "services": {
    "auth": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8000
    },
    "strategy": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8001
    },
    "data": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8002
    },
    "trade": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8003
    },
    "backtest": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8004
    }
  },
  "database": {
    "url": "sqlite:///cryptobot.db"
  },
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "logging": {
    "level": "INFO",
    "file": "cryptobot.log"
  }
}
```

### Environment Variables

You can also configure CryptoBot using environment variables:

```bash
# Windows
set CRYPTOBOT_ENV=production
set CRYPTOBOT_DB_URL=sqlite:///cryptobot.db
set CRYPTOBOT_REDIS_HOST=localhost
set CRYPTOBOT_REDIS_PORT=6379
set CRYPTOBOT_LOG_LEVEL=INFO

# Linux/macOS
export CRYPTOBOT_ENV=production
export CRYPTOBOT_DB_URL=sqlite:///cryptobot.db
export CRYPTOBOT_REDIS_HOST=localhost
export CRYPTOBOT_REDIS_PORT=6379
export CRYPTOBOT_LOG_LEVEL=INFO
```

### Service-Specific Configuration

Each service has its own configuration section in the main configuration file. You can also create service-specific configuration files in the `config` directory:

- `config/auth.json`: Authentication Service configuration
- `config/strategy.json`: Strategy Service configuration
- `config/data.json`: Data Service configuration
- `config/trade.json`: Trade Service configuration
- `config/backtest.json`: Backtest Service configuration

### Exchange Configuration

To configure exchange connections:

1. Navigate to Settings > Exchanges in the dashboard
2. Click "Add Exchange"
3. Select the exchange from the dropdown
4. Enter your API key and secret
5. Configure additional settings:
   - Trading limits
   - IP restrictions
   - Permissions
6. Click "Save"

### Strategy Configuration

To configure trading strategies:

1. Navigate to Strategies > Strategy Manager in the dashboard
2. Click "Create New Strategy" or select an existing strategy to edit
3. Configure the strategy parameters:
   - Trading pair
   - Timeframe
   - Entry and exit conditions
   - Position sizing
   - Risk management settings
4. Click "Save Strategy"

## Managing Services

### Service Management through the Launcher

The Quick Start Launcher provides a simple interface for managing services:

1. **Starting Services**:
   - Select the services you want to start
   - Click "Start Selected Services"

2. **Stopping Services**:
   - Click "Stop All Services" to stop all running services
   - Click the "Stop" button next to a service to stop that specific service

3. **Restarting Services**:
   - Click the "Restart" button next to a service to restart that specific service

### Service Management through the Command Line

You can also manage services through the command line:

```bash
# Start all services
cryptobot --all

# Start specific services
cryptobot --service auth --service strategy --service data

# Stop all services
cryptobot --stop

# Restart all services
cryptobot --restart
```

### Running as a Service

#### Windows

The Windows installer includes an option to run CryptoBot at system startup. If you didn't select this option during installation, you can enable it later:

1. Open the Start Menu and search for "Task Scheduler"
2. Click "Create Basic Task"
3. Enter a name and description for the task
4. Select "When the computer starts" as the trigger
5. Select "Start a program" as the action
6. Browse to the CryptoBot executable (`C:\Program Files\CryptoBot\cryptobot.exe`)
7. Add any command-line arguments you need
8. Complete the wizard

#### macOS

To run CryptoBot as a service on macOS:

1. Create a LaunchAgent plist file at `~/Library/LaunchAgents/com.cryptobot.trading.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cryptobot.trading</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/CryptoBot.app/Contents/MacOS/CryptoBot</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>~/Library/Logs/CryptoBot/cryptobot.log</string>
    <key>StandardErrorPath</key>
    <string>~/Library/Logs/CryptoBot/cryptobot.log</string>
</dict>
</plist>
```

2. Load the LaunchAgent:

```bash
launchctl load ~/Library/LaunchAgents/com.cryptobot.trading.plist
```

#### Linux

The Linux packages include a systemd service file. To manage the service:

```bash
# Start the service
sudo systemctl start cryptobot

# Stop the service
sudo systemctl stop cryptobot

# Enable the service to start at boot
sudo systemctl enable cryptobot

# Disable the service from starting at boot
sudo systemctl disable cryptobot

# Check the service status
sudo systemctl status cryptobot
```

## Monitoring Service Health

### Dashboard Monitoring

The CryptoBot dashboard provides a comprehensive view of the system's health:

1. **Service Status**:
   - Navigate to Dashboard > System Status
   - View the status of all services
   - Check resource usage (CPU, memory, disk)
   - Monitor response times and error rates

2. **Trading Performance**:
   - Navigate to Dashboard > Performance
   - View account balance and equity
   - Monitor open positions and recent trades
   - Track profit/loss and drawdown

3. **Alerts and Notifications**:
   - Configure alerts for service issues
   - Set up notifications for trading events
   - Receive alerts via email, SMS, or Telegram

### Log Monitoring

CryptoBot generates logs that can be used to monitor the system's health:

1. **Log Locations**:
   - **Windows**: `%APPDATA%\CryptoBot\logs\`
   - **macOS**: `~/Library/Logs/CryptoBot/`
   - **Linux**: `/var/log/cryptobot/`

2. **Log Files**:
   - `cryptobot.log`: Main log file
   - `auth.log`: Authentication Service logs
   - `strategy.log`: Strategy Service logs
   - `data.log`: Data Service logs
   - `trade.log`: Trade Service logs
   - `backtest.log`: Backtest Service logs

3. **Log Levels**:
   - **DEBUG**: Detailed debugging information
   - **INFO**: General information about system operation
   - **WARNING**: Warning messages about potential issues
   - **ERROR**: Error messages about critical issues

### Health Checks

CryptoBot includes built-in health checks for all services:

1. **API Health Checks**:
   - Each service exposes a `/health` endpoint
   - Returns service status and health metrics
   - Example: `http://localhost:8000/health` for the Authentication Service

2. **Database Health Checks**:
   - Monitors database connectivity
   - Checks for database performance issues
   - Alerts on database errors

3. **Exchange Connectivity Checks**:
   - Monitors connectivity to exchanges
   - Checks API key validity
   - Alerts on exchange connectivity issues

## Updating the Application

CryptoBot includes a built-in update mechanism that can automatically check for, download, and install updates.

### Automatic Updates

The update mechanism can be configured to automatically check for updates at regular intervals:

1. Open the CryptoBot Quick Start Launcher
2. Click "Check for Updates"
3. In the update dialog, you can configure automatic update settings:
   - Check for updates automatically
   - Download updates automatically
   - Install updates automatically

### Manual Updates

You can manually check for updates at any time:

1. Open the CryptoBot Quick Start Launcher
2. Click "Check for Updates"
3. If an update is available, you can download and install it

### Update Configuration

The update mechanism can be configured through the main configuration file:

```json
{
  "update": {
    "update_url": "https://api.cryptobot.com/updates",
    "check_interval": 86400,
    "auto_check": true,
    "auto_download": false,
    "auto_install": false
  }
}
```

### Update Process

The update process consists of the following steps:

1. **Check for Updates**: The system checks for updates from the update server
2. **Download Update**: If an update is available, it is downloaded and verified
3. **Backup Current Installation**: Before installing the update, a backup of the current installation is created
4. **Install Update**: The update is installed
5. **Restart Application**: The application is restarted after the update is installed

If any step fails, the update process is aborted and the system is rolled back to the previous state.

### Rollback

If an update fails or causes issues, you can roll back to the previous version:

1. Open the CryptoBot Quick Start Launcher
2. Click "Check for Updates"
3. In the update dialog, click "Rollback"

This will restore the previous version of CryptoBot from the backup created during the update process.