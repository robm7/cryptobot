"""
Integration tests for the Order Execution System

These tests verify that the ReliableOrderExecutor works correctly
with exchange APIs and other components of the system.
"""

import pytest
import asyncio
import logging
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import random

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.mcp.order_execution.reliable_executor import (
    ReliableOrderExecutor,
    CircuitState,
    RetryConfig,
    CircuitBreakerConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockExchangeAPI:
    """Mock exchange API for testing"""
    
    def __init__(self, should_fail_rate=0.2, should_timeout_rate=0.1, should_rate_limit_rate=0.1):
        """
        Initialize with failure rates
        
        Args:
            should_fail_rate: Rate of random failures (0.0 - 1.0)
            should_timeout_rate: Rate of timeout failures (0.0 - 1.0)
            should_rate_limit_rate: Rate of rate limit failures (0.0 - 1.0)
        """
        self.should_fail_rate = should_fail_rate
        self.should_timeout_rate = should_timeout_rate
        self.should_rate_limit_rate = should_rate_limit_rate
        self.orders = {}
        self.call_count = 0
        self.failure_count = 0
        
    async def create_order(self, symbol, side, order_type, quantity, price=None):
        """
        Create an order on the exchange
        
        Args:
            symbol: Trading pair symbol
            side: buy or sell
            order_type: limit, market, etc.
            quantity: Order quantity
            price: Order price (for limit orders)
            
        Returns:
            Order ID if successful
            
        Raises:
            Exception if the order fails
        """
        self.call_count += 1
        
        # Simulate random failures
        rand = random.random()
        if rand < self.should_timeout_rate:
            self.failure_count += 1
            raise TimeoutError("Exchange API timeout")
        elif rand < self.should_timeout_rate + self.should_rate_limit_rate:
            self.failure_count += 1
            raise Exception("Rate limit exceeded")
        elif rand < self.should_fail_rate + self.should_timeout_rate + self.should_rate_limit_rate:
            self.failure_count += 1
            raise Exception("Exchange API error")
        
        # Create order
        order_id = f"ORDER_{int(time.time() * 1000)}_{len(self.orders)}"
        self.orders[order_id] = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "status": "open",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Simulate network delay
        await asyncio.sleep(0.05)
        
        return order_id
    
    async def get_order(self, order_id):
        """
        Get order details
        
        Args:
            order_id: Order ID
            
        Returns:
            Order details if found
            
        Raises:
            Exception if the order is not found
        """
        self.call_count += 1
        
        # Simulate random failures
        rand = random.random()
        if rand < self.should_timeout_rate:
            self.failure_count += 1
            raise TimeoutError("Exchange API timeout")
        elif rand < self.should_timeout_rate + self.should_rate_limit_rate:
            self.failure_count += 1
            raise Exception("Rate limit exceeded")
        
        # Get order
        if order_id in self.orders:
            # Simulate network delay
            await asyncio.sleep(0.05)
            
            # Simulate order being filled over time
            order = self.orders[order_id].copy()
            created_at = datetime.fromisoformat(order["created_at"])
            time_diff = (datetime.utcnow() - created_at).total_seconds()
            
            if time_diff > 0.5:
                order["status"] = "filled"
            
            return order
        else:
            self.failure_count += 1
            raise Exception(f"Order {order_id} not found")
    
    async def cancel_order(self, order_id):
        """
        Cancel an order
        
        Args:
            order_id: Order ID
            
        Returns:
            True if successful
            
        Raises:
            Exception if the cancellation fails
        """
        self.call_count += 1
        
        # Simulate random failures
        rand = random.random()
        if rand < self.should_timeout_rate:
            self.failure_count += 1
            raise TimeoutError("Exchange API timeout")
        elif rand < self.should_timeout_rate + self.should_rate_limit_rate:
            self.failure_count += 1
            raise Exception("Rate limit exceeded")
        
        # Cancel order
        if order_id in self.orders:
            # Simulate network delay
            await asyncio.sleep(0.05)
            
            self.orders[order_id]["status"] = "canceled"
            return True
        else:
            self.failure_count += 1
            raise Exception(f"Order {order_id} not found")

class MockPortfolioService:
    """Mock portfolio service for testing"""
    
    def __init__(self):
        self.portfolio = {
            "BTC": 10.0,
            "ETH": 100.0,
            "USD": 500000.0
        }
        self.updates = []
    
    async def update_portfolio(self, symbol, side, quantity, price):
        """Update portfolio after trade execution"""
        base, quote = symbol.split("/")
        
        if side == "buy":
            self.portfolio[base] += quantity
            self.portfolio[quote] -= quantity * price
        else:
            self.portfolio[base] -= quantity
            self.portfolio[quote] += quantity * price
        
        self.updates.append({
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def get_portfolio(self):
        """Get current portfolio"""
        return self.portfolio.copy()

@pytest.fixture
def exchange_api():
    """Create a mock exchange API"""
    return MockExchangeAPI()

@pytest.fixture
def portfolio_service():
    """Create a mock portfolio service"""
    return MockPortfolioService()

@pytest.fixture
def executor(exchange_api, portfolio_service):
    """Create a ReliableOrderExecutor with mocked dependencies"""
    executor = ReliableOrderExecutor()
    
    # Patch the executor to use our mock services
    executor._exchange_api = exchange_api
    executor._portfolio_service = portfolio_service
    
    # Configure for testing
    executor.retry_config.max_retries = 3
    executor.retry_config.initial_delay = 0.01
    executor.retry_config.max_delay = 0.1
    
    executor.circuit_config.error_threshold = 10
    executor.circuit_config.warning_threshold = 5
    executor.circuit_config.window_size_minutes = 1
    executor.circuit_config.cool_down_seconds = 0.5
    
    return executor

@pytest.mark.asyncio
async def test_successful_order_execution(executor, exchange_api, portfolio_service):
    """Test successful order execution"""
    # Set up a more reliable exchange for this test
    exchange_api.should_fail_rate = 0.0
    exchange_api.should_timeout_rate = 0.0
    exchange_api.should_rate_limit_rate = 0.0
    
    # Define order parameters
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "quantity": 1.0,
        "price": 50000.0
    }
    
    # Execute order
    with patch.object(executor, '_verify_order_execution', return_value=True):
        order_id = await executor.execute_order(order_params)
        
        # Verify order was executed
        assert order_id is not None
        assert order_id in exchange_api.orders
        
        # Verify order details
        order = exchange_api.orders[order_id]
        assert order["symbol"] == order_params["symbol"]
        assert order["side"] == order_params["side"]
        assert order["type"] == order_params["type"]
        assert order["quantity"] == order_params["quantity"]
        assert order["price"] == order_params["price"]
        
        # Verify executor stats
        stats = await executor.get_execution_stats()
        assert stats["total_orders"] == 1
        assert stats["successful_orders"] == 1
        assert stats["failed_orders"] == 0

@pytest.mark.asyncio
async def test_retry_logic(executor, exchange_api):
    """Test retry logic with failing exchange"""
    # Set up a failing exchange that will work on the third try
    exchange_api.should_fail_rate = 0.0
    exchange_api.should_timeout_rate = 0.0
    exchange_api.should_rate_limit_rate = 0.0
    
    # Mock create_order to fail twice then succeed
    original_create_order = exchange_api.create_order
    call_count = 0
    
    async def mock_create_order(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise TimeoutError("Exchange API timeout")
        return await original_create_order(*args, **kwargs)
    
    exchange_api.create_order = mock_create_order
    
    # Define order parameters
    order_params = {
        "symbol": "ETH/USD",
        "side": "buy",
        "type": "limit",
        "quantity": 5.0,
        "price": 3000.0
    }
    
    # Execute order - should succeed after retries
    with patch.object(executor, '_verify_order_execution', return_value=True):
        order_id = await executor.execute_order(order_params)
        
        # Verify order was executed after retries
        assert order_id is not None
        assert order_id in exchange_api.orders
        
        # Verify retry count
        assert call_count == 3
        
        # Verify executor stats
        stats = await executor.get_execution_stats()
        assert stats["total_orders"] == 1
        assert stats["successful_orders"] == 1
        assert stats["failed_orders"] == 0
        assert stats["retry_count"] > 0

@pytest.mark.asyncio
async def test_circuit_breaker(executor, exchange_api):
    """Test circuit breaker functionality"""
    # Set up a consistently failing exchange
    exchange_api.should_fail_rate = 1.0
    exchange_api.should_timeout_rate = 0.5
    exchange_api.should_rate_limit_rate = 0.5
    
    # Define order parameters
    order_params = {
        "symbol": "BTC/USD",
        "side": "sell",
        "type": "limit",
        "quantity": 0.5,
        "price": 50000.0
    }
    
    # Execute multiple orders to trigger circuit breaker
    with patch.object(executor, '_verify_order_execution', return_value=True):
        for _ in range(15):  # Should be enough to trip the circuit breaker
            try:
                await executor.execute_order(order_params)
            except Exception:
                pass  # Ignore failures
        
        # Verify circuit breaker is open
        assert executor.circuit_state == CircuitState.OPEN
        
        # Try to execute another order - should be rejected by circuit breaker
        order_id = await executor.execute_order(order_params)
        assert order_id is None
        
        # Wait for cool-down period
        await asyncio.sleep(0.6)
        
        # Circuit should now be half-open
        assert executor.circuit_state == CircuitState.HALF_OPEN
        
        # Fix the exchange
        exchange_api.should_fail_rate = 0.0
        exchange_api.should_timeout_rate = 0.0
        exchange_api.should_rate_limit_rate = 0.0
        
        # Execute successful order to close circuit
        order_id = await executor.execute_order(order_params)
        assert order_id is not None
        
        # Circuit should be closed
        assert executor.circuit_state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_order_verification(executor, exchange_api, portfolio_service):
    """Test order verification process"""
    # Set up a reliable exchange
    exchange_api.should_fail_rate = 0.0
    exchange_api.should_timeout_rate = 0.0
    exchange_api.should_rate_limit_rate = 0.0
    
    # Create an order
    order_id = await exchange_api.create_order(
        symbol="BTC/USD",
        side="buy",
        order_type="limit",
        quantity=1.0,
        price=50000.0
    )
    
    # Wait for order to be filled
    await asyncio.sleep(0.6)
    
    # Test verification
    result = await executor._verify_order_execution(order_id, {
        "symbol": "BTC/USD",
        "side": "buy",
        "quantity": 1.0,
        "price": 50000.0
    })
    
    # Verification should succeed
    assert result is True

@pytest.mark.asyncio
async def test_high_volume_order_execution(executor, exchange_api):
    """Test executing multiple orders in parallel"""
    # Set up a mostly reliable exchange
    exchange_api.should_fail_rate = 0.1
    exchange_api.should_timeout_rate = 0.05
    exchange_api.should_rate_limit_rate = 0.05
    
    # Define order parameters for multiple orders
    symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "DOT/USD"]
    sides = ["buy", "sell"]
    quantities = [0.1, 0.5, 1.0, 2.0, 5.0]
    prices = [50000.0, 3000.0, 100.0, 2.0, 20.0]
    
    order_params_list = []
    for i in range(20):  # Create 20 different orders
        symbol = symbols[i % len(symbols)]
        side = sides[i % len(sides)]
        quantity = quantities[i % len(quantities)]
        price = prices[i % len(prices)]
        
        order_params_list.append({
            "symbol": symbol,
            "side": side,
            "type": "limit",
            "quantity": quantity,
            "price": price
        })
    
    # Execute orders in parallel
    with patch.object(executor, '_verify_order_execution', return_value=True):
        tasks = [executor.execute_order(params) for params in order_params_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful orders
        successful_orders = [r for r in results if isinstance(r, str)]
        failed_orders = [r for r in results if isinstance(r, Exception) or r is None]
        
        # Verify some orders succeeded
        assert len(successful_orders) > 0
        
        # Verify executor stats
        stats = await executor.get_execution_stats()
        assert stats["total_orders"] == len(successful_orders)
        assert stats["successful_orders"] == len(successful_orders)
        
        # Some retries should have occurred
        assert stats["retry_count"] > 0

@pytest.mark.asyncio
async def test_reconciliation(executor, exchange_api):
    """Test order reconciliation process"""
    # Create some orders directly with the exchange
    for i in range(5):
        await exchange_api.create_order(
            symbol="BTC/USD",
            side="buy" if i % 2 == 0 else "sell",
            order_type="limit",
            quantity=1.0,
            price=50000.0
        )
    
    # Run reconciliation
    result = await executor.reconcile_orders()
    
    # Verify reconciliation ran
    assert isinstance(result, dict)
    assert "total_orders" in result
    assert result["total_orders"] > 0

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])