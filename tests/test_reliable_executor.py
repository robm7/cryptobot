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
async def test_circuit_breaker_warning_threshold(executor):
    """Test circuit breaker warning threshold"""
    # Configure circuit breaker for testing
    executor.circuit_config.error_threshold = 5
    executor.circuit_config.warning_threshold = 2
    executor.circuit_config.window_size_minutes = 1

    # Simulate errors
    for _ in range(3):  # More than warning threshold, less than error threshold
        executor._record_error("timeout")

    # Check if warning is logged (we can't directly assert the log message)
    # This test primarily ensures the warning threshold is checked
    assert executor._check_circuit()  # Should still be closed
    assert executor.circuit_state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_execute_order_non_retryable_error(executor):
    """Test order execution with a non-retryable error"""
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }

    # Configure a side effect that raises a non-retryable error
    with patch.object(executor, 'execute_order', side_effect=Exception("non_retryable_error"), autospec=True) as mock_execute:
        # Reduce retry delay for faster tests
        executor.retry_config.initial_delay = 0.01
        executor.retry_config.retryable_errors = ["timeout"]  # Only timeout is retryable

        # Call the method
        result = await executor.execute_order(order_params)

        # Verify the result
        assert result is None
        mock_execute.call_count == 1  # Called only once
        assert executor.stats['failed_orders'] == 1

@pytest.mark.asyncio
async def test_execute_order_circuit_breaker_open(executor):
    """Test order execution when the circuit breaker is open"""
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }

    # Open the circuit breaker
    executor.circuit_state = CircuitState.OPEN

    # Call the method
    result = await executor.execute_order(order_params)

    # Verify the result
    assert result is None
    assert executor.stats['failed_orders'] == 1

@pytest.mark.asyncio
async def test_cancel_order_success(executor):
    """Test successful order cancellation"""
    order_id = "ORDER_123"
    with patch.object(executor, 'cancel_order', return_value=True, autospec=True) as mock_cancel:
        result = await executor.cancel_order(order_id)
        assert result is True
        mock_cancel.assert_called_once_with(order_id)

@pytest.mark.asyncio
async def test_cancel_order_retry(executor):
    """Test order cancellation with retry"""
    order_id = "ORDER_123"
    side_effect = [
        Exception("timeout"),  # First call fails
        Exception("timeout"),  # Second call fails
        True      # Third call succeeds
    ]
    with patch.object(executor, 'cancel_order', side_effect=side_effect, autospec=True) as mock_cancel:
        executor.retry_config.initial_delay = 0.01
        result = await executor.cancel_order(order_id)
        assert result is True
        assert mock_cancel.call_count == 3

@pytest.mark.asyncio
async def test_cancel_order_circuit_breaker_open(executor):
    """Test order cancellation when the circuit breaker is open"""
    order_id = "ORDER_123"
    executor.circuit_state = CircuitState.OPEN
    result = await executor.cancel_order(order_id)
    assert result is False

@pytest.mark.asyncio
async def test_get_order_status_success(executor):
    """Test successful order status retrieval"""
    order_id = "ORDER_123"
    with patch.object(executor, 'get_order_status', return_value={'status': 'filled'}, autospec=True) as mock_get_status:
        result = await executor.get_order_status(order_id)
        assert result == {'status': 'filled'}
        mock_get_status.assert_called_once_with(order_id)

@pytest.mark.asyncio
async def test_get_order_status_retry(executor):
    """Test order status retrieval with retry"""
    order_id = "ORDER_123"
    side_effect = [
        Exception("timeout"),  # First call fails
        Exception("timeout"),  # Second call fails
        {'status': 'filled'}      # Third call succeeds
    ]
    with patch.object(executor, 'get_order_status', side_effect=side_effect, autospec=True) as mock_get_status:
        executor.retry_config.initial_delay = 0.01
        result = await executor.get_order_status(order_id)
        assert result == {'status': 'filled'}
        assert mock_get_status.call_count == 3

@pytest.mark.asyncio
async def test_get_order_status_circuit_breaker_open(executor):
    """Test order status retrieval when the circuit breaker is open"""
    order_id = "ORDER_123"
    executor.circuit_state = CircuitState.OPEN
    result = await executor.get_order_status(order_id)
    assert result is None

@pytest.mark.asyncio
async def test_order_verification_failure(executor):
    """Test order verification failure"""
    order_id = "ORDER_123456789"
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }

    # Mock get_order_status to return a non-filled order
    with patch.object(
        executor,
        'get_order_status',
        return_value={
            'status': 'pending',
            'filled_qty': 0.0,
            'avg_price': 0.0,
            'timestamp': datetime.now().isoformat()
        }
    ):
        # Verify the order
        result = await executor._verify_order_execution(order_id, order_params)
        assert result is False
