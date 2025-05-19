import pytest
import asyncio
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
import aiohttp # For aiohttp specific exceptions

from trade.utils.exchange import ExchangeInterface, CoinbaseProExchange, BinanceExchange
from trade.utils.exceptions import (
    ExchangeError, ConnectionError, AuthenticationError, OrderError,
    RateLimitError, InsufficientFundsError, InvalidOrderError, MarketClosedError
)
from trade.config import exchange_config # Used by the factory

# Mock environment variables that exchange_config might use
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("COINBASE_API_KEY", "test_cb_key")
    monkeypatch.setenv("COINBASE_API_SECRET", "test_cb_secret")
    monkeypatch.setenv("COINBASE_PASSPHRASE", "test_cb_passphrase")
    monkeypatch.setenv("EXCHANGE_API_KEY", "test_binance_key") # Generic key for Binance
    monkeypatch.setenv("EXCHANGE_API_SECRET", "test_binance_secret") # Generic secret for Binance
    # Force reload or re-initialize exchange_config if it caches values at import
    # This can be tricky. A better way might be to mock exchange_config directly
    # or ensure it has a method to reload configuration.
    # For now, assume the factory method in ExchangeInterface will pick up fresh env vars
    # or that exchange_config is instantiated/used in a way that sees these mocks.
    if hasattr(exchange_config, '_config'): # Simple way to reset a hypothetical cache
        exchange_config._config = None
    if hasattr(exchange_config, 'load_config'): # If there's a reload method
        exchange_config.load_config()


@pytest.fixture
def mock_aiohttp_session_factory():
    """Factory to create mock aiohttp session instances for each test if needed."""
    def _create_mock_session():
        mock_session_instance = AsyncMock(spec=aiohttp.ClientSession)
        # Mock the context manager methods for `async with session.request(...) as response:`
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})
        mock_response.text = AsyncMock(return_value="{}") # Default text for non-JSON cases
        
        # Setup for async with client.session.request(...)
        async def mock_request_context_manager(*args, **kwargs):
            return mock_response
        
        mock_session_instance.request.return_value.__aenter__ = mock_request_context_manager
        mock_session_instance.request.return_value.__aexit__ = AsyncMock(return_value=None)

        # Setup for async with client.session.get(...) etc.
        async def mock_method_context_manager(*args, **kwargs):
            return mock_response

        for method_name in ['get', 'post', 'delete', 'put', 'patch']:
            method_mock = getattr(mock_session_instance, method_name)
            method_mock.return_value.__aenter__ = mock_method_context_manager
            method_mock.return_value.__aexit__ = AsyncMock(return_value=None)
            
        mock_session_instance.closed = False # Simulate an open session initially
        return mock_session_instance

    return _create_mock_session


@pytest.fixture
async def coinbase_client(mock_aiohttp_session_factory, mock_env_vars):
    client = CoinbaseProExchange(api_key="test_cb_key", api_secret="test_cb_secret", passphrase="test_cb_passphrase")
    # Replace the client's session with our mock one
    if client.session: # Close any real session that might have been created
        await client.session.close()
    client.session = mock_aiohttp_session_factory()
    return client

@pytest.fixture
async def binance_client(mock_aiohttp_session_factory, mock_env_vars):
    client = BinanceExchange(api_key="test_binance_key", api_secret="test_binance_secret")
    if client.session:
        await client.session.close()
    client.session = mock_aiohttp_session_factory()
    return client


class TestExchangeInterfaceFactory:
    def test_get_coinbase_pro_exchange(self, mock_env_vars):
        # This test relies on exchange_config picking up the mocked env vars.
        # If exchange_config is a singleton loading at import, this might need adjustment.
        with patch.object(exchange_config, 'get_coinbase_pro_credentials', return_value={
            "api_key": "test_cb_key", "api_secret": "test_cb_secret", "passphrase": "test_cb_passphrase"
        }):
            client = ExchangeInterface.get_exchange("coinbasepro")
            assert isinstance(client, CoinbaseProExchange)
            assert client.api_key == "test_cb_key"

    def test_get_binance_exchange(self, mock_env_vars):
         with patch.object(exchange_config, 'api_key', "test_binance_key"), \
              patch.object(exchange_config, 'api_secret', "test_binance_secret"):
            client = ExchangeInterface.get_exchange("binance")
            assert isinstance(client, BinanceExchange)
            assert client.api_key == "test_binance_key"

    def test_get_unsupported_exchange(self):
        with pytest.raises(ValueError, match="Unsupported exchange: unknown"):
            ExchangeInterface.get_exchange("unknown")

    def test_get_coinbase_pro_missing_creds(self, monkeypatch):
        with patch.object(exchange_config, 'get_coinbase_pro_credentials', return_value={
            "api_key": None, "api_secret": "secret", "passphrase": "pass"
        }):
            with pytest.raises(ValueError, match="Coinbase Pro API key, secret, and passphrase must be configured."):
                ExchangeInterface.get_exchange("coinbasepro")

    def test_get_binance_missing_creds(self, monkeypatch):
        with patch.object(exchange_config, 'api_key', None): # Mock that api_key is None
            with pytest.raises(ValueError, match="API key and secret for binance are not configured."):
                ExchangeInterface.get_exchange("binance")


@pytest.mark.asyncio
class TestCoinbaseProExchange:
    async def test_init(self, coinbase_client):
        assert coinbase_client.api_key == "test_cb_key"
        assert coinbase_client.BASE_URL == "https://api.pro.coinbase.com"
        assert coinbase_client.session is not None

    async def test_close_session(self, coinbase_client):
        await coinbase_client.close()
        coinbase_client.session.close.assert_called_once()

    async def test_get_balances_success(self, coinbase_client):
        mock_response_data = [
            {"currency": "BTC", "available": "1.23"}, {"currency": "USD", "available": "1000.45"},
            {"currency": "ETH", "available": "0.0"},
        ]
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response_data)
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 200

        balances = await coinbase_client.get_balances()
        assert balances["BTC"] == Decimal("1.23")
        assert "ETH" not in balances # Zero balances are filtered

    async def test_get_balances_auth_error(self, coinbase_client):
        error_payload = {"message": "Invalid API Key"}
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 401
        with pytest.raises(AuthenticationError, match="Invalid API Key"):
            await coinbase_client.get_balances()

    async def test_get_balances_rate_limit_error(self, coinbase_client):
        error_payload = {"message": "Rate limit exceeded"}
        mock_response = coinbase_client.session.request.return_value.__aenter__.return_value
        mock_response.json = AsyncMock(return_value=error_payload)
        mock_response.status = 429
        mock_response.headers = {'Retry-After': '60'} # Simulate Retry-After header

        with pytest.raises(RateLimitError) as excinfo:
            await coinbase_client.get_balances()
        assert "Rate limit exceeded" in str(excinfo.value)
        assert excinfo.value.details == {'retry_after_seconds': 60}

    async def test_get_balances_insufficient_funds_error_on_order(self, coinbase_client): # Test for create_order
        error_payload = {"message": "insufficient funds"}
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 400
        with pytest.raises(InsufficientFundsError, match="insufficient funds"):
             await coinbase_client.create_order("BTC-USD", "buy", "market", Decimal("100"))


    async def test_create_order_invalid_params(self, coinbase_client):
        error_payload = {"message": "size is too small"}
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 400
        with pytest.raises(InvalidOrderError, match="size is too small"):
            await coinbase_client.create_order("BTC-USD", "buy", "market", Decimal("0.00001"))

    async def test_create_order_market_closed(self, coinbase_client):
        error_payload = {"message": "Product BTC-USD is not available for trading."} # Example message
        mock_response = coinbase_client.session.request.return_value.__aenter__.return_value
        mock_response.json = AsyncMock(return_value=error_payload)
        mock_response.status = 400 # Coinbase might use 400 or 404 for this
        
        with pytest.raises(MarketClosedError, match="Product BTC-USD is not available for trading."):
            await coinbase_client.create_order("BTC-USD", "buy", "market", Decimal("1"))

    async def test_cancel_order_success(self, coinbase_client):
        order_id = "order123"
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=[order_id])
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 200
        
        result = await coinbase_client.cancel_order(order_id)
        assert result["status"] == "cancelled"
        assert result["order_id"] == order_id

    async def test_cancel_order_not_found(self, coinbase_client):
        order_id = "order_not_found"
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={"message": "Order not found"})
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 404
        with pytest.raises(InvalidOrderError, match="Resource not found: Order not found"):
            await coinbase_client.cancel_order(order_id)

    async def test_test_connection_success(self, coinbase_client):
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value=[{"currency": "USD", "available": "100"}])
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 200
        assert await coinbase_client.test_connection() is True

    async def test_test_connection_auth_failure(self, coinbase_client):
        coinbase_client.session.request.return_value.__aenter__.return_value.status = 401
        coinbase_client.session.request.return_value.__aenter__.return_value.json = AsyncMock(return_value={"message": "auth failed"})
        with pytest.raises(AuthenticationError):
            await coinbase_client.test_connection()

    async def test_test_connection_network_failure(self, coinbase_client):
        coinbase_client.session.request.side_effect = aiohttp.ClientConnectorError(MagicMock(), OSError())
        with pytest.raises(ConnectionError):
            await coinbase_client.test_connection()
            
    async def test_get_ticker_non_json_response(self, coinbase_client):
        coinbase_client.session.get.return_value.__aenter__.return_value.status = 503 # Service Unavailable
        coinbase_client.session.get.return_value.__aenter__.return_value.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))
        coinbase_client.session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value="Service Unavailable HTML page")
        with pytest.raises(ExchangeError, match="Non-JSON response. Status: 503"):
            await coinbase_client.get_ticker("BTC-USD")

    async def test_create_oco_order_not_implemented(self, coinbase_client):
        with pytest.raises(NotImplementedError, match="Native OCO orders are not supported by CoinbasePro"):
            await coinbase_client.create_oco_order(
                symbol="BTC-USD",
                side="SELL",
                quantity=Decimal("0.1"),
                price=Decimal("60000"),
                stop_price=Decimal("58000")
            )

    async def test_create_trailing_stop_order_not_implemented(self, coinbase_client):
        with pytest.raises(NotImplementedError, match="Native server-side trailing stop orders are not supported by CoinbasePro"):
            await coinbase_client.create_trailing_stop_order(
                symbol="BTC-USD",
                side="SELL",
                quantity=Decimal("0.1"),
                callback_rate=Decimal("1.0")
            )

@pytest.mark.asyncio
class TestBinanceExchange:
    async def test_init(self, binance_client):
        assert binance_client.api_key == "test_binance_key"
        assert binance_client.BASE_URL == "https://api.binance.com"
        assert binance_client.session is not None

    async def test_close_session(self, binance_client):
        await binance_client.close()
        binance_client.session.close.assert_called_once()

    async def test_get_balances_success(self, binance_client):
        mock_response_data = {"balances": [{"asset": "BTC", "free": "1.23"}, {"asset": "USDT", "free": "1000.45"}]}
        binance_client.session.get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response_data)
        binance_client.session.get.return_value.__aenter__.return_value.status = 200
        balances = await binance_client.get_balances()
        assert balances["BTC"] == Decimal("1.23")

    async def test_get_balances_auth_error(self, binance_client):
        error_payload = {"code": -2015, "msg": "Invalid API-key."}
        binance_client.session.get.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        binance_client.session.get.return_value.__aenter__.return_value.status = 401 # Binance uses 401/403 for auth
        with pytest.raises(AuthenticationError, match="Invalid API-key."):
            await binance_client.get_balances()

    async def test_get_balances_rate_limit_error_http_429(self, binance_client):
        error_payload = {"code": -1003, "msg": "Too many requests."}
        mock_response = binance_client.session.get.return_value.__aenter__.return_value
        mock_response.json = AsyncMock(return_value=error_payload)
        mock_response.status = 429
        mock_response.headers = {'Retry-After': '120'}

        with pytest.raises(RateLimitError) as excinfo:
            await binance_client.get_balances()
        assert "Too many requests" in str(excinfo.value)
        assert excinfo.value.details == {'retry_after_seconds': 120}
            
    async def test_get_balances_rate_limit_error_http_418(self, binance_client):
        error_payload = {"code": -1003, "msg": "Banned due to rate limits."}
        mock_response = binance_client.session.get.return_value.__aenter__.return_value
        mock_response.json = AsyncMock(return_value=error_payload)
        mock_response.status = 418
        mock_response.headers = {} # No Retry-After for IP ban usually

        with pytest.raises(RateLimitError) as excinfo:
            await binance_client.get_balances()
        assert "Banned due to rate limits" in str(excinfo.value)
        assert excinfo.value.details == {} # Expect empty details if no header

    async def test_create_order_insufficient_funds(self, binance_client):
        error_payload = {"code": -2010, "msg": "Account has insufficient balance for requested action."}
        binance_client.session.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        binance_client.session.post.return_value.__aenter__.return_value.status = 400 # Binance often uses 400 for such errors
        with pytest.raises(InsufficientFundsError, match="Account has insufficient balance"):
            await binance_client.create_order("BTCUSDT", "BUY", "MARKET", Decimal("10"))

    async def test_create_order_invalid_lot_size(self, binance_client):
        error_payload = {"code": -1013, "msg": "Filter failure: LOT_SIZE"}
        binance_client.session.post.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        binance_client.session.post.return_value.__aenter__.return_value.status = 400
        with pytest.raises(InvalidOrderError, match="Filter failure: LOT_SIZE"):
            await binance_client.create_order("BTCUSDT", "BUY", "LIMIT", Decimal("0.0000001"), Decimal("20000"))

    async def test_create_order_market_closed(self, binance_client):
        # Scenario 1: Error code -2010 with "market is closed"
        error_payload_2010 = {"code": -2010, "msg": "Market is closed."}
        mock_response_2010 = binance_client.session.post.return_value.__aenter__.return_value
        mock_response_2010.json = AsyncMock(return_value=error_payload_2010)
        mock_response_2010.status = 400

        with pytest.raises(MarketClosedError, match="Market is closed."):
            await binance_client.create_order("BTCUSDT", "BUY", "MARKET", Decimal("1"))

        # Scenario 2: Error code -1013 with "Trading is disabled"
        error_payload_1013 = {"code": -1013, "msg": "Trading is disabled on this symbol."}
        mock_response_1013 = binance_client.session.post.return_value.__aenter__.return_value
        mock_response_1013.json = AsyncMock(return_value=error_payload_1013)
        mock_response_1013.status = 400
        
        with pytest.raises(MarketClosedError, match="Trading is disabled on this symbol."):
            await binance_client.create_order("BTCUSDT", "BUY", "MARKET", Decimal("1"))

    async def test_cancel_order_success(self, binance_client):
        order_id = "order123"
        symbol = "BTCUSDT"
        mock_cancel_response = {"symbol": symbol, "orderId": order_id, "status": "CANCELED"}
        binance_client.session.delete.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_cancel_response)
        binance_client.session.delete.return_value.__aenter__.return_value.status = 200
        
        result = await binance_client.cancel_order(order_id, symbol)
        assert result["status"] == "CANCELED"
        assert result["orderId"] == order_id

    async def test_cancel_order_not_found(self, binance_client):
        order_id = "unknown_order"
        symbol = "BTCUSDT"
        error_payload = {"code": -2011, "msg": "Unknown order sent."} # Or -2013 "Order does not exist."
        binance_client.session.delete.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload)
        binance_client.session.delete.return_value.__aenter__.return_value.status = 400 # Or 404 depending on specific error
        
        # The new _handle_response maps -2011 to OrderError, -2013 to InvalidOrderError
        # Let's assume -2013 for "order does not exist"
        error_payload_not_exist = {"code": -2013, "msg": "Order does not exist."}
        binance_client.session.delete.return_value.__aenter__.return_value.json = AsyncMock(return_value=error_payload_not_exist)

        with pytest.raises(InvalidOrderError, match="Order not found: Order does not exist."):
            await binance_client.cancel_order(order_id, symbol)

    async def test_test_connection_success(self, binance_client):
        binance_client.session.get.return_value.__aenter__.return_value.json = AsyncMock(return_value={"balances": []})
        binance_client.session.get.return_value.__aenter__.return_value.status = 200
        assert await binance_client.test_connection() is True

    async def test_test_connection_auth_failure(self, binance_client):
        binance_client.session.get.return_value.__aenter__.return_value.status = 401
        binance_client.session.get.return_value.__aenter__.return_value.json = AsyncMock(return_value={"code":-2015, "msg": "auth failed"})
        with pytest.raises(AuthenticationError):
            await binance_client.test_connection()

    async def test_test_connection_network_failure(self, binance_client):
        binance_client.session.get.side_effect = aiohttp.ClientConnectorError(MagicMock(), OSError())
        with pytest.raises(ConnectionError):
            await binance_client.test_connection()

    async def test_get_ticker_non_json_response(self, binance_client):
        binance_client.session.get.return_value.__aenter__.return_value.status = 503 # Service Unavailable
        binance_client.session.get.return_value.__aenter__.return_value.json = AsyncMock(side_effect=aiohttp.ContentTypeError(MagicMock(), MagicMock()))
        binance_client.session.get.return_value.__aenter__.return_value.text = AsyncMock(return_value="Service Unavailable HTML page")
        with pytest.raises(ExchangeError, match="Non-JSON response. Status: 503"):
            await binance_client.get_ticker("BTCUSDT")

    @patch('trade.utils.exchange.BinanceExchange._signed_request', new_callable=AsyncMock)
    async def test_create_oco_order_success(self, mock_signed_request, binance_client):
        mock_signed_request.return_value = {
            "orderListId": 123,
            "contingencyType": "OCO",
            "listStatusType": "EXEC_STARTED",
            "listOrderStatus": "EXECUTING",
            "listClientOrderId": "myOcoOrder",
            "transactionTime": 1678886400000,
            "symbol": "BTCUSDT",
            "orders": [
                {"symbol": "BTCUSDT", "orderId": 1, "clientOrderId": "limitPart"},
                {"symbol": "BTCUSDT", "orderId": 2, "clientOrderId": "stopPart"}
            ],
            "orderReports": [
                {"symbol": "BTCUSDT", "orderId": 1, "clientOrderId": "limitPart", "status": "NEW", "type": "LIMIT_MAKER"},
                {"symbol": "BTCUSDT", "orderId": 2, "clientOrderId": "stopPart", "status": "NEW", "type": "STOP_LOSS_LIMIT"}
            ]
        }
        
        result = await binance_client.create_oco_order(
            symbol="BTCUSDT",
            side="SELL",
            quantity=Decimal("0.1"),
            price=Decimal("60000"),
            stop_price=Decimal("58000"),
            stop_limit_price=Decimal("57900"),
            list_client_order_id="myOcoOrder"
        )
        
        mock_signed_request.assert_called_once()
        args, kwargs = mock_signed_request.call_args
        assert args[0] == "POST"
        assert args[1] == "/api/v3/order/oco"
        assert kwargs['symbol'] == "BTCUSDT"
        assert kwargs['side'] == "SELL"
        assert kwargs['quantity'] == "0.1"
        assert kwargs['price'] == "60000"
        assert kwargs['stopPrice'] == "58000"
        assert kwargs['stopLimitPrice'] == "57900"
        assert kwargs['listClientOrderId'] == "myOcoOrder"
        
        assert result["orderListId"] == 123
        assert result["contingencyType"] == "OCO"

    @patch('trade.utils.exchange.BinanceExchange._signed_request', new_callable=AsyncMock)
    async def test_create_trailing_stop_order_success(self, mock_signed_request, binance_client):
        mock_signed_request.return_value = {
            "orderId": 789,
            "symbol": "ETHUSDT",
            "clientOrderId": "myTrailingStop",
            "price": "0", # Market order price is 0
            "origQty": "1.0",
            "executedQty": "0.0",
            "status": "NEW",
            "timeInForce": "GTC",
            "type": "TRAILING_STOP_MARKET",
            "side": "BUY",
            "stopPrice": "0", # Not used for TRAILING_STOP_MARKET with callbackRate
            "callbackRate": "1.5", # 1.5%
            "workingType": "CONTRACT_PRICE",
            "activatePrice": "0", # Not used for TRAILING_STOP_MARKET with callbackRate
            "priceRate": "0",
            "origType": "TRAILING_STOP_MARKET",
            "positionSide": "BOTH",
            "transactionTime": 1678886400000,
        }

        result = await binance_client.create_trailing_stop_order(
            symbol="ETHUSDT",
            side="BUY",
            quantity=Decimal("1.0"),
            callback_rate=Decimal("1.5"), # 1.5%
            working_type="CONTRACT_PRICE"
        )

        mock_signed_request.assert_called_once()
        args, kwargs = mock_signed_request.call_args
        assert args[0] == "POST"
        assert args[1] == "/api/v3/order"
        assert kwargs['symbol'] == "ETHUSDT"
        assert kwargs['side'] == "BUY"
        assert kwargs['quantity'] == "1.0"
        assert kwargs['type'] == "TRAILING_STOP_MARKET"
        assert kwargs['callbackRate'] == "1.5"
        assert kwargs['workingType'] == "CONTRACT_PRICE"

        assert result["orderId"] == 789
        assert result["type"] == "TRAILING_STOP_MARKET"
        assert result["callbackRate"] == "1.5"