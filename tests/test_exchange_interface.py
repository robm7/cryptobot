import pytest
import os
from unittest.mock import patch, MagicMock
from utils.exchange_interface import MockExchangeInterface, CcxtExchangeInterface

@pytest.fixture
def mock_interface():
    """Provides a fresh MockExchangeInterface for each test."""
    # Reset class variables before each test to ensure isolation
    MockExchangeInterface._orders = {}
    MockExchangeInterface._order_id_counter = 1
    MockExchangeInterface._balances = {'USDT': 10000.0, 'BTC': 1.0}
    return MockExchangeInterface(testnet=True)

@pytest.fixture
def binance_interface():
    """Provides a Binance CcxtExchangeInterface with test API keys."""
    return CcxtExchangeInterface(
        api_key=os.getenv('BINANCE_API_KEY', 'test_key'),
        api_secret=os.getenv('BINANCE_SECRET_KEY', 'test_secret'),
        testnet=True
    )

@pytest.mark.asyncio
async def test_place_market_buy_order(mock_interface: MockExchangeInterface, binance_interface: CcxtExchangeInterface):
    symbol = 'BTCUSDT'
    amount = 0.1
    
    # Test with mock interface
    initial_usdt = mock_interface._balances['USDT']
    initial_btc = mock_interface._balances['BTC']
    order = await mock_interface.place_order(symbol, 'market', 'buy', amount)
    assert order['symbol'] == symbol
    assert order['type'] == 'market'
    assert order['side'] == 'buy'
    assert order['amount'] == amount
    assert order['status'] == 'filled'
    assert order['id'] == '1'
    expected_cost = amount * 30000
    assert mock_interface._balances['USDT'] == initial_usdt - expected_cost
    assert mock_interface._balances['BTC'] == initial_btc + amount
    assert len(mock_interface._orders) == 1

    # Test with Binance interface (mocked)
    with patch('ccxt.async_support.binance') as mock_binance:
        mock_binance.return_value.create_order.return_value = {
            'id': 'binance123',
            'symbol': symbol,
            'type': 'market',
            'side': 'buy',
            'amount': amount,
            'status': 'filled'
        }
        order = await binance_interface.place_order(symbol, 'market', 'buy', amount)
        assert order['id'] == 'binance123'
        assert order['symbol'] == symbol
        assert order['type'] == 'market'
        assert order['side'] == 'buy'

@pytest.mark.asyncio
async def test_place_limit_sell_order(mock_interface: MockExchangeInterface):
    symbol = 'BTCUSDT'
    amount = 0.05
    price = 31000.0
    initial_usdt = mock_interface._balances['USDT']
    initial_btc = mock_interface._balances['BTC']

    order = await mock_interface.place_order(symbol, 'limit', 'sell', amount, price)

    assert order['symbol'] == symbol
    assert order['type'] == 'limit'
    assert order['side'] == 'sell'
    assert order['amount'] == amount
    assert order['price'] == price
    assert order['status'] == 'open' # Limit orders remain open in mock
    assert order['id'] == '1'

    # Balance should not change until filled
    assert mock_interface._balances['USDT'] == initial_usdt
    assert mock_interface._balances['BTC'] == initial_btc
    assert len(mock_interface._orders) == 1
    assert mock_interface._orders['1'] == order

@pytest.mark.asyncio
async def test_cancel_open_order(mock_interface: MockExchangeInterface):
    # Place an order first
    order = await mock_interface.place_order('ETHUSDT', 'limit', 'buy', 1.0, 2000.0)
    order_id = order['id']
    assert mock_interface._orders[order_id]['status'] == 'open'

    # Cancel the order
    cancel_result = await mock_interface.cancel_order(order_id)

    assert cancel_result['status'] == 'success'
    assert cancel_result['order_id'] == order_id
    assert mock_interface._orders[order_id]['status'] == 'canceled'

@pytest.mark.asyncio
async def test_cancel_filled_order(mock_interface: MockExchangeInterface):
    # Place and fill a market order
    order = await mock_interface.place_order('BTCUSDT', 'market', 'buy', 0.01)
    order_id = order['id']
    assert mock_interface._orders[order_id]['status'] == 'filled'

    # Attempt to cancel the filled order
    cancel_result = await mock_interface.cancel_order(order_id)

    assert cancel_result['status'] == 'error'
    assert 'not open' in cancel_result['message'].lower()
    assert mock_interface._orders[order_id]['status'] == 'filled' # Status remains filled

@pytest.mark.asyncio
async def test_cancel_nonexistent_order(mock_interface: MockExchangeInterface):
    cancel_result = await mock_interface.cancel_order('nonexistent-id')
    assert cancel_result['status'] == 'error'
    assert 'not found' in cancel_result['message'].lower()

@pytest.mark.asyncio
async def test_get_order_status_open(mock_interface: MockExchangeInterface):
    order = await mock_interface.place_order('ETHUSDT', 'limit', 'buy', 1.0, 2000.0)
    order_id = order['id']

    status = await mock_interface.get_order_status(order_id)
    assert status == order
    assert status['status'] == 'open'

@pytest.mark.asyncio
async def test_get_order_status_filled(mock_interface: MockExchangeInterface):
    order = await mock_interface.place_order('BTCUSDT', 'market', 'sell', 0.01)
    order_id = order['id']

    status = await mock_interface.get_order_status(order_id)
    assert status['id'] == order_id
    assert status['status'] == 'filled'

@pytest.mark.asyncio
async def test_get_order_status_canceled(mock_interface: MockExchangeInterface):
    order = await mock_interface.place_order('ETHUSDT', 'limit', 'buy', 1.0, 2000.0)
    order_id = order['id']
    await mock_interface.cancel_order(order_id)

    status = await mock_interface.get_order_status(order_id)
    assert status['id'] == order_id
    assert status['status'] == 'canceled'

@pytest.mark.asyncio
async def test_get_order_status_nonexistent(mock_interface: MockExchangeInterface):
    status = await mock_interface.get_order_status('nonexistent-id')
    assert status['status'] == 'error'
    assert 'not found' in status['message'].lower()

@pytest.mark.asyncio
async def test_get_balance_all(mock_interface: MockExchangeInterface):
    balances = await mock_interface.get_balance()
    assert balances == {'USDT': 10000.0, 'BTC': 1.0}

@pytest.mark.asyncio
async def test_get_balance_specific(mock_interface: MockExchangeInterface):
    usdt_balance = await mock_interface.get_balance('USDT')
    assert usdt_balance == {'USDT': 10000.0}

    btc_balance = await mock_interface.get_balance('BTC')
    assert btc_balance == {'BTC': 1.0}

@pytest.mark.asyncio
async def test_get_balance_zero(mock_interface: MockExchangeInterface):
    eth_balance = await mock_interface.get_balance('ETH')
    assert eth_balance == {'ETH': 0.0}

@pytest.mark.asyncio
async def test_get_open_orders_none(mock_interface: MockExchangeInterface):
    # Place only a market order (which fills immediately)
    await mock_interface.place_order('BTCUSDT', 'market', 'buy', 0.01)
    open_orders = await mock_interface.get_open_orders()
    assert open_orders == []

@pytest.mark.asyncio
async def test_get_open_orders_multiple(mock_interface: MockExchangeInterface):
    order1 = await mock_interface.place_order('ETHUSDT', 'limit', 'buy', 1.0, 2000.0)
    order2 = await mock_interface.place_order('BTCUSDT', 'limit', 'sell', 0.1, 32000.0)
    await mock_interface.place_order('LTCUSDT', 'market', 'buy', 5.0) # Filled

    open_orders = await mock_interface.get_open_orders()
    assert len(open_orders) == 2
    # Order might not be guaranteed, check contents
    order_ids = {o['id'] for o in open_orders}
    assert order1['id'] in order_ids
    assert order2['id'] in order_ids
    assert all(o['status'] == 'open' for o in open_orders)

@pytest.mark.asyncio
async def test_get_open_orders_filtered(mock_interface: MockExchangeInterface):
    order_eth = await mock_interface.place_order('ETHUSDT', 'limit', 'buy', 1.0, 2000.0)
    await mock_interface.place_order('BTCUSDT', 'limit', 'sell', 0.1, 32000.0)

    open_eth_orders = await mock_interface.get_open_orders(symbol='ETHUSDT')
    assert len(open_eth_orders) == 1
    assert open_eth_orders[0]['id'] == order_eth['id']
    assert open_eth_orders[0]['symbol'] == 'ETHUSDT'

    open_ltc_orders = await mock_interface.get_open_orders(symbol='LTCUSDT')
    assert open_ltc_orders == []

@pytest.mark.asyncio
async def test_rate_limiting(mock_interface: MockExchangeInterface, binance_interface: CcxtExchangeInterface):
    """Test rate limiting behavior"""
    # Test with mock interface
    balance1 = await mock_interface.get_balance()
    assert balance1 == {'USDT': 10000.0, 'BTC': 1.0}
    
    mock_interface._rate_limited = True
    with pytest.raises(Exception, match='Rate limit exceeded'):
        await mock_interface.get_balance()
    
    mock_interface._rate_limited = False
    balance3 = await mock_interface.get_balance()
    assert balance3 == {'USDT': 10000.0, 'BTC': 1.0}

    # Test with Binance interface (mocked)
    with patch('ccxt.async_support.binance') as mock_binance:
        # First call succeeds
        mock_binance.return_value.fetch_balance.return_value = {'USDT': 10000.0, 'BTC': 1.0}
        balance = await binance_interface.get_balance()
        assert balance == {'USDT': 10000.0, 'BTC': 1.0}

        # Second call hits rate limit
        mock_binance.return_value.fetch_balance.side_effect = Exception('Rate limit exceeded')
        with pytest.raises(Exception, match='Rate limit exceeded'):
            await binance_interface.get_balance()

@pytest.mark.asyncio
async def test_api_error_responses(mock_interface: MockExchangeInterface, binance_interface: CcxtExchangeInterface):
    """Test handling of various API error responses"""
    # Test with mock interface
    mock_interface._force_error = '400 Bad Request'
    with pytest.raises(Exception, match='400 Bad Request'):
        await mock_interface.get_balance()
    
    mock_interface._force_error = '401 Unauthorized'
    with pytest.raises(Exception, match='401 Unauthorized'):
        await mock_interface.get_balance()
    
    mock_interface._force_error = '403 Forbidden'
    with pytest.raises(Exception, match='403 Forbidden'):
        await mock_interface.get_balance()
    
    mock_interface._force_error = '500 Internal Server Error'
    with pytest.raises(Exception, match='500 Internal Server Error'):
        await mock_interface.get_balance()
    
    mock_interface._force_error = None
    balance = await mock_interface.get_balance()
    assert balance == {'USDT': 10000.0, 'BTC': 1.0}

    # Test with Binance interface (mocked)
    with patch('ccxt.async_support.binance') as mock_binance:
        # Test Binance-specific errors
        mock_binance.return_value.fetch_balance.side_effect = Exception('Binance API error: Invalid API key')
        with pytest.raises(Exception, match='Invalid API key'):
            await binance_interface.get_balance()

        mock_binance.return_value.fetch_balance.side_effect = Exception('Binance API error: IP banned')
        with pytest.raises(Exception, match='IP banned'):
            await binance_interface.get_balance()

        # Test successful call after errors
        mock_binance.return_value.fetch_balance.side_effect = None
        mock_binance.return_value.fetch_balance.return_value = {'USDT': 10000.0, 'BTC': 1.0}
        balance = await binance_interface.get_balance()
        assert balance == {'USDT': 10000.0, 'BTC': 1.0}

@pytest.mark.asyncio
async def test_partial_response_data(mock_interface: MockExchangeInterface):
    """Test handling of partial/incomplete response data"""
    # Test partial balance response
    mock_interface._balances = {'USDT': 10000.0}  # Missing BTC balance
    balance = await mock_interface.get_balance()
    assert balance == {'USDT': 10000.0}
    
    # Test partial order response
    mock_interface._orders = {
        '1': {
            'id': '1',
            'symbol': 'BTCUSDT',
            'side': 'buy',
            # Missing 'type' and 'status'
        }
    }
    order = await mock_interface.get_order_status('1')
    assert order['id'] == '1'
    assert order['symbol'] == 'BTCUSDT'
    
    # Reset to full data
    mock_interface._balances = {'USDT': 10000.0, 'BTC': 1.0}
    mock_interface._orders = {}

@pytest.mark.asyncio
async def test_websocket_connection(mock_interface: MockExchangeInterface, binance_interface: CcxtExchangeInterface):
    """Test websocket connection handling"""
    # Test with mock interface
    mock_interface._websocket_connected = True
    assert await mock_interface.websocket_connect() is True
    
    mock_interface._websocket_should_fail = True
    with pytest.raises(Exception, match='WebSocket connection failed'):
        await mock_interface.websocket_connect()
    
    mock_interface._websocket_should_fail = False
    assert await mock_interface.websocket_connect() is True

    # Test with Binance interface (mocked)
    with patch('ccxt.async_support.binance') as mock_binance:
        # Test successful websocket connection
        mock_binance.return_value.has = {'websocket': True}
        mock_binance.return_value.websocket_connect.return_value = True
        assert await binance_interface.websocket_connect() is True

        # Test websocket connection failure
        mock_binance.return_value.websocket_connect.side_effect = Exception('WebSocket error')
        with pytest.raises(Exception, match='WebSocket error'):
            await binance_interface.websocket_connect()

@pytest.mark.asyncio
async def test_order_book_depth(mock_interface: MockExchangeInterface, binance_interface: CcxtExchangeInterface):
    """Test order book depth scenarios"""
    # Test with mock interface
    mock_interface._order_book = {'bids': [], 'asks': []}
    book = await mock_interface.get_order_book('BTCUSDT')
    assert book['bids'] == []
    assert book['asks'] == []
    
    mock_interface._order_book = {
        'bids': [[50000, 1.0]],
        'asks': [[51000, 1.5]]
    }
    book = await mock_interface.get_order_book('BTCUSDT')
    assert len(book['bids']) == 1
    assert len(book['asks']) == 1
    
    mock_interface._order_book = {
        'bids': [[50000, 1.0], [49900, 2.0], [49800, 3.0]],
        'asks': [[51000, 1.5], [51100, 2.5], [51200, 3.5]]
    }
    book = await mock_interface.get_order_book('BTCUSDT')
    assert len(book['bids']) == 3
    assert len(book['asks']) == 3

    # Test with Binance interface (mocked)
    with patch('ccxt.async_support.binance') as mock_binance:
        # Test Binance order book depth
        mock_binance.return_value.fetch_order_book.return_value = {
            'bids': [[50000, 1.0], [49900, 2.0]],
            'asks': [[51000, 1.5], [51100, 2.5]],
            'symbol': 'BTCUSDT'
        }
        book = await binance_interface.get_order_book('BTCUSDT')
        assert len(book['bids']) == 2
        assert len(book['asks']) == 2
        assert book['symbol'] == 'BTCUSDT'

        # Test Binance order book with depth limit
        mock_binance.return_value.fetch_order_book.return_value = {
            'bids': [[50000, 1.0]],
            'asks': [[51000, 1.5]],
            'symbol': 'BTCUSDT'
        }
        book = await binance_interface.get_order_book('BTCUSDT', {'limit': 1})
        assert len(book['bids']) == 1
        assert len(book['asks']) == 1

@pytest.mark.asyncio
async def test_binance_testnet_connectivity(binance_interface: CcxtExchangeInterface):
    """Test Binance testnet connectivity"""
    with patch('ccxt.async_support.binance') as mock_binance:
        # Verify testnet URL is used
        mock_binance.return_value.urls = {'api': 'https://testnet.binance.vision'}
        interface = CcxtExchangeInterface(
            api_key='test_key',
            api_secret='test_secret',
            testnet=True
        )
        assert 'testnet' in interface.exchange.urls['api']

        # Test testnet-specific behavior
        mock_binance.return_value.fetch_balance.return_value = {'USDT': 10000.0}
        balance = await interface.get_balance()
        assert balance == {'USDT': 10000.0}

@pytest.mark.asyncio
async def test_binance_specific_error_handling(binance_interface: CcxtExchangeInterface):
    """Test Binance-specific error handling"""
    with patch('ccxt.async_support.binance') as mock_binance:
        # Test Binance's "Too many requests" error
        mock_binance.return_value.create_order.side_effect = Exception('Binance API error: Too many requests')
        with pytest.raises(Exception, match='Too many requests'):
            await binance_interface.place_order('BTCUSDT', 'market', 'buy', 0.1)

        # Test Binance's "Timestamp for this request was 1000ms ahead" error
        mock_binance.return_value.create_order.side_effect = Exception('Binance API error: Timestamp for this request was 1000ms ahead')
        with pytest.raises(Exception, match='Timestamp'):
            await binance_interface.place_order('BTCUSDT', 'market', 'buy', 0.1)

        # Test successful retry after error
        mock_binance.return_value.create_order.side_effect = None
        mock_binance.return_value.create_order.return_value = {
            'id': 'binance123',
            'symbol': 'BTCUSDT',
            'type': 'market',
            'side': 'buy',
            'amount': 0.1,
            'status': 'filled'
        }
        order = await binance_interface.place_order('BTCUSDT', 'market', 'buy', 0.1)
        assert order['id'] == 'binance123'

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_high_error_rate(mock_interface: MockExchangeInterface):
    """Test circuit breaker opens when error rate exceeds threshold"""
    # Simulate errors to trigger circuit breaker
    for _ in range(10):
        mock_interface.error_window.append(1)  # Record errors
    
    # Should open circuit
    assert mock_interface._check_circuit_breaker() is True
    assert mock_interface.circuit_open is True
    assert mock_interface.circuit_open_time is not None

@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_timeout(mock_interface: MockExchangeInterface):
    """Test circuit breaker closes after timeout period"""
    mock_interface.circuit_open = True
    mock_interface.circuit_open_time = time.time() - 61  # 1 second past timeout
    
    assert mock_interface._is_circuit_open() is False
    assert mock_interface.circuit_open is False

@pytest.mark.asyncio
async def test_place_order_with_retry_success(mock_interface: MockExchangeInterface):
    """Test successful order placement with retries"""
    with patch.object(mock_interface, 'place_order', new_callable=AsyncMock) as mock_place:
        mock_place.return_value = {'id': '123', 'status': 'filled'}
        order = await mock_interface.place_order_with_retry(
            'BTCUSDT', 'market', 'buy', 0.1
        )
        assert order['id'] == '123'
        mock_place.assert_called_once()

@pytest.mark.asyncio
async def test_place_order_with_retry_failure(mock_interface: MockExchangeInterface):
    """Test order placement fails after max retries"""
    with patch.object(mock_interface, 'place_order', new_callable=AsyncMock) as mock_place:
        mock_place.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            await mock_interface.place_order_with_retry(
                'BTCUSDT', 'market', 'buy', 0.1,
                max_retries=3
            )
        assert mock_place.call_count == 3

@pytest.mark.asyncio
async def test_verify_order_execution_success(mock_interface: MockExchangeInterface):
    """Test successful order execution verification"""
    with patch.object(mock_interface, 'get_order_status', new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {'status': 'closed'}
        result = await mock_interface.verify_order_execution('123', 'BTCUSDT')
        assert result is True

@pytest.mark.asyncio
async def test_verify_order_execution_failure(mock_interface: MockExchangeInterface):
    """Test failed order execution verification"""
    with patch.object(mock_interface, 'get_order_status', new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {'status': 'open'}
        result = await mock_interface.verify_order_execution('123', 'BTCUSDT')
        assert result is False

@pytest.mark.asyncio
async def test_metrics_collection(mock_interface: MockExchangeInterface):
    """Test Prometheus metrics are collected correctly"""
    # Reset metrics
    for metric in REGISTRY.collect():
        REGISTRY.unregister(metric)
    
    # Import metrics again to reset them
    from utils.exchange_interface import (
        ORDER_ATTEMPTS, ORDER_SUCCESS, ORDER_FAILURES,
        ORDER_LATENCY, CIRCUIT_STATE, ERROR_RATE
    )
    
    # Simulate order attempts
    with patch.object(mock_interface, 'place_order', new_callable=AsyncMock):
        # Successful order
        mock_interface.place_order.return_value = {'id': '1', 'status': 'filled'}
        await mock_interface.place_order_with_retry('BTCUSDT', 'market', 'buy', 0.1)
        
        # Failed order
        mock_interface.place_order.side_effect = Exception("API error")
        with pytest.raises(Exception):
            await mock_interface.place_order_with_retry('BTCUSDT', 'market', 'buy', 0.1)
    
    # Check metrics
    assert ORDER_ATTEMPTS.labels(symbol='BTCUSDT', side='buy')._value.get() == 2
    assert ORDER_SUCCESS.labels(symbol='BTCUSDT', side='buy')._value.get() == 1
    assert ORDER_FAILURES.labels(symbol='BTCUSDT', side='buy')._value.get() == 1
    assert CIRCUIT_STATE._value.get() == 0
    assert ERROR_RATE._value.get() == 50.0  # 1 success, 1 failure = 50% error rate

@pytest.mark.asyncio
async def test_performance_boundary_large_order(mock_interface: MockExchangeInterface):
    """Test handling of very large orders"""
    # Test max order size
    max_size = 10000  # Assuming this is MAX_ORDER_SIZE
    order = await mock_interface.place_order(
        'BTCUSDT', 'market', 'buy', max_size * 1.1  # Exceeds max
    )
    assert order['amount'] == max_size  # Should be capped

@pytest.mark.asyncio
async def test_performance_boundary_small_order(mock_interface: MockExchangeInterface):
    """Test handling of very small orders"""
    # Test min order size
    order = await mock_interface.place_order(
        'BTCUSDT', 'market', 'buy', 0.00000001  # Very small
    )
    assert order['amount'] >= 0.000001  # Should meet exchange minimum

@pytest.mark.asyncio
async def test_error_rate_monitoring(mock_interface: MockExchangeInterface):
    """Test error rate monitoring and alert thresholds"""
    # Simulate errors to reach alert threshold
    for _ in range(10):
        mock_interface.error_window.append(1)  # Record errors
    
    error_rate = sum(mock_interface.error_window) / len(mock_interface.error_window)
    assert error_rate > 0.5  # Should trigger circuit breaker
    assert mock_interface._check_circuit_breaker() is True

@pytest.mark.asyncio
async def test_historical_volatility_integration(mock_interface: MockExchangeInterface):
    """Test integration with historical volatility data"""
    with patch('trade.services.risk.get_historical_volatility') as mock_vol:
        mock_vol.return_value = 0.2  # 20% volatility
        size = await mock_interface.calculate_position_size(
            'BTCUSDT',
            100000,
            volatility_factor=True
        )
        # Should adjust size based on volatility
        assert size < 1000  # Assuming base size would be 1000 without volatility