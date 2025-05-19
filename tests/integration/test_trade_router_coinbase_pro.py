import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, ANY
from decimal import Decimal

# Assuming your FastAPI app is defined in trade.main
# You might need to adjust the import path based on your project structure
from trade.main import app # Import your FastAPI app instance
from trade.config import exchange_config # To ensure config is loaded for the factory

# It's crucial that the test environment is set up correctly for exchange_config
# to provide the Coinbase Pro credentials when the factory is called by the router.
@pytest.fixture(scope="module", autouse=True)
def setup_coinbase_pro_env_vars(monkeypatch_module):
    monkeypatch_module.setenv("COINBASE_API_KEY", "test_cb_api_key_integration")
    monkeypatch_module.setenv("COINBASE_API_SECRET", "test_cb_api_secret_integration")
    monkeypatch_module.setenv("COINBASE_PASSPHRASE", "test_cb_passphrase_integration")
    monkeypatch_module.setenv("TRADE_API_KEY", "test_trade_api_key") # For router authentication

@pytest.fixture(scope="module")
def client_app(setup_coinbase_pro_env_vars):
    # Reload exchange_config or ensure it picks up new env vars if it's a singleton
    # For simplicity, assume it's re-evaluated or fresh for each test module.
    # If exchange_config is imported once and caches, this might need more work.
    # One way is to mock exchange_config.get_coinbase_pro_credentials() directly if needed.
    with TestClient(app) as c:
        yield c

@pytest.mark.asyncio
async def test_create_coinbase_pro_limit_order_via_router(client_app):
    order_payload = {
        "exchange": "coinbasepro",
        "symbol": "BTC-USD",
        "side": "buy",
        "type": "limit",
        "amount": "0.01",
        "price": "30000.00"
    }
    
    mock_api_response = {
        "id": "integration-test-order-id",
        "product_id": "BTC-USD",
        "side": "buy",
        "type": "limit",
        "size": "0.01",
        "price": "30000.00",
        "status": "pending",
        # ... other fields Coinbase Pro might return
    }

    # We need to mock the _signed_request method of the CoinbaseProExchange instance
    # that will be created by the ExchangeInterface.get_exchange factory.
    with patch('trade.utils.exchange.CoinbaseProExchange._signed_request', new_callable=AsyncMock) as mock_signed_request:
        mock_signed_request.return_value = mock_api_response
        
        headers = {"X-API-KEY": "test_trade_api_key"}
        response = client_app.post("/api/trades/orders", json=order_payload, headers=headers)
        
        assert response.status_code == 201
        response_data = response.json()
        
        assert response_data["id"] == "integration-test-order-id"
        assert response_data["product_id"] == "BTC-USD"
        assert response_data["side"] == "buy"
        assert response_data["type"] == "limit" # Ensure type is preserved
        assert response_data["price"] == "30000.00"
        assert response_data["size"] == "0.01"

        mock_signed_request.assert_called_once()
        # Check the actual arguments passed to _signed_request
        args, kwargs = mock_signed_request.call_args
        assert args[0] == "POST"  # method
        assert args[1] == "/orders"  # path
        
        expected_body = {
            'product_id': 'BTC-USD',
            'side': 'buy',
            'type': 'limit',
            'price': '30000.00',
            'size': '0.01',
            'post_only': False
        }
        assert kwargs['body'] == expected_body


@pytest.mark.asyncio
async def test_get_coinbase_pro_order_status_via_router(client_app):
    order_id = "some-cb-order-id"
    exchange_name = "coinbasepro"
    
    mock_api_response = {
        "id": order_id,
        "product_id": "ETH-USD",
        "status": "filled",
        "filled_size": "1.0",
        # ... other fields
    }

    with patch('trade.utils.exchange.CoinbaseProExchange._signed_request', new_callable=AsyncMock) as mock_signed_request:
        mock_signed_request.return_value = mock_api_response
        
        headers = {"X-API-KEY": "test_trade_api_key"}
        response = client_app.get(f"/api/trades/orders/{order_id}?exchange={exchange_name}", headers=headers)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["id"] == order_id
        assert response_data["status"] == "filled"
        
        mock_signed_request.assert_called_once()
        args, kwargs = mock_signed_request.call_args
        assert args[0] == "GET" # method
        assert args[1] == f"/orders/{order_id}" # path
        assert kwargs.get('body') is None


@pytest.mark.asyncio
async def test_cancel_coinbase_pro_order_via_router(client_app):
    order_id = "cancel-this-cb-order"
    exchange_name = "coinbasepro"

    # Coinbase Pro returns a list with the order_id on successful cancel
    mock_api_response = [order_id] 

    with patch('trade.utils.exchange.CoinbaseProExchange._signed_request', new_callable=AsyncMock) as mock_signed_request:
        mock_signed_request.return_value = mock_api_response
        
        headers = {"X-API-KEY": "test_trade_api_key"}
        response = client_app.delete(f"/api/trades/orders/{order_id}?exchange={exchange_name}", headers=headers)
        
        assert response.status_code == 200
        response_data = response.json() # The router returns the direct API response
        
        assert response_data == True # cancel_order in CoinbaseProExchange returns True on success

        mock_signed_request.assert_called_once()
        args, kwargs = mock_signed_request.call_args
        assert args[0] == "DELETE" # method
        assert args[1] == f"/orders/{order_id}" # path
        assert kwargs.get('body') is None

# TODO: Add tests for other CoinbaseProExchange methods via the router if they have endpoints
# e.g., get_balances, get_ticker, get_open_orders etc., if router exposes them.
# The current router only has create, get_status, cancel.