"""
Integration Test Configuration

This module provides configuration for integration tests.
"""

import os
import json
from typing import Dict, Any, Optional

# Test environment
TEST_ENV = os.environ.get("TEST_ENV", "test")

# Database configuration
DB_CONFIG = {
    "test": {
        "url": "sqlite:///test_integration.db",
        "echo": False
    },
    "development": {
        "url": "sqlite:///dev_integration.db",
        "echo": True
    }
}

# Redis configuration
REDIS_CONFIG = {
    "test": {
        "host": "localhost",
        "port": 6379,
        "db": 10,  # Use a separate database for tests
        "password": None,
        "ssl": False
    },
    "development": {
        "host": "localhost",
        "port": 6379,
        "db": 11,
        "password": None,
        "ssl": False
    }
}

# Exchange configuration
EXCHANGE_CONFIG = {
    "test": {
        "binance": {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "testnet": True
        },
        "kraken": {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "testnet": True
        }
    },
    "development": {
        "binance": {
            "api_key": os.environ.get("BINANCE_API_KEY", ""),
            "api_secret": os.environ.get("BINANCE_API_SECRET", ""),
            "testnet": True
        },
        "kraken": {
            "api_key": os.environ.get("KRAKEN_API_KEY", ""),
            "api_secret": os.environ.get("KRAKEN_API_SECRET", ""),
            "testnet": True
        }
    }
}

# Test data configuration
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Test symbols
TEST_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Test timeframes
TEST_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Test users
TEST_USERS = {
    "admin": {
        "username": "admin",
        "password": "admin_password",
        "email": "admin@example.com",
        "roles": ["admin", "user"]
    },
    "user": {
        "username": "user",
        "password": "user_password",
        "email": "user@example.com",
        "roles": ["user"]
    },
    "trader": {
        "username": "trader",
        "password": "trader_password",
        "email": "trader@example.com",
        "roles": ["user", "trader"]
    }
}

# Test strategies
TEST_STRATEGIES = {
    "mean_reversion": {
        "name": "Mean Reversion",
        "description": "Mean reversion strategy for testing",
        "parameters": {
            "lookback_period": 20,
            "entry_threshold": 2.0,
            "exit_threshold": 0.5,
            "stop_loss": 2.0,
            "take_profit": 5.0
        }
    },
    "breakout_reset": {
        "name": "Breakout Reset",
        "description": "Breakout reset strategy for testing",
        "parameters": {
            "breakout_period": 20,
            "reset_threshold": 0.5,
            "stop_loss": 2.0,
            "take_profit": 5.0
        }
    }
}

# Test orders
TEST_ORDERS = {
    "limit_buy": {
        "symbol": "BTC/USDT",
        "side": "buy",
        "type": "limit",
        "quantity": 0.1,
        "price": 50000.0
    },
    "limit_sell": {
        "symbol": "BTC/USDT",
        "side": "sell",
        "type": "limit",
        "quantity": 0.1,
        "price": 60000.0
    },
    "market_buy": {
        "symbol": "ETH/USDT",
        "side": "buy",
        "type": "market",
        "quantity": 1.0
    },
    "market_sell": {
        "symbol": "ETH/USDT",
        "side": "sell",
        "type": "market",
        "quantity": 1.0
    }
}

# Performance optimization configuration
PERFORMANCE_CONFIG = {
    "query_optimizer": {
        "enabled": True,
        "slow_query_threshold": 0.1,
        "auto_optimize": True,
        "auto_index": False
    },
    "cache_manager": {
        "enabled": True,
        "default_ttl": 60,
        "memory_cache_fallback": True
    },
    "rate_limiter": {
        "enabled": True,
        "exchange_limits": {
            "binance": {
                "requests_per_second": 10.0,
                "burst_size": 20
            },
            "kraken": {
                "requests_per_second": 1.0,
                "burst_size": 5
            }
        }
    },
    "memory_optimizer": {
        "enabled": True,
        "monitoring": {
            "enabled": True,
            "interval": 60
        }
    },
    "performance_monitor": {
        "enabled": True,
        "thresholds": {
            "warning": 0.5,
            "critical": 2.0
        }
    }
}

# Get database configuration
def get_db_config() -> Dict[str, Any]:
    """
    Get database configuration for the current test environment.
    
    Returns:
        Database configuration
    """
    return DB_CONFIG.get(TEST_ENV, DB_CONFIG["test"])

# Get Redis configuration
def get_redis_config() -> Dict[str, Any]:
    """
    Get Redis configuration for the current test environment.
    
    Returns:
        Redis configuration
    """
    return REDIS_CONFIG.get(TEST_ENV, REDIS_CONFIG["test"])

# Get exchange configuration
def get_exchange_config(exchange: Optional[str] = None) -> Dict[str, Any]:
    """
    Get exchange configuration for the current test environment.
    
    Args:
        exchange: Exchange name (optional)
        
    Returns:
        Exchange configuration
    """
    config = EXCHANGE_CONFIG.get(TEST_ENV, EXCHANGE_CONFIG["test"])
    
    if exchange:
        return config.get(exchange, {})
    
    return config

# Load test data
def load_test_data(filename: str) -> Any:
    """
    Load test data from a file.
    
    Args:
        filename: File name
        
    Returns:
        Test data
    """
    file_path = os.path.join(TEST_DATA_DIR, filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Test data file not found: {file_path}")
    
    with open(file_path, "r") as f:
        if file_path.endswith(".json"):
            return json.load(f)
        else:
            return f.read()

# Save test data
def save_test_data(filename: str, data: Any) -> None:
    """
    Save test data to a file.
    
    Args:
        filename: File name
        data: Data to save
    """
    # Create test data directory if it doesn't exist
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    
    file_path = os.path.join(TEST_DATA_DIR, filename)
    
    with open(file_path, "w") as f:
        if file_path.endswith(".json"):
            json.dump(data, f, indent=2)
        else:
            f.write(str(data))

# Get test user
def get_test_user(user_type: str = "user") -> Dict[str, Any]:
    """
    Get test user data.
    
    Args:
        user_type: User type (admin, user, trader)
        
    Returns:
        Test user data
    """
    return TEST_USERS.get(user_type, TEST_USERS["user"])

# Get test strategy
def get_test_strategy(strategy_type: str = "mean_reversion") -> Dict[str, Any]:
    """
    Get test strategy data.
    
    Args:
        strategy_type: Strategy type
        
    Returns:
        Test strategy data
    """
    return TEST_STRATEGIES.get(strategy_type, TEST_STRATEGIES["mean_reversion"])

# Get test order
def get_test_order(order_type: str = "limit_buy") -> Dict[str, Any]:
    """
    Get test order data.
    
    Args:
        order_type: Order type
        
    Returns:
        Test order data
    """
    return TEST_ORDERS.get(order_type, TEST_ORDERS["limit_buy"])