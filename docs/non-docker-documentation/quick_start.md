# Quick Start Guide

This guide provides a quick introduction to get you up and running with the non-Docker version of Cryptobot.

## Table of Contents
- [Installation](#installation)
- [Initial Setup](#initial-setup)
- [Launching the Application](#launching-the-application)
- [Setting Up Exchange API Keys](#setting-up-exchange-api-keys)
- [Creating Your First Strategy](#creating-your-first-strategy)
- [Running a Backtest](#running-a-backtest)
- [Deploying a Strategy](#deploying-a-strategy)
- [Monitoring Your Trades](#monitoring-your-trades)
- [Next Steps](#next-steps)

## Installation

### Windows

1. Download the installer from the [Releases page](https://github.com/yourusername/cryptobot/releases)
2. Run the installer and follow the on-screen instructions
3. Launch CryptoBot from the Start Menu or desktop shortcut

### macOS

1. Download the DMG file from the [Releases page](https://github.com/yourusername/cryptobot/releases)
2. Open the DMG file and drag CryptoBot to the Applications folder
3. Launch CryptoBot from the Applications folder

### Linux

#### Debian/Ubuntu
```bash
wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot_1.0.0_amd64.deb
sudo dpkg -i cryptobot_1.0.0_amd64.deb
sudo apt-get install -f  # Install any missing dependencies
```

#### Fedora/RHEL/CentOS
```bash
wget https://github.com/yourusername/cryptobot/releases/download/v1.0.0/cryptobot-1.0.0-1.x86_64.rpm
sudo dnf install cryptobot-1.0.0-1.x86_64.rpm
```

For more detailed installation instructions, see the [Installation Guide](installation_guide.md).

## Initial Setup

After installing CryptoBot, you'll need to perform some initial setup:

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
   - **Dashboard**: Web interface for monitoring and control

4. **Start Services**:
   - Click "Start Selected Services" to start the selected services
   - The status of each service will be displayed in the "Service Status" section

5. **Access the Dashboard**:
   - Click "Open in Browser" to open the dashboard in your web browser
   - Alternatively, navigate to `http://localhost:8080` in your web browser

## Launching the Application

### Using the Quick Start Launcher

The Quick Start Launcher provides a user-friendly interface to start and manage the CryptoBot application:

1. **Start the Quick Start Launcher**:
   - Windows: Start Menu > CryptoBot > CryptoBot Launcher
   - macOS: Applications > CryptoBot Launcher
   - Linux: Run `cryptobot-launcher` from the terminal or application menu

2. **Select Services**:
   - Check the services you want to start
   - At minimum, select Auth, Strategy, Data, Trade, and Dashboard

3. **Configure Environment**:
   - For beginners, use the default settings:
     - Environment: dev
     - Profile: default
     - Log Level: INFO

4. **Start Services**:
   - Click "Start Selected Services"
   - Wait for all services to show "Running" status

5. **Open Dashboard**:
   - Click "Open in Browser"
   - The dashboard will open in your default web browser

### Using the Command Line

You can also launch CryptoBot from the command line:

```bash
# Start all services
cryptobot --all

# Start specific services
cryptobot --service auth --service strategy --service data --service trade --service dashboard

# Start with specific environment
cryptobot --all --env prod
```

## Setting Up Exchange API Keys

Before you can trade, you need to set up API keys for your exchanges:

1. **Create API Keys on Your Exchange**:
   - Log in to your exchange account
   - Navigate to the API management section
   - Create a new API key with trading permissions
   - Note down the API key and secret

2. **Add API Keys to CryptoBot**:
   - Open the CryptoBot dashboard in your web browser
   - Navigate to Settings > API Keys
   - Click "Add New API Key"
   - Select your exchange (e.g., Binance, Kraken, Coinbase Pro)
   - Enter your API Key and Secret
   - Set permissions and trading limits
   - Click "Save"

3. **Verify API Key**:
   - After adding the API key, click "Test Connection"
   - If successful, you'll see a green checkmark
   - If unsuccessful, verify your API key and secret

## Creating Your First Strategy

Let's create a simple Mean Reversion strategy:

1. **Navigate to Strategies**:
   - In the dashboard, go to Strategies > Strategy Manager
   - Click "Create New Strategy"

2. **Select Strategy Type**:
   - Choose "Mean Reversion" from the dropdown

3. **Configure Trading Pair and Timeframe**:
   - Select a trading pair (e.g., BTC/USD)
   - Choose a timeframe (e.g., 1h)

4. **Set Strategy Parameters**:
   - Window: 20 (number of periods for calculating the mean)
   - Standard Deviation: 2.0 (entry/exit threshold)
   - Take Profit: 5% (exit when profit reaches this percentage)
   - Stop Loss: 2% (exit when loss reaches this percentage)

5. **Configure Position Sizing**:
   - Position Size: 5% (percentage of available capital per trade)
   - Max Open Positions: 3 (maximum number of concurrent positions)

6. **Save Strategy**:
   - Name your strategy (e.g., "BTC-USD Mean Reversion")
   - Click "Save Strategy"

## Running a Backtest

Before deploying your strategy, it's a good idea to backtest it:

1. **Navigate to Backtest**:
   - In the dashboard, go to Backtest > New Backtest
   - Select your strategy from the dropdown

2. **Set Backtest Parameters**:
   - Start Date: Choose a start date (e.g., 1 year ago)
   - End Date: Choose an end date (e.g., today)
   - Initial Capital: Set your initial capital (e.g., $10,000)
   - Trading Fees: Set the trading fees (e.g., 0.1%)

3. **Run Backtest**:
   - Click "Run Backtest"
   - Wait for the backtest to complete

4. **Analyze Results**:
   - Review the performance metrics:
     - Total Return
     - Sharpe Ratio
     - Maximum Drawdown
     - Win Rate
   - Examine the trade history
   - Study the equity curve and drawdown chart

5. **Optimize Strategy (Optional)**:
   - If the results aren't satisfactory, adjust your strategy parameters
   - Run another backtest with the new parameters
   - Repeat until you're satisfied with the results

## Deploying a Strategy

Once you're satisfied with your backtest results, you can deploy your strategy:

1. **Navigate to Strategy Manager**:
   - In the dashboard, go to Strategies > Strategy Manager
   - Find your strategy and click "Deploy"

2. **Select Deployment Options**:
   - Trading Mode:
     - Paper Trading (simulated trading with no real money)
     - Live Trading (real trading with real money)
   - Trading Frequency: How often to check for signals
   - Notification Settings: When to receive notifications

3. **Deploy Strategy**:
   - Click "Deploy Strategy"
   - Confirm the deployment

4. **Verify Deployment**:
   - Check the "Active Strategies" section
   - Verify that your strategy shows "Running" status

## Monitoring Your Trades

After deploying your strategy, you'll want to monitor its performance:

1. **Dashboard Overview**:
   - The main dashboard shows a summary of your trading activity
   - Check account balance, open positions, and recent trades

2. **Performance Monitoring**:
   - Navigate to Dashboard > Performance
   - Monitor your strategy's performance:
     - Account balance and equity
     - Open positions
     - Recent trades
     - Profit/loss

3. **Trade History**:
   - Navigate to Trades > Trade History
   - View all trades executed by your strategies
   - Filter by strategy, trading pair, or date range
   - Export trade history for further analysis

4. **Alerts and Notifications**:
   - Configure alerts for important events:
     - Trade execution
     - Position opened/closed
     - Profit/loss thresholds
     - Strategy errors
   - Receive notifications via:
     - Dashboard
     - Email
     - Telegram (if configured)

## Next Steps

Now that you have CryptoBot up and running, here are some next steps to explore:

1. **Explore Different Strategies**:
   - Try different strategy types (Breakout, Momentum, etc.)
   - Experiment with different parameters
   - Combine multiple strategies

2. **Advanced Configuration**:
   - Customize risk management settings
   - Configure advanced order types
   - Set up portfolio rebalancing

3. **Learn More**:
   - Read the [User Guide](user-guide.md) for detailed usage instructions
   - Check the [Administrator Guide](administrator-guide.md) for advanced configuration
   - Explore the [Developer Guide](developer-guide.md) if you want to extend CryptoBot

4. **Join the Community**:
   - Join the CryptoBot community forum
   - Share your strategies and results
   - Learn from other users' experiences

5. **Stay Updated**:
   - Keep CryptoBot updated to the latest version
   - Follow the project on GitHub
   - Subscribe to the newsletter for updates and tips