import pytest
from fastapi import status, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

# Assuming your FastAPI app is defined in trade.main
from trade.main import app # Import your FastAPI app instance

VALID_TRADE_API_KEY = "test_trade_api_key_general_router"
BASE_URL = "/api/trades/orders" # Assuming this is the prefix from main app

@pytest.fixture(scope="module", autouse=True)
def set_trade_api_key_env(monkeypatch_module):
    monkeypatch_module.setenv("TRADE_API_KEY", VALID_TRADE_API_KEY)
    # Ensure other potentially conflicting exchange-specific keys are not set by default for these general tests
    # or are overridden if necessary by specific test functions or fixtures.
    # For now, we rely on TRADE_API_KEY for router auth.

@pytest.fixture(scope="module")
def client(set_trade_api_key_env): # Ensure env var is set
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_exchange_instance():
    exchange = AsyncMock()
    exchange.create_market_order = AsyncMock(return_value={"id": "mock_market_order_id", "status": "filled"})
    exchange.create_limit_order = AsyncMock(return_value={"id": "mock_limit_order_id", "status": "pending"})
    exchange.get_order_status = AsyncMock(return_value={"id": "some_order_id", "status": "filled"})
    exchange.cancel_order = AsyncMock(return_value=True) # Assuming boolean or simple success indicator
    return exchange

# Tests for POST /orders (create_order)

@pytest.mark.asyncio
async def test_create_market_order_success(client, mock_exchange_instance):
    market_order_payload = {
        "exchange": "mockexchange",
        "symbol": "BTC-USD",
        "side": "buy",
        "type": "market", # Ensure type is explicit if schema requires, or router infers
        "amount": "0.01"
    }
    with patch('trade.routers.trades.RiskService.validate_order', new_callable=AsyncMock) as mock_validate_order, \
         patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:
        
        mock_validate_order.return_value = None # Risk validation passes

        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.post(BASE_URL, json=market_order_payload, headers=headers)

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == "mock_market_order_id"
        assert response_data["status"] == "filled"

        mock_validate_order.assert_called_once()
        mock_get_exchange.assert_called_once_with("mockexchange")
        mock_exchange_instance.create_market_order.assert_called_once_with(
            symbol="BTC-USD", side="buy", amount=0.01 # Pydantic model might convert amount
        )

@pytest.mark.asyncio
async def test_create_limit_order_success(client, mock_exchange_instance):
    limit_order_payload = {
        "exchange": "mockexchange",
        "symbol": "ETH-USD",
        "side": "sell",
        "type": "limit",
        "amount": "1.5",
        "price": "3000.00"
    }
    with patch('trade.routers.trades.RiskService.validate_order', new_callable=AsyncMock) as mock_validate_order, \
         patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:

        mock_validate_order.return_value = None

        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.post(BASE_URL, json=limit_order_payload, headers=headers)

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert response_data["id"] == "mock_limit_order_id"
        assert response_data["status"] == "pending"

        mock_validate_order.assert_called_once()
        mock_get_exchange.assert_called_once_with("mockexchange")
        mock_exchange_instance.create_limit_order.assert_called_once_with(
            symbol="ETH-USD", side="sell", amount=1.5, price=3000.00
        )

def test_create_order_missing_api_key(client):
    payload = {"exchange": "mock", "symbol": "BTC-USD", "side": "buy", "type": "market", "amount": "1"}
    response = client.post(BASE_URL, json=payload) # No X-API-KEY header
    assert response.status_code == status.HTTP_403_FORBIDDEN # FastAPI default for missing APIKeyHeader

def test_create_order_invalid_api_key(client):
    payload = {"exchange": "mock", "symbol": "BTC-USD", "side": "buy", "type": "market", "amount": "1"}
    headers = {"X-API-KEY": "invalid_key"}
    response = client.post(BASE_URL, json=payload, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid API Key"

def test_create_order_invalid_payload_missing_field(client):
    # Missing 'symbol'
    payload = {"exchange": "mockexchange", "side": "buy", "type": "market", "amount": "0.01"}
    headers = {"X-API-KEY": VALID_TRADE_API_KEY}
    response = client.post(BASE_URL, json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY 
    # Check for specific field error if needed, e.g. response.json()['detail'][0]['loc']

def test_create_order_invalid_payload_wrong_type(client):
    # 'amount' should be a number (or string convertible to Decimal/float)
    payload = {"exchange": "mockexchange", "symbol": "BTC-USD", "side": "buy", "type": "market", "amount": True}
    headers = {"X-API-KEY": VALID_TRADE_API_KEY}
    response = client.post(BASE_URL, json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@pytest.mark.asyncio
async def test_create_order_risk_service_validation_fails(client):
    payload = {"exchange": "mock", "symbol": "BTC-USD", "side": "buy", "type": "market", "amount": "1000"} # High amount
    with patch('trade.routers.trades.RiskService.validate_order', new_callable=AsyncMock) as mock_validate_order:
        mock_validate_order.side_effect = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Risk validation failed: Order too large")
        
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.post(BASE_URL, json=payload, headers=headers)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Risk validation failed: Order too large"
        mock_validate_order.assert_called_once()

@pytest.mark.asyncio
async def test_create_order_exchange_not_found(client):
    payload = {"exchange": "nonexistentexchange", "symbol": "BTC-USD", "side": "buy", "type": "market", "amount": "0.01"}
    with patch('trade.routers.trades.RiskService.validate_order', new_callable=AsyncMock) as mock_validate_order, \
         patch('trade.routers.trades.ExchangeInterface.get_exchange') as mock_get_exchange:
        
        mock_validate_order.return_value = None
        mock_get_exchange.side_effect = ValueError("Exchange 'nonexistentexchange' not found.") # Example exception

        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.post(BASE_URL, json=payload, headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Exchange 'nonexistentexchange' not found." in response.json()["detail"]
        mock_validate_order.assert_called_once()
        mock_get_exchange.assert_called_once_with("nonexistentexchange")

@pytest.mark.asyncio
async def test_create_order_exchange_method_fails(client, mock_exchange_instance):
    payload = {"exchange": "mockexchange", "symbol": "BTC-USD", "side": "buy", "type": "market", "amount": "0.01"}
    with patch('trade.routers.trades.RiskService.validate_order', new_callable=AsyncMock) as mock_validate_order, \
         patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:
        
        mock_validate_order.return_value = None
        mock_exchange_instance.create_market_order.side_effect = Exception("Exchange API error: Insufficient funds")

        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.post(BASE_URL, json=payload, headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Exchange API error: Insufficient funds" in response.json()["detail"]
        mock_validate_order.assert_called_once()
        mock_get_exchange.assert_called_once_with("mockexchange")
        mock_exchange_instance.create_market_order.assert_called_once()

# Placeholder for GET /orders/{order_id} tests
@pytest.mark.asyncio
async def test_get_order_status_success(client, mock_exchange_instance):
    order_id = "test_order_123"
    exchange_name = "mockexchange"
    with patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.get(f"{BASE_URL}/{order_id}?exchange={exchange_name}", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["id"] == "some_order_id" # From mock_exchange_instance
        assert response_data["status"] == "filled"
        
        mock_get_exchange.assert_called_once_with(exchange_name)
        mock_exchange_instance.get_order_status.assert_called_once_with(order_id)

# Placeholder for DELETE /orders/{order_id} tests
@pytest.mark.asyncio
async def test_cancel_order_success(client, mock_exchange_instance):
    order_id = "test_order_to_cancel_456"
    exchange_name = "mockexchange"
    with patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.delete(f"{BASE_URL}/{order_id}?exchange={exchange_name}", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == True # From mock_exchange_instance

        mock_get_exchange.assert_called_once_with(exchange_name)
        mock_exchange_instance.cancel_order.assert_called_once_with(order_id)

# Tests for GET /orders/{order_id} (get_order_status)

def test_get_order_status_missing_api_key(client):
    response = client.get(f"{BASE_URL}/some_order_id?exchange=mockexchange")
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_order_status_invalid_api_key(client):
    headers = {"X-API-KEY": "invalid_key"}
    response = client.get(f"{BASE_URL}/some_order_id?exchange=mockexchange", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid API Key"

@pytest.mark.asyncio
async def test_get_order_status_exchange_not_found(client):
    order_id = "test_order_123"
    exchange_name = "nonexistentexchange"
    with patch('trade.routers.trades.ExchangeInterface.get_exchange') as mock_get_exchange:
        mock_get_exchange.side_effect = ValueError(f"Exchange '{exchange_name}' not found.")
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.get(f"{BASE_URL}/{order_id}?exchange={exchange_name}", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert f"Exchange '{exchange_name}' not found." in response.json()["detail"]
        mock_get_exchange.assert_called_once_with(exchange_name)

@pytest.mark.asyncio
async def test_get_order_status_exchange_method_fails(client, mock_exchange_instance):
    order_id = "test_order_123"
    exchange_name = "mockexchange"
    with patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:
        mock_exchange_instance.get_order_status.side_effect = Exception("Exchange API error: Order not found")
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.get(f"{BASE_URL}/{order_id}?exchange={exchange_name}", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Exchange API error: Order not found" in response.json()["detail"]
        mock_get_exchange.assert_called_once_with(exchange_name)
        mock_exchange_instance.get_order_status.assert_called_once_with(order_id)

# Tests for DELETE /orders/{order_id} (cancel_order)

def test_cancel_order_missing_api_key(client):
    response = client.delete(f"{BASE_URL}/some_order_id?exchange=mockexchange")
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_cancel_order_invalid_api_key(client):
    headers = {"X-API-KEY": "invalid_key"}
    response = client.delete(f"{BASE_URL}/some_order_id?exchange=mockexchange", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid API Key"

@pytest.mark.asyncio
async def test_cancel_order_exchange_not_found(client):
    order_id = "test_order_to_cancel_456"
    exchange_name = "nonexistentexchange"
    with patch('trade.routers.trades.ExchangeInterface.get_exchange') as mock_get_exchange:
        mock_get_exchange.side_effect = ValueError(f"Exchange '{exchange_name}' not found.")
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.delete(f"{BASE_URL}/{order_id}?exchange={exchange_name}", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert f"Exchange '{exchange_name}' not found." in response.json()["detail"]
        mock_get_exchange.assert_called_once_with(exchange_name)

@pytest.mark.asyncio
async def test_cancel_order_exchange_method_fails(client, mock_exchange_instance):
    order_id = "test_order_to_cancel_456"
    exchange_name = "mockexchange"
    with patch('trade.routers.trades.ExchangeInterface.get_exchange', return_value=mock_exchange_instance) as mock_get_exchange:
        mock_exchange_instance.cancel_order.side_effect = Exception("Exchange API error: Order already cancelled or filled")
        headers = {"X-API-KEY": VALID_TRADE_API_KEY}
        response = client.delete(f"{BASE_URL}/{order_id}?exchange={exchange_name}", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Exchange API error: Order already cancelled or filled" in response.json()["detail"]
        mock_get_exchange.assert_called_once_with(exchange_name)
        mock_exchange_instance.cancel_order.assert_called_once_with(order_id)

# TODO: Add tests for rate limiting if not covered elsewhere.
# The router has @limiter.limit("10/minute"), which might be better tested
# in a dedicated test file for middleware or with specific rate limit testing tools/techniques.