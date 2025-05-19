import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
import os

# Assuming your trade service app is accessible from trade.main
from trade.main import app as trade_app 
from trade.utils.exceptions import InvalidOrderError, ExchangeError

@pytest.fixture(scope="module")
def client():
    # Set a dummy API key for testing purposes
    os.environ["TRADE_API_KEY"] = "test_trade_api_key"
    return TestClient(trade_app)

@pytest.fixture
def auth_headers():
    return {"X-API-KEY": "test_trade_api_key"}

# Mock for ExchangeInterface and its methods
@pytest.fixture
def mock_exchange_interface():
    with patch('trade.routers.trades.ExchangeInterface.get_exchange') as mock_get_exchange:
        mock_exchange_instance = AsyncMock()
        mock_get_exchange.return_value = mock_exchange_instance
        yield mock_exchange_instance

# Mock for RiskService
@pytest.fixture
def mock_risk_service():
    with patch('trade.routers.trades.RiskService.validate_order', new_callable=AsyncMock) as mock_validate:
        yield mock_validate

def test_create_market_order_success(client, auth_headers, mock_exchange_interface, mock_risk_service):
    mock_risk_service.return_value = None # Simulate successful validation
    mock_exchange_interface.create_market_order = AsyncMock(return_value={
        "id": "market123", "symbol": "BTC/USDT", "type": "MARKET", "side": "BUY",
        "amount": 0.1, "status": "FILLED"
    })

    order_payload = {
        "exchange": "binance", "symbol": "BTC/USDT", "side": "BUY",
        "type": "MARKET", "amount": 0.1
    }
    response = client.post("/api/trades/orders", json=order_payload, headers=auth_headers)
    
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "market123"
    assert data["type"] == "MARKET"
    mock_risk_service.assert_called_once()
    mock_exchange_interface.create_market_order.assert_called_once()

def test_create_limit_order_success(client, auth_headers, mock_exchange_interface, mock_risk_service):
    mock_risk_service.return_value = None # Simulate successful validation
    mock_exchange_interface.create_limit_order = AsyncMock(return_value={
        "id": "limit456", "symbol": "ETH/USDT", "type": "LIMIT", "side": "SELL",
        "amount": 1.0, "price": 3000.0, "status": "NEW"
    })

    order_payload = {
        "exchange": "binance", "symbol": "ETH/USDT", "side": "SELL",
        "type": "LIMIT", "amount": 1.0, "price": 3000.0
    }
    response = client.post("/api/trades/orders", json=order_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "limit456"
    assert data["type"] == "LIMIT"
    mock_risk_service.assert_called_once()
    mock_exchange_interface.create_limit_order.assert_called_once()

def test_create_order_risk_validation_failure(client, auth_headers, mock_risk_service):
    mock_risk_service.side_effect = ValueError("Order exceeds risk limits")

    order_payload = {
        "exchange": "binance", "symbol": "BTC/USDT", "side": "BUY",
        "type": "MARKET", "amount": 100.0 # Large amount likely to fail risk
    }
    response = client.post("/api/trades/orders", json=order_payload, headers=auth_headers)

    assert response.status_code == 400
    assert "Order exceeds risk limits" in response.json()["detail"]
    mock_risk_service.assert_called_once()

def test_create_order_exchange_error(client, auth_headers, mock_exchange_interface, mock_risk_service):
    mock_risk_service.return_value = None
    mock_exchange_interface.create_market_order = AsyncMock(side_effect=ExchangeError("Binance API error"))

    order_payload = {
        "exchange": "binance", "symbol": "BTC/USDT", "side": "BUY",
        "type": "MARKET", "amount": 0.1
    }
    response = client.post("/api/trades/orders", json=order_payload, headers=auth_headers)

    assert response.status_code == 400
    assert "Binance API error" in response.json()["detail"]

def test_get_order_status_success(client, auth_headers, mock_exchange_interface):
    mock_exchange_interface.get_order_status = AsyncMock(return_value={
        "id": "test_order_id", "status": "FILLED", "symbol": "BTC/USDT"
    })

    response = client.get("/api/trades/orders/test_order_id?exchange=binance", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test_order_id"
    assert data["status"] == "FILLED"
    mock_exchange_interface.get_order_status.assert_called_once_with("test_order_id")

def test_get_order_status_not_found(client, auth_headers, mock_exchange_interface):
    mock_exchange_interface.get_order_status = AsyncMock(side_effect=InvalidOrderError("Order not found"))
    
    response = client.get("/api/trades/orders/unknown_id?exchange=binance", headers=auth_headers)

    assert response.status_code == 400 # Based on current router exception handling
    assert "Order not found" in response.json()["detail"]

def test_cancel_order_success(client, auth_headers, mock_exchange_interface):
    mock_exchange_interface.cancel_order = AsyncMock(return_value={
        "id": "test_cancel_id", "status": "CANCELED"
    })

    response = client.delete("/api/trades/orders/test_cancel_id?exchange=binance", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELED"
    mock_exchange_interface.cancel_order.assert_called_once_with("test_cancel_id")

def test_cancel_order_not_found(client, auth_headers, mock_exchange_interface):
    mock_exchange_interface.cancel_order = AsyncMock(side_effect=InvalidOrderError("Cannot cancel, order not found"))

    response = client.delete("/api/trades/orders/unknown_cancel_id?exchange=binance", headers=auth_headers)

    assert response.status_code == 400 # Based on current router exception handling
    assert "Cannot cancel, order not found" in response.json()["detail"]

def test_create_order_missing_api_key(client):
    order_payload = {
        "exchange": "binance", "symbol": "BTC/USDT", "side": "BUY",
        "type": "MARKET", "amount": 0.1
    }
    response = client.post("/api/trades/orders", json=order_payload) # No auth_headers
    assert response.status_code == 403 # FastAPI default for missing APIKeyHeader
    # The actual response might vary based on how `api_key_header` dependency failure is handled by FastAPI
    # It might be 403 Forbidden if the dependency itself fails before our custom 401.
    # If the dependency allows optional and our code checks for os.getenv, it would be 401.
    # Given the current setup, APIKeyHeader will likely cause a 403 if header is missing.

def test_create_order_invalid_api_key(client):
    order_payload = {
        "exchange": "binance", "symbol": "BTC/USDT", "side": "BUY",
        "type": "MARKET", "amount": 0.1
    }
    response = client.post("/api/trades/orders", json=order_payload, headers={"X-API-KEY": "wrong_key"})
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]