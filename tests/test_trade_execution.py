import pytest
from unittest.mock import AsyncMock, patch
from fastapi import status
from httpx import AsyncClient
from trade.routers.trades import router
from trade.schemas.trade import MarketOrder, LimitOrder
from trade.services.risk import RiskService

@pytest.fixture
def mock_exchange():
    with patch('trade.utils.exchange_interface.ExchangeInterface') as mock:
        exchange = AsyncMock()
        mock.get_exchange.return_value = exchange
        yield exchange

@pytest.fixture
def mock_risk():
    with patch('trade.services.risk.RiskService.validate_order') as mock:
        yield mock

@pytest.mark.asyncio
async def test_create_market_order_success(client: AsyncClient, mock_exchange, mock_risk):
    """Test successful market order creation"""
    order_data = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": "0.1",
        "type": "market"
    }
    
    mock_exchange.create_market_order.return_value = {
        "id": "12345",
        "status": "open"
    }
    
    response = await client.post(
        "/api/orders",
        json=order_data,
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == "12345"
    mock_risk.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_limit_order_success(client: AsyncClient, mock_exchange, mock_risk):
    """Test successful limit order creation"""
    order_data = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": "0.1",
        "price": "50000",
        "type": "limit"
    }
    
    mock_exchange.create_limit_order.return_value = {
        "id": "12345",
        "status": "open"
    }
    
    response = await client.post(
        "/api/orders",
        json=order_data,
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["id"] == "12345"
    mock_risk.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_order_status_success(client: AsyncClient, mock_exchange):
    """Test successful order status retrieval"""
    mock_exchange.get_order_status.return_value = {
        "id": "12345",
        "status": "partial",
        "filled": "0.05"
    }
    
    response = await client.get(
        "/api/orders/12345?exchange=binance",
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "partial"

@pytest.mark.asyncio
async def test_cancel_order_success(client: AsyncClient, mock_exchange):
    """Test successful order cancellation"""
    mock_exchange.cancel_order.return_value = {
        "id": "12345",
        "status": "canceled"
    }
    
    response = await client.delete(
        "/api/orders/12345?exchange=binance",
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "canceled"

@pytest.mark.asyncio
async def test_order_risk_validation_failure(client: AsyncClient, mock_risk):
    """Test order rejection due to risk validation"""
    mock_risk.side_effect = ValueError("Order size exceeds maximum allowed")
    
    order_data = {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": "100000",
        "type": "market"
    }
    
    response = await client.post(
        "/api/orders",
        json=order_data,
        headers={"X-API-KEY": "test-key"}
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Order size exceeds" in response.json()["detail"]