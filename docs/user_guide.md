# Cryptobot User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Dashboard](#dashboard)
5. [Trading Strategies](#trading-strategies)
6. [Backtesting](#backtesting)
7. [Live Trading](#live-trading)
8. [API Keys](#api-keys)
9. [Configuration](#configuration)
10. [Monitoring](#monitoring)
11. [Troubleshooting](#troubleshooting)
12. [FAQ](#faq)

## Introduction

Cryptobot is a comprehensive cryptocurrency trading system that allows you to create, backtest, and deploy trading strategies across multiple exchanges. It provides a user-friendly dashboard for monitoring your strategies and trades, as well as a powerful API for integration with other systems.

### Key Features

- **Multiple Exchanges**: Support for major cryptocurrency exchanges including Binance, Kraken, and Coinbase.
- **Strategy Development**: Create custom trading strategies using Python.
- **Backtesting**: Test your strategies against historical data.
- **Live Trading**: Deploy your strategies for automated trading.
- **Dashboard**: Monitor your strategies and trades through a web interface.
- **API**: Integrate with other systems through a RESTful API.
- **Security**: Secure API key management with automatic rotation.

## Installation

### Prerequisites

- **Operating System**: Windows 10/11 or Linux (Ubuntu 20.04+ recommended)
- **Hardware**: 
  - CPU: 2+ cores
  - RAM: 4GB+ (8GB+ recommended)
  - Storage: 1GB+ free space
- **Network**: Stable internet connection

### Windows Installation

1. **Download the Installer**:
   - Download the latest Windows installer from the [releases page](https://github.com/yourusername/cryptobot/releases).
   - Choose either the single-file executable (`cryptobot-windows-[version].exe`) or the ZIP archive (`cryptobot-windows-[version].zip`).

2. **Run the Installer**:
   - If you downloaded the single-file executable, simply run it.
   - If you downloaded the ZIP archive, extract it to a location of your choice and run `cryptobot.exe`.

3. **First-Time Setup**:
   - The first time you run Cryptobot, it will guide you through the initial setup process.
   - Follow the on-screen instructions to configure your system.

### Linux Installation

1. **Download the Installer**:
   - Download the latest Linux installer from the [releases page](https://github.com/yourusername/cryptobot/releases).
   - Choose either the single-file executable (`cryptobot-linux-[version]`) or the tarball archive (`cryptobot-linux-[version].tar.gz`).

2. **Run the Installer**:
   - If you downloaded the single-file executable:
     ```bash
     chmod +x cryptobot-linux-[version]
     ./cryptobot-linux-[version]
     ```
   - If you downloaded the tarball archive:
     ```bash
     tar -xzf cryptobot-linux-[version].tar.gz
     cd cryptobot
     ./cryptobot
     ```

3. **First-Time Setup**:
   - The first time you run Cryptobot, it will guide you through the initial setup process.
   - Follow the on-screen instructions to configure your system.

### Docker Installation

1. **Pull the Docker Image**:
   ```bash
   docker pull yourusername/cryptobot:latest
   ```

2. **Run the Container**:
   ```bash
   docker run -d -p 8080:8080 -v cryptobot-data:/app/data yourusername/cryptobot:latest
   ```

3. **Access the Dashboard**:
   - Open your web browser and navigate to `http://localhost:8080`.

## Getting Started

### First-Time Setup

When you first run Cryptobot, you'll be guided through the following setup steps:

1. **Create an Account**:
   - Set up your administrator account with a username and password.
   - Enable two-factor authentication (recommended).

2. **Configure Exchanges**:
   - Add your exchange API keys.
   - Set trading limits and preferences.

3. **Set Up Notifications**:
   - Configure email or Telegram notifications.
   - Set up alerts for important events.

4. **Choose Default Strategy**:
   - Select a starter strategy or create your own.

### Command-Line Options

Cryptobot supports the following command-line options:

```
cryptobot [options]

Options:
  --config PATH       Path to configuration file
  --dashboard         Run the dashboard
  --cli               Run the command-line interface
  --service SERVICE   Run a specific service (auth, strategy, data, trade, backtest)
  --all               Run all services
  --version           Show version information
```

### Starting the Dashboard

To start the dashboard:

```bash
cryptobot --dashboard
```

Then open your web browser and navigate to `http://localhost:8080`.

## Dashboard

The dashboard is the main interface for interacting with Cryptobot. It provides a comprehensive view of your trading strategies, current positions, historical performance, and system status.

### Dashboard Layout

The dashboard is divided into several sections:

1. **Overview**: Summary of your trading performance, active strategies, and account balance.
2. **Strategies**: List of your trading strategies with performance metrics.
3. **Positions**: Current open positions across all exchanges.
4. **History**: Historical trades and performance.
5. **Backtesting**: Interface for backtesting strategies.
6. **Settings**: System configuration and preferences.
7. **API Keys**: Management of exchange API keys.
8. **Logs**: System logs and alerts.

### Navigation

- Use the sidebar to navigate between different sections.
- Use the top bar for account settings, notifications, and quick actions.
- Use the search bar to find specific strategies, trades, or settings.

### Customization

- **Themes**: Choose between light and dark themes.
- **Layouts**: Customize the dashboard layout to suit your preferences.
- **Widgets**: Add, remove, or rearrange widgets on the overview page.

## Trading Strategies

Cryptobot allows you to create, test, and deploy custom trading strategies.

### Built-in Strategies

Cryptobot comes with several built-in strategies:

1. **Mean Reversion**: Trades based on the assumption that prices will revert to their mean.
2. **Breakout Reset**: Identifies breakouts from consolidation patterns and trades the reset.
3. **Moving Average Crossover**: Trades when fast and slow moving averages cross.
4. **RSI Divergence**: Identifies divergences between price and RSI indicator.
5. **MACD Histogram**: Trades based on MACD histogram reversals.

### Creating a Custom Strategy

To create a custom strategy:

1. Navigate to the **Strategies** section of the dashboard.
2. Click the **Create Strategy** button.
3. Choose a template or start from scratch.
4. Implement your strategy logic using Python.
5. Save and backtest your strategy.

### Strategy Structure

A basic strategy consists of the following components:

```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, params=None):
        super().__init__(params)
        # Initialize your strategy parameters
        self.param1 = self.params.get('param1', default_value)
        self.param2 = self.params.get('param2', default_value)
    
    def generate_signals(self, data):
        # Implement your signal generation logic
        signals = []
        # ... your logic here ...
        return signals
    
    def should_open_position(self, data):
        # Determine if a new position should be opened
        return True/False, position_data
    
    def should_close_position(self, position, data):
        # Determine if an existing position should be closed
        return True/False, close_reason
```

### Strategy Parameters

Each strategy can have configurable parameters:

- **Entry Conditions**: Conditions for entering a trade.
- **Exit Conditions**: Conditions for exiting a trade.
- **Risk Management**: Stop loss, take profit, and position sizing.
- **Timeframes**: Trading timeframes (e.g., 1h, 4h, 1d).
- **Indicators**: Technical indicators used by the strategy.

## Backtesting

Backtesting allows you to test your strategies against historical data to evaluate their performance.

### Running a Backtest

To run a backtest:

1. Navigate to the **Backtesting** section of the dashboard.
2. Select a strategy to backtest.
3. Configure the backtest parameters:
   - **Exchange**: Select the exchange to backtest on.
   - **Symbol**: Select the trading pair (e.g., BTC/USD).
   - **Timeframe**: Select the timeframe (e.g., 1h, 4h, 1d).
   - **Period**: Select the historical period to backtest.
   - **Initial Capital**: Set the initial capital for the backtest.
   - **Strategy Parameters**: Configure strategy-specific parameters.
4. Click **Run Backtest** to start the backtest.

### Backtest Results

The backtest results include:

- **Performance Metrics**: Total return, Sharpe ratio, drawdown, etc.
- **Trade List**: List of all trades executed during the backtest.
- **Equity Curve**: Chart showing the equity curve over time.
- **Drawdown Chart**: Chart showing drawdowns over time.
- **Monthly Returns**: Table showing returns by month.
- **Position Sizing**: Analysis of position sizing.

### Optimizing Strategies

Cryptobot provides tools for optimizing strategy parameters:

1. Navigate to the **Optimization** tab in the backtesting section.
2. Select the parameters to optimize.
3. Set the parameter ranges.
4. Choose an optimization metric (e.g., total return, Sharpe ratio).
5. Click **Run Optimization** to find the optimal parameters.

## Live Trading

Once you've developed and backtested a strategy, you can deploy it for live trading.

### Deploying a Strategy

To deploy a strategy for live trading:

1. Navigate to the **Strategies** section of the dashboard.
2. Select a strategy to deploy.
3. Click **Deploy Strategy**.
4. Configure the deployment parameters:
   - **Exchange**: Select the exchange to trade on.
   - **Symbol**: Select the trading pair (e.g., BTC/USD).
   - **Timeframe**: Select the timeframe (e.g., 1h, 4h, 1d).
   - **Capital Allocation**: Set the capital to allocate to this strategy.
   - **Risk Parameters**: Configure risk management parameters.
   - **Strategy Parameters**: Configure strategy-specific parameters.
5. Click **Start Trading** to deploy the strategy.

### Monitoring Live Strategies

Monitor your live strategies through the dashboard:

- **Active Strategies**: View all active strategies and their performance.
- **Open Positions**: View all open positions and their current status.
- **Recent Trades**: View recent trades executed by your strategies.
- **Performance Metrics**: View performance metrics for each strategy.

### Stopping a Strategy

To stop a live trading strategy:

1. Navigate to the **Strategies** section of the dashboard.
2. Find the strategy you want to stop.
3. Click the **Stop** button.
4. Choose whether to close open positions or leave them open.

## API Keys

Cryptobot uses API keys to connect to exchanges and execute trades. The API Key Rotation System ensures that your keys are securely managed and regularly rotated.

### Adding an API Key

To add a new API key:

1. Navigate to the **API Keys** section of the dashboard.
2. Click **Add API Key**.
3. Select the exchange.
4. Enter your API key and secret.
5. Set permissions and restrictions.
6. Click **Save**.

### API Key Rotation

Cryptobot automatically rotates API keys to enhance security:

- **Rotation Schedule**: Keys are rotated every 90 days by default.
- **Grace Period**: Old keys remain valid for 24 hours after rotation.
- **Manual Rotation**: You can manually rotate keys at any time.

### Emergency Revocation

In case of a security breach:

1. Navigate to the **API Keys** section of the dashboard.
2. Find the compromised key.
3. Click **Emergency Revoke**.
4. Confirm the revocation.

## Configuration

Cryptobot is highly configurable to suit your specific needs.

### Configuration File

The main configuration file is located at `config/config.json`. You can edit this file directly or through the dashboard.

### Configuration Options

Key configuration options include:

- **Services**: Enable/disable and configure individual services.
- **Database**: Configure database connection settings.
- **Redis**: Configure Redis connection settings.
- **Logging**: Configure logging settings.
- **Security**: Configure security settings.
- **Exchanges**: Configure exchange-specific settings.
- **Order Execution**: Configure order execution settings.
- **Risk Management**: Configure risk management settings.
- **Notifications**: Configure notification settings.

### Environment Variables

You can also configure Cryptobot using environment variables:

- **CRYPTOBOT_CONFIG_PATH**: Path to configuration file.
- **CRYPTOBOT_LOG_LEVEL**: Logging level (INFO, DEBUG, etc.).
- **CRYPTOBOT_DB_URL**: Database connection URL.
- **CRYPTOBOT_REDIS_HOST**: Redis host.
- **CRYPTOBOT_REDIS_PORT**: Redis port.

## Monitoring

Cryptobot provides comprehensive monitoring capabilities to help you track system health and performance.

### System Monitoring

Monitor system health through the dashboard:

- **Service Status**: Status of all Cryptobot services.
- **Resource Usage**: CPU, memory, and disk usage.
- **Database Status**: Database connection status and performance.
- **Redis Status**: Redis connection status and performance.
- **API Status**: Status of exchange API connections.

### Performance Monitoring

Monitor trading performance through the dashboard:

- **Strategy Performance**: Performance metrics for each strategy.
- **Trade Execution**: Trade execution metrics (latency, success rate, etc.).
- **Order Book Analysis**: Analysis of order book depth and liquidity.
- **Market Data**: Market data metrics (update frequency, latency, etc.).

### Alerts and Notifications

Configure alerts and notifications:

- **Email Notifications**: Receive alerts via email.
- **Telegram Notifications**: Receive alerts via Telegram.
- **Dashboard Notifications**: Receive alerts in the dashboard.
- **Custom Webhooks**: Send alerts to custom webhooks.

## Troubleshooting

### Common Issues

#### Connection Issues

- **Exchange API Connection Failures**:
  - Check your internet connection.
  - Verify API key permissions.
  - Check if the exchange is experiencing issues.

- **Database Connection Failures**:
  - Check database server status.
  - Verify database credentials.
  - Check database connection settings.

- **Redis Connection Failures**:
  - Check Redis server status.
  - Verify Redis credentials.
  - Check Redis connection settings.

#### Strategy Issues

- **Strategy Not Generating Signals**:
  - Check strategy logic.
  - Verify data availability.
  - Check for errors in strategy code.

- **Unexpected Trading Behavior**:
  - Check strategy parameters.
  - Verify risk management settings.
  - Check for market anomalies.

#### System Issues

- **High CPU/Memory Usage**:
  - Check for resource-intensive strategies.
  - Reduce the number of active strategies.
  - Increase system resources.

- **Slow Dashboard Performance**:
  - Clear browser cache.
  - Reduce the number of open dashboard tabs.
  - Check for network issues.

### Logs

Cryptobot generates detailed logs to help diagnose issues:

- **System Logs**: Located at `logs/cryptobot.log`.
- **Service Logs**: Located at `logs/[service_name].log`.
- **Trade Logs**: Located at `logs/trades.log`.
- **Error Logs**: Located at `logs/errors.log`.

### Getting Help

If you encounter issues that you can't resolve:

- **Documentation**: Check the documentation for solutions.
- **Community Forum**: Ask for help on the community forum.
- **GitHub Issues**: Report bugs on GitHub.
- **Support Email**: Contact support at support@example.com.

## FAQ

### General Questions

**Q: Is Cryptobot suitable for beginners?**  
A: Cryptobot is designed to be user-friendly, but some knowledge of trading and programming is helpful.

**Q: Can I use Cryptobot for multiple exchanges?**  
A: Yes, Cryptobot supports multiple exchanges including Binance, Kraken, and Coinbase.

**Q: Is Cryptobot free to use?**  
A: Cryptobot is open-source and free to use. However, exchanges may charge trading fees.

### Trading Questions

**Q: What trading strategies does Cryptobot support?**  
A: Cryptobot comes with several built-in strategies and allows you to create custom strategies.

**Q: Can Cryptobot trade futures/options/margin?**  
A: Cryptobot primarily supports spot trading, but futures and margin trading are available on some exchanges.

**Q: How does Cryptobot handle risk management?**  
A: Cryptobot includes comprehensive risk management features including position sizing, stop loss, and take profit.

### Technical Questions

**Q: Can I run Cryptobot on a VPS?**  
A: Yes, Cryptobot can run on any VPS with sufficient resources.

**Q: Does Cryptobot require a constant internet connection?**  
A: Yes, Cryptobot requires a stable internet connection for live trading.

**Q: Can I access Cryptobot remotely?**  
A: Yes, you can access the Cryptobot dashboard from any device with a web browser.