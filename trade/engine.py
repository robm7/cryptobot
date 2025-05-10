from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable, Type, Dict
import asyncio
from datetime import datetime
from decimal import Decimal
from .utils.exchange import ExchangeInterface
from .utils.retry import async_retry
from .utils.websocket import BinanceWebSocket

class OrderStatus(Enum):
    PENDING = auto()
    OPEN = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()

@dataclass
class Order:
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    type: str  # 'limit', 'market', etc
    amount: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

class TradingEngine:
    def __init__(self, exchange: Type[ExchangeInterface], api_key: str, api_secret: str):
        self.orders = {}
        self._order_listeners = []
        self._price_listeners = []
        self.exchange = exchange(api_key, api_secret)
        self.websocket = BinanceWebSocket()
        self._current_prices: Dict[str, Decimal] = {}
        self._order_books: Dict[str, Dict[str, Dict[Decimal, Decimal]]] = {}
        self._depth_listeners = []
        
    @async_retry(max_retries=3, delay=1)
    async def start(self):
        """Start WebSocket connections"""
        await self.websocket.connect()
        await self._setup_market_data()
        listen_key = await self.exchange.get_listen_key()
        await self.websocket.subscribe_user_data(listen_key)
        
        # Register execution handler
        async def handle_execution(msg):
            order_id = msg['order_id']
            status = {
                'NEW': OrderStatus.OPEN,
                'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
                'FILLED': OrderStatus.FILLED,
                'CANCELED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED
            }.get(msg['status'], OrderStatus.PENDING)
            
            if order_id in self.orders:
                await self._update_order_status(order_id, status)
        
        self.websocket._callbacks['execution'] = handle_execution

    async def _setup_market_data(self):
        """Subscribe to relevant market data streams"""
        async def handle_ticker(msg):
            data = msg['data']
            symbol = data['s']
            price = Decimal(data['c'])
            self._current_prices[symbol] = price
            for callback in self._price_listeners:
                await callback(symbol, price)

        async def handle_depth(msg):
            symbol = msg['symbol']
            self._order_books[symbol] = {
                'bids': msg['bids'],
                'asks': msg['asks']
            }
            for callback in self._depth_listeners:
                await callback(symbol, msg['bids'], msg['asks'])

        await self.websocket.subscribe(
            f"!ticker@arr",
            handle_ticker
        )
        await self.websocket.subscribe_depth("BTCUSDT")

    def add_price_listener(self, callback: Callable[[str, Decimal], None]):
        """Register callback for price updates"""
        self._price_listeners.append(callback)

    def add_depth_listener(self, callback: Callable[[str, Dict[Decimal, Decimal], Dict[Decimal, Decimal]], None]):
        """Register callback for price updates"""
        self._price_listeners.append(callback)

    async def place_order(self, order: Order) -> Order:
        """Place a new order and track its lifecycle"""
        self.orders[order.id] = order
        try:
            exchange_order = await self.exchange.create_order(
                symbol=order.symbol,
                side=order.side,
                type=order.type,
                amount=Decimal(str(order.amount)),
                price=Decimal(str(order.price)) if order.price else None
            )
            order.id = exchange_order['orderId']
            await self._update_order_status(order.id, OrderStatus.OPEN)
            return order
        except Exception as e:
            await self._update_order_status(order.id, OrderStatus.REJECTED)
            raise
        
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        if order_id in self.orders:
            await self._update_order_status(order_id, OrderStatus.CANCELLED)
            return True
        return False
        
    def add_order_listener(self, callback: Callable[[Order], None]):
        """Register callback for order updates"""
        self._order_listeners.append(callback)
        
    async def _update_order_status(self, order_id: str, status: OrderStatus):
        """Internal method to update order status"""
        order = self.orders[order_id]
        order.status = status
        order.updated_at = datetime.now()
        
        # Notify listeners
        for callback in self._order_listeners:
            await callback(order)