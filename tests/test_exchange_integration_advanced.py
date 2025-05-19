"""
Advanced exchange integration tests for the crypto trading bot.
Tests advanced order types, rate limiting, and error handling.
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, MagicMock
from utils.exchange_clients import ExchangeClient, RateLimitError, NetworkError, OrderError
from utils.advanced_order_types import AdvancedOrderManager
from utils.rate_limit_manager import RateLimitManager, apply_rate_limiting, rate_limited

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@pytest.fixture
def mock_exchange_client():
    """Create a mock exchange client for testing"""
    mock_client = AsyncMock(spec=ExchangeClient)
    
    # Mock ticker response
    mock_client.get_ticker.return_value = {
        'symbol': 'BTC/USDT',
        'last': 50000.0,
        'bid': 49900.0,
        'ask': 50100.0,
        'high': 51000.0,
        'low': 49000.0,
        'volume': 100.0,
        'timestamp': 1625097600000
    }
    
    # Mock order responses
    mock_client.create_order.return_value = {
        'id': 'test-order-id',
        'symbol': 'BTC/USDT',
        'type': 'limit',
        'side': 'buy',
        'price': 50000.0,
        'amount': 1.0,
        'status': 'open',
        'timestamp': 1625097600000
    }
    
    # Mock order status responses
    mock_client.get_order_status.return_value = {
        'id': 'test-order-id',
        'symbol': 'BTC/USDT',
        'type': 'limit',
        'side': 'buy',
        'price': 50000.0,
        'amount': 1.0,
        'status': 'open',
        'timestamp': 1625097600000
    }
    
    # Mock cancel order response
    mock_client.cancel_order.return_value = {
        'id': 'test-order-id',
        'status': 'canceled'
    }
    
    return mock_client

@pytest.fixture
def advanced_order_manager(mock_exchange_client):
    """Create an advanced order manager with a mock exchange client"""
    return AdvancedOrderManager(mock_exchange_client)

@pytest.mark.asyncio
async def test_oco_order_creation(advanced_order_manager):
    """Test creating an OCO (One-Cancels-Other) order"""
    # Create an OCO order
    oco_order = await advanced_order_manager.create_oco_order(
        symbol='BTC/USDT',
        side='sell',
        amount=0.1,
        price=52000.0,  # Limit price
        stop_price=48000.0  # Stop price
    )
    
    # Verify the OCO order structure
    assert oco_order['type'] == 'oco'
    assert oco_order['symbol'] == 'BTC/USDT'
    assert oco_order['side'] == 'sell'
    assert oco_order['amount'] == 0.1
    assert oco_order['price'] == 52000.0
    assert oco_order['stop_price'] == 48000.0
    assert 'limit_order_id' in oco_order
    assert 'stop_order_id' in oco_order
    assert oco_order['status'] == 'open'

@pytest.mark.asyncio
async def test_trailing_stop_order_creation(advanced_order_manager):
    """Test creating a trailing stop order"""
    # Create a trailing stop order
    trailing_order = await advanced_order_manager.create_trailing_stop_order(
        symbol='ETH/USDT',
        side='sell',
        amount=1.0,
        activation_price=3000.0,
        callback_rate=1.0  # 1% callback rate
    )
    
    # Verify the trailing stop order structure
    assert trailing_order['type'] == 'trailing_stop'
    assert trailing_order['symbol'] == 'ETH/USDT'
    assert trailing_order['side'] == 'sell'
    assert trailing_order['amount'] == 1.0
    assert trailing_order['activation_price'] == 3000.0
    assert trailing_order['callback_rate'] == 1.0
    assert trailing_order['status'] == 'pending'
    assert 'current_stop_price' in trailing_order

@pytest.mark.asyncio
async def test_oco_order_monitoring(advanced_order_manager, mock_exchange_client):
    """Test OCO order monitoring and cancellation logic"""
    # Create an OCO order
    oco_order = await advanced_order_manager.create_oco_order(
        symbol='BTC/USDT',
        side='sell',
        amount=0.1,
        price=52000.0,
        stop_price=48000.0
    )
    
    # Get the OCO ID
    oco_id = oco_order['id']
    
    # Verify the monitoring task was created
    assert oco_id in advanced_order_manager.running_tasks
    
    # Simulate limit order being filled
    mock_exchange_client.get_order_status.side_effect = lambda order_id, symbol: {
        oco_order['limit_order_id']: {
            'id': oco_order['limit_order_id'],
            'status': 'filled',
            'symbol': 'BTC/USDT'
        },
        oco_order['stop_order_id']: {
            'id': oco_order['stop_order_id'],
            'status': 'open',
            'symbol': 'BTC/USDT'
        }
    }.get(order_id, {})
    
    # Wait for the monitoring task to detect the fill
    await asyncio.sleep(0.1)
    
    # Check the order status
    status = await advanced_order_manager.get_advanced_order_status(oco_id)
    
    # The stop order should be canceled when the limit order fills
    assert mock_exchange_client.cancel_order.called
    assert mock_exchange_client.cancel_order.call_args[0][0] == oco_order['stop_order_id']

@pytest.mark.asyncio
async def test_trailing_stop_activation(advanced_order_manager, mock_exchange_client):
    """Test trailing stop order activation and adjustment"""
    # Create a trailing stop order
    trailing_order = await advanced_order_manager.create_trailing_stop_order(
        symbol='ETH/USDT',
        side='sell',
        amount=1.0,
        activation_price=3000.0,
        callback_rate=1.0
    )
    
    # Get the trailing stop ID
    trailing_id = trailing_order['id']
    
    # Verify the monitoring task was created
    assert trailing_id in advanced_order_manager.running_tasks
    
    # Simulate price movement to activate the trailing stop
    # First, price reaches activation price
    mock_exchange_client.get_ticker.return_value = {
        'symbol': 'ETH/USDT',
        'last': 3100.0,  # Above activation price
        'bid': 3090.0,
        'ask': 3110.0
    }
    
    # Wait for the monitoring task to detect the activation
    await asyncio.sleep(0.1)
    
    # Check the order status - should be active now
    status = await advanced_order_manager.get_advanced_order_status(trailing_id)
    assert status['status'] == 'active'
    
    # Simulate price moving higher
    mock_exchange_client.get_ticker.return_value = {
        'symbol': 'ETH/USDT',
        'last': 3200.0,  # Price moved higher
        'bid': 3190.0,
        'ask': 3210.0
    }
    
    # Wait for the monitoring task to adjust the stop price
    await asyncio.sleep(0.1)
    
    # Check the order status - stop price should be adjusted
    status = await advanced_order_manager.get_advanced_order_status(trailing_id)
    assert status['current_stop_price'] > trailing_order['current_stop_price']
    
    # Simulate price dropping below stop price
    mock_exchange_client.get_ticker.return_value = {
        'symbol': 'ETH/USDT',
        'last': 3000.0,  # Below the new stop price
        'bid': 2990.0,
        'ask': 3010.0
    }
    
    # Wait for the monitoring task to trigger the stop
    await asyncio.sleep(0.1)
    
    # A market order should be created when the stop is triggered
    assert mock_exchange_client.create_order.called
    assert mock_exchange_client.create_order.call_args[1]['type'] == 'market'
    assert mock_exchange_client.create_order.call_args[1]['side'] == 'sell'

@pytest.mark.asyncio
async def test_rate_limit_manager_configuration():
    """Test rate limit manager configuration"""
    # Create a rate limit manager
    rate_manager = RateLimitManager()
    
    # Configure custom limits for a test exchange
    rate_manager.configure_exchange('test_exchange', [
        {'max_requests': 10, 'time_window_seconds': 5},
        {'max_requests': 50, 'time_window_seconds': 60}
    ])
    
    # Configure an endpoint-specific limit
    rate_manager.configure_endpoint(
        'test_exchange',
        'orders',
        max_requests=5,
        time_window_seconds=10,
        weight_multiplier=2.0
    )
    
    # Verify the configuration
    assert 'test_exchange' in rate_manager.exchange_limits
    assert len(rate_manager.exchange_limits['test_exchange']) == 2
    assert rate_manager.exchange_limits['test_exchange'][0].max_requests == 10
    assert rate_manager.exchange_limits['test_exchange'][0].time_window_seconds == 5
    
    assert 'test_exchange' in rate_manager.endpoint_limits
    assert 'orders' in rate_manager.endpoint_limits['test_exchange']
    assert rate_manager.endpoint_limits['test_exchange']['orders'].max_requests == 5
    assert rate_manager.endpoint_limits['test_exchange']['orders'].weight_multiplier == 2.0

@pytest.mark.asyncio
async def test_rate_limit_throttling():
    """Test rate limit throttling behavior"""
    # Create a rate limit manager
    rate_manager = RateLimitManager()
    
    # Configure a strict limit for testing
    rate_manager.configure_exchange('test_exchange', [
        {'max_requests': 5, 'time_window_seconds': 5}
    ])
    
    # Make several requests in quick succession
    for i in range(4):
        should_throttle, wait_time = rate_manager.should_throttle('test_exchange')
        assert not should_throttle, f"Should not throttle on request {i+1}"
        rate_manager.record_request('test_exchange')
    
    # The 5th request should be close to the limit
    should_throttle, wait_time = rate_manager.should_throttle('test_exchange')
    rate_manager.record_request('test_exchange')
    
    # The 6th request should trigger throttling
    should_throttle, wait_time = rate_manager.should_throttle('test_exchange')
    assert should_throttle, "Should throttle after reaching the limit"
    assert wait_time > 0, "Wait time should be positive"

@pytest.mark.asyncio
async def test_rate_limit_decorator():
    """Test the rate_limited decorator"""
    # Create a test function with the decorator
    @rate_limited('test_exchange', 'orders', 2.0)
    async def test_function():
        return "success"
    
    # Mock the apply_rate_limiting function
    with patch('utils.rate_limit_manager.apply_rate_limiting') as mock_apply:
        # Call the decorated function
        result = await test_function()
        
        # Verify the rate limiting was applied
        assert mock_apply.called
        assert mock_apply.call_args[0][0] == 'test_exchange'
        assert mock_apply.call_args[0][1] == 'orders'
        assert mock_apply.call_args[0][2] == 2.0
        
        # Verify the function was executed
        assert result == "success"

@pytest.mark.asyncio
async def test_error_handling_rate_limit(mock_exchange_client):
    """Test handling of rate limit errors"""
    # Create a function that raises a rate limit error
    @rate_limited('binance')
    async def test_rate_limit_error():
        raise RateLimitError("Rate limit exceeded", retry_after=5)
    
    # Mock the record_error method
    with patch.object(RateLimitManager, 'record_error') as mock_record:
        # Call the function and expect the error to be re-raised
        with pytest.raises(RateLimitError):
            await test_rate_limit_error()
        
        # Verify the error was recorded
        assert mock_record.called
        assert mock_record.call_args[0][0] == 'binance'
        assert mock_record.call_args[0][1] == 'rate_limit'

@pytest.mark.asyncio
async def test_error_handling_network(mock_exchange_client):
    """Test handling of network errors"""
    # Create a function that raises a network error
    @rate_limited('binance')
    async def test_network_error():
        raise NetworkError("Connection timeout")
    
    # Mock the record_error method
    with patch.object(RateLimitManager, 'record_error') as mock_record:
        # Call the function and expect the error to be re-raised
        with pytest.raises(NetworkError):
            await test_network_error()
        
        # Verify the error was recorded
        assert mock_record.called
        assert mock_record.call_args[0][0] == 'binance'
        assert mock_record.call_args[0][1] == 'other'

@pytest.mark.asyncio
async def test_error_handling_order(mock_exchange_client):
    """Test handling of order errors"""
    # Create a function that raises an order error
    @rate_limited('binance')
    async def test_order_error():
        raise OrderError("Insufficient funds")
    
    # Mock the record_error method
    with patch.object(RateLimitManager, 'record_error') as mock_record:
        # Call the function and expect the error to be re-raised
        with pytest.raises(OrderError):
            await test_order_error()
        
        # Verify the error was recorded
        assert mock_record.called
        assert mock_record.call_args[0][0] == 'binance'
        assert mock_record.call_args[0][1] == 'other'

@pytest.mark.asyncio
async def test_backoff_strategy():
    """Test the exponential backoff strategy"""
    # Create a rate limit manager
    rate_manager = RateLimitManager()
    
    # Record several errors to increase the backoff multiplier
    for _ in range(3):
        rate_manager.record_error('test_exchange', 'rate_limit')
    
    # Verify the backoff multiplier has increased
    assert 'test_exchange' in rate_manager.backoff_multipliers
    assert rate_manager.backoff_multipliers['test_exchange'] > 1.0
    
    # Get the current backoff multiplier
    current_backoff = rate_manager.backoff_multipliers['test_exchange']
    
    # Reset the backoff
    rate_manager.reset_backoff('test_exchange')
    
    # Verify the backoff multiplier has decreased
    assert rate_manager.backoff_multipliers['test_exchange'] < current_backoff
    
    # Record more errors to test the cap
    for _ in range(10):
        rate_manager.record_error('test_exchange', 'rate_limit')
    
    # Verify the backoff multiplier is capped
    assert rate_manager.backoff_multipliers['test_exchange'] <= 10.0

@pytest.mark.asyncio
async def test_advanced_order_cancellation(advanced_order_manager):
    """Test cancellation of advanced orders"""
    # Create an OCO order
    oco_order = await advanced_order_manager.create_oco_order(
        symbol='BTC/USDT',
        side='sell',
        amount=0.1,
        price=52000.0,
        stop_price=48000.0
    )
    
    # Create a trailing stop order
    trailing_order = await advanced_order_manager.create_trailing_stop_order(
        symbol='ETH/USDT',
        side='sell',
        amount=1.0,
        activation_price=3000.0,
        callback_rate=1.0
    )
    
    # Cancel the OCO order
    oco_cancel = await advanced_order_manager.cancel_advanced_order(oco_order['id'])
    
    # Verify the cancellation
    assert oco_cancel['success']
    assert oco_cancel['order_id'] == oco_order['id']
    assert oco_cancel['status'] == 'canceled'
    
    # Cancel the trailing stop order
    trailing_cancel = await advanced_order_manager.cancel_advanced_order(trailing_order['id'])
    
    # Verify the cancellation
    assert trailing_cancel['success']
    assert trailing_cancel['order_id'] == trailing_order['id']
    assert trailing_cancel['status'] == 'canceled'