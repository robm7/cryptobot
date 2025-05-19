import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime

from services.mcp.order_execution import ReliableOrderExecutor
from services.mcp.order_execution.reliable_executor import CircuitState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockExchangeGateway:
    """Mock exchange gateway for testing integration"""
    
    def __init__(self, should_fail=False, fail_count=0):
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_fails = 0
        self.orders = {}
        self.calls = []
    
    async def execute_order(self, symbol, side, order_type, amount, price=None):
        """Mock order execution"""
        self.calls.append(('execute_order', symbol, side, order_type, amount, price))
        
        if self.should_fail and self.current_fails < self.fail_count:
            self.current_fails += 1
            raise Exception("Exchange timeout")
        
        order_id = f"ORDER_{len(self.orders) + 1}_{int(datetime.now().timestamp())}"
        self.orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': amount,
            'price': price,
            'status': 'open',
            'filled': 0.0,
            'timestamp': datetime.now().isoformat()
        }
        return order_id
    
    async def cancel_order(self, order_id):
        """Mock order cancellation"""
        self.calls.append(('cancel_order', order_id))
        
        if self.should_fail and self.current_fails < self.fail_count:
            self.current_fails += 1
            raise Exception("Exchange timeout")
        
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'cancelled'
            return True
        return False
    
    async def get_order_status(self, order_id):
        """Mock get order status"""
        self.calls.append(('get_order_status', order_id))
        
        if self.should_fail and self.current_fails < self.fail_count:
            self.current_fails += 1
            raise Exception("Exchange timeout")
        
        if order_id in self.orders:
            # Simulate order being filled
            self.orders[order_id]['status'] = 'filled'
            self.orders[order_id]['filled'] = self.orders[order_id]['amount']
            return self.orders[order_id]
        return None

class MockPortfolioService:
    """Mock portfolio service for testing integration"""
    
    def __init__(self):
        self.portfolio = {
            'BTC': 10.0,
            'ETH': 100.0,
            'USD': 500000.0
        }
        self.calls = []
    
    async def update_portfolio(self, symbol, side, amount, price):
        """Mock portfolio update"""
        self.calls.append(('update_portfolio', symbol, side, amount, price))
        
        base, quote = symbol.split('/')
        
        if side == 'buy':
            self.portfolio[base] += amount
            self.portfolio[quote] -= amount * price
        else:  # sell
            self.portfolio[base] -= amount
            self.portfolio[quote] += amount * price
        
        return True
    
    async def get_portfolio(self):
        """Get current portfolio"""
        self.calls.append(('get_portfolio',))
        return self.portfolio.copy()

@pytest.fixture
def exchange_gateway():
    """Create a mock exchange gateway"""
    return MockExchangeGateway()

@pytest.fixture
def failing_exchange_gateway():
    """Create a mock exchange gateway that fails initially"""
    return MockExchangeGateway(should_fail=True, fail_count=2)

@pytest.fixture
def portfolio_service():
    """Create a mock portfolio service"""
    return MockPortfolioService()

@pytest.fixture
def executor(exchange_gateway, portfolio_service):
    """Create a ReliableOrderExecutor with mocked dependencies"""
    executor = ReliableOrderExecutor()
    
    # Patch the executor to use our mock services
    executor._exchange_gateway = exchange_gateway
    executor._portfolio_service = portfolio_service
    
    return executor

@pytest.mark.asyncio
async def test_integration_successful_order(executor, exchange_gateway, portfolio_service):
    """Test successful order execution integration"""
    # Configure the executor
    config = {
        "retry": {
            "max_retries": 3,
            "initial_delay": 0.01  # Small delay for faster tests
        }
    }
    await executor.configure(config)
    
    # Define order parameters
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    
    # Execute order
    with patch.object(executor, '_verify_order_execution', wraps=executor._verify_order_execution):
        order_id = await executor.execute_order(order_params)
        
        # Verify order was executed
        assert order_id is not None
        assert order_id in exchange_gateway.orders
        
        # Verify exchange gateway was called
        assert ('execute_order', 'BTC/USD', 'buy', 'limit', 1.0, 50000.0) in exchange_gateway.calls
        
        # Verify order status was checked during verification
        assert any(call[0] == 'get_order_status' for call in exchange_gateway.calls)
        
        # Check executor stats
        stats = await executor.get_execution_stats()
        assert stats['total_orders'] == 1
        assert stats['successful_orders'] == 1
        assert stats['failed_orders'] == 0

@pytest.mark.asyncio
async def test_integration_retry_logic(failing_exchange_gateway, portfolio_service):
    """Test retry logic with failing exchange"""
    # Create executor with failing exchange
    executor = ReliableOrderExecutor()
    executor._exchange_gateway = failing_exchange_gateway
    executor._portfolio_service = portfolio_service
    
    # Configure the executor with fast retries
    config = {
        "retry": {
            "max_retries": 5,
            "initial_delay": 0.01,
            "backoff_base": 1.2,
            "max_delay": 0.1
        }
    }
    await executor.configure(config)
    
    # Define order parameters
    order_params = {
        "symbol": "ETH/USD",
        "side": "buy",
        "type": "limit",
        "amount": 5.0,
        "price": 3000.0
    }
    
    # Execute order - should succeed after retries
    with patch.object(executor, '_verify_order_execution', return_value=True):
        order_id = await executor.execute_order(order_params)
        
        # Verify order was executed after retries
        assert order_id is not None
        assert order_id in failing_exchange_gateway.orders
        
        # Verify exchange gateway was called multiple times
        execute_calls = [call for call in failing_exchange_gateway.calls if call[0] == 'execute_order']
        assert len(execute_calls) > 1  # Should have retried
        
        # Check executor stats
        stats = await executor.get_execution_stats()
        assert stats['total_orders'] == 1
        assert stats['successful_orders'] == 1
        assert stats['failed_orders'] == 0
        assert stats['retry_count'] > 0

@pytest.mark.asyncio
async def test_integration_circuit_breaker(executor):
    """Test circuit breaker integration"""
    # Configure circuit breaker with low threshold
    config = {
        "circuit_breaker": {
            "error_threshold": 3,  # Trip after 3 errors per minute
            "warning_threshold": 1,
            "window_size_minutes": 1,
            "cool_down_seconds": 0.1  # Short cool-down for testing
        }
    }
    await executor.configure(config)
    
    # Simulate errors to trip circuit breaker
    for _ in range(4):
        executor._record_error("timeout")
    
    # Verify circuit is open
    assert executor.circuit_state == CircuitState.OPEN
    
    # Try to execute order - should be rejected
    order_params = {
        "symbol": "BTC/USD",
        "side": "sell",
        "type": "limit",
        "amount": 0.5,
        "price": 50000.0
    }
    
    order_id = await executor.execute_order(order_params)
    assert order_id is None
    
    # Wait for cool-down
    await asyncio.sleep(0.2)
    
    # Circuit should now be half-open
    assert executor.circuit_state == CircuitState.HALF_OPEN
    
    # Execute successful order to close circuit
    with patch.object(executor, '_verify_order_execution', return_value=True):
        order_id = await executor.execute_order(order_params)
        assert order_id is not None
    
    # Circuit should be closed
    assert executor.circuit_state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_integration_reconciliation(executor, exchange_gateway):
    """Test order reconciliation integration"""
    # Add some orders to the exchange
    for i in range(5):
        symbol = "BTC/USD" if i % 2 == 0 else "ETH/USD"
        side = "buy" if i % 2 == 0 else "sell"
        amount = 1.0 + i * 0.5
        price = 50000.0 if symbol == "BTC/USD" else 3000.0
        
        await exchange_gateway.execute_order(symbol, side, "limit", amount, price)
    
    # Run reconciliation
    with patch('services.mcp.order_execution.reliable_executor.logger') as mock_logger:
        result = await executor.reconcile_orders()
        
        # Verify reconciliation ran
        assert isinstance(result, dict)
        assert "total_orders" in result
        assert "matched_orders" in result
        
        # Verify logging occurred
        assert mock_logger.info.called

@pytest.mark.asyncio
async def test_integration_order_cancellation(executor, exchange_gateway):
    """Test order cancellation integration"""
    # Execute an order first
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    order_id = await executor.execute_order(order_params)
    assert order_id is not None

    # Cancel the order
    await executor.cancel_order(order_id)

    # Verify order was cancelled in the exchange
    assert exchange_gateway.orders[order_id]['status'] == 'cancelled'
    assert ('cancel_order', order_id) in exchange_gateway.calls

@pytest.mark.asyncio
async def test_integration_get_order_status(executor, exchange_gateway):
    """Test get order status integration"""
    # Execute an order first
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    order_id = await executor.execute_order(order_params)
    assert order_id is not None

    # Get order status
    status = await executor.get_order_status(order_id)

    # Verify order status is filled
    assert status['status'] == 'filled'
    assert ('get_order_status', order_id) in exchange_gateway.calls

@pytest.mark.asyncio
async def test_integration_configuration(executor):
    """Test configuration integration"""
    # Configure the executor
    config = {
        "retry": {
            "max_retries": 5,
            "initial_delay": 0.1
        },
        "circuit_breaker": {
            "error_threshold": 10
        }
    }
    await executor.configure(config)

    # Verify configuration was applied
    assert executor.retry_config.max_retries == 5
    assert executor.retry_config.initial_delay == 0.1
    assert executor.circuit_config.error_threshold == 10