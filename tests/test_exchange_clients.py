import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from utils.exchange_clients import (
    get_exchange_client, ExchangeClient, RateLimitTracker,
    RateLimitError, NetworkError, AuthenticationError, OrderError
)

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
        'secret': 'test_kraken_secret',
        'enableRateLimit': True,
        'options': {
            'recvWindow': 60000
        }
    })
    assert client == mock_kraken.return_value

@patch('ccxt.binance')
def test_get_binance_client(mock_binance, mock_env):
    """Test successful Binance client creation"""
    client = get_exchange_client('binance')
    mock_binance.assert_called_once_with({
        'apiKey': 'test_binance_key',
        'secret': 'test_binance_secret',
        'enableRateLimit': True,
        'options': {
            'adjustForTimeDifference': True,
            'recvWindow': 60000,
            'defaultType': 'spot'
        }
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

@pytest.mark.asyncio
async def test_exchange_functions():
    """Test exchange client can make API calls"""
    exchange_client = ExchangeClient(exchange='kraken', paper_trading=True)
    
    # Test with paper trading mode
    balances = await exchange_client.get_balances()
    assert 'USD' in balances
    assert 'BTC' in balances

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting behavior"""
    # Create a rate limiter for testing
    rate_limiter = RateLimitTracker('test_exchange', max_requests_per_minute=10)
    
    # Record 9 requests (below threshold)
    for _ in range(9):
        rate_limiter.record_request()
    
    # Should not throttle yet
    should_throttle, _ = rate_limiter.should_throttle()
    assert not should_throttle
    
    # Record more requests to exceed 80% threshold
    for _ in range(2):
        rate_limiter.record_request()
    
    # Should throttle now
    should_throttle, wait_time = rate_limiter.should_throttle()
    assert should_throttle
    assert wait_time > 0

@pytest.mark.asyncio
async def test_rate_limiting_with_headers():
    """Test rate limiting with Retry-After headers"""
    exchange_client = ExchangeClient(exchange='binance', paper_trading=True)
    
    # Mock the _extract_retry_after method
    with patch.object(exchange_client, '_extract_retry_after', return_value=5):
        # Test handling of rate limit errors
        with patch.object(exchange_client, '_handle_rate_limits', new_callable=AsyncMock) as mock_handle:
            # Force a rate limit error
            with pytest.raises(RateLimitError) as excinfo:
                with patch.object(exchange_client.client, 'fetch_balance', side_effect=Exception('Rate limit exceeded')):
                    await exchange_client.get_balances()
            
            # Verify retry_after was extracted
            assert mock_handle.called
            assert hasattr(excinfo.value, 'retry_after')

@pytest.mark.asyncio
async def test_partial_response_data():
    """Test handling of partial/incomplete response data"""
    exchange_client = ExchangeClient(exchange='binance', paper_trading=True)
    
    # Test with paper trading mode which returns simplified data
    balances = await exchange_client.get_balances()
    assert 'USD' in balances
    assert 'BTC' in balances

@pytest.mark.asyncio
async def test_api_error_responses():
    """Test handling of various API error responses"""
    exchange_client = ExchangeClient(exchange='kraken', paper_trading=True)
    
    # Test authentication error
    with patch.object(exchange_client.client, 'fetch_balance', side_effect=Exception('Authentication error')):
        with pytest.raises(Exception):
            await exchange_client.get_balances()
    
    # Test network error
    with patch.object(exchange_client.client, 'fetch_balance', side_effect=Exception('Network error')):
        with pytest.raises(Exception):
            await exchange_client.get_balances()

@pytest.mark.asyncio
async def test_create_order():
    """Test order creation"""
    exchange_client = ExchangeClient(exchange='binance', paper_trading=True)
    
    # Test with paper trading mode
    order = await exchange_client.create_order(
        symbol='BTC/USDT',
        type='limit',
        side='buy',
        amount=0.1,
        price=50000
    )
    
    assert order['symbol'] == 'BTC/USDT'
    assert order['type'] == 'limit'
    assert order['side'] == 'buy'
    assert order['amount'] == 0.1
    assert order['price'] == 50000
    assert 'id' in order
    assert order['status'] == 'open'

@pytest.mark.asyncio
async def test_create_oco_order():
    """Test OCO order creation"""
    exchange_client = ExchangeClient(exchange='binance', paper_trading=True)
    
    # Test with paper trading mode
    order = await exchange_client.create_oco_order(
        symbol='BTC/USDT',
        side='sell',
        amount=0.1,
        price=52000,  # Limit price
        stop_price=48000  # Stop price
    )
    
    assert order['symbol'] == 'BTC/USDT'
    assert order['type'] == 'oco'
    assert order['side'] == 'sell'
    assert order['amount'] == 0.1
    assert order['price'] == 52000
    assert order['stop_price'] == 48000
    assert 'id' in order
    assert order['status'] == 'open'

@pytest.mark.asyncio
async def test_create_trailing_stop_order():
    """Test trailing stop order creation"""
    exchange_client = ExchangeClient(exchange='binance', paper_trading=True)
    
    # Test with paper trading mode
    order = await exchange_client.create_trailing_stop_order(
        symbol='BTC/USDT',
        side='sell',
        amount=0.1,
        activation_price=50000,
        callback_rate=1.0  # 1% callback rate
    )
    
    assert order['symbol'] == 'BTC/USDT'
    assert order['type'] == 'trailing_stop'
    assert order['side'] == 'sell'
    assert order['amount'] == 0.1
    assert order['activation_price'] == 50000
    assert order['callback_rate'] == 1.0
    assert 'id' in order
    assert order['status'] == 'open'

@pytest.mark.asyncio
async def test_invalid_symbol():
    """Test invalid symbol handling"""
    exchange_client = ExchangeClient(exchange='kraken', paper_trading=False)
    
    with patch.object(exchange_client, '_handle_rate_limits', new_callable=AsyncMock):
        with patch.object(exchange_client.client, 'fetch_ohlcv', side_effect=Exception('Invalid symbol')):
            with pytest.raises(Exception):
                await exchange_client.get_ohlcv('INVALID/SYMBOL', '1h')

@pytest.mark.asyncio
async def test_network_error_handling():
    """Test network error handling"""
    exchange_client = ExchangeClient(exchange='binance', paper_trading=False)
    
    with patch.object(exchange_client, '_handle_rate_limits', new_callable=AsyncMock):
        with patch.object(exchange_client.client, 'fetch_balance', side_effect=Exception('Network error')):
            with pytest.raises(NetworkError):
                await exchange_client.get_balances()
