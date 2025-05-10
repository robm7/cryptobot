from abc import ABC, abstractmethod
import logging
import ccxt.async_support as ccxt
from datetime import datetime, timedelta
import time
import asyncio
from prometheus_client import Counter, Gauge, Histogram
from collections import deque

logger = logging.getLogger(__name__) # Added logger

# Prometheus metrics
ORDER_ATTEMPTS = Counter('exchange_order_attempts', 'Total order attempts', ['symbol', 'side'])
ORDER_SUCCESS = Counter('exchange_order_success', 'Successful orders', ['symbol', 'side'])
ORDER_FAILURES = Counter('exchange_order_failures', 'Failed orders', ['symbol', 'side'])
ORDER_LATENCY = Histogram('exchange_order_latency', 'Order execution latency in seconds', ['symbol'])
CIRCUIT_STATE = Gauge('exchange_circuit_state', 'Circuit breaker state (0=closed, 1=open)')
ERROR_RATE = Gauge('exchange_error_rate', 'Current error rate percentage')

# Alert thresholds
ALERT_THRESHOLDS = {
    'error_rate': 30,  # Percentage
    'circuit_breaker_trips': 3,  # Per hour
    'consecutive_failures': 5,  # In a row
    'latency_p99': 2.0  # Seconds
}

class ExchangeInterface(ABC):
    """Abstract base class for exchange interactions."""

    def __init__(self, api_key=None, api_secret=None, testnet=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.error_window = deque(maxlen=100)  # Track last 100 errors
        self.circuit_open = False
        self.circuit_open_time = None
        self.circuit_timeout = 60  # 1 minute circuit breaker timeout
        logger.info(f"Initialized ExchangeInterface for {'Testnet' if testnet else 'Live'} environment.")

    def _check_circuit_breaker(self):
        """Check if circuit breaker should be opened based on recent errors"""
        if len(self.error_window) < 10:  # Need at least 10 samples
            return False
            
        error_rate = sum(self.error_window) / len(self.error_window)
        if error_rate > 0.5:  # Open circuit if >50% error rate
            self.circuit_open = True
            self.circuit_open_time = time.time()
            logger.error("Circuit breaker opened due to high error rate")
            return True
        return False

    def _is_circuit_open(self):
        """Check if circuit is still open"""
        if not self.circuit_open:
            return False
            
        if time.time() - self.circuit_open_time > self.circuit_timeout:
            self.circuit_open = False
            logger.info("Circuit breaker closed after timeout")
            return False
            
        return True

    @abstractmethod
    async def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = None):
        """Place an order on the exchange.

        Args:
            symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
            order_type (str): Type of order ('market', 'limit', etc.).
            side (str): 'buy' or 'sell'.
            amount (float): Quantity of the asset to trade.
            price (float, optional): Price for limit orders. Defaults to None.
            params (dict, optional): Additional exchange-specific parameters. Defaults to None.

        Returns:
            dict: Information about the placed order.
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str = None):
        """Cancel an existing order.

        Args:
            order_id (str): The ID of the order to cancel.
            symbol (str, optional): Trading pair symbol. Required by some exchanges.

        Returns:
            dict: Information about the cancellation attempt.
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str = None):
        """Get the status of a specific order.

        Args:
            order_id (str): The ID of the order.
            symbol (str, optional): Trading pair symbol. Required by some exchanges.

        Returns:
            dict: Information about the order status.
        """
        pass

    @abstractmethod
    async def get_balance(self, currency: str = None):
        """Get account balance information.

        Args:
            currency (str, optional): Specific currency to get balance for. Defaults to None (all balances).

        Returns:
            dict: Account balance details.
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str = None):
        """Get all open orders.

        Args:
            symbol (str, optional): Filter orders by symbol. Defaults to None (all symbols).

        Returns:
            list: A list of open orders.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict:
        """Get ticker information for a trading pair.

        Args:
            symbol (str): Trading pair symbol (e.g., 'BTC/USDT')

        Returns:
            dict: Ticker information including bid, ask, last price, etc.
        """
        pass

class MockExchangeInterface(ExchangeInterface):
    """A mock implementation for testing purposes."""
    
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        super().__init__(api_key, api_secret, testnet)
        self._last_price = {}
        self._orders = {}
        logger.info("Initialized MockExchangeInterface")

    async def get_ticker(self, symbol: str) -> dict:
        """Mock implementation of get_ticker"""
        logger.info(f"[Mock] Getting ticker for {symbol}")
        if symbol not in self._last_price:
            self._last_price[symbol] = 30000  # Default price for BTC/USDT
        return {
            'symbol': symbol,
            'bid': self._last_price[symbol] * 0.999,
            'ask': self._last_price[symbol] * 1.001,
            'last': self._last_price[symbol],
            'info': {'mock': True}
        }

    async def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = None):
        """Mock implementation of place_order"""
        order_id = f"mock_order_{len(self._orders) + 1}"
        order = {
            'id': order_id,
            'symbol': symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'price': price or self._last_price.get(symbol, 30000),
            'status': 'open',
            'info': {'mock': True}
        }
        self._orders[order_id] = order
        logger.info(f"[Mock] Placed order {order_id} for {symbol}")
        return order

    async def cancel_order(self, order_id: str, symbol: str = None):
        """Mock implementation of cancel_order"""
        if order_id not in self._orders:
            raise Exception("Order not found")
        self._orders[order_id]['status'] = 'canceled'
        logger.info(f"[Mock] Cancelled order {order_id}")
        return {'id': order_id, 'status': 'canceled', 'info': {'mock': True}}

    async def get_order_status(self, order_id: str, symbol: str = None):
        """Mock implementation of get_order_status"""
        if order_id not in self._orders:
            raise Exception("Order not found")
        return self._orders[order_id]

    async def get_balance(self, currency: str = None):
        """Mock implementation of get_balance"""
        balances = {
            'BTC': {'free': 1.0, 'used': 0.0, 'total': 1.0},
            'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0},
            'ETH': {'free': 10.0, 'used': 0.0, 'total': 10.0}
        }
        if currency:
            return balances.get(currency, {'free': 0.0, 'used': 0.0, 'total': 0.0})
        return {'info': {'mock': True}, **balances}

    async def get_open_orders(self, symbol: str = None):
        """Mock implementation of get_open_orders"""
        open_orders = [o for o in self._orders.values() if o['status'] == 'open']
        if symbol:
            open_orders = [o for o in open_orders if o['symbol'] == symbol]
        logger.info(f"[Mock] Found {len(open_orders)} open orders")
        return open_orders

class BinanceExchangeInterface(ExchangeInterface):
    """Implementation using the ccxt library with reliability enhancements."""
    
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        super().__init__(api_key, api_secret, testnet)
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if testnet else 'spot'
            }
        })
        logger.info("Initialized BinanceExchangeInterface")

    async def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = None):
        """Place an order on Binance"""
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )
            logger.info(f"Placed order {order['id']} for {symbol}")
            return order
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error placing order: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error placing order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str = None):
        """Cancel an order on Binance"""
        try:
            if not symbol:
                raise ValueError("Symbol is required for Binance order cancellation")
            result = await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id} for {symbol}")
            return result
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error cancelling order: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error cancelling order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling order: {e}")
            raise

    async def get_order_status(self, order_id: str, symbol: str = None):
        """Get order status from Binance"""
        try:
            if not symbol:
                raise ValueError("Symbol is required for Binance order status")
            order = await self.exchange.fetch_order(order_id, symbol)
            logger.debug(f"Order status for {order_id}: {order['status']}")
            return order
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting order status: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error getting order status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting order status: {e}")
            raise

    async def get_balance(self, currency: str = None):
        """Get account balance from Binance"""
        try:
            balance = await self.exchange.fetch_balance()
            if currency:
                return balance[currency]
            return balance
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting balance: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error getting balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting balance: {e}")
            raise

    async def get_open_orders(self, symbol: str = None):
        """Get open orders from Binance"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            logger.debug(f"Found {len(orders)} open orders")
            return orders
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting open orders: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error getting open orders: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting open orders: {e}")
            raise

    async def get_ticker(self, symbol: str) -> dict:
        """Get ticker information from Binance"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            logger.debug(f"Ticker data for {symbol}: {ticker}")
            return ticker
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching ticker: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching ticker: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching ticker: {e}")
            raise

class KrakenExchangeInterface(ExchangeInterface):
    """Implementation using the ccxt library with reliability enhancements."""
    
    def __init__(self, api_key=None, api_secret=None, testnet=False):
        super().__init__(api_key, api_secret, testnet)
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
        logger.info("Initialized KrakenExchangeInterface")

    async def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, params: dict = None):
        """Place an order on Kraken"""
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )
            logger.info(f"Placed order {order['id']} for {symbol}")
            return order
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error placing order: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error placing order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error placing order: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str = None):
        """Cancel an order on Kraken"""
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order {order_id}")
            return result
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error cancelling order: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error cancelling order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling order: {e}")
            raise

    async def get_order_status(self, order_id: str, symbol: str = None):
        """Get order status from Kraken"""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            logger.debug(f"Order status for {order_id}: {order['status']}")
            return order
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting order status: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error getting order status: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting order status: {e}")
            raise

    async def get_balance(self, currency: str = None):
        """Get account balance from Kraken"""
        try:
            balance = await self.exchange.fetch_balance()
            if currency:
                return balance[currency]
            return balance
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting balance: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error getting balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting balance: {e}")
            raise

    async def get_open_orders(self, symbol: str = None):
        """Get open orders from Kraken"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            logger.debug(f"Found {len(orders)} open orders")
            return orders
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error getting open orders: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error getting open orders: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting open orders: {e}")
            raise

    async def get_ticker(self, symbol: str) -> dict:
        """Get ticker information from Kraken"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            logger.debug(f"Ticker data for {symbol}: {ticker}")
            return ticker
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching ticker: {e}")
            raise
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching ticker: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching ticker: {e}")
            raise

    async def verify_order_execution(self, order_id: str, symbol: str) -> bool:
        """Verify an order was properly executed by checking exchange.
        
        Args:
            order_id: The exchange order ID
            symbol: Trading pair symbol
            
        Returns:
            bool: True if order is confirmed executed, False otherwise
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order['status'] == 'closed'
        except Exception as e:
            logger.error(f"Failed to verify order {order_id}: {e}")
            return False

    async def place_order_with_retry(self, symbol: str, order_type: str, side: str,
                                  amount: float, price: float = None,
                                  params: dict = None, max_retries: int = 3,
                                  retry_delay: float = 1.0,
                                  verify_execution: bool = True) -> dict:
        """Place an order with automatic retry logic for failed attempts.
        
        Args:
            symbol: Trading pair symbol
            order_type: Order type ('market', 'limit', etc.)
            side: 'buy' or 'sell'
            amount: Quantity to trade
            price: Price for limit orders
            params: Additional exchange parameters
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            verify_execution: Whether to verify order execution with exchange
            
        Returns:
            Order information if successful
            
        Raises:
            Exception: If order fails after all retry attempts or circuit is open
        """
        # Update metrics
        ORDER_ATTEMPTS.labels(symbol=symbol, side=side).inc()
        CIRCUIT_STATE.set(1 if self._is_circuit_open() else 0)
        ERROR_RATE.set((sum(self.error_window)/len(self.error_window))*100 if self.error_window else 0)
        
        if self._is_circuit_open():
            ORDER_FAILURES.labels(symbol=symbol, side=side).inc()
            raise Exception("Circuit breaker is open - no orders allowed")
            
        attempt = 0
        last_error = None
        start_time = time.time()
        
        while attempt < max_retries:
            try:
                result = await self.place_order(symbol, order_type, side,
                                             amount, price, params)
                
                # Verify execution if requested
                if verify_execution:
                    if not await self.verify_order_execution(result['id'], symbol):
                        raise Exception("Order execution verification failed")
                
                # Record success metrics
                self.error_window.append(0)
                ORDER_SUCCESS.labels(symbol=symbol, side=side).inc()
                ORDER_LATENCY.labels(symbol=symbol).observe(time.time() - start_time)
                return result
            except Exception as e:
                attempt += 1
                last_error = e
                self.error_window.append(1)
                self._check_circuit_breaker()
                
                # Update metrics
                ORDER_FAILURES.labels(symbol=symbol, side=side).inc()
                CIRCUIT_STATE.set(1 if self._is_circuit_open() else 0)
                ERROR_RATE.set((sum(self.error_window)/len(self.error_window))*100)
                
                logger.warning(f"Order attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries and not self._is_circuit_open():
                    await asyncio.sleep(retry_delay * attempt)  # Exponential backoff
                else:
                    break
                    
        if self._is_circuit_open():
            logger.error("Order failed - circuit breaker is open")
            raise Exception("Circuit breaker is open - order rejected")
        else:
            logger.error(f"Order failed after {attempt} attempts")
            raise last_error
        """Place an order with automatic retry logic for failed attempts.
        
        Args:
            symbol: Trading pair symbol
            order_type: Order type ('market', 'limit', etc.)
            side: 'buy' or 'sell'
            amount: Quantity to trade
            price: Price for limit orders
            params: Additional exchange parameters
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Order information if successful
            
        Raises:
            Exception: If order fails after all retry attempts or circuit is open
        """
        # Update metrics
        ORDER_ATTEMPTS.labels(symbol=symbol, side=side).inc()
        CIRCUIT_STATE.set(1 if self._is_circuit_open() else 0)
        ERROR_RATE.set((sum(self.error_window)/len(self.error_window))*100 if self.error_window else 0)
        
        if self._is_circuit_open():
            ORDER_FAILURES.labels(symbol=symbol, side=side).inc()
            raise Exception("Circuit breaker is open - no orders allowed")
            
        attempt = 0
        last_error = None
        start_time = time.time()
        
        while attempt < max_retries:
            try:
                result = await self.place_order(symbol, order_type, side,
                                             amount, price, params)
                # Record success metrics
                self.error_window.append(0)
                ORDER_SUCCESS.labels(symbol=symbol, side=side).inc()
                ORDER_LATENCY.labels(symbol=symbol).observe(time.time() - start_time)
                return result
            except (ccxt.ExchangeError, ccxt.NetworkError) as e:
                attempt += 1
                last_error = e
                self.error_window.append(1)
                self._check_circuit_breaker()
                
                # Update metrics
                ORDER_FAILURES.labels(symbol=symbol, side=side).inc()
                CIRCUIT_STATE.set(1 if self._is_circuit_open() else 0)
                ERROR_RATE.set((sum(self.error_window)/len(self.error_window))*100)
                
                logger.warning(f"Order attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries and not self._is_circuit_open():
                    await asyncio.sleep(retry_delay * attempt)  # Exponential backoff
                else:
                    break
                    
        if self._is_circuit_open():
            logger.error("Order failed - circuit breaker is open")
            raise Exception("Circuit breaker is open - order rejected")
        else:
            logger.error(f"Order failed after {attempt} attempts")
            raise last_error


def get_exchange_interface(exchange_name: str, api_key: str = None, api_secret: str = None, testnet: bool = False) -> ExchangeInterface:
    """Factory function to create exchange interface instances."""
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'binance':
        return BinanceExchangeInterface(api_key, api_secret, testnet)
    elif exchange_name == 'kraken':
        return KrakenExchangeInterface(api_key, api_secret, testnet)
    elif exchange_name == 'mock':
        return MockExchangeInterface(api_key, api_secret, testnet)
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}")