import pytest
import os
from unittest.mock import patch, MagicMock
from utils.exchange_clients import get_exchange_client

@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to mock environment variables"""
    monkeypatch.setenv("KRAKEN_API_KEY", "test_kraken_key")
    monkeypatch.setenv("KRAKEN_API_SECRET", "test_kraken_secret")
    monkeypatch.setenv("BINANCE_API_KEY", "test_binance_key")
    monkeypatch.setenv("BINANCE_API_SECRET", "test_binance_secret")

@patch('ccxt.kraken')
def test_get_kraken_client(mock_kraken, mock_env):
    """Test successful Kraken client creation"""
    client = get_exchange_client('kraken')
    mock_kraken.assert_called_once_with({
        'apiKey': 'test_kraken_key',
        'secret': 'test_kraken_secret'
    })
    assert client == mock_kraken.return_value

@patch('ccxt.binance') 
def test_get_binance_client(mock_binance, mock_env):
    """Test successful Binance client creation"""
    client = get_exchange_client('binance')
    mock_binance.assert_called_once_with({
        'apiKey': 'test_binance_key',
        'secret': 'test_binance_secret',
        'options': {'adjustForTimeDifference': True}
    })
    assert client == mock_binance.return_value

def test_missing_kraken_credentials(monkeypatch):
    """Test missing Kraken credentials raises error"""
    monkeypatch.delenv("KRAKEN_API_KEY", raising=False)
    monkeypatch.delenv("KRAKEN_API_SECRET", raising=False)
    with pytest.raises(ValueError, match="KRAKEN_API_KEY"):
        get_exchange_client('kraken')

def test_missing_binance_credentials():
    """Test missing Binance credentials raises error"""
    with pytest.raises(ValueError, match="BINANCE_API_KEY"):
        get_exchange_client('binance')

def test_unsupported_exchange():
    """Test unsupported exchange raises error"""
    with pytest.raises(ValueError, match="Unsupported exchange"):
        get_exchange_client('unsupported')

@patch('ccxt.kraken')
def test_exchange_functions(mock_kraken, mock_env):
    """Test exchange client can make API calls"""
    mock_client = MagicMock()
    mock_kraken.return_value = mock_client
    mock_client.fetch_balance.return_value = {'free': {'BTC': 1.0}}
    
    client = get_exchange_client('kraken')
    balance = client.fetch_balance()
    
    assert balance == {'free': {'BTC': 1.0}}
    mock_client.fetch_balance.assert_called_once()


@patch('ccxt.kraken')
def test_rate_limiting(mock_kraken, mock_env):
    """Test rate limiting behavior"""
    mock_client = MagicMock()
    mock_kraken.return_value = mock_client
    mock_client.fetch_balance.side_effect = [
        Exception('Rate limit exceeded'),
        {'free': {'BTC': 1.0}}
    ]
    
    client = get_exchange_client('kraken')
    
    # First call should fail
    with pytest.raises(Exception, match='Rate limit exceeded'):
        client.fetch_balance()
    
    # Second call should succeed after delay
    balance = client.fetch_balance()
    assert balance == {'free': {'BTC': 1.0}}
    assert mock_client.fetch_balance.call_count == 2

@patch('ccxt.binance')
def test_rate_limiting_with_headers(mock_binance, mock_env):
    """Test rate limiting with Retry-After headers"""
    mock_client = MagicMock()
    mock_binance.return_value = mock_client
    
    # Create a mock HTTP response with headers
    response = MagicMock()
    response.status_code = 429
    response.headers = {'Retry-After': '5'}
    response.json.return_value = {'code': -1003, 'msg': 'Too many requests'}
    
    mock_client.fetch_balance.side_effect = [
        Exception(response),
        {'free': {'BTC': 1.0}}
    ]
    
    client = get_exchange_client('binance')
    
    # First call should fail with rate limit
    with pytest.raises(Exception):
        client.fetch_balance()

@patch('ccxt.binance')
def test_partial_response_data(mock_binance, mock_env):
    """Test handling of partial/incomplete response data"""
    mock_client = MagicMock()
    mock_binance.return_value = mock_client
    
    # Test partial balance response
    mock_client.fetch_balance.return_value = {'free': {'BTC': 1.0}}  # Missing 'used' and 'total'
    client = get_exchange_client('binance')
    balance = client.fetch_balance()
    assert balance == {'free': {'BTC': 1.0}}
    
    # Test partial order book
    mock_client.fetch_order_book.return_value = {
        'bids': [[50000, 1.0]],
        'asks': [[51000, 1.5]],
        # Missing 'timestamp' and 'nonce'
    }
    order_book = client.fetch_order_book('BTC/USDT')
    assert len(order_book['bids']) == 1
    assert len(order_book['asks']) == 1
    
    # Test partial trade history
    mock_client.fetch_trades.return_value = [{
        'id': '12345',
        'price': 50000,
        'amount': 0.1,
        # Missing 'side' and 'timestamp'
    }]
    trades = client.fetch_trades('BTC/USDT')
    assert len(trades) == 1
    assert trades[0]['price'] == 50000

@patch('ccxt.kraken')
def test_websocket_connection(mock_kraken, mock_env):
    """Test websocket connection handling"""
    mock_client = MagicMock()
    mock_kraken.return_value = mock_client
    
    # Test successful connection
    mock_client.websocket_connect.return_value = True
    client = get_exchange_client('kraken')
    assert client.websocket_connect() is True
    
    # Test connection failure
    mock_client.websocket_connect.side_effect = Exception('Connection failed')
    with pytest.raises(Exception, match='Connection failed'):
        client.websocket_connect()
    
    # Test reconnection
    mock_client.websocket_connect.side_effect = [
        Exception('First attempt failed'),
        True
    ]
    assert client.websocket_connect() is True
    assert mock_client.websocket_connect.call_count == 2
    
    # Second call should succeed after delay
    balance = client.fetch_balance()
    assert balance == {'free': {'BTC': 1.0}}
    assert mock_client.fetch_balance.call_count == 2

@patch('ccxt.kraken')
def test_api_error_responses(mock_kraken, mock_env):
    """Test handling of various API error responses"""
    mock_client = MagicMock()
    mock_kraken.return_value = mock_client
    
    # Test 400 Bad Request
    mock_client.fetch_balance.side_effect = Exception('400 Bad Request')
    client = get_exchange_client('kraken')
    with pytest.raises(Exception, match='400 Bad Request'):
        client.fetch_balance()
    
    # Test 401 Unauthorized
    mock_client.fetch_balance.side_effect = Exception('401 Unauthorized')
    with pytest.raises(Exception, match='401 Unauthorized'):
        client.fetch_balance()
    
    # Test 403 Forbidden
    mock_client.fetch_balance.side_effect = Exception('403 Forbidden')
    with pytest.raises(Exception, match='403 Forbidden'):
        client.fetch_balance()
    
    # Test 500 Internal Server Error
    mock_client.fetch_balance.side_effect = Exception('500 Internal Server Error')
    with pytest.raises(Exception, match='500 Internal Server Error'):
        client.fetch_balance()

@patch('ccxt.binance')
def test_create_order(mock_binance, mock_env):
    """Test order creation"""
    mock_client = MagicMock()
    mock_binance.return_value = mock_client
    mock_client.create_order.return_value = {
        'id': '12345',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'amount': 0.1,
        'price': 50000
    }
    
    client = get_exchange_client('binance')
    order = client.create_order(
        symbol='BTC/USDT',
        type='limit',
        side='buy',
        amount=0.1,
        price=50000
    )
    
    assert order['id'] == '12345'
    mock_client.create_order.assert_called_once_with(
        symbol='BTC/USDT',
        type='limit',
        side='buy',
        amount=0.1,
        price=50000
    )

@patch('ccxt.kraken')
def test_invalid_symbol(mock_kraken, mock_env):
    """Test invalid symbol handling"""
    mock_client = MagicMock()
    mock_kraken.return_value = mock_client
    mock_client.fetch_ohlcv.side_effect = Exception('Invalid symbol')
    
    client = get_exchange_client('kraken')
    with pytest.raises(Exception, match='Invalid symbol'):
        client.fetch_ohlcv('INVALID/SYMBOL', '1h')

@patch('ccxt.binance')
def test_network_error_handling(mock_binance, mock_env):
    """Test network error handling"""
    mock_client = MagicMock()
    mock_binance.return_value = mock_client
    mock_client.fetch_balance.side_effect = Exception('Network error')
    
    client = get_exchange_client('binance')
    with pytest.raises(Exception, match='Network error'):
        client.fetch_balance()
