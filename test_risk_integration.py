"""
Risk Management Integration Test Script

This script tests the integration of the risk management system with the trading engine.
It simulates various trading scenarios to verify risk controls are working properly.
"""
import asyncio
import logging
from decimal import Decimal
import sys
from datetime import datetime
import pandas as pd
import numpy as np

# Add the current directory to the path so we can import modules
sys.path.append('.')

from trade.engine import TradingEngine, Order, OrderStatus
from trade.services.portfolio_manager import PortfolioManager
from trade.services.risk_manager import RiskManager
from trade.utils.metrics import MetricsCollector
from trade.config.risk_config import risk_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock exchange class for testing
class MockExchange:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.orders = {}
        self.next_order_id = 1
    
    async def create_order(self, symbol, side, type, amount, price=None):
        order_id = f"order_{self.next_order_id}"
        self.next_order_id += 1
        
        self.orders[order_id] = {
            "orderId": order_id,
            "symbol": symbol,
            "side": side,
            "type": type,
            "amount": amount,
            "price": price,
            "status": "NEW",
            "timestamp": datetime.now().timestamp() * 1000
        }
        
        logger.info(f"Created order: {order_id} - {symbol} {side} {amount} @ {price}")
        return self.orders[order_id]
    
    async def get_listen_key(self):
        return "mock_listen_key"

# Mock WebSocket class for testing
class MockWebSocket:
    def __init__(self):
        self._callbacks = {}
    
    async def connect(self):
        logger.info("WebSocket connected")
    
    async def subscribe(self, channel, callback):
        self._callbacks[channel] = callback
        logger.info(f"Subscribed to channel: {channel}")
    
    async def subscribe_user_data(self, listen_key):
        logger.info(f"Subscribed to user data with listen key: {listen_key}")
    
    async def subscribe_depth(self, symbol):
        logger.info(f"Subscribed to depth for symbol: {symbol}")
    
    async def close(self):
        logger.info("WebSocket closed")
    
    async def simulate_price_update(self, symbol, price):
        """Simulate a price update from the WebSocket"""
        if "!ticker@arr" in self._callbacks:
            await self._callbacks["!ticker@arr"]({
                'data': {
                    's': symbol,
                    'c': str(price)
                }
            })
            logger.info(f"Simulated price update: {symbol} @ {price}")

async def test_normal_trading():
    """Test normal trading within risk limits"""
    logger.info("=== Testing Normal Trading ===")
    
    # Create trading engine with mock components
    engine = TradingEngine(MockExchange, "test_api_key", "test_api_secret")
    engine.websocket = MockWebSocket()
    
    # Start the engine
    await engine.start()
    
    # Create a test order within risk limits
    order = Order(
        id="test_order_1",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=0.1,
        price=50000
    )
    
    try:
        # Place the order
        result = await engine.place_order(order)
        logger.info(f"Order placed successfully: {result.id}, Status: {result.status}")
        
        # Simulate price updates
        await engine.websocket.simulate_price_update("BTC/USDT", 50500)
        await asyncio.sleep(1)
        await engine.websocket.simulate_price_update("BTC/USDT", 51000)
        await asyncio.sleep(1)
        
        # Get risk report
        risk_report = await engine.get_risk_report()
        logger.info(f"Risk Report: {risk_report}")
        
    except Exception as e:
        logger.error(f"Error during normal trading test: {e}")
    
    # Stop the engine
    await engine.stop()
    logger.info("Normal trading test completed")

async def test_excessive_position_size():
    """Test order rejection due to excessive position size"""
    logger.info("=== Testing Excessive Position Size ===")
    
    # Create trading engine with mock components
    engine = TradingEngine(MockExchange, "test_api_key", "test_api_secret")
    engine.websocket = MockWebSocket()
    
    # Start the engine
    await engine.start()
    
    # Create a test order that exceeds position size limits
    order = Order(
        id="test_order_2",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=10.0,  # Very large position (500,000 USD at 50,000 per BTC)
        price=50000
    )
    
    try:
        # Place the order - should be rejected
        result = await engine.place_order(order)
        logger.info(f"Order placed successfully: {result.id}, Status: {result.status}")
    except ValueError as e:
        logger.info(f"Order correctly rejected: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during excessive position test: {e}")
    
    # Stop the engine
    await engine.stop()
    logger.info("Excessive position size test completed")

async def test_drawdown_control():
    """Test position sizing with drawdown control"""
    logger.info("=== Testing Drawdown Control ===")
    
    # Create trading engine with mock components
    engine = TradingEngine(MockExchange, "test_api_key", "test_api_secret")
    engine.websocket = MockWebSocket()
    
    # Manually set drawdown for testing
    engine.portfolio_manager.current_drawdown = Decimal("0.15")  # 15% drawdown
    
    # Start the engine
    await engine.start()
    
    # Calculate position size with drawdown
    position_size = await engine.calculate_position_size(
        "BTC/USDT",
        risk_percentage=Decimal("0.01"),
        stop_loss_pct=Decimal("0.05")
    )
    
    logger.info(f"Position size with 15% drawdown: {position_size}")
    
    # Reset drawdown and calculate again for comparison
    engine.portfolio_manager.current_drawdown = Decimal("0")
    
    position_size_no_drawdown = await engine.calculate_position_size(
        "BTC/USDT",
        risk_percentage=Decimal("0.01"),
        stop_loss_pct=Decimal("0.05")
    )
    
    logger.info(f"Position size with no drawdown: {position_size_no_drawdown}")
    logger.info(f"Reduction factor: {float(position_size / position_size_no_drawdown):.2f}x")
    
    # Stop the engine
    await engine.stop()
    logger.info("Drawdown control test completed")

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    logger.info("=== Testing Circuit Breaker ===")
    
    # Create trading engine with mock components
    engine = TradingEngine(MockExchange, "test_api_key", "test_api_secret")
    engine.websocket = MockWebSocket()
    
    # Start the engine
    await engine.start()
    
    # Register circuit breaker for BTC/USDT with 5% threshold
    engine.risk_manager.register_circuit_breaker(
        "BTC/USDT", 
        threshold=Decimal("0.05"),  # 5% threshold
        cooldown_minutes=1  # 1 minute cooldown for testing
    )
    
    # Simulate normal price updates
    await engine.websocket.simulate_price_update("BTC/USDT", 50000)
    await asyncio.sleep(1)
    await engine.websocket.simulate_price_update("BTC/USDT", 50500)  # +1%
    await asyncio.sleep(1)
    
    # Create a test order
    order1 = Order(
        id="test_order_3",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=0.1,
        price=50500
    )
    
    try:
        # Place the order - should succeed
        result = await engine.place_order(order1)
        logger.info(f"Order placed successfully before circuit breaker: {result.id}")
    except Exception as e:
        logger.error(f"Error placing order before circuit breaker: {e}")
    
    # Simulate large price movement to trigger circuit breaker
    await engine.websocket.simulate_price_update("BTC/USDT", 53000)  # +6% from 50000
    await asyncio.sleep(1)
    
    # Create another test order
    order2 = Order(
        id="test_order_4",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=0.1,
        price=53000
    )
    
    try:
        # Place the order - should be rejected due to circuit breaker
        result = await engine.place_order(order2)
        logger.info(f"Order placed successfully after circuit breaker (unexpected): {result.id}")
    except ValueError as e:
        logger.info(f"Order correctly rejected due to circuit breaker: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during circuit breaker test: {e}")
    
    # Get risk report
    risk_report = await engine.get_risk_report()
    logger.info(f"Circuit breaker status: {risk_report['circuit_breakers']}")
    
    # Stop the engine
    await engine.stop()
    logger.info("Circuit breaker test completed")

async def test_correlation_risk():
    """Test correlation risk management"""
    logger.info("=== Testing Correlation Risk ===")
    
    # Create trading engine with mock components
    engine = TradingEngine(MockExchange, "test_api_key", "test_api_secret")
    engine.websocket = MockWebSocket()
    
    # Start the engine
    await engine.start()
    
    # Add some correlated positions to the portfolio
    await engine.portfolio_manager.add_position("BTC/USDT", Decimal("0.5"), Decimal("50000"))
    await engine.portfolio_manager.add_position("ETH/USDT", Decimal("5"), Decimal("3000"))
    
    # Mock the correlation matrix to simulate high correlation
    engine.portfolio_manager.correlation_matrix = pd.DataFrame({
        "BTC/USDT": [1.0, 0.9],
        "ETH/USDT": [0.9, 1.0]
    }, index=["BTC/USDT", "ETH/USDT"])
    
    # Set high correlation limit for testing
    original_limit = risk_config.MAX_CORRELATION
    risk_config.MAX_CORRELATION = Decimal("0.85")
    
    # Create a test order for another correlated asset
    order = Order(
        id="test_order_5",
        symbol="SOL/USDT",  # Another crypto asset
        side="buy",
        type="limit",
        amount=10,
        price=100
    )
    
    # Mock the position risk to simulate high correlation
    async def mock_position_risk(*args, **kwargs):
        return {
            "volatility": 0.7,
            "correlation_risk": 0.9,  # High correlation
            "concentration": 0.1
        }
    
    # Replace the get_position_risk method with our mock
    original_get_position_risk = engine.portfolio_manager.get_position_risk
    engine.portfolio_manager.get_position_risk = mock_position_risk
    
    try:
        # Place the order - should be rejected due to high correlation
        result = await engine.place_order(order)
        logger.info(f"Order placed successfully despite high correlation (unexpected): {result.id}")
    except ValueError as e:
        logger.info(f"Order correctly rejected due to high correlation: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during correlation test: {e}")
    
    # Restore original methods and settings
    engine.portfolio_manager.get_position_risk = original_get_position_risk
    risk_config.MAX_CORRELATION = original_limit
    
    # Stop the engine
    await engine.stop()
    logger.info("Correlation risk test completed")

async def run_tests():
    """Run all tests"""
    logger.info("Starting risk management integration tests")
    
    await test_normal_trading()
    await asyncio.sleep(1)
    
    await test_excessive_position_size()
    await asyncio.sleep(1)
    
    await test_drawdown_control()
    await asyncio.sleep(1)
    
    await test_circuit_breaker()
    await asyncio.sleep(1)
    
    await test_correlation_risk()
    
    logger.info("All risk management integration tests completed")

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_tests())