from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable, Type, Dict, List, Tuple, Union
import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from .utils.exchange import ExchangeInterface, BinanceExchange, CoinbaseProExchange
from .utils.retry import async_retry
from .utils.websocket import BinanceWebSocket # TODO: Generalize WebSocket handling
from .services.risk_manager import RiskManager
from .services.portfolio_manager import PortfolioManager
from .utils.metrics import MetricsCollector
from .utils.alerting import AlertManager
from .config.risk_config import risk_config
from .config import exchange_config # Import new exchange_config
from config.settings import settings # Added for DRY_RUN (initial default)
from core.runtime_settings import RuntimeSettings # For dynamic DRY_RUN status
from services.mcp.risk_management.basic_rules import BasicRiskRules

logger = logging.getLogger(__name__)

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
    def __init__(self, exchange_name: str):
        self.orders = {}
        self._order_listeners = []
        self._price_listeners = []
        self.exchange_name = exchange_name.lower()
        
        if self.exchange_name == "binance":
            # Assuming generic keys in config are for Binance for now, or update config to have BINANCE_API_KEY etc.
            # For this example, let's assume exchange_config.api_key and api_secret are for Binance
            # This part might need refinement based on how Binance keys are stored in your final config.
            # If exchange_config.get_exchange_config("binance") provides them, use that.
            # Let's assume for now the generic os.getenv("EXCHANGE_API_KEY") are for Binance.
            api_key = exchange_config.api_key
            api_secret = exchange_config.api_secret
            if not api_key or not api_secret:
                raise ValueError("Binance API key and secret must be configured.")
            self.exchange: ExchangeInterface = BinanceExchange(api_key=api_key, api_secret=api_secret)
            self.websocket = BinanceWebSocket() # Specific to Binance
        elif self.exchange_name == "coinbasepro":
            cb_creds = exchange_config.get_coinbase_pro_credentials()
            if not cb_creds["api_key"] or not cb_creds["api_secret"] or not cb_creds["passphrase"]:
                raise ValueError("Coinbase Pro API key, secret, and passphrase must be configured.")
            self.exchange: ExchangeInterface = CoinbaseProExchange(
                api_key=cb_creds["api_key"],
                api_secret=cb_creds["api_secret"],
                passphrase=cb_creds["passphrase"]
            )
            # TODO: Implement or select a WebSocket client for Coinbase Pro if needed for real-time updates.
            # For now, some functionalities relying on WebSocket might be limited for Coinbase Pro.
            self.websocket = None # Placeholder, as BinanceWebSocket is specific
            logger.warning("WebSocket functionality is not yet implemented for Coinbase Pro in TradingEngine.")
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        self._current_prices: Dict[str, Decimal] = {}
        self._order_books: Dict[str, Dict[str, Dict[Decimal, Decimal]]] = {}
        self._depth_listeners = []
        
        # Initialize portfolio manager
        self.portfolio_manager = PortfolioManager()
        
        # Initialize metrics collector
        self.metrics_collector = MetricsCollector()
        
        # Initialize risk manager
        self.risk_manager = RiskManager(self.portfolio_manager, self.metrics_collector)

        # Initialize basic risk rules
        self.basic_risk_rules = BasicRiskRules()
        
        # Initialize alert manager
        self.alert_manager = AlertManager()
        
        # Risk monitoring flag
        self.risk_monitoring_enabled = True
        
    @async_retry(max_retries=3, delay=1)
    async def start(self):
        """Start WebSocket connections and risk monitoring"""
        # Start WebSocket connections (if available)
        if self.websocket:
            await self.websocket.connect()
            await self._setup_market_data() # This uses self.websocket
            if hasattr(self.exchange, 'get_listen_key'): # Binance specific
                listen_key = await self.exchange.get_listen_key()
                await self.websocket.subscribe_user_data(listen_key)
        else:
            logger.info(f"WebSocket not available or not started for {self.exchange_name}.")
        
        # Register execution handler (if websocket available)
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
                
                # Update portfolio if order is filled
                if status == OrderStatus.FILLED and 'price' in msg and 'quantity' in msg:
                    symbol = self.orders[order_id].symbol
                    side = self.orders[order_id].side
                    price = Decimal(str(msg['price']))
                    quantity = Decimal(str(msg['quantity']))
                    
                    # Adjust quantity sign based on side
                    if side == 'sell':
                        quantity = -quantity
                    
                    # Update portfolio
                    await self.portfolio_manager.add_position(symbol, quantity, price)
                    
                    # Record metrics
                    self.metrics_collector.record_counter(f"trades.count.{symbol}", 1)
                    self.metrics_collector.record_counter("trades.count.total", 1)
        
        if self.websocket and hasattr(self.websocket, '_callbacks'):
            self.websocket._callbacks['execution'] = handle_execution
        
        # Start risk monitoring
        if self.risk_monitoring_enabled:
            await self.risk_manager.start_monitoring()
        
        # Start metrics exporting
        await self.metrics_collector.start_exporting()
        
        logger.info("Trading engine started with risk management integration")

    async def _setup_market_data(self):
        """Subscribe to relevant market data streams"""
        async def handle_ticker(msg):
            data = msg['data']
            symbol = data['s']
            price = Decimal(data['c'])
            self._current_prices[symbol] = price
            
            # Update portfolio position prices
            if symbol in self.portfolio_manager.positions:
                await self.portfolio_manager.update_position_price(symbol, price)
            
            # Update circuit breakers
            if symbol in self.risk_manager.circuit_breakers:
                self.risk_manager.circuit_breakers[symbol].update_price(price)
            
            # Notify price listeners
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

        if self.websocket: # Only subscribe if websocket is available
            await self.websocket.subscribe(
                f"!ticker@arr", # This is Binance specific stream name
                handle_ticker
            )
            await self.websocket.subscribe_depth("BTCUSDT") # Binance specific
        else:
            logger.warning(f"Market data WebSocket subscriptions skipped for {self.exchange_name} due to no WebSocket client.")
        
        # Register circuit breakers for major symbols
        major_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        for symbol in major_symbols:
            self.risk_manager.register_circuit_breaker(symbol)

    def add_price_listener(self, callback: Callable[[str, Decimal], None]):
        """Register callback for price updates"""
        self._price_listeners.append(callback)

    def add_depth_listener(self, callback: Callable[[str, Dict[Decimal, Decimal], Dict[Decimal, Decimal]], None]):
        """Register callback for price updates"""
        self._price_listeners.append(callback)

    async def place_order(self, order: Order) -> Order:
        """Place a new order and track its lifecycle"""
        # Validate order against basic risk rules
        if not self.basic_risk_rules.check_position_size(order.symbol, Decimal(str(order.amount))):
            reason = "Order exceeds maximum position size"
            logger.warning(f"Order rejected by risk manager: {reason}")
            order.status = OrderStatus.REJECTED
            
            # Send alert
            self.alert_manager.send_alert(
                "Order Rejected",
                f"Order for {order.symbol} rejected: {reason}",
                level="warning"
            )
            
            # Record metric
            self.metrics_collector.record_counter("orders.rejected", 1)
            
            # Raise exception
            raise ValueError(f"Order rejected by risk manager: {reason}")

        positions = self.portfolio_manager.positions
        if not self.basic_risk_rules.check_portfolio_risk(positions):
            reason = "Order exceeds maximum portfolio risk"
            logger.warning(f"Order rejected by risk manager: {reason}")
            order.status = OrderStatus.REJECTED
            
            # Send alert
            self.alert_manager.send_alert(
                "Order Rejected",
                f"Order for {order.symbol} rejected: {reason}",
                level="warning"
            )
            
            # Record metric
            self.metrics_collector.record_counter("orders.rejected", 1)
            
            # Raise exception
            raise ValueError(f"Order rejected by risk manager: {reason}")
            
        # Validate order against risk limits
        account_equity = await self.portfolio_manager.get_account_equity()
        is_valid, reason = await self.risk_manager.validate_order(order, account_equity)
        
        if not is_valid:
            logger.warning(f"Order rejected by risk manager: {reason}")
            order.status = OrderStatus.REJECTED
            
            # Send alert
            self.alert_manager.send_alert(
                "Order Rejected",
                f"Order for {order.symbol} rejected: {reason}",
                level="warning"
            )
            
            # Record metric
            self.metrics_collector.record_counter("orders.rejected", 1)
            
            # Raise exception
            raise ValueError(f"Order rejected by risk manager: {reason}")
        
        # Track order
        self.orders[order.id] = order

        if RuntimeSettings.get_dry_run_status():
            logger.info(
                f"[DRY RUN] Simulated trade (current status: {RuntimeSettings.get_dry_run_status()}): "
                f"Order ID: {order.id}, Symbol: {order.symbol}, Side: {order.side}, "
                f"Type: {order.type}, Amount: {order.amount}, Price: {order.price}, "
                f"Timestamp: {datetime.now()}"
            )
            # In dry run, we don't interact with the exchange.
            # We can simulate a successful placement for internal tracking.
            await self._update_order_status(order.id, OrderStatus.OPEN) # Simulate open status
            self.metrics_collector.record_counter("orders.simulated", 1)
            return order
        
        try:
            # Check exchange connectivity with retry
            try:
                await self.exchange.test_connection(max_retries=3, delay=1)
            except Exception as conn_err:
                logger.error(f"Exchange connection is not available: {conn_err}")
                self.alert_manager.send_alert(
                    "Exchange Connectivity Issue",
                    f"Could not place order for {order.symbol} due to exchange connectivity issues: {conn_err}",
                    level="critical",
                    data={"order_id": order.id, "symbol": order.symbol, "side": order.side, "type": order.type, "amount": order.amount, "price": order.price}
                )
                raise Exception(f"Exchange connection is not available: {conn_err}")

            # Place order on exchange
            exchange_order = await self.exchange.create_order(
                symbol=order.symbol,
                side=order.side,
                type=order.type,
                amount=Decimal(str(order.amount)),
                price=Decimal(str(order.price)) if order.price else None
            )
            
            # Update order with exchange ID
            order.id = exchange_order['orderId'] # Actual exchange order ID
            await self._update_order_status(order.id, OrderStatus.OPEN)
            
            # Record metric
            self.metrics_collector.record_counter("orders.placed", 1)
            
            return order
        except Exception as e:
            # Handle failure
            await self._update_order_status(order.id, OrderStatus.REJECTED)
            
            # Record metric
            self.metrics_collector.record_counter("orders.failed", 1)
            
            # Log error
            logger.error(f"Order placement failed: {e}")

            # Send alert
            self.alert_manager.send_alert(
                "Order Placement Failed",
                f"Order for {order.symbol} failed to be placed: {e}",
                level="error",
                data={"order_id": order.id, "symbol": order.symbol, "side": order.side, "type": order.type, "amount": order.amount, "price": order.price}
            )
            
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
    
    async def stop(self):
        """Stop the trading engine and all services"""
        # Stop risk monitoring
        await self.risk_manager.stop_monitoring()
        
        # Stop metrics exporting
        await self.metrics_collector.stop_exporting()
        
        # Close WebSocket connections (if available)
        if self.websocket:
            await self.websocket.close()
        
        logger.info("Trading engine stopped")
    
    async def get_risk_report(self) -> Dict:
        """Get comprehensive risk report"""
        return await self.risk_manager.get_risk_report()
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return self.portfolio_manager.get_performance_metrics()
    
    def set_risk_limit(self, limit_name: str, value: Union[Decimal, int, bool]):
        """
        Set a risk limit parameter.
        
        Args:
            limit_name: Name of the risk limit parameter
            value: New value for the parameter
        """
        if hasattr(risk_config, limit_name.upper()):
            setattr(risk_config, limit_name.upper(), value)
            logger.info(f"Risk limit {limit_name} set to {value}")
        else:
            logger.warning(f"Unknown risk limit parameter: {limit_name}")
    
    async def calculate_position_size(self, symbol: str, risk_percentage: Optional[Decimal] = None,
                                   stop_loss_pct: Optional[Decimal] = None) -> Decimal:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            symbol: Trading pair symbol
            risk_percentage: Percentage of account to risk (overrides default)
            stop_loss_pct: Stop loss percentage (if applicable)
            
        Returns:
            Decimal: Calculated position size in quote currency
        """
        account_equity = await self.portfolio_manager.get_account_equity()
        
        return await self.risk_manager.calculate_position_size(
            symbol,
            account_equity,
            risk_percentage=risk_percentage,
            stop_loss_pct=stop_loss_pct
        )