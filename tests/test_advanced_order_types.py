import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from utils.advanced_order_types import AdvancedOrderManager

@pytest.fixture
def mock_exchange_client():
    """Create a mock exchange client for testing"""
    client = AsyncMock()
    
    # Mock get_ticker method
    client.get_ticker.return_value = {
        'last': 50000.0,
        'bid': 49900.0,
        'ask': 50100.0
    }
    
    # Mock create_order method
    client.create_order.return_value = {
        'id': 'test-order-id',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'type': 'limit',
        'price': 50000.0,
        'amount': 1.0,
        'status': 'open'
    }
    
    # Mock get_order_status method
    client.get_order_status.return_value = {
        'id': 'test-order-id',
        'symbol': 'BTC/USDT',
        'status': 'open'
    }
    
    # Mock cancel_order method
    client.cancel_order.return_value = True
    
    return client

@pytest.fixture
def order_manager(mock_exchange_client):
    """Create an AdvancedOrderManager instance for testing"""
    return AdvancedOrderManager(mock_exchange_client)

@pytest.mark.asyncio
async def test_create_oco_order(order_manager, mock_exchange_client):
    """Test creating an OCO order"""
    # Mock different order IDs for limit and stop orders
    mock_exchange_client.create_order.side_effect = [
        {'id': 'limit-order-id', 'status': 'open', 'symbol': 'BTC/USDT'},
        {'id': 'stop-order-id', 'status': 'open', 'symbol': 'BTC/USDT'}
    ]
    
    # Create OCO order
    order = await order_manager.create_oco_order(
        symbol='BTC/USDT',
        side='sell',
        amount=1.0,
        price=52000.0,
        stop_price=48000.0
    )
    
    # Verify order details
    assert order['type'] == 'oco'
    assert order['symbol'] == 'BTC/USDT'
    assert order['side'] == 'sell'
    assert order['amount'] == 1.0
    assert order['price'] == 52000.0
    assert order['stop_price'] == 48000.0
    assert order['limit_order_id'] == 'limit-order-id'
    assert order['stop_order_id'] == 'stop-order-id'
    assert order['status'] == 'open'
    
    # Verify exchange client calls
    assert mock_exchange_client.create_order.call_count == 2
    
    # Verify order is being tracked
    assert order['id'] in order_manager.managed_orders
    assert order['id'] in order_manager.running_tasks
    
    # Clean up the background task
    order_manager.running_tasks[order['id']].cancel()
    try:
        await order_manager.running_tasks[order['id']]
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_create_trailing_stop_order(order_manager, mock_exchange_client):
    """Test creating a trailing stop order"""
    # Create trailing stop order
    order = await order_manager.create_trailing_stop_order(
        symbol='BTC/USDT',
        side='sell',
        amount=1.0,
        activation_price=50000.0,
        callback_rate=1.0
    )
    
    # Verify order details
    assert order['type'] == 'trailing_stop'
    assert order['symbol'] == 'BTC/USDT'
    assert order['side'] == 'sell'
    assert order['amount'] == 1.0
    assert order['activation_price'] == 50000.0
    assert order['callback_rate'] == 1.0
    assert order['status'] == 'pending'
    
    # Verify order is being tracked
    assert order['id'] in order_manager.managed_orders
    assert order['id'] in order_manager.running_tasks
    
    # Clean up the background task
    order_manager.running_tasks[order['id']].cancel()
    try:
        await order_manager.running_tasks[order['id']]
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_cancel_oco_order(order_manager, mock_exchange_client):
    """Test canceling an OCO order"""
    # Setup a mock OCO order
    oco_id = 'test-oco-id'
    order_manager.managed_orders[oco_id] = {
        'type': 'oco',
        'symbol': 'BTC/USDT',
        'side': 'sell',
        'amount': 1.0,
        'price': 52000.0,
        'stop_price': 48000.0,
        'limit_order_id': 'limit-order-id',
        'stop_order_id': 'stop-order-id',
        'status': 'open',
        'created_at': 1234567890.0
    }
    
    # Create a mock task
    mock_task = AsyncMock()
    order_manager.running_tasks[oco_id] = mock_task
    
    # Cancel the order
    result = await order_manager.cancel_advanced_order(oco_id)
    
    # Verify result
    assert result['success'] is True
    assert result['order_id'] == oco_id
    assert result['status'] == 'canceled'
    
    # Verify exchange client calls
    assert mock_exchange_client.cancel_order.call_count == 2
    
    # Verify task was canceled
    assert mock_task.cancel.called
    assert oco_id not in order_manager.running_tasks

@pytest.mark.asyncio
async def test_cancel_trailing_stop_order(order_manager, mock_exchange_client):
    """Test canceling a trailing stop order"""
    # Setup a mock trailing stop order
    order_id = 'test-trailing-id'
    order_manager.managed_orders[order_id] = {
        'type': 'trailing_stop',
        'symbol': 'BTC/USDT',
        'side': 'sell',
        'amount': 1.0,
        'activation_price': 50000.0,
        'callback_rate': 1.0,
        'current_stop_price': 49500.0,
        'highest_price': 50000.0,
        'lowest_price': 50000.0,
        'order_id': None,  # No actual order placed yet
        'status': 'pending',
        'created_at': 1234567890.0
    }
    
    # Create a mock task
    mock_task = AsyncMock()
    order_manager.running_tasks[order_id] = mock_task
    
    # Cancel the order
    result = await order_manager.cancel_advanced_order(order_id)
    
    # Verify result
    assert result['success'] is True
    assert result['order_id'] == order_id
    assert result['status'] == 'canceled'
    
    # Verify task was canceled
    assert mock_task.cancel.called
    assert order_id not in order_manager.running_tasks

@pytest.mark.asyncio
async def test_get_oco_order_status(order_manager, mock_exchange_client):
    """Test getting OCO order status"""
    # Setup a mock OCO order
    oco_id = 'test-oco-id'
    order_manager.managed_orders[oco_id] = {
        'type': 'oco',
        'symbol': 'BTC/USDT',
        'side': 'sell',
        'amount': 1.0,
        'price': 52000.0,
        'stop_price': 48000.0,
        'limit_order_id': 'limit-order-id',
        'stop_order_id': 'stop-order-id',
        'status': 'open',
        'created_at': 1234567890.0
    }
    
    # Mock different statuses for limit and stop orders
    mock_exchange_client.get_order_status.side_effect = [
        {'id': 'limit-order-id', 'status': 'open', 'symbol': 'BTC/USDT'},
        {'id': 'stop-order-id', 'status': 'open', 'symbol': 'BTC/USDT'}
    ]
    
    # Get order status
    status = await order_manager.get_advanced_order_status(oco_id)
    
    # Verify status
    assert status['id'] == oco_id
    assert status['status'] == 'open'
    assert status['symbol'] == 'BTC/USDT'
    assert status['type'] == 'oco'
    assert 'limit_order' in status
    assert 'stop_order' in status
    
    # Test filled status
    mock_exchange_client.get_order_status.side_effect = [
        {'id': 'limit-order-id', 'status': 'filled', 'symbol': 'BTC/USDT'},
        {'id': 'stop-order-id', 'status': 'open', 'symbol': 'BTC/USDT'}
    ]
    
    status = await order_manager.get_advanced_order_status(oco_id)
    assert status['status'] == 'filled'
    assert order_manager.managed_orders[oco_id]['filled_by'] == 'limit'

@pytest.mark.asyncio
async def test_get_trailing_stop_order_status(order_manager, mock_exchange_client):
    """Test getting trailing stop order status"""
    # Setup a mock trailing stop order
    order_id = 'test-trailing-id'
    order_manager.managed_orders[order_id] = {
        'type': 'trailing_stop',
        'symbol': 'BTC/USDT',
        'side': 'sell',
        'amount': 1.0,
        'activation_price': 50000.0,
        'callback_rate': 1.0,
        'current_stop_price': 49500.0,
        'highest_price': 50000.0,
        'lowest_price': 50000.0,
        'order_id': None,  # No actual order placed yet
        'status': 'pending',
        'created_at': 1234567890.0
    }
    
    # Get order status
    status = await order_manager.get_advanced_order_status(order_id)
    
    # Verify status
    assert status['id'] == order_id
    assert status['status'] == 'pending'
    assert status['symbol'] == 'BTC/USDT'
    assert status['type'] == 'trailing_stop'
    assert status['activation_price'] == 50000.0
    assert status['callback_rate'] == 1.0
    assert status['current_stop_price'] == 49500.0
    
    # Test with actual order placed
    order_manager.managed_orders[order_id]['order_id'] = 'stop-order-id'
    order_manager.managed_orders[order_id]['status'] = 'active'
    
    mock_exchange_client.get_order_status.return_value = {
        'id': 'stop-order-id', 
        'status': 'open', 
        'symbol': 'BTC/USDT'
    }
    
    status = await order_manager.get_advanced_order_status(order_id)
    assert status['status'] == 'active'
    assert 'order_details' in status

@pytest.mark.asyncio
async def test_monitor_oco_order(order_manager, mock_exchange_client):
    """Test OCO order monitoring logic"""
    # Setup test data
    oco_id = 'test-oco-id'
    symbol = 'BTC/USDT'
    limit_order_id = 'limit-order-id'
    stop_order_id = 'stop-order-id'
    
    order_manager.managed_orders[oco_id] = {
        'type': 'oco',
        'symbol': symbol,
        'side': 'sell',
        'amount': 1.0,
        'price': 52000.0,
        'stop_price': 48000.0,
        'limit_order_id': limit_order_id,
        'stop_order_id': stop_order_id,
        'status': 'open',
        'created_at': 1234567890.0
    }
    
    # Mock the get_order_status method to simulate limit order being filled
    mock_exchange_client.get_order_status.side_effect = [
        {'id': limit_order_id, 'status': 'filled', 'symbol': symbol},  # Limit order filled
        {'id': stop_order_id, 'status': 'open', 'symbol': symbol}      # Stop order still open
    ]
    
    # Start monitoring task
    task = asyncio.create_task(
        order_manager._monitor_oco_order(oco_id, symbol, limit_order_id, stop_order_id)
    )
    
    # Give the task time to run
    await asyncio.sleep(0.1)
    
    # Verify the stop order was canceled
    mock_exchange_client.cancel_order.assert_called_once_with(stop_order_id, symbol)
    
    # Verify order status was updated
    assert order_manager.managed_orders[oco_id]['status'] == 'filled'
    assert order_manager.managed_orders[oco_id]['filled_by'] == 'limit'
    
    # Clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_monitor_trailing_stop(order_manager, mock_exchange_client):
    """Test trailing stop monitoring logic"""
    # Setup test data
    order_id = 'test-trailing-id'
    symbol = 'BTC/USDT'
    
    order_manager.managed_orders[order_id] = {
        'type': 'trailing_stop',
        'symbol': symbol,
        'side': 'sell',
        'amount': 1.0,
        'activation_price': 50000.0,
        'callback_rate': 1.0,
        'current_stop_price': 49500.0,
        'highest_price': 50000.0,
        'lowest_price': 50000.0,
        'order_id': None,
        'status': 'pending',
        'created_at': 1234567890.0
    }
    
    # Mock ticker to simulate price movement
    mock_exchange_client.get_ticker.side_effect = [
        {'last': 50100.0, 'bid': 50050.0, 'ask': 50150.0},  # Price above activation
        {'last': 50200.0, 'bid': 50150.0, 'ask': 50250.0},  # Price moves up
        {'last': 49400.0, 'bid': 49350.0, 'ask': 49450.0}   # Price drops below stop
    ]
    
    # Start monitoring task
    task = asyncio.create_task(
        order_manager._monitor_trailing_stop(
            order_id, symbol, 'sell', 1.0, 50000.0, 1.0
        )
    )
    
    # Give the task time to run
    await asyncio.sleep(0.3)
    
    # Verify market order was placed when stop triggered
    mock_exchange_client.create_order.assert_called_once()
    call_args = mock_exchange_client.create_order.call_args[1]
    assert call_args['symbol'] == symbol
    assert call_args['type'] == 'market'
    assert call_args['side'] == 'sell'
    assert call_args['amount'] == 1.0
    
    # Verify order status was updated
    assert order_manager.managed_orders[order_id]['status'] == 'filled'
    assert order_manager.managed_orders[order_id]['order_id'] is not None
    
    # Clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass