import os
import ccxt
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from collections import deque

# Configure logging
logger = logging.getLogger(__name__)

# Rate limit tracking per exchange
RATE_LIMIT_TRACKERS = {}

class RateLimitTracker:
    """Tracks API usage and enforces rate limits"""
    
    def __init__(self, exchange_id, max_requests_per_minute=60, max_requests_per_hour=1200):
        self.exchange_id = exchange_id
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_hour = max_requests_per_hour
        self.minute_requests = deque(maxlen=60)  # Track last minute of requests
        self.hour_requests = deque(maxlen=3600)  # Track last hour of requests
        self.last_request_time = 0
        logger.info(f"Initialized rate limit tracker for {exchange_id}")
    
    def record_request(self):
        """Record an API request"""
        now = time.time()
        self.minute_requests.append(now)
        self.hour_requests.append(now)
        self.last_request_time = now
    
    def should_throttle(self) -> tuple[bool, float]:
        """
        Check if requests should be throttled
        
        Returns:
            tuple: (should_throttle, wait_time_seconds)
        """
        now = time.time()
        
        # Clean up old entries
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Count recent requests
        minute_count = sum(1 for t in self.minute_requests if t > minute_ago)
        hour_count = sum(1 for t in self.hour_requests if t > hour_ago)
        
        # Check if approaching limits
        minute_usage = minute_count / self.max_requests_per_minute
        hour_usage = hour_count / self.max_requests_per_hour
        
        # If over 80% of either limit, start throttling
        if minute_usage > 0.8 or hour_usage > 0.8:
            # Calculate wait time based on most restrictive limit
            if minute_usage > hour_usage:
                # Wait until we're under 80% of minute limit
                wait_time = 60 - (now - self.minute_requests[0])
            else:
                # Wait until we're under 80% of hour limit
                wait_time = 3600 - (now - self.hour_requests[0])
                
            # Ensure wait time is reasonable
            wait_time = max(0.5, min(wait_time, 30))
            return True, wait_time
            
        return False, 0

class ExchangeError(Exception):
    """Base class for exchange-related errors"""
    pass

class RateLimitError(ExchangeError):
    """Raised when rate limits are exceeded"""
    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after

class NetworkError(ExchangeError):
    """Raised for network-related issues"""
    pass

class AuthenticationError(ExchangeError):
    """Raised for authentication failures"""
    pass

class OrderError(ExchangeError):
    """Raised for order-related errors"""
    pass

class ExchangeClient:
    """Wrapper class for exchange client operations with enhanced reliability"""
    
    def __init__(self, exchange='kraken', paper_trading=False):
        self.client = get_exchange_client(exchange, paper_trading)
        self.paper_trading = paper_trading
        self.exchange_id = exchange.lower()
        
        # Initialize rate limit tracker if not exists
        if self.exchange_id not in RATE_LIMIT_TRACKERS:
            if self.exchange_id == 'binance':
                RATE_LIMIT_TRACKERS[self.exchange_id] = RateLimitTracker(
                    self.exchange_id,
                    max_requests_per_minute=1200,  # Binance limits
                    max_requests_per_hour=48000
                )
            elif self.exchange_id == 'kraken':
                RATE_LIMIT_TRACKERS[self.exchange_id] = RateLimitTracker(
                    self.exchange_id,
                    max_requests_per_minute=60,  # Kraken limits
                    max_requests_per_hour=1000
                )
            else:
                RATE_LIMIT_TRACKERS[self.exchange_id] = RateLimitTracker(self.exchange_id)
                
        self.rate_limiter = RATE_LIMIT_TRACKERS[self.exchange_id]
        logger.info(f"Initialized ExchangeClient for {exchange} (Paper Trading: {paper_trading})")
    
    async def _handle_rate_limits(self):
        """Handle rate limiting before making API calls"""
        should_throttle, wait_time = self.rate_limiter.should_throttle()
        if should_throttle:
            logger.warning(f"Rate limit throttling for {self.exchange_id}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self.rate_limiter.record_request()
    
    async def get_ohlcv(self, symbol, timeframe, limit=100):
        """Get OHLCV data from exchange with rate limit handling"""
        await self._handle_rate_limits()
        
        try:
            return self.client.fetch_ohlcv(symbol, timeframe, limit=limit)
        except ccxt.RateLimitExceeded as e:
            retry_after = self._extract_retry_after(e)
            logger.warning(f"Rate limit exceeded for {self.exchange_id}: {e}, retry after {retry_after}s")
            raise RateLimitError(f"Rate limit exceeded: {e}", retry_after=retry_after)
        except ccxt.NetworkError as e:
            logger.error(f"Network error for {self.exchange_id}: {e}")
            raise NetworkError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise ExchangeError(f"Error fetching OHLCV data: {e}")
    
    async def create_order(self, symbol, type, side, amount, price=None, params=None):
        """Create an order on the exchange with enhanced error handling"""
        if params is None:
            params = {}
            
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Would create {type} order: {side} {amount} {symbol} @ {price}")
            return {
                'id': 'PAPER-' + str(hash(str((symbol, type, side, amount, price)))),
                'status': 'open',
                'symbol': symbol,
                'type': type,
                'side': side,
                'amount': amount,
                'price': price,
                'timestamp': datetime.now().timestamp() * 1000,
                'datetime': datetime.now().isoformat()
            }
            
        await self._handle_rate_limits()
        
        try:
            return self.client.create_order(symbol, type, side, amount, price, params)
        except ccxt.RateLimitExceeded as e:
            retry_after = self._extract_retry_after(e)
            logger.warning(f"Rate limit exceeded for {self.exchange_id}: {e}, retry after {retry_after}s")
            raise RateLimitError(f"Rate limit exceeded: {e}", retry_after=retry_after)
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for {self.exchange_id}: {e}")
            raise OrderError(f"Insufficient funds: {e}")
        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid order for {self.exchange_id}: {e}")
            raise OrderError(f"Invalid order: {e}")
        except ccxt.NetworkError as e:
            logger.error(f"Network error for {self.exchange_id}: {e}")
            raise NetworkError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise ExchangeError(f"Error creating order: {e}")

    async def create_oco_order(self, symbol, side, amount, price, stop_price, stop_limit_price=None, params=None):
        """
        Create a One-Cancels-Other (OCO) order
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order quantity
            price: Limit order price
            stop_price: Stop trigger price
            stop_limit_price: Optional price for stop-limit (defaults to stop_price)
            params: Additional exchange-specific parameters
            
        Returns:
            dict: Order information
        """
        if params is None:
            params = {}
            
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Would create OCO order: {side} {amount} {symbol} @ {price} / stop {stop_price}")
            return {
                'id': 'PAPER-OCO-' + str(hash(str((symbol, side, amount, price, stop_price)))),
                'status': 'open',
                'symbol': symbol,
                'type': 'oco',
                'side': side,
                'amount': amount,
                'price': price,
                'stop_price': stop_price,
                'timestamp': datetime.now().timestamp() * 1000,
                'datetime': datetime.now().isoformat()
            }
            
        await self._handle_rate_limits()
        
        try:
            if self.exchange_id == 'binance':
                # Binance-specific OCO implementation
                if stop_limit_price is None:
                    stop_limit_price = stop_price
                    
                oco_params = {
                    'stopPrice': stop_price,
                    'stopLimitPrice': stop_limit_price,
                    'stopLimitTimeInForce': 'GTC',
                    **params
                }
                
                return self.client.create_order(
                    symbol=symbol,
                    type='oco',
                    side=side,
                    amount=amount,
                    price=price,
                    params=oco_params
                )
            elif self.exchange_id == 'kraken':
                # Kraken doesn't support OCO directly, so we create two orders
                # and manage them ourselves
                
                # Create the limit order
                limit_order = await self.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side,
                    amount=amount,
                    price=price
                )
                
                # Create the stop order
                stop_params = {'stopLoss': {'price': stop_price}}
                if stop_limit_price:
                    stop_params['stopLoss']['price2'] = stop_limit_price
                    
                stop_order = await self.create_order(
                    symbol=symbol,
                    type='stop',
                    side=side,
                    amount=amount,
                    price=stop_price,
                    params=stop_params
                )
                
                # Return combined info
                return {
                    'id': f"{limit_order['id']}+{stop_order['id']}",
                    'status': 'open',
                    'symbol': symbol,
                    'type': 'oco',
                    'side': side,
                    'amount': amount,
                    'price': price,
                    'stop_price': stop_price,
                    'limit_order_id': limit_order['id'],
                    'stop_order_id': stop_order['id'],
                    'timestamp': datetime.now().timestamp() * 1000,
                    'datetime': datetime.now().isoformat()
                }
            else:
                raise ExchangeError(f"OCO orders not supported for {self.exchange_id}")
        except Exception as e:
            logger.error(f"Error creating OCO order: {e}")
            raise OrderError(f"Error creating OCO order: {e}")

    async def create_trailing_stop_order(self, symbol, side, amount, activation_price=None,
                                       callback_rate=None, params=None):
        """
        Create a trailing stop order
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order quantity
            activation_price: Price at which trailing stop becomes active
            callback_rate: Callback rate in percentage (e.g., 1.0 for 1%)
            params: Additional exchange-specific parameters
            
        Returns:
            dict: Order information
        """
        if params is None:
            params = {}
            
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Would create trailing stop: {side} {amount} {symbol} @ {activation_price} with {callback_rate}% callback")
            return {
                'id': 'PAPER-TRAILING-' + str(hash(str((symbol, side, amount, activation_price, callback_rate)))),
                'status': 'open',
                'symbol': symbol,
                'type': 'trailing_stop',
                'side': side,
                'amount': amount,
                'activation_price': activation_price,
                'callback_rate': callback_rate,
                'timestamp': datetime.now().timestamp() * 1000,
                'datetime': datetime.now().isoformat()
            }
            
        await self._handle_rate_limits()
        
        try:
            if self.exchange_id == 'binance':
                # Binance-specific trailing stop implementation
                trailing_params = {
                    'type': 'TRAILING_STOP_MARKET',
                    'callbackRate': callback_rate,
                    **params
                }
                
                if activation_price:
                    trailing_params['activationPrice'] = activation_price
                    
                return self.client.create_order(
                    symbol=symbol,
                    type='trailing_stop_market',
                    side=side,
                    amount=amount,
                    params=trailing_params
                )
            elif self.exchange_id == 'kraken':
                # Kraken trailing stop implementation
                trailing_params = {
                    'trailingStopDeactivationPrice': activation_price,
                    'trailingStopOffset': callback_rate,
                    **params
                }
                
                return self.client.create_order(
                    symbol=symbol,
                    type='trailing_stop',
                    side=side,
                    amount=amount,
                    params=trailing_params
                )
            else:
                raise ExchangeError(f"Trailing stop orders not supported for {self.exchange_id}")
        except Exception as e:
            logger.error(f"Error creating trailing stop order: {e}")
            raise OrderError(f"Error creating trailing stop order: {e}")

    async def cancel_order(self, order_id, symbol=None):
        """Cancel an order on the exchange with enhanced error handling"""
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Would cancel order {order_id}")
            return True
            
        await self._handle_rate_limits()
        
        try:
            # Some exchanges require symbol for cancellation
            if symbol and self.exchange_id in ['binance', 'kraken']:
                return self.client.cancel_order(order_id, symbol)
            return self.client.cancel_order(order_id)
        except ccxt.OrderNotFound as e:
            logger.warning(f"Order not found for cancellation: {order_id}")
            return False
        except ccxt.RateLimitExceeded as e:
            retry_after = self._extract_retry_after(e)
            logger.warning(f"Rate limit exceeded for {self.exchange_id}: {e}, retry after {retry_after}s")
            raise RateLimitError(f"Rate limit exceeded: {e}", retry_after=retry_after)
        except ccxt.NetworkError as e:
            logger.error(f"Network error for {self.exchange_id}: {e}")
            raise NetworkError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise ExchangeError(f"Error cancelling order: {e}")

    async def get_balances(self):
        """Get account balances with enhanced error handling"""
        if self.paper_trading:
            logger.info("[PAPER TRADING] Returning mock balances")
            return {
                'USD': 10000.00,
                'BTC': 0.5
            }
            
        await self._handle_rate_limits()
        
        try:
            return await self.client.fetch_balance() # Added await
        except ccxt.AuthenticationError as e:
            logger.error(f"Authentication error for {self.exchange_id}: {e}")
            raise AuthenticationError(f"Authentication error: {e}")
        except ccxt.RateLimitExceeded as e:
            retry_after = self._extract_retry_after(e)
            logger.warning(f"Rate limit exceeded for {self.exchange_id}: {e}, retry after {retry_after}s")
            raise RateLimitError(f"Rate limit exceeded: {e}", retry_after=retry_after)
        except ccxt.NetworkError as e:
            logger.error(f"Network error for {self.exchange_id}: {e}")
            raise NetworkError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
            raise ExchangeError(f"Error fetching balances: {e}")
    
    def _extract_retry_after(self, exception):
        """Extract retry-after time from exception if available"""
        retry_after = 60  # Default retry after 60 seconds
        
        try:
            # Try to extract from exception message
            if hasattr(exception, 'response'):
                response = exception.response
                if hasattr(response, 'headers') and 'Retry-After' in response.headers:
                    retry_after = int(response.headers['Retry-After'])
                elif hasattr(response, 'json'):
                    json_data = response.json()
                    if 'retryAfter' in json_data:
                        retry_after = int(json_data['retryAfter'])
        except Exception:
            pass
            
        return retry_after

def get_exchange_client(exchange='kraken', paper_trading=False):
    """
    Initialize and return a ccxt client for the specified exchange.
    Supported exchanges: 'kraken', 'binance'
    """
    exchange = exchange.lower()
    
    if exchange == 'kraken':
        if paper_trading:
            api_key = os.getenv("KRAKEN_PAPER_API_KEY")
            api_secret = os.getenv("KRAKEN_PAPER_API_SECRET")
            if not api_key or not api_secret:
                raise ValueError("KRAKEN_PAPER_API_KEY and/or KRAKEN_PAPER_API_SECRET not set in environment variables.")
        else:
            api_key = os.getenv("KRAKEN_API_KEY")
            api_secret = os.getenv("KRAKEN_API_SECRET")
            if not api_key or not api_secret:
                raise ValueError("KRAKEN_API_KEY and/or KRAKEN_API_SECRET not set in environment variables.")
        
        return ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Enable built-in rate limiting
            'options': {
                'recvWindow': 60000  # Extended window for requests
            }
        })
    elif exchange == 'binance':
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and/or BINANCE_API_SECRET not set in environment variables.")
        return ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Enable built-in rate limiting
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000,  # Extended window for requests
                'defaultType': 'spot'  # Default to spot trading
            }
        })
    else:
        raise ValueError(f"Unsupported exchange: {exchange}")