# Cryptobot Documentation

## API Response Structure

### Backtest Results
The `/api/backtest` endpoint returns a JSON response with these fields:

**Required Fields:**
- `final_capital`: float - The ending portfolio value
- `trades`: array - List of executed trades with details
- `return_pct`: float - Percentage return from initial to final capital

**Optional Fields:**
- `portfolio`: object - Detailed portfolio metrics including:
  - `cash`: array - Cash balance over time
  - `holdings`: array - Asset holdings over time
  - `value`: array - Total portfolio value over time
- `returns`: object - Time series of returns
- `max_drawdown`: float - Maximum drawdown percentage

## Overview
Cryptobot is a Flask-based trading application that provides:
- Real-time cryptocurrency trading
- Backtesting capabilities
- Strategy management
- Trade history tracking
- User authentication

## Architecture

### Backend
- **Flask** web framework
- **SQLAlchemy** ORM for database interactions
- **JWT** for authentication
- **SocketIO** for real-time updates
- **CCXT** for exchange integration

### Frontend
- Template-based HTML structure
- Chart.js for data visualization
- AJAX calls to backend API
- Responsive design

## Features

### User Authentication
- JWT-based authentication
- Access and refresh tokens
- Protected routes
- Token refresh endpoint

### Trading Features
- Multiple strategy support
- Real-time price data via Kraken API
- Trade execution
- Account balance monitoring

### Backtesting
- Historical data analysis
- Parameter controls:
  - Lookback period
  - Volatility multiplier
  - Reset threshold
  - Take profit/stop loss
- Performance metrics:
  - Return percentage
  - Win rate
  - Total trades

### Trade Management
- Trade history with filtering
- Trade execution logging
- Profit/loss tracking
- Backtest vs live trade differentiation

## API Endpoints

### Authentication
- `/api/refresh` - Refresh access token
- `/api/login` - User login (via auth_service.py)

### Trading Data
- `/api/ohlcv` - Get OHLCV data
- `/api/account-balance` - Get account balances
- `/api/trades` - Get trade history

### Strategy Management
- `/api/strategies` - List/create strategies
- `/api/backtest` - Execute backtest (POST)
  - Requires: strategy_id, symbol, timeframe, start_date, end_date, initial_capital
  - Returns: performance metrics and trade details
- `/api/save-backtest` - Save backtest results
- `/api/backtest-results` - Get backtest history

## Exchange Integration
- Kraken integration via CCXT
- API key configuration via .env
- OHLCV data fetching
- Account balance retrieval
- Trade execution

## Frontend Structure

### Templates
- `index.html` - Landing page
- `dashboard.html` - Main trading dashboard
- `backtest.html` - Backtesting interface
- `settings.html` - User settings

### JavaScript
- `main.js` - Core application logic:
  - Chart rendering
  - API interactions
  - Data formatting
  - Event handling

## Database Schema
- **User** - Authentication data
- **Strategy** - Trading strategies
- **Trade** - Trade records
- **BacktestResult** - Backtest outcomes

## Dependencies
See requirements.txt for complete list of dependencies.

## Setup
1. Install Python 3.11+
2. Create virtual environment
3. Install requirements: `pip install -r requirements.txt`
4. Configure .env file
5. Run: `python app.py`

## Configuration
Environment variables:
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key
- `DATABASE_URI` - Database connection string
- `KRAKEN_API_KEY` - Exchange API key
- `KRAKEN_SECRET` - Exchange API secret

## Distribution

Cryptobot can be packaged as a standalone executable for easy distribution:

### Build Requirements
- Python 3.9+
- PyInstaller 5.13.0+
- Development dependencies (see requirements-dev.txt)

### Building
1. Install build dependencies: `pip install -r requirements-dev.txt`
2. Run build script: `python build.py`

This creates platform-specific packages:
- Windows: cryptobot-windows.zip
- Linux: cryptobot-linux.tar.gz
- MacOS: cryptobot-macos.zip

See [Build Process Documentation](docs/implementation/build-process.md) for details.