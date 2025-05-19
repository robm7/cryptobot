import logging
from typing import Dict, List, Optional
import asyncio
import aiohttp
from decimal import Decimal
import time
import hmac
import hashlib
import urllib.parse
import base64
import json
from datetime import datetime, timezone

from .exceptions import (
    ExchangeError, ConnectionError, AuthenticationError, OrderError,
    RateLimitError, InsufficientFundsError, InvalidOrderError, MarketClosedError
)
from ..config import exchange_config

logger = logging.getLogger(__name__)

class ExchangeInterface:
    """Unified interface for cryptocurrency exchanges"""

    def __init__(self, api_key: str, api_secret: str, exchange_name: str = "UnknownExchange"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange_name = exchange_name
        # Ensure session is created within an async context or managed by the event loop
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def get_balances(self) -> Dict[str, Decimal]:
        """Get current account balances"""
        raise NotImplementedError

    async def get_ticker(self, symbol: str) -> Dict:
        """Get current market price for symbol"""
        raise NotImplementedError

    async def create_order(self, symbol: str, side: str, type: str,
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        """Create new trading order"""
        raise NotImplementedError

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        """
        Cancel existing order.
        Returns a dictionary with order details or confirmation.
        Raises specific exceptions on failure.
        """
        raise NotImplementedError

    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get list of open orders"""
        raise NotImplementedError

    async def create_oco_order(self, symbol: str, side: str, quantity: Decimal, price: Decimal,
                               stop_price: Decimal, stop_limit_price: Optional[Decimal] = None,
                               list_client_order_id: Optional[str] = None,
                               limit_client_order_id: Optional[str] = None,
                               stop_client_order_id: Optional[str] = None) -> Dict:
        """Create a new OCO (One-Cancels-the-Other) order."""
        raise NotImplementedError

    async def create_trailing_stop_order(self, symbol: str, side: str, quantity: Decimal,
                                         activation_price: Optional[Decimal] = None,
                                         callback_rate: Decimal = None,  # e.g., 1 for 1%
                                         strategy_id: Optional[str] = None, # For Binance: TRAILING_DELTA
                                         working_type: Optional[str] = None # For Binance: CONTRACT_PRICE
                                         ) -> Dict:
        """
        Create a new trailing stop order.
        Note: Parameters might vary significantly between exchanges.
        'callback_rate' is common for percentage-based trailing.
        'activation_price' is when the trailing stop becomes active.
        'strategy_id' for Binance is used for TRAILING_DELTA orders to specify the delta.
        """
        raise NotImplementedError

    async def test_connection(self) -> bool:
        """Test the connection to the exchange"""
        raise NotImplementedError

    async def close(self):
        """Clean up resources"""
        if self.session and not self.session.closed:
            await self.session.close()

    @classmethod
    def get_exchange(cls, exchange_name: str) -> 'ExchangeInterface':
        """Factory method to get an exchange instance."""
        name_lower = exchange_name.lower()
        if name_lower == "binance":
            api_key = exchange_config.api_key
            api_secret = exchange_config.api_secret
            if not api_key or not api_secret:
                logger.error("Binance API key and secret are not configured.")
                raise ValueError(f"API key and secret for {exchange_name} are not configured.")
            return BinanceExchange(api_key=api_key, api_secret=api_secret)
        elif name_lower == "coinbasepro":
            cb_creds = exchange_config.get_coinbase_pro_credentials()
            if not cb_creds["api_key"] or not cb_creds["api_secret"] or not cb_creds["passphrase"]:
                logger.error("Coinbase Pro API credentials are not fully configured.")
                raise ValueError(f"Coinbase Pro API key, secret, and passphrase must be configured.")
            return CoinbaseProExchange(
                api_key=cb_creds["api_key"],
                api_secret=cb_creds["api_secret"],
                passphrase=cb_creds["passphrase"]
            )
        else:
            logger.error(f"Unsupported exchange: {exchange_name}")
            raise ValueError(f"Unsupported exchange: {exchange_name}")

class BinanceExchange(ExchangeInterface):
    """Binance exchange implementation"""
    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret, exchange_name="Binance")

    async def _handle_response(self, response: aiohttp.ClientResponse, method: str, endpoint: str):
        """Handle API response and errors for Binance."""
        try:
            data = await response.json()
        except aiohttp.ContentTypeError:
            text_data = await response.text()
            logger.error(
                f"{self.exchange_name} API request failed: Non-JSON response. Status: {response.status}. "
                f"Method: {method}, Endpoint: {endpoint}. Response: {text_data[:500]}..."
            )
            raise ExchangeError(
                f"{self.exchange_name} API request failed: Non-JSON response. Status: {response.status}. Response: {text_data[:200]}...",
                code=response.status, exchange=self.exchange_name
            )

        if not (200 <= response.status < 300):
            error_msg = data.get('msg', 'Unknown Binance API error')
            error_code = data.get('code', response.status) # Use Binance code if available, else HTTP status
            log_message = (f"{self.exchange_name} API Error: {error_msg} (Code: {error_code}). "
                           f"Method: {method}, Endpoint: {endpoint}, HTTP Status: {response.status}")
            logger.error(log_message)

            # Map Binance error codes to custom exceptions
            if error_code == -1003 or response.status == 429 or response.status == 418: # TOO_MANY_REQUESTS or banned
                retry_after_seconds = response.headers.get('Retry-After')
                details = {}
                if retry_after_seconds:
                    try:
                        details['retry_after_seconds'] = int(retry_after_seconds)
                    except ValueError:
                        logger.warning(f"Could not parse Retry-After header value: {retry_after_seconds}")
                raise RateLimitError(error_msg, code=error_code, exchange=self.exchange_name, details=details)
            elif error_code == -1022 or error_code == -2014 or error_code == -2015: # Signature/API key issues
                raise AuthenticationError(error_msg, code=error_code, exchange=self.exchange_name)
            elif error_code == -2010: # New order rejected (e.g. insufficient balance)
                if "insufficient balance" in error_msg.lower():
                    raise InsufficientFundsError(error_msg, code=error_code, exchange=self.exchange_name)
                # Check for market closed or trading disabled messages within -2010
                if "market is closed" in error_msg.lower() or "trading is disabled" in error_msg.lower():
                    raise MarketClosedError(error_msg, code=error_code, exchange=self.exchange_name)
                raise OrderError(error_msg, code=error_code, exchange=self.exchange_name)
            elif error_code == -1013: # Filter failure (LOT_SIZE, PRICE_FILTER etc.)
                # -1013 can also indicate market closed or other trading rule violations
                if "market is closed" in error_msg.lower() or "trading is disabled" in error_msg.lower():
                    raise MarketClosedError(error_msg, code=error_code, exchange=self.exchange_name)
                if "account has insufficient balance" in error_msg.lower(): # Sometimes balance errors appear as -1013
                    raise InsufficientFundsError(error_msg, code=error_code, exchange=self.exchange_name)
                raise InvalidOrderError(error_msg, code=error_code, exchange=self.exchange_name)
            elif error_code == -2011: # Cancel order failed
                raise OrderError(error_msg, code=error_code, exchange=self.exchange_name)
            elif error_code == -2013: # Order does not exist
                raise InvalidOrderError(f"Order not found: {error_msg}", code=error_code, exchange=self.exchange_name)
            elif response.status == 401 or response.status == 403:
                 raise AuthenticationError(error_msg, code=error_code, exchange=self.exchange_name)
            else:
                raise ExchangeError(error_msg, code=error_code, exchange=self.exchange_name)
        return data

    async def _signed_request(self, method: str, endpoint: str, **params):
        """Make authenticated API request with signature"""
        await self._ensure_session()
        timestamp = int(time.time() * 1000)
        params['timestamp'] = timestamp

        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {'X-MBX-APIKEY': self.api_key}
        url = f"{self.BASE_URL}{endpoint}"

        try:
            if method.upper() == "GET":
                url_with_params = f"{url}?{query_string}&signature={signature}"
                async with self.session.get(url_with_params, headers=headers) as response:
                    return await self._handle_response(response, method, endpoint)
            elif method.upper() == "POST":
                params['signature'] = signature # Signature in body for POST
                async with self.session.post(url, headers=headers, data=params) as response:
                    return await self._handle_response(response, method, endpoint)
            elif method.upper() == "DELETE":
                url_with_params = f"{url}?{query_string}&signature={signature}"
                async with self.session.delete(url_with_params, headers=headers) as response:
                    return await self._handle_response(response, method, endpoint)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Network connection error for {self.exchange_name} {method} {endpoint}: {e}")
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout for {self.exchange_name} {method} {endpoint}: {e}")
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)
        except aiohttp.ClientError as e: # Catch other client errors
            logger.error(f"AIOHTTP client error for {self.exchange_name} {method} {endpoint}: {e}")
            raise ExchangeError(f"HTTP client error: {e}", exchange=self.exchange_name)


    async def get_balances(self) -> Dict[str, Decimal]:
        endpoint = "/api/v3/account"
        data = await self._signed_request("GET", endpoint)
        return {
            asset['asset']: Decimal(asset['free'])
            for asset in data.get('balances', [])
            if Decimal(asset.get('free', '0')) > 0
        }

    async def test_connection(self) -> bool:
        try:
            await self.get_balances()
            logger.info(f"{self.exchange_name} connection test successful.")
            return True
        except AuthenticationError as e:
            logger.error(f"{self.exchange_name} authentication failed: {e}")
            raise  # Re-raise for the caller to handle
        except ConnectionError as e:
            logger.error(f"{self.exchange_name} connection failed: {e}")
            raise
        except ExchangeError as e:
            logger.error(f"{self.exchange_name} connection test failed with ExchangeError: {e}")
            raise
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"{self.exchange_name} connection test failed with an unexpected error: {e}")
            raise ExchangeError(f"Unexpected error during {self.exchange_name} connection test: {e}", exchange=self.exchange_name)


    async def get_ticker(self, symbol: str) -> Dict:
        endpoint = "/api/v3/ticker/24hr"
        # Binance public endpoints usually don't need signing, but _signed_request handles general structure
        # For truly public, could use a different method. For now, this is fine.
        await self._ensure_session()
        url = f"{self.BASE_URL}{endpoint}?symbol={symbol.upper()}"
        try:
            async with self.session.get(url) as response:
                return await self._handle_response(response, "GET", endpoint)
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Network connection error for {self.exchange_name} GET {endpoint}: {e}")
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout for {self.exchange_name} GET {endpoint}: {e}")
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)
        except aiohttp.ClientError as e:
            logger.error(f"AIOHTTP client error for {self.exchange_name} GET {endpoint}: {e}")
            raise ExchangeError(f"HTTP client error: {e}", exchange=self.exchange_name)


    async def create_order(self, symbol: str, side: str, type: str,
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': type.upper(),
            'quantity': str(amount),
        }
        if type.upper() == 'LIMIT':
            if price is None:
                raise InvalidOrderError("Price is required for limit orders.", exchange=self.exchange_name)
            params['price'] = str(price)
            params['timeInForce'] = 'GTC' # Good Till Cancelled, common for limit orders
        elif type.upper() == 'MARKET':
            pass # No price or timeInForce for basic market orders
        else:
            raise InvalidOrderError(f"Unsupported order type: {type}", exchange=self.exchange_name)

        return await self._signed_request("POST", endpoint, **params)

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        if not symbol:
            # Binance requires symbol for cancelling orders.
            # This is a deviation from the base interface if symbol is truly optional.
            # For now, let's require it or fetch it if possible, or raise.
            raise InvalidOrderError("Symbol is required to cancel an order on Binance.", exchange=self.exchange_name)

        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        # This will raise specific exceptions on failure as per _handle_response
        return await self._signed_request("DELETE", endpoint, **params)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        endpoint = "/api/v3/openOrders"
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        return await self._signed_request("GET", endpoint, **params)

    async def create_oco_order(self, symbol: str, side: str, quantity: Decimal, price: Decimal,
                               stop_price: Decimal, stop_limit_price: Optional[Decimal] = None,
                               list_client_order_id: Optional[str] = None,
                               limit_client_order_id: Optional[str] = None,
                               stop_client_order_id: Optional[str] = None) -> Dict:
        """Create a new OCO (One-Cancels-the-Other) order on Binance."""
        endpoint = "/api/v3/order/oco"
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'quantity': str(quantity),
            'price': str(price),  # Price for the LIMIT part of the OCO
            'stopPrice': str(stop_price), # Price for the STOP_LOSS or STOP_LOSS_LIMIT part
        }
        if stop_limit_price:
            params['stopLimitPrice'] = str(stop_limit_price)
            params['stopLimitTimeInForce'] = 'GTC'  # Required if stopLimitPrice is sent

        # Optional client order IDs
        if list_client_order_id:
            params['listClientOrderId'] = list_client_order_id
        if limit_client_order_id:
            params['limitClientOrderId'] = limit_client_order_id
        if stop_client_order_id:
            params['stopClientOrderId'] = stop_client_order_id
        
        return await self._signed_request("POST", endpoint, **params)

    async def create_trailing_stop_order(self, symbol: str, side: str, quantity: Decimal,
                                         activation_price: Optional[Decimal] = None, # Not directly used by TRAILING_STOP_MARKET with callbackRate
                                         callback_rate: Decimal = None,
                                         strategy_id: Optional[str] = None, # For TRAILING_DELTA
                                         working_type: Optional[str] = None # For TRAILING_STOP_MARKET, usually CONTRACT_PRICE
                                         ) -> Dict:
        """
        Create a new TRAILING_STOP_MARKET order on Binance using callbackRate.
        Activation price is not directly supported for TRAILING_STOP_MARKET with callbackRate on Binance API.
        The trailing begins as soon as the order is placed and market moves.
        If strategy_id (for TRAILING_DELTA) is provided, it takes precedence.
        """
        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'quantity': str(quantity),
        }

        if strategy_id: # TRAILING_DELTA order
            params['type'] = 'TRAILING_DELTA'
            params['strategyId'] = strategy_id # Delta in BIPS (e.g. 100 for 1%)
            if working_type: # e.g. CONTRACT_PRICE or MARK_PRICE
                 params['workingType'] = working_type.upper()
        elif callback_rate: # TRAILING_STOP_MARKET order
            params['type'] = 'TRAILING_STOP_MARKET'
            params['callbackRate'] = str(callback_rate) # e.g., 1 for 1%, 0.5 for 0.5%
            if working_type: # e.g. CONTRACT_PRICE or MARK_PRICE
                 params['workingType'] = working_type.upper()
            # Activation price for TRAILING_STOP_MARKET with callbackRate is not a direct Binance API param.
            # It activates based on market movement after placement.
            # If an activation price is desired, it usually implies a STOP or STOP_MARKET order first,
            # which then, if triggered, might place a trailing stop. This is more complex logic.
            if activation_price:
                logger.warning(f"Activation price for Binance TRAILING_STOP_MARKET with callbackRate is not directly supported by API. Order will trail based on market movement from placement.")

        else:
            raise InvalidOrderError("Either callback_rate (for TRAILING_STOP_MARKET) or strategy_id (for TRAILING_DELTA) must be provided for a trailing stop order.", exchange=self.exchange_name)

        return await self._signed_request("POST", endpoint, **params)


class CoinbaseProExchange(ExchangeInterface):
    """Coinbase Pro exchange implementation"""
    BASE_URL = "https://api.pro.coinbase.com"

    def __init__(self, api_key: str, api_secret: str, passphrase: str):
        super().__init__(api_key, api_secret, exchange_name="CoinbasePro")
        self.passphrase = passphrase

    async def _handle_response(self, response: aiohttp.ClientResponse, method: str, path: str):
        """Handle API response and errors for Coinbase Pro."""
        try:
            data = await response.json()
        except (aiohttp.ContentTypeError, json.JSONDecodeError): # Handle cases where response is not JSON
            text_data = await response.text()
            logger.error(
                f"{self.exchange_name} API request failed: Non-JSON response. Status: {response.status}. "
                f"Method: {method}, Path: {path}. Response: {text_data[:500]}..."
            )
            # For non-JSON, often HTML error pages, map common HTTP errors
            if response.status == 401 or response.status == 403:
                raise AuthenticationError(f"Authentication failed. Status: {response.status}. Response: {text_data[:200]}", code=response.status, exchange=self.exchange_name)
            if response.status == 429:
                retry_after_seconds = response.headers.get('Retry-After')
                details = {}
                if retry_after_seconds:
                    try:
                        details['retry_after_seconds'] = int(retry_after_seconds)
                    except ValueError:
                        logger.warning(f"Could not parse Retry-After header value for {self.exchange_name}: {retry_after_seconds}")
                raise RateLimitError(f"Rate limit exceeded. Status: {response.status}. Response: {text_data[:200]}", code=response.status, exchange=self.exchange_name, details=details)
            raise ExchangeError(
                f"{self.exchange_name} API request failed: Non-JSON response. Status: {response.status}. Response: {text_data[:200]}...",
                code=response.status, exchange=self.exchange_name
            )

        if not (200 <= response.status < 300):
            error_message = data.get('message', 'Unknown Coinbase Pro API error')
            if 'reason' in data: # Coinbase sometimes has more details in 'reason'
                error_message += f" Reason: {data['reason']}"

            log_message = (f"{self.exchange_name} API Error: {error_message}. "
                           f"Method: {method}, Path: {path}, HTTP Status: {response.status}, Response Data: {data}")
            logger.error(log_message)

            # Map Coinbase Pro HTTP status codes and messages
            if response.status == 400:
                if "insufficient fund" in error_message.lower():
                    raise InsufficientFundsError(error_message, code=response.status, exchange=self.exchange_name)
                if "market is closed" in error_message.lower() or "trading is disabled" in error_message.lower() or "product_id is not available for trading" in error_message.lower():
                    raise MarketClosedError(error_message, code=response.status, exchange=self.exchange_name)
                # "Invalid amount", "Invalid price", "product_id does not exist", "Invalid order type"
                # "Order already done", "size is too small", "price is too precise"
                raise InvalidOrderError(error_message, code=response.status, exchange=self.exchange_name)
            elif response.status == 401 or response.status == 403: # Unauthorized or Forbidden
                raise AuthenticationError(error_message, code=response.status, exchange=self.exchange_name)
            elif response.status == 404: # Not Found (e.g., order_id, product_id)
                 # Check if it's a product not found, which could imply market closed or delisted
                if "product_id" in error_message.lower() and ("not found" in error_message.lower() or "does not exist" in error_message.lower()):
                    raise MarketClosedError(f"Product not found or not available for trading: {error_message}", code=response.status, exchange=self.exchange_name)
                raise InvalidOrderError(f"Resource not found: {error_message}", code=response.status, exchange=self.exchange_name)
            elif response.status == 429: # Too Many Requests
                retry_after_seconds = response.headers.get('Retry-After')
                details = {}
                if retry_after_seconds:
                    try:
                        details['retry_after_seconds'] = int(retry_after_seconds)
                    except ValueError:
                        logger.warning(f"Could not parse Retry-After header value for {self.exchange_name}: {retry_after_seconds}")
                raise RateLimitError(error_message, code=response.status, exchange=self.exchange_name, details=details)
            elif response.status == 500 or response.status == 503: # Internal Server Error or Service Unavailable
                raise ExchangeError(f"Server error: {error_message}", code=response.status, exchange=self.exchange_name)
            else:
                raise ExchangeError(error_message, code=response.status, exchange=self.exchange_name)
        return data

    async def _signed_request(self, method: str, path: str, body_json: Optional[Dict] = None) -> Dict:
        """Make authenticated API request to Coinbase Pro"""
        await self._ensure_session()
        current_time = str(time.time())
        body_str = json.dumps(body_json) if body_json else ''
        message = current_time + method.upper() + path + body_str

        signature = hmac.new(base64.b64decode(self.api_secret), message.encode('utf-8'), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')

        headers = {
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': current_time,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        url = f"{self.BASE_URL}{path}"

        try:
            async with self.session.request(method.upper(), url, headers=headers, data=body_str) as response:
                return await self._handle_response(response, method, path)
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Network connection error for {self.exchange_name} {method} {path}: {e}")
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout for {self.exchange_name} {method} {path}: {e}")
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)
        except aiohttp.ClientError as e:
            logger.error(f"AIOHTTP client error for {self.exchange_name} {method} {path}: {e}")
            raise ExchangeError(f"HTTP client error: {e}", exchange=self.exchange_name)

    async def get_balances(self) -> Dict[str, Decimal]:
        path = "/accounts"
        response_data = await self._signed_request("GET", path)
        balances: Dict[str, Decimal] = {}
        for account in response_data:
            currency = account.get('currency')
            balance_str = account.get('available', '0')
            if currency and balance_str:
                try:
                    balance = Decimal(balance_str)
                    if balance > Decimal('0'):
                        balances[currency] = balance
                except Exception as e: # Handle cases where balance might not be a valid decimal
                    logger.warning(f"Could not parse balance for {currency} on {self.exchange_name}: {balance_str}. Error: {e}")
                    # Optionally raise a specific error or continue
        return balances

    async def get_ticker(self, symbol: str) -> Dict:
        path = f"/products/{symbol.upper()}/ticker"
        await self._ensure_session()
        url = f"{self.BASE_URL}{path}"
        try:
            async with self.session.get(url) as response: # Public endpoint
                return await self._handle_response(response, "GET", path)
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Network connection error for {self.exchange_name} GET {path}: {e}")
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout for {self.exchange_name} GET {path}: {e}")
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)
        except aiohttp.ClientError as e:
            logger.error(f"AIOHTTP client error for {self.exchange_name} GET {path}: {e}")
            raise ExchangeError(f"HTTP client error: {e}", exchange=self.exchange_name)


    async def create_order(self, symbol: str, side: str, type: str,
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        path = "/orders"
        payload: Dict[str, any] = {
            'product_id': symbol.upper(),
            'side': side.lower(),
            'type': type.lower(),
        }

        if type.lower() == 'limit':
            if price is None:
                raise InvalidOrderError("Price is required for limit orders.", exchange=self.exchange_name)
            payload['price'] = str(price)
            payload['size'] = str(amount)
            payload['post_only'] = False
        elif type.lower() == 'market':
            # For market orders, Coinbase Pro uses 'size' (for crypto amount) or 'funds' (for fiat amount)
            # This implementation uses 'size'. If 'funds' is needed, logic needs adjustment.
            payload['size'] = str(amount)
        else:
            raise InvalidOrderError(f"Unsupported order type: {type}", exchange=self.exchange_name)

        return await self._signed_request("POST", path, body_json=payload)

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        # Coinbase Pro's DELETE /orders/{order_id} does not require symbol in path or body.
        # Symbol might be useful for logging or if client_oid is used, but not for this specific API.
        path = f"/orders/{order_id}"
        response_data = await self._signed_request("DELETE", path)
        # Successful cancel returns 200 OK with the order_id in an array, e.g., ["id"]
        # or sometimes just the id as a string.
        if isinstance(response_data, list) and order_id in response_data:
            return {"status": "cancelled", "order_id": order_id, "response": response_data}
        if isinstance(response_data, str) and response_data == order_id: # some APIs might return just the ID
             return {"status": "cancelled", "order_id": order_id, "response": response_data}
        # If _handle_response didn't raise and we are here, it means 2xx status.
        # However, the response format for cancel might vary.
        # The _handle_response should have already validated success.
        # This part is more about confirming the expected payload structure for cancellation.
        logger.info(f"Order {order_id} cancellation confirmed by {self.exchange_name}. Response: {response_data}")
        return {"status": "cancelled_unknown_format", "order_id": order_id, "response": response_data}


    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        path = "/orders"
        # Coinbase API uses 'status' query param, which can be repeated.
        # aiohttp handles list params by repeating: status=open&status=pending
        params_list = [('status', 'open'), ('status', 'pending'), ('status', 'active')]
        if symbol:
            params_list.append(('product_id', symbol.upper()))

        # Reconstruct path with query parameters correctly for lists
        query_string = urllib.parse.urlencode(params_list)
        full_path = f"{path}?{query_string}" if query_string else path
        return await self._signed_request("GET", full_path) # Pass full_path, not path and body_json

    async def test_connection(self) -> bool:
        try:
            await self.get_balances()
            logger.info(f"{self.exchange_name} connection test successful.")
            return True
        except AuthenticationError as e:
            logger.error(f"{self.exchange_name} authentication failed: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"{self.exchange_name} connection failed: {e}")
            raise
        except ExchangeError as e:
            logger.error(f"{self.exchange_name} connection test failed with ExchangeError: {e}")
            raise
        except Exception as e:
            logger.error(f"{self.exchange_name} connection test failed with an unexpected error: {e}")
            raise ExchangeError(f"Unexpected error during {self.exchange_name} connection test: {e}", exchange=self.exchange_name)

    # --- Additional Coinbase Pro specific methods from original file, ensure they use new error handling ---
    async def get_order_status(self, order_id: str) -> Dict:
        path = f"/orders/{order_id}"
        return await self._signed_request("GET", path)

    async def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        path = "/orders"
        params_list = [('status', 'done'), ('status', 'rejected'), ('limit', str(limit))]
        if symbol:
            params_list.append(('product_id', symbol.upper()))
        query_string = urllib.parse.urlencode(params_list)
        full_path = f"{path}?{query_string}" if query_string else path
        return await self._signed_request("GET", full_path)

    async def get_order_book(self, symbol: str, level: int = 2) -> Dict:
        if level not in [1, 2, 3]:
            raise InvalidOrderError("Level must be 1, 2, or 3 for Coinbase Pro order book.", exchange=self.exchange_name)
        path = f"/products/{symbol.upper()}/book?level={level}" # Public endpoint
        await self._ensure_session()
        url = f"{self.BASE_URL}{path}"
        try:
            async with self.session.get(url) as response:
                return await self._handle_response(response, "GET", path)
        except aiohttp.ClientConnectorError as e:
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)

    async def get_recent_trades(self, symbol: str, limit: Optional[int] = None) -> List[Dict]:
        path = f"/products/{symbol.upper()}/trades"
        params = {}
        if limit is not None:
            params['limit'] = str(min(max(limit, 1), 100))
        query_string = urllib.parse.urlencode(params)
        full_path = f"{path}?{query_string}" if query_string else path # Public endpoint
        await self._ensure_session()
        url = f"{self.BASE_URL}{full_path}"
        try:
            async with self.session.get(url) as response:
                return await self._handle_response(response, "GET", full_path)
        except aiohttp.ClientConnectorError as e:
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)

    async def get_klines(self, symbol: str, interval: str, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: Optional[int] = None) -> List[List]:
        path_base = f"/products/{symbol.upper()}/candles"
        granularity_map = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400}
        if interval not in granularity_map:
            try: granularity = int(interval)
            except ValueError: raise InvalidOrderError(f"Unsupported interval: {interval}", exchange=self.exchange_name)
        else: granularity = granularity_map[interval]

        params_dict = {'granularity': str(granularity)}
        if start_time:
            params_dict['start'] = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        if end_time:
            params_dict['end'] = datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        # Coinbase Pro's /candles limit is implicitly 300 if not constrained by start/end.
        # The 'limit' param in func signature is not directly used by Coinbase API for /candles.

        query_string = urllib.parse.urlencode(params_dict)
        path = f"{path_base}?{query_string}" if query_string else path_base # Public endpoint
        await self._ensure_session()
        url = f"{self.BASE_URL}{path}"
        try:
            async with self.session.get(url) as response:
                return await self._handle_response(response, "GET", path)
        except aiohttp.ClientConnectorError as e:
            raise ConnectionError(f"Network connection error: {e}", exchange=self.exchange_name)
        except asyncio.TimeoutError as e:
            raise ConnectionError(f"Request timed out: {e}", exchange=self.exchange_name)
    async def create_oco_order(self, symbol: str, side: str, quantity: Decimal, price: Decimal,
                               stop_price: Decimal, stop_limit_price: Optional[Decimal] = None,
                               list_client_order_id: Optional[str] = None,
                               limit_client_order_id: Optional[str] = None,
                               stop_client_order_id: Optional[str] = None) -> Dict:
        """Coinbase Pro does not support native OCO orders via its standard API."""
        logger.warning(f"Native OCO orders are not supported by {self.exchange_name} via standard API.")
        raise NotImplementedError(f"Native OCO orders are not supported by {self.exchange_name} via standard API.")

    async def create_trailing_stop_order(self, symbol: str, side: str, quantity: Decimal,
                                         activation_price: Optional[Decimal] = None,
                                         callback_rate: Decimal = None,
                                         strategy_id: Optional[str] = None,
                                         working_type: Optional[str] = None) -> Dict:
        """Coinbase Pro does not support native server-side trailing stop orders via its standard API."""
        logger.warning(f"Native server-side trailing stop orders are not supported by {self.exchange_name} via standard API.")
        raise NotImplementedError(f"Native server-side trailing stop orders are not supported by {self.exchange_name} via standard API.")