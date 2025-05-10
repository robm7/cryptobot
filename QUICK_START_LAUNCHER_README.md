# CryptoBot Quick Start Launcher

The Quick Start Launcher is a user-friendly interface to start and manage the CryptoBot application. It provides an easy way to:

1. Select which services to start
2. Configure basic options
3. Monitor the status of running services
4. Open the dashboard in a web browser

## Features

- **Service Selection**: Choose which services to start from a list of core services, MCP services, and the dashboard.
- **Configuration Options**: Set the environment, profile, and log level.
- **Service Status Monitoring**: View the status of all services in real-time.
- **Log Display**: See logs from all services in one place.
- **Cross-Platform**: Works on Windows, macOS, and Linux.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Tkinter (usually comes with Python)

### Running the Launcher

To start the Quick Start Launcher, run:

```bash
python quick_start_launcher.py
```

### Using the Launcher

1. **Select Services**: Check the boxes next to the services you want to start.
   - Core Services: Authentication, Strategy, Data, Trade, and Backtest
   - MCP Services: Exchange Gateway, Market Data, Order Execution, etc.
   - Dashboard: Web interface for monitoring and control

2. **Configure Options**: Set the environment, profile, and log level as needed.
   - Environment: dev, test, stage, prod
   - Profile: default, docker, kubernetes
   - Log Level: DEBUG, INFO, WARNING, ERROR

3. **Start Services**: Click the "Start Selected Services" button to start the selected services.

4. **Monitor Status**: The status of each service will be displayed in the "Service Status" section.

5. **View Logs**: Logs from all services will be displayed in the "Logs" section.

6. **Open Dashboard**: Click the "Open in Browser" button to open the dashboard in your web browser.

7. **Stop Services**: Click the "Stop All Services" button to stop all running services.

## Service Descriptions

### Core Services

- **Authentication Service**: Handles user authentication and API key management
- **Strategy Service**: Manages trading strategies and signals
- **Data Service**: Provides market data and historical prices
- **Trade Service**: Executes trades and manages positions
- **Backtest Service**: Runs strategy backtests on historical data

### MCP Services

- **Exchange Gateway**: Provides a unified interface to multiple exchanges
- **Market Data**: Collects and processes market data
- **Order Execution**: Executes orders on exchanges
- **Paper Trading**: Simulates trading without real money
- **Portfolio Management**: Manages the portfolio and allocations
- **Reporting**: Generates reports on performance
- **Risk Management**: Manages risk and exposure
- **Strategy Execution**: Executes trading strategies

### User Interface

- **Dashboard**: Web interface for monitoring and control

## Troubleshooting

- If a service fails to start, check the logs for error messages.
- Make sure all required dependencies are installed.
- Verify that the ports required by the services are not in use.
- If the dashboard doesn't open automatically, try opening it manually at http://localhost:8080.

## Advanced Usage

### Command-Line Arguments

The Quick Start Launcher doesn't currently support command-line arguments, but you can use the main.py script directly with the following arguments:

```bash
python main.py --help
```

This will show all available command-line arguments for the CryptoBot application.