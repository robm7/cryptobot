# Cryptobot Developer Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Development Environment](#development-environment)
4. [Core Components](#core-components)
5. [Creating Custom Strategies](#creating-custom-strategies)
6. [Adding Exchange Support](#adding-exchange-support)
7. [Extending the API](#extending-the-api)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Contributing](#contributing)

## Introduction

This developer guide provides information on how to extend and customize the Cryptobot trading system. It covers the system architecture, development environment setup, and guides for implementing custom components.

### Target Audience

This guide is intended for developers who want to:

- Understand the Cryptobot architecture
- Develop custom trading strategies
- Add support for new exchanges
- Extend the API with new endpoints
- Contribute to the Cryptobot project

### Prerequisites

To work with the Cryptobot codebase, you should have:

- Intermediate Python programming skills
- Basic understanding of trading concepts
- Familiarity with RESTful APIs
- Knowledge of FastAPI and SQLAlchemy (helpful)
- Understanding of asynchronous programming (helpful)

## Architecture Overview

Cryptobot follows a microservices architecture, with several independent services that communicate through APIs and message queues.

### System Components

![Architecture Diagram](./architecture/component-diagram.png)

The main components are:

1. **Auth Service**: Handles authentication, authorization, and API key management
2. **Strategy Service**: Manages trading strategies and their execution
3. **Data Service**: Provides market data and historical data
4. **Trade Service**: Executes trades and manages orders
5. **Backtest Service**: Runs backtests for strategy evaluation
6. **Dashboard**: Web interface for user interaction

### Communication Flow

Services communicate through:

- RESTful APIs for synchronous operations
- WebSockets for real-time updates
- Message queues for asynchronous operations

### Data Flow

1. Market data flows from exchanges to the Data Service
2. The Strategy Service consumes market data and generates trading signals
3. Trading signals are sent to the Trade Service for execution
4. Execution results are stored and reported back to the Strategy Service

## Development Environment

### Setting Up the Development Environment

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/cryptobot.git
   cd cryptobot
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the project root:
   ```
   CRYPTOBOT_ENV=development
   CRYPTOBOT_LOG_LEVEL=DEBUG
   CRYPTOBOT_DB_URL=sqlite:///cryptobot_dev.db
   CRYPTOBOT_REDIS_HOST=localhost
   CRYPTOBOT_REDIS_PORT=6379
   ```

5. **Initialize the Database**:
   ```bash
   python -m scripts.init_db
   ```

### Running the Development Server

To run all services:

```bash
python main.py --all
```

To run a specific service:

```bash
python main.py --service auth
```

To run the dashboard:

```bash
python main.py --dashboard
```

### Development Tools

- **Code Linting**: Use `flake8` for code linting
  ```bash
  flake8 .
  ```

- **Type Checking**: Use `mypy` for type checking
  ```bash
  mypy .
  ```

- **Code Formatting**: Use `black` for code formatting
  ```bash
  black .
  ```

- **Dependency Management**: Use `scripts/manage_dependencies.py` for dependency management
  ```bash
  python scripts/manage_dependencies.py --update
  ```

## Core Components

### Auth Service

The Auth Service handles authentication, authorization, and API key management.

#### Key Files

- `auth/main.py`: Main entry point
- `auth/auth_service.py`: Core authentication logic
- `auth/key_manager.py`: API key management
- `auth/routers/auth.py`: Authentication endpoints
- `auth/routers/api_keys.py`: API key endpoints

#### Authentication Flow

1. User authenticates with username/password
2. Auth Service issues JWT tokens (access and refresh)
3. Access token is used for API requests
4. Refresh token is used to obtain new access tokens

#### API Key Rotation

The API Key Rotation System provides secure management of API keys:

1. Keys are automatically rotated every 90 days
2. Old keys remain valid during a grace period
3. Keys can be manually rotated or revoked
4. Emergency revocation is available for compromised keys

### Strategy Service

The Strategy Service manages trading strategies and their execution.

#### Key Files

- `strategy/main.py`: Main entry point
- `strategy/models/strategy.py`: Strategy data models
- `strategy/routers/strategies.py`: Strategy endpoints
- `strategies/base_strategy.py`: Base strategy class
- `strategies/mean_reversion.py`: Example strategy implementation

#### Strategy Lifecycle

1. Strategy is created and configured
2. Strategy is backtested for evaluation
3. Strategy is deployed for live trading
4. Strategy generates trading signals
5. Trading signals are executed as orders
6. Strategy performance is monitored

### Data Service

The Data Service provides market data and historical data.

#### Key Files

- `data/main.py`: Main entry point
- `data/providers/`: Exchange-specific data providers
- `data/routers/market_data.py`: Market data endpoints
- `data/cache.py`: Data caching logic

#### Data Flow

1. Data Service connects to exchanges via APIs
2. Market data is fetched and normalized
3. Data is cached for performance
4. Data is provided to other services via APIs

### Trade Service

The Trade Service executes trades and manages orders.

#### Key Files

- `trade/main.py`: Main entry point
- `trade/models/trade.py`: Trade data models
- `trade/routers/orders.py`: Order endpoints
- `trade/engine.py`: Trade execution engine

#### Order Execution

The Order Execution System provides reliable order execution:

1. Orders are received from the Strategy Service
2. Orders are validated and normalized
3. Orders are executed on the exchange
4. Order status is monitored and updated
5. Order results are reported back

### Backtest Service

The Backtest Service runs backtests for strategy evaluation.

#### Key Files

- `backtest/main.py`: Main entry point
- `backtest/engine.py`: Backtest engine
- `backtest/routers/backtest.py`: Backtest endpoints

#### Backtest Flow

1. Backtest request is received with strategy and parameters
2. Historical data is fetched from the Data Service
3. Strategy is executed against historical data
4. Performance metrics are calculated
5. Results are returned to the client

## Creating Custom Strategies

### Strategy Structure

Custom strategies should inherit from the `BaseStrategy` class:

```python
from strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def __init__(self, params=None):
        super().__init__(params)
        # Initialize strategy parameters
        self.lookback_period = self.params.get('lookback_period', 20)
        self.entry_threshold = self.params.get('entry_threshold', 2.0)
        self.exit_threshold = self.params.get('exit_threshold', 0.5)
        
    def generate_signals(self, data):
        """Generate trading signals from market data"""
        signals = []
        # Implement your signal generation logic here
        return signals
    
    def should_open_position(self, data):
        """Determine if a new position should be opened"""
        # Implement your entry logic here
        return True/False, position_data
    
    def should_close_position(self, position, data):
        """Determine if an existing position should be closed"""
        # Implement your exit logic here
        return True/False, close_reason
```

### Strategy Registration

Register your strategy in `strategies/__init__.py`:

```python
from strategies.base_strategy import BaseStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.my_custom_strategy import MyCustomStrategy

STRATEGY_REGISTRY = {
    'base': BaseStrategy,
    'mean_reversion': MeanReversionStrategy,
    'my_custom_strategy': MyCustomStrategy
}
```

### Strategy Parameters

Define strategy parameters in the strategy class:

```python
class MyCustomStrategy(BaseStrategy):
    @classmethod
    def get_parameters(cls):
        """Get strategy parameters with defaults and descriptions"""
        return {
            'lookback_period': {
                'type': 'integer',
                'default': 20,
                'min': 5,
                'max': 100,
                'description': 'Number of periods to look back'
            },
            'entry_threshold': {
                'type': 'float',
                'default': 2.0,
                'min': 0.5,
                'max': 5.0,
                'description': 'Threshold for entry signals'
            },
            'exit_threshold': {
                'type': 'float',
                'default': 0.5,
                'min': 0.1,
                'max': 2.0,
                'description': 'Threshold for exit signals'
            }
        }
```

### Strategy Testing

Test your strategy with the Backtest Service:

```python
from backtest.engine import BacktestEngine
from strategies.my_custom_strategy import MyCustomStrategy

# Create strategy instance
strategy = MyCustomStrategy({
    'lookback_period': 20,
    'entry_threshold': 2.0,
    'exit_threshold': 0.5
})

# Create backtest engine
engine = BacktestEngine(
    strategy=strategy,
    symbol='BTC/USD',
    timeframe='1h',
    start_date='2024-01-01',
    end_date='2024-12-31',
    initial_capital=10000.0
)

# Run backtest
results = engine.run()

# Print results
print(f"Total Return: {results['total_return']}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']}")
print(f"Max Drawdown: {results['max_drawdown']}%")
```

## Adding Exchange Support

### Exchange Integration

To add support for a new exchange:

1. Create a new exchange client in `services/mcp/market-data/`:

```python
from services.mcp.market-data.interfaces import MarketDataProvider

class NewExchangeProvider(MarketDataProvider):
    def __init__(self, api_key=None, api_secret=None):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        # Initialize exchange-specific client
        
    async def get_ticker(self, symbol):
        """Get ticker for a symbol"""
        # Implement exchange-specific logic
        
    async def get_orderbook(self, symbol, depth=10):
        """Get order book for a symbol"""
        # Implement exchange-specific logic
        
    async def get_historical_data(self, symbol, timeframe, start, end):
        """Get historical data for a symbol"""
        # Implement exchange-specific logic
```

2. Create a new order executor in `services/mcp/order-execution/`:

```python
from services.mcp.order-execution.interfaces import OrderExecutionInterface

class NewExchangeExecutor(OrderExecutionInterface):
    def __init__(self, api_key=None, api_secret=None):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        # Initialize exchange-specific client
        
    async def execute_order(self, order_params):
        """Execute an order"""
        # Implement exchange-specific logic
        
    async def cancel_order(self, order_id):
        """Cancel an order"""
        # Implement exchange-specific logic
        
    async def get_order_status(self, order_id):
        """Get order status"""
        # Implement exchange-specific logic
```

3. Register the new exchange in `config/default_config.json`:

```json
{
  "exchanges": {
    "new_exchange": {
      "enabled": true,
      "timeout": 10,
      "rate_limit": {
        "max_requests_per_second": 5,
        "max_requests_per_minute": 300
      }
    }
  }
}
```

### Exchange Testing

Test the exchange integration:

```python
import asyncio
from services.mcp.market-data.new_exchange_provider import NewExchangeProvider

async def test_exchange():
    provider = NewExchangeProvider(api_key='your_api_key', api_secret='your_api_secret')
    
    # Test ticker
    ticker = await provider.get_ticker('BTC/USD')
    print(f"Ticker: {ticker}")
    
    # Test order book
    orderbook = await provider.get_orderbook('BTC/USD', depth=10)
    print(f"Order Book: {orderbook}")
    
    # Test historical data
    data = await provider.get_historical_data(
        symbol='BTC/USD',
        timeframe='1h',
        start='2024-01-01',
        end='2024-01-02'
    )
    print(f"Historical Data: {data}")

if __name__ == '__main__':
    asyncio.run(test_exchange())
```

## Extending the API

### Adding New Endpoints

To add new API endpoints:

1. Create a new router file or extend an existing one:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.my_model import MyModel
from schemas.my_schema import MySchema, MyCreateSchema
from auth_service import get_current_active_user

router = APIRouter(prefix="/my-endpoint", tags=["my-endpoint"])

@router.get("/", response_model=List[MySchema])
async def get_items(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all items"""
    items = db.query(MyModel).filter(MyModel.user_id == current_user.id).all()
    return items

@router.post("/", response_model=MySchema)
async def create_item(
    item: MyCreateSchema,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new item"""
    db_item = MyModel(**item.dict(), user_id=current_user.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
```

2. Include the router in the main application:

```python
from fastapi import FastAPI
from routers import my_router

app = FastAPI()
app.include_router(my_router.router)
```

### API Documentation

Document your API endpoints using FastAPI's built-in documentation:

```python
@router.get("/", response_model=List[MySchema])
async def get_items(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all items for the current user.
    
    This endpoint returns a list of all items owned by the authenticated user.
    Items are sorted by creation date in descending order.
    """
    items = db.query(MyModel).filter(MyModel.user_id == current_user.id).all()
    return items
```

## Testing

### Unit Testing

Write unit tests for your code:

```python
import pytest
from strategies.my_custom_strategy import MyCustomStrategy

def test_my_custom_strategy():
    # Create strategy instance
    strategy = MyCustomStrategy({
        'lookback_period': 20,
        'entry_threshold': 2.0,
        'exit_threshold': 0.5
    })
    
    # Create test data
    data = [
        {'timestamp': '2024-01-01T00:00:00Z', 'close': 50000.0},
        {'timestamp': '2024-01-01T01:00:00Z', 'close': 51000.0},
        {'timestamp': '2024-01-01T02:00:00Z', 'close': 52000.0}
    ]
    
    # Test signal generation
    signals = strategy.generate_signals(data)
    
    # Assert expected results
    assert len(signals) > 0
    assert signals[0]['direction'] in ['buy', 'sell']
```

### Integration Testing

Write integration tests for your components:

```python
import pytest
import asyncio
from services.mcp.market-data.new_exchange_provider import NewExchangeProvider
from services.mcp.order-execution.new_exchange_executor import NewExchangeExecutor

@pytest.mark.asyncio
async def test_exchange_integration():
    # Create provider and executor
    provider = NewExchangeProvider(api_key='test_key', api_secret='test_secret')
    executor = NewExchangeExecutor(api_key='test_key', api_secret='test_secret')
    
    # Get market data
    ticker = await provider.get_ticker('BTC/USD')
    
    # Execute test order
    order_params = {
        'symbol': 'BTC/USD',
        'side': 'buy',
        'type': 'limit',
        'quantity': 0.1,
        'price': ticker['bid'] * 0.9  # 10% below current bid
    }
    
    order_id = await executor.execute_order(order_params)
    assert order_id is not None
    
    # Check order status
    status = await executor.get_order_status(order_id)
    assert status['status'] in ['open', 'filled', 'canceled']
    
    # Cancel order
    if status['status'] == 'open':
        result = await executor.cancel_order(order_id)
        assert result is True
```

### Running Tests

Run tests using pytest:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_custom_strategy.py

# Run tests with coverage
pytest --cov=.
```

## Deployment

### Docker Deployment

Deploy Cryptobot using Docker:

1. Build the Docker images:
   ```bash
   docker-compose build
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Check the logs:
   ```bash
   docker-compose logs -f
   ```

### Standalone Deployment

Deploy Cryptobot as a standalone application:

1. Build the executable:
   ```bash
   # Windows
   .\scripts\build_windows.ps1 -Clean -Optimize
   
   # Linux
   ./scripts/build_linux.sh --clean --optimize
   ```

2. Run the executable:
   ```bash
   # Windows
   .\dist\cryptobot\cryptobot.exe --all
   
   # Linux
   ./dist/cryptobot/cryptobot --all
   ```

### Configuration

Configure the deployment using environment variables or a configuration file:

```bash
# Using environment variables
export CRYPTOBOT_ENV=production
export CRYPTOBOT_DB_URL=postgresql://user:password@localhost/cryptobot
export CRYPTOBOT_REDIS_HOST=redis.example.com

# Using configuration file
cryptobot --config /path/to/config.json --all
```

## Contributing

### Contribution Guidelines

1. **Fork the Repository**: Fork the Cryptobot repository on GitHub

2. **Create a Branch**: Create a branch for your feature or bugfix
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make Changes**: Make your changes to the codebase

4. **Run Tests**: Ensure all tests pass
   ```bash
   pytest
   ```

5. **Format Code**: Format your code using black
   ```bash
   black .
   ```

6. **Commit Changes**: Commit your changes with a descriptive message
   ```bash
   git commit -m "Add my feature"
   ```

7. **Push Changes**: Push your changes to your fork
   ```bash
   git push origin feature/my-feature
   ```

8. **Create Pull Request**: Create a pull request on GitHub

### Code Style

Follow these code style guidelines:

- Use PEP 8 for Python code style
- Use black for code formatting
- Use type hints for function parameters and return values
- Write docstrings for all functions and classes
- Keep functions small and focused
- Write unit tests for all new code

### Documentation

Update documentation for all changes:

- Update docstrings for modified functions and classes
- Update API documentation for new or modified endpoints
- Update the user guide for user-facing changes
- Update the developer guide for developer-facing changes