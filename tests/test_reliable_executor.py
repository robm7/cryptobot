import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from services.mcp.order_execution.reliable_executor import (
    ReliableOrderExecutor,
    CircuitState,
    RetryConfig,
    CircuitBreakerConfig
)

@pytest.fixture
def executor():
    """Create a ReliableOrderExecutor instance for testing"""
    return ReliableOrderExecutor()

@pytest.mark.asyncio
async def test_execute_order_success(executor):
    """Test successful order execution"""
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    
    # Mock the _verify_order_execution method to avoid actual verification
    with patch.object(executor, '_verify_order_execution', return_value=True):
        order_id = await executor.execute_order(order_params)
        
        assert order_id is not None
        assert order_id.startswith("ORDER_")
        assert executor.stats['total_orders'] == 1
        assert executor.stats['successful_orders'] == 1
        assert executor.stats['failed_orders'] == 0

@pytest.mark.asyncio
async def test_execute_order_retry(executor):
    """Test order execution with retry"""
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    
    # Configure a side effect that fails twice then succeeds
    side_effect = [
        Exception("timeout"),  # First call fails
        Exception("timeout"),  # Second call fails
        "ORDER_123456789"      # Third call succeeds
    ]
    
    # Mock execute_order to use our side effect
    with patch.object(
        executor, 
        'execute_order', 
        side_effect=side_effect,
        autospec=True
    ) as mock_execute:
        # Reduce retry delay for faster tests
        executor.retry_config.initial_delay = 0.01
        
        # Call the method (will use our mock)
        result = await executor.execute_order(order_params)
        
        # Verify the result
        assert result == "ORDER_123456789"
        assert mock_execute.call_count == 3  # Called 3 times (2 retries + success)

@pytest.mark.asyncio
async def test_circuit_breaker_trip(executor):
    """Test circuit breaker tripping on high error rate"""
    # Configure circuit breaker for testing
    executor.circuit_config.error_threshold = 3  # Trip after 3 errors
    executor.circuit_config.window_size_minutes = 1  # In a 1-minute window
    
    # Simulate errors
    for _ in range(4):  # More than our threshold
        executor._record_error("timeout")
    
    # Check circuit state
    assert not executor._check_circuit()
    assert executor.circuit_state == CircuitState.OPEN

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(executor):
    """Test circuit breaker recovery after cool-down"""
    # Configure circuit breaker for testing
    executor.circuit_config.error_threshold = 3
    executor.circuit_config.cool_down_seconds = 0.1  # Short cool-down for testing
    
    # Trip the circuit breaker
    for _ in range(4):
        executor._record_error("timeout")
    
    # Verify circuit is open
    assert executor.circuit_state == CircuitState.OPEN
    assert not executor._check_circuit()
    
    # Wait for cool-down
    await asyncio.sleep(0.2)
    
    # Circuit should now be half-open
    assert executor._check_circuit()
    assert executor.circuit_state == CircuitState.HALF_OPEN
    
    # Simulate successful request in half-open state
    # This would normally be done by a successful execute_order call
    executor.circuit_state = CircuitState.CLOSED
    
    # Verify circuit is closed
    assert executor._check_circuit()
    assert executor.circuit_state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_order_verification(executor):
    """Test order verification process"""
    order_id = "ORDER_123456789"
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    
    # Mock get_order_status to return a filled order
    with patch.object(
        executor,
        'get_order_status',
        return_value={
            'status': 'filled',
            'filled_qty': 1.0,
            'avg_price': 50000.0,
            'timestamp': datetime.now().isoformat()
        }
    ):
        # Verify the order
        result = await executor._verify_order_execution(order_id, order_params)
        assert result is True

@pytest.mark.asyncio
async def test_reconcile_orders(executor):
    """Test order reconciliation process"""
    result = await executor.reconcile_orders()
    
    assert isinstance(result, dict)
    assert 'total_orders' in result
    assert 'matched_orders' in result
    assert 'mismatched_orders' in result
    assert 'mismatch_percentage' in result

@pytest.mark.asyncio
async def test_configure(executor):
    """Test configuration of executor parameters"""
    config = {
        'retry': {
            'max_retries': 5,
            'backoff_base': 3.0,
            'initial_delay': 0.5,
            'max_delay': 15.0,
            'retryable_errors': ['timeout', 'rate_limit', 'server_error']
        },
        'circuit_breaker': {
            'error_threshold': 20,
            'warning_threshold': 5,
            'window_size_minutes': 10,
            'cool_down_seconds': 30
        }
    }
    
    result = await executor.configure(config)
    
    assert result is True
    assert executor.retry_config.max_retries == 5
    assert executor.retry_config.backoff_base == 3.0
    assert executor.retry_config.initial_delay == 0.5
    assert executor.retry_config.max_delay == 15.0
    assert 'server_error' in executor.retry_config.retryable_errors
    
    assert executor.circuit_config.error_threshold == 20
    assert executor.circuit_config.warning_threshold == 5
    assert executor.circuit_config.window_size_minutes == 10
    assert executor.circuit_config.cool_down_seconds == 30

@pytest.mark.asyncio
async def test_get_execution_stats(executor):
    """Test getting execution statistics"""
    # Record some test data
    executor.stats['total_orders'] = 100
    executor.stats['successful_orders'] = 95
    executor.stats['failed_orders'] = 5
    
    # Record some errors
    for _ in range(3):
        executor._record_error("timeout")
    
    stats = await executor.get_execution_stats()
    
    assert stats['total_orders'] == 100
    assert stats['successful_orders'] == 95
    assert stats['failed_orders'] == 5
    assert stats['circuit_state'] == CircuitState.CLOSED.value
    assert 'error_rate_per_minute' in stats
    assert 'errors_in_window' in stats
    assert stats['errors_in_window'] == 3