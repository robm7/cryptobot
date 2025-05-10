import asyncio
import json
import logging
import time
from typing import Callable, Dict, Optional
import aiohttp
from aiohttp import ClientWebSocketResponse
from prometheus_client import Counter, Gauge, Histogram

class BinanceWebSocket:
    """WebSocket client for Binance real-time data"""
    
    BASE_URL = "wss://stream.binance.com:9443/ws"
    
    def __init__(self):
        # Metrics
        self._metrics = {
            'rate_limit_events': Counter(
                'websocket_rate_limit_events_total',
                'Total rate limit events',
                ['endpoint']
            ),
            'circuit_state': Gauge(
                'websocket_circuit_state',
                'Current circuit breaker state',
                ['state']
            ),
            'request_errors': Counter(
                'websocket_request_errors_total',
                'Total request errors',
                ['error_type']
            ),
            'request_latency': Histogram(
                'websocket_request_latency_seconds',
                'Request latency distribution',
                buckets=[0.1, 0.5, 1, 2, 5]
            )
        }

        self._ws: Optional[ClientWebSocketResponse] = None
        self._session = aiohttp.ClientSession()
        self._callbacks = {}
        self._running = False
        self._rate_limits = {
            'orders': {'limit': 10, 'remaining': 10, 'reset': 0},
            'streams': {'limit': 5, 'remaining': 5, 'reset': 0}
        }
        self._last_request = 0
        self._circuit_state = 'closed'  # closed, open, half-open
        self._error_count = 0
        self._last_error_time = 0
        self._circuit_reset_time = 0
        
    async def connect(self):
        """Establish WebSocket connection"""
        if self._ws is not None and not self._ws.closed:
            return
            
        self._ws = await self._session.ws_connect(self.BASE_URL)
        self._running = True
        asyncio.create_task(self._listen())
        
    async def _listen(self):
        """Listen for incoming messages"""
        while self._running and self._ws and not self._ws.closed:
            try:
                msg = await self._ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    stream = data.get('stream')
                    if stream in self._callbacks:
                        self._callbacks[stream](data)
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
                await self._reconnect()
                
    async def _check_rate_limit(self, endpoint: str) -> bool:
        """Check if request is allowed by rate limits"""
        now = time.time()
        limit = self._rate_limits[endpoint]
        
        if now > limit['reset']:
            limit['remaining'] = limit['limit']
            limit['reset'] = now + 60  # Reset after 60 seconds
            
        if limit['remaining'] <= 0:
            retry_after = max(0, limit['reset'] - now)
            logging.warning(f"Rate limited on {endpoint}, retrying in {retry_after:.1f}s")
            self._metrics['rate_limit_events'].labels(endpoint=endpoint).inc()
            await asyncio.sleep(retry_after)
            return False
            
        limit['remaining'] -= 1
        self._last_request = now
        return True

    def _update_rate_limits(self, headers: Dict[str, str]):
        """Update rate limits from API response headers"""
        start_time = time.time()
        if 'x-mbx-used-weight-1m' in headers:
            used = int(headers['x-mbx-used-weight-1m'])
            limit = int(headers.get('x-mbx-weight-1m', 1200))
            remaining = max(0, limit - used)
            
            self._rate_limits['orders']['limit'] = limit // 10
            self._rate_limits['orders']['remaining'] = remaining // 10
            self._rate_limits['orders']['reset'] = time.time() + 60
            
        if 'x-mbx-order-count-1m' in headers:
            used = int(headers['x-mbx-order-count-1m'])
            limit = int(headers.get('x-mbx-order-count-limit-1m', 50))
            remaining = max(0, limit - used)
            
            self._rate_limits['streams']['limit'] = limit // 5
            self._rate_limits['streams']['remaining'] = remaining // 5
            self._rate_limits['streams']['reset'] = time.time() + 60

    async def subscribe(self, stream: str, callback: Callable[[Dict], None]):
        """Subscribe to market data stream with rate limiting"""
        if not self._ws or self._ws.closed:
            await self.connect()
            
        if not await self._check_rate_limit('streams'):
            logging.warning("Rate limited - waiting to subscribe")
            return
            
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": [stream],
            "id": 1
        }
        await self._ws.send_json(subscribe_msg)
        self._callbacks[stream] = callback
        
    async def subscribe_depth(self, symbol: str, levels: int = 20):
        """Subscribe to order book depth updates"""
        stream = f"{symbol.lower()}@depth{levels}@100ms"
        await self.subscribe(stream, self._handle_depth_update)

    async def subscribe_user_data(self, listen_key: str):
        """Subscribe to user data stream (orders, executions)"""
        stream = f"{listen_key}"
        await self.subscribe(stream, self._handle_user_data)

    def _handle_user_data(self, msg: Dict):
        """Process user data updates (orders, executions)"""
        if msg['e'] == 'executionReport':
            self._callbacks['execution']({
                'order_id': msg['c'],
                'symbol': msg['s'],
                'side': msg['S'],
                'price': Decimal(msg['p']),
                'quantity': Decimal(msg['q']),
                'status': msg['X'],
                'timestamp': msg['E']
            })
        
    def _handle_depth_update(self, msg: Dict):
        """Process order book depth updates"""
        data = msg['data']
        symbol = data['s']
        bids = {Decimal(price): Decimal(amount) for price, amount in data['b']}
        asks = {Decimal(price): Decimal(amount) for price, amount in data['a']}
        self._callbacks[f'depth_{symbol}']({
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': data['E']
        })
        
    async def _reconnect(self):
        """Handle reconnection with circuit breaker"""
        # Update circuit state metrics
        self._metrics['circuit_state'].labels(state='closed').set(1 if self._circuit_state == 'closed' else 0)
        self._metrics['circuit_state'].labels(state='open').set(1 if self._circuit_state == 'open' else 0)
        self._metrics['circuit_state'].labels(state='half-open').set(1 if self._circuit_state == 'half-open' else 0)
        now = time.time()
        
        if self._circuit_state == 'open':
            if now < self._circuit_reset_time:
                return
            self._circuit_state = 'half-open'
            
        try:
            await self.connect()
            if self._circuit_state == 'half-open':
                self._circuit_state = 'closed'
                self._error_count = 0
        except Exception as e:
            self._error_count += 1
            self._last_error_time = now
            
            if self._error_count > 5 or (now - self._last_error_time < 10 and self._error_count > 2):
                self._circuit_state = 'open'
                self._circuit_reset_time = now + min(300, 5 * (2 ** self._error_count))  # Exponential backoff
                logging.error(f"Circuit breaker tripped! Will retry in {self._circuit_reset_time - now:.1f}s")
            
            await asyncio.sleep(5)
        
    async def close(self):
        """Close WebSocket connection"""
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        await self._session.close()