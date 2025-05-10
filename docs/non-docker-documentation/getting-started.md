# Getting Started Guide

This guide will help you get started with the non-Docker version of Cryptobot, covering system requirements, installation, initial configuration, and a quick start tutorial.

## Table of Contents
- [System Requirements](#system-requirements)
- [Installation Instructions](#installation-instructions)
  - [Windows Installation](#windows-installation)
  - [macOS Installation](#macos-installation)
  - [Linux Installation](#linux-installation)
- [Initial Configuration](#initial-configuration)
- [Quick Start Tutorial](#quick-start-tutorial)

## System Requirements

### Minimum Requirements

- **CPU**: Dual-core processor, 2.0 GHz or higher
- **RAM**: 4 GB
- **Storage**: 1 GB free space
- **Operating System**:
  - Windows 10/11 (64-bit)
  - macOS 11 (Big Sur) or newer
  - Ubuntu 20.04 LTS, Debian 10, Fedora 32, or later
- **Network**: Stable internet connection
- **Dependencies**:
  - Python 3.8 or newer (included in the installer for Windows and macOS)

### Recommended Requirements

- **CPU**: Quad-core processor, 2.5 GHz or higher
- **RAM**: 8 GB or more
- **Storage**: 5 GB free space
- **Network**: High-speed internet connection

## Installation Instructions

### Windows Installation

1. **Download the Installer**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest Windows installer (`cryptobot-setup.exe`)

2. **Run the Installer**:
   - Double-click the installer to start the installation process
   - Follow the on-screen instructions:
     - Choose the installation directory (default: `C:\Program Files\CryptoBot`)
     - Select components to install (Core Application, Trading Strategies, Exchange Connectors, etc.)
     - Choose whether to create desktop and Start Menu shortcuts
     - Choose whether to start CryptoBot at system startup

3. **Launch Cryptobot**:
   - After installation completes, you can launch CryptoBot from the Start Menu or desktop shortcut

#### Silent Installation (for automated deployment)

```
cryptobot-setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-
```

Additional options:
- `/DIR="X:\path\to\install"` - Set the installation directory
- `/COMPONENTS="main,strategies,exchanges,dashboard"` - Select components to install
- `/TASKS="desktopicon,startmenu,autostart"` - Select tasks to perform

### macOS Installation

1. **Download the Installer**:
   - Go to the [Releases page](https://github.com/yourusername/cryptobot/releases)
   - Download the latest macOS installer (`CryptoBot-1.0.0.dmg`)

2. **Install the Application**:
   - Double-click the DMG file to mount it
   - Drag the CryptoBot application to the Applications folder
   - Optionally, drag the CryptoBot Launcher application to the Applications folder
   - Eject the DMG

3. **Launch Cryptobot**:
   - Open the Applications folder and double-click CryptoBot or CryptoBot Launcher to start the application

#### First Run on macOS

When you first run CryptoBot on macOS, you may see a security warning. To allow the application to run:

1. Open System Preferences > Security & Privacy
2. Click the "Open Anyway" button next to the message about CryptoBot
3. Confirm by clicking "Open" in the dialog that appears

### Linux Installation

#### Debian/Ubuntu (DEB package)

1. **Download the Package**:
   ```bash
   wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot_1.0.0_amd64.deb
   ```

2. **Install the Package**:
   ```bash
   sudo dpkg -i cryptobot_1.0.0_amd64.deb
   sudo apt-get install -f  # Install any missing dependencies
   ```

3. **Launch Cryptobot**:
   ```bash
   cryptobot
   ```
   or
   ```bash
   cryptobot-launcher
   ```

#### Fedora/RHEL/CentOS (RPM package)

1. **Download the Package**:
   ```bash
   wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot-1.0.0-1.x86_64.rpm
   ```

2. **Install the Package**:
   ```bash
   sudo dnf install cryptobot-1.0.0-1.x86_64.rpm
   ```
   or
   ```bash
   sudo yum install cryptobot-1.0.0-1.x86_64.rpm
   ```

3. **Launch Cryptobot**:
   ```bash
   cryptobot
   ```
   or
   ```bash
   cryptobot-launcher
   ```

## Initial Configuration

After installing CryptoBot, you'll need to configure it for your specific needs:

1. **Launch the CryptoBot Quick Start Launcher**:
   - Windows: Start Menu > CryptoBot > CryptoBot Launcher
   - macOS: Applications > CryptoBot Launcher
   - Linux: Run `cryptobot-launcher` from the terminal or application menu

2. **Configure Environment Settings**:
   - **Environment**: Choose between dev, test, stage, or prod
   - **Profile**: Select default (for non-Docker)
   - **Log Level**: Choose between DEBUG, INFO, WARNING, or ERROR

3. **Select Services to Start**:
   - **Core Services**: Authentication, Strategy, Data, Trade, Backtest
   - **MCP Services**: Exchange Gateway, Market Data, Order Execution, etc.
   - **Dashboard**: Web interface for monitoring and control

4. **Start Services**:
   - Click "Start Selected Services" to start the selected services
   - The status of each service will be displayed in the "Service Status" section

5. **Access the Dashboard**:
   - Click "Open in Browser" to open the dashboard in your web browser
   - Alternatively, navigate to `http://localhost:8080` in your web browser

## Quick Start Tutorial

This tutorial will guide you through setting up a basic trading strategy:

### Step 1: Set Up Exchange API Keys

1. Open the CryptoBot dashboard in your web browser
2. Navigate to Settings > API Keys
3. Click "Add New API Key"
4. Select your exchange (e.g., Binance, Kraken, Coinbase Pro)
5. Enter your API Key and Secret
6. Set permissions and trading limits
7. Click "Save"

### Step 2: Configure a Trading Strategy

1. Navigate to Strategies > Strategy Manager
2. Click "Create New Strategy"
3. Select a strategy type (e.g., Mean Reversion)
4. Configure the strategy parameters:
   - Trading pair (e.g., BTC/USD)
   - Timeframe (e.g., 1h)
   - Entry and exit conditions
   - Position sizing
   - Risk management settings
5. Click "Save Strategy"

### Step 3: Backtest the Strategy

1. Navigate to Backtest > New Backtest
2. Select your strategy from the dropdown
3. Set the backtest parameters:
   - Start and end dates
   - Initial capital
   - Trading fees
4. Click "Run Backtest"
5. Review the backtest results:
   - Performance metrics
   - Trade history
   - Equity curve
   - Drawdown chart

### Step 4: Deploy the Strategy

1. Navigate to Strategies > Strategy Manager
2. Find your strategy and click "Deploy"
3. Select deployment options:
   - Live trading or paper trading
   - Trading frequency
   - Notification settings
4. Click "Deploy Strategy"
5. Monitor the strategy performance in the dashboard

### Step 5: Monitor and Adjust

1. Navigate to Dashboard > Performance
2. Monitor your strategy's performance:
   - Open positions
   - Recent trades
   - Account balance
   - Profit/loss
3. Adjust your strategy as needed:
   - Fine-tune parameters
   - Add or modify risk management rules
   - Pause or stop the strategy if necessary

Congratulations! You've successfully set up and deployed a trading strategy with CryptoBot.