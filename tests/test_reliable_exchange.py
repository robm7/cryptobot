import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from trade.utils.exchange import ReliableExchangeWrapper, get_exchange
from utils.exchange_interface import ExchangeInterface
from .retry import RetryableError
from .circuit_breaker import CircuitState
import os

@pytest.fixture
def mock_exchange():
    exchange = AsyncMock(spec=ExchangeInterface)
    exchange.exchange_id = "binance"
    return exchange

@pytest.fixture
def reliable_exchange(mock_exchange):
    return ReliableExchangeWrapper(mock_exchange)

@pytest.mark.asyncio
async def test_get_balance_success(reliable_exchange, mock_exchange):
    """Test successful balance retrieval"""
    mock_exchange.get_balance.return_value = 100.0
    balance = await reliable_exchange.get_balance("BTC")
    assert balance == 100.0
    mock_exchange.get_balance.assert_awaited_once_with("BTC")

@pytest.mark.asyncio
async def test_get_balance_circuit_breaker_open(reliable_exchange):
    """Test circuit breaker blocking requests when open"""
    reliable_exchange.circuit_breaker.trip()
    with pytest.raises(Exception, match="Circuit breaker open"):
        await reliable_exchange.get_balance("BTC")

@pytest.mark.asyncio
async def test_create_order_success(reliable_exchange, mock_exchange):
    """Test successful order creation"""
    mock_exchange.create_order.return_value = {
        "id": "123", 
        "filled": 0.1,
        "amount": 0.1,
        "price": 50000,
        "average": 50001
    }
    order = await reliable_exchange.create_order(
        "BTC/USDT", "buy", "market", 0.1
    )
    assert order["id"] == "123"
    mock_exchange.create_order.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_order_retry(reliable_exchange, mock_exchange):
    """Test retry behavior on transient errors"""
    mock_exchange.create_order.side_effect = [
        RetryableError("Timeout"),
        {"id": "123", "filled": 0.1}
    ]
    order = await reliable_exchange.create_order(
        "BTC/USDT", "buy", "market", 0.1
    )
    assert order["id"] == "123"
    assert mock_exchange.create_order.call_count == 2

@pytest.mark.asyncio
async def test_place_order_validation(reliable_exchange, mock_exchange):
    """Test order validation in place_order"""
    mock_exchange.place_order.return_value = {
        "id": "123", 
        "status": "open"
    }
    order = await reliable_exchange.place_order(
        "BTC/USDT", "buy", "limit", 0.1, 50000
    )
    assert order["id"] == "123"

@pytest.mark.asyncio
async def test_get_ticker_success(reliable_exchange, mock_exchange):
    """Test successful ticker retrieval"""
    mock_exchange.get_ticker.return_value = {
        "bid": 50000,
        "ask": 50001,
        "last": 50000.5
    }
    ticker = await reliable_exchange.get_ticker("BTC/USDT")
    assert ticker["last"] == 50000.5

def test_get_exchange_factory_mock():
    """Test factory function with mock exchange"""
    with patch.dict(os.environ, {}):
        exchange = get_exchange(mock=True)
        assert isinstance(exchange._exchange, MockExchangeInterface)

def test_get_exchange_factory_real(monkeypatch):
    """Test factory function with real exchange (requires env vars)"""
    monkeypatch.setenv("BINANCE_API_KEY", "test-key")
    monkeypatch.setenv("BINANCE_SECRET_KEY", "test-secret")
    exchange = get_exchange("binance")
    assert isinstance(exchange, ReliableExchangeWrapper)

@pytest.mark.asyncio
async def test_error_handling_metrics(reliable_exchange, mock_exchange):
    """Test error handling records appropriate metrics"""
    mock_exchange.get_balance.side_effect = RetryableError("API Error")
    with pytest.raises(RetryableError):
        await reliable_exchange.get_balance("BTC")
    assert reliable_exchange.circuit_breaker.error_count == 1
    assert reliable_exchange.circuit_breaker.state == CircuitState.HALF_OPEN

@pytest.mark.asyncio
async def test_performance_boundaries(reliable_exchange, mock_exchange):
    """Test performance boundaries with large order sizes"""
    mock_exchange.create_order.return_value = {
        "id": "123",
        "filled": 1000,
        "amount": 1000
    }
    order = await reliable_exchange.create_order(
        "BTC/USDT", "buy", "market", 1000
    )
    assert order["filled"] == 1000