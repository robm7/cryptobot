"""
Risk Management Integration Tests

This module contains integration tests for the risk management workflow in the Cryptobot system.
It tests the interactions between trade execution, portfolio management, and risk management services.
"""

import pytest
import asyncio
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.framework.base import IntegrationTestBase
from tests.integration.framework.container import ServiceContainer
from tests.integration.framework.mocks import (
    MockExchangeService, MockDatabaseService, MockRedisService
)

# Import risk management related modules
from trade.services.risk import RiskManager
from trade.services.portfolio import PortfolioManager
from trade.schemas.trade import TradeRequest, TradeResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestRiskManagementIntegration(IntegrationTestBase):
    """
    Integration tests for the risk management workflow.
    
    These tests verify that the risk management system works correctly with
    trade execution and portfolio management.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        super().setup_class()
        
        # Create service container
        cls.container = ServiceContainer()
        
        # Register mock services
        cls.container.register_instance("exchange", MockExchangeService("test_exchange"))
        cls.container.register_instance("database", MockDatabaseService("test_db"))
        cls.container.register_instance("redis", MockRedisService("test_redis"))
        
        # Start mock services
        cls.container.get("exchange").start()
        cls.container.get("database").start()
        cls.container.get("redis").start()
        
        # Add to services started list for cleanup
        cls.services_started = ["exchange", "database", "redis"]
        
        # Set up portfolio data
        cls.container.get("database").insert("portfolios", {
            "user_id": 1,
            "assets": {
                "BTC": 1.0,
                "ETH": 10.0,
                "USDT": 50000.0
            },
            "updated_at": datetime.now().isoformat()
        })
        
        # Set up risk limits
        cls.container.get("database").insert("risk_limits", {
            "user_id": 1,
            "max_position_size": 10000.0,
            "max_daily_drawdown": 5.0,
            "max_leverage": 2.0,
            "max_concentration": 20.0,
            "updated_at": datetime.now().isoformat()
        })
    
    @classmethod
    def teardown_class(cls):
        """Tear down the test class."""
        # Stop mock services
        for service_name in reversed(cls.services_started):
            service = cls.container.get(service_name)
            service.stop()
        
        # Reset container
        cls.container.reset()
        
        super().teardown_class()
    
    @pytest.mark.integration
    async def test_position_size_limit(self):
        """Test position size risk limit."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        
        # Set up exchange market data
        exchange.add_market("BTC/USDT", {
            "id": "BTCUSDT",
            "symbol": "BTC/USDT",
            "base": "BTC",
            "quote": "USDT",
            "active": True
        })
        
        exchange.set_default_response("get_ticker", {
            "symbol": "BTC/USDT",
            "bid": 50000.0,
            "ask": 50050.0,
            "last": 50025.0,
            "high": 51000.0,
            "low": 49000.0,
            "volume": 100.5,
            "timestamp": 1620000000000
        })
        
        # Create portfolio manager
        portfolio_manager = PortfolioManager(database)
        
        # Create risk manager
        risk_manager = RiskManager(database, portfolio_manager)
        
        # Create trade request that exceeds position size limit
        trade_request = TradeRequest(
            user_id=1,
            symbol="BTC/USDT",
            side="buy",
            type="limit",
            quantity=0.5,  # 0.5 BTC at ~$50,000 = $25,000 (exceeds $10,000 limit)
            price=50000.0,
            strategy_id=1
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was rejected due to position size limit
        assert is_allowed is False
        assert "position size" in reason.lower()
        
        # Create trade request within position size limit
        trade_request = TradeRequest(
            user_id=1,
            symbol="BTC/USDT",
            side="buy",
            type="limit",
            quantity=0.1,  # 0.1 BTC at ~$50,000 = $5,000 (within $10,000 limit)
            price=50000.0,
            strategy_id=1
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was allowed
        assert is_allowed is True
        assert reason is None
    
    @pytest.mark.integration
    async def test_concentration_limit(self):
        """Test portfolio concentration risk limit."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        
        # Set up exchange market data
        exchange.add_market("ETH/USDT", {
            "id": "ETHUSDT",
            "symbol": "ETH/USDT",
            "base": "ETH",
            "quote": "USDT",
            "active": True
        })
        
        exchange.set_default_response("get_ticker", {
            "symbol": "ETH/USDT",
            "bid": 3000.0,
            "ask": 3010.0,
            "last": 3005.0,
            "high": 3100.0,
            "low": 2900.0,
            "volume": 1000.5,
            "timestamp": 1620000000000
        })
        
        # Create portfolio manager
        portfolio_manager = PortfolioManager(database)
        
        # Create risk manager
        risk_manager = RiskManager(database, portfolio_manager)
        
        # Get current portfolio
        portfolio = await portfolio_manager.get_portfolio(1)
        
        # Calculate total portfolio value
        btc_value = portfolio["assets"]["BTC"] * 50000.0  # 1 BTC * $50,000
        eth_value = portfolio["assets"]["ETH"] * 3000.0   # 10 ETH * $3,000
        usdt_value = portfolio["assets"]["USDT"]          # $50,000 USDT
        total_value = btc_value + eth_value + usdt_value  # ~$130,000
        
        # Create trade request that would exceed concentration limit
        # Max concentration is 20%, so ETH should not exceed ~$26,000
        # Current ETH value is $30,000, so buying more would exceed limit
        trade_request = TradeRequest(
            user_id=1,
            symbol="ETH/USDT",
            side="buy",
            type="limit",
            quantity=5.0,  # 5 ETH at ~$3,000 = $15,000 more ETH
            price=3000.0,
            strategy_id=1
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was rejected due to concentration limit
        assert is_allowed is False
        assert "concentration" in reason.lower()
        
        # Create trade request within concentration limit
        trade_request = TradeRequest(
            user_id=1,
            symbol="ETH/USDT",
            side="sell",
            type="limit",
            quantity=5.0,  # Selling 5 ETH reduces concentration
            price=3000.0,
            strategy_id=1
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was allowed
        assert is_allowed is True
        assert reason is None
    
    @pytest.mark.integration
    async def test_drawdown_limit(self):
        """Test daily drawdown risk limit."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        
        # Set up exchange market data
        exchange.add_market("BTC/USDT", {
            "id": "BTCUSDT",
            "symbol": "BTC/USDT",
            "base": "BTC",
            "quote": "USDT",
            "active": True
        })
        
        exchange.set_default_response("get_ticker", {
            "symbol": "BTC/USDT",
            "bid": 50000.0,
            "ask": 50050.0,
            "last": 50025.0,
            "high": 51000.0,
            "low": 49000.0,
            "volume": 100.5,
            "timestamp": 1620000000000
        })
        
        # Create portfolio manager
        portfolio_manager = PortfolioManager(database)
        
        # Create risk manager
        risk_manager = RiskManager(database, portfolio_manager)
        
        # Get current portfolio
        portfolio = await portfolio_manager.get_portfolio(1)
        
        # Calculate total portfolio value
        btc_value = portfolio["assets"]["BTC"] * 50000.0  # 1 BTC * $50,000
        eth_value = portfolio["assets"]["ETH"] * 3000.0   # 10 ETH * $3,000
        usdt_value = portfolio["assets"]["USDT"]          # $50,000 USDT
        total_value = btc_value + eth_value + usdt_value  # ~$130,000
        
        # Add some daily PnL data
        # Max daily drawdown is 5%, so losses should not exceed ~$6,500
        database.insert("daily_pnl", {
            "user_id": 1,
            "date": datetime.now().date().isoformat(),
            "realized_pnl": -6000.0,  # Already lost $6,000 today
            "updated_at": datetime.now().isoformat()
        })
        
        # Create trade request that would potentially exceed drawdown limit
        trade_request = TradeRequest(
            user_id=1,
            symbol="BTC/USDT",
            side="sell",
            type="limit",
            quantity=0.1,  # 0.1 BTC at ~$50,000 = $5,000 at risk
            price=49000.0,  # Selling below market, potential loss
            strategy_id=1
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was rejected due to drawdown limit
        assert is_allowed is False
        assert "drawdown" in reason.lower()
        
        # Create trade request with smaller risk
        trade_request = TradeRequest(
            user_id=1,
            symbol="BTC/USDT",
            side="sell",
            type="limit",
            quantity=0.01,  # 0.01 BTC at ~$50,000 = $500 at risk
            price=49000.0,
            strategy_id=1
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was allowed
        assert is_allowed is True
        assert reason is None
    
    @pytest.mark.integration
    async def test_risk_adjusted_position_sizing(self):
        """Test risk-adjusted position sizing."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        
        # Set up exchange market data
        exchange.add_market("BTC/USDT", {
            "id": "BTCUSDT",
            "symbol": "BTC/USDT",
            "base": "BTC",
            "quote": "USDT",
            "active": True
        })
        
        exchange.set_default_response("get_ticker", {
            "symbol": "BTC/USDT",
            "bid": 50000.0,
            "ask": 50050.0,
            "last": 50025.0,
            "high": 51000.0,
            "low": 49000.0,
            "volume": 100.5,
            "timestamp": 1620000000000
        })
        
        # Create portfolio manager
        portfolio_manager = PortfolioManager(database)
        
        # Create risk manager
        risk_manager = RiskManager(database, portfolio_manager)
        
        # Create trade request with risk parameters
        trade_request = TradeRequest(
            user_id=1,
            symbol="BTC/USDT",
            side="buy",
            type="limit",
            quantity=None,  # To be calculated based on risk
            price=50000.0,
            strategy_id=1,
            risk_percentage=1.0,  # Risk 1% of portfolio
            stop_loss_price=48000.0  # 4% stop loss
        )
        
        # Calculate position size based on risk
        position_size = await risk_manager.calculate_position_size(trade_request)
        
        # Verify position size calculation
        # Portfolio value ~$130,000, 1% risk = $1,300
        # Stop loss is 4% away, so position value should be ~$32,500
        # At $50,000 per BTC, that's ~0.65 BTC
        assert position_size is not None
        assert 0.6 <= position_size <= 0.7
        
        # Update trade request with calculated position size
        trade_request.quantity = position_size
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # Verify trade was allowed
        assert is_allowed is True
        assert reason is None
    
    @pytest.mark.integration
    async def test_end_to_end_risk_workflow(self):
        """Test end-to-end risk management workflow."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        redis = self.container.get("redis")
        
        # Set up exchange market data
        exchange.add_market("ETH/USDT", {
            "id": "ETHUSDT",
            "symbol": "ETH/USDT",
            "base": "ETH",
            "quote": "USDT",
            "active": True
        })
        
        exchange.set_default_response("get_ticker", {
            "symbol": "ETH/USDT",
            "bid": 3000.0,
            "ask": 3010.0,
            "last": 3005.0,
            "high": 3100.0,
            "low": 2900.0,
            "volume": 1000.5,
            "timestamp": 1620000000000
        })
        
        exchange.set_default_response("place_order", {
            "id": "test_order_1",
            "symbol": "ETH/USDT",
            "type": "limit",
            "side": "sell",
            "amount": 2.0,
            "price": 3000.0,
            "status": "open"
        })
        
        # Create portfolio manager
        portfolio_manager = PortfolioManager(database)
        
        # Create risk manager
        risk_manager = RiskManager(database, portfolio_manager)
        
        # Simulate strategy service generating a signal
        signal = {
            "strategy_id": 1,
            "symbol": "ETH/USDT",
            "side": "sell",
            "type": "limit",
            "quantity": 2.0,
            "price": 3000.0,
            "user_id": 1
        }
        
        # Store signal in Redis (as strategy service would)
        redis.set("signal:test_signal_1", signal)
        
        # Simulate trade service processing the signal
        # Retrieve signal from Redis (as trade service would)
        retrieved_signal = redis.get("signal:test_signal_1")
        
        # Create trade request from signal
        trade_request = TradeRequest(
            user_id=retrieved_signal["user_id"],
            symbol=retrieved_signal["symbol"],
            side=retrieved_signal["side"],
            type=retrieved_signal["type"],
            quantity=retrieved_signal["quantity"],
            price=retrieved_signal["price"],
            strategy_id=retrieved_signal["strategy_id"]
        )
        
        # Check risk limits
        is_allowed, reason = await risk_manager.check_risk_limits(trade_request)
        
        # If allowed, place order on exchange
        if is_allowed:
            order = exchange.place_order(
                trade_request.symbol,
                trade_request.type,
                trade_request.side,
                trade_request.quantity,
                trade_request.price
            )
            
            # Store order in database
            trade_id = database.insert("trades", {
                "symbol": order["symbol"],
                "trade_type": order["type"],
                "side": order["side"],
                "amount": order["amount"],
                "price": order["price"],
                "strategy_id": trade_request.strategy_id,
                "user_id": trade_request.user_id,
                "exchange_order_id": order["id"]
            })
            
            # Update portfolio
            await portfolio_manager.update_portfolio(
                trade_request.user_id,
                trade_request.symbol,
                trade_request.side,
                trade_request.quantity,
                trade_request.price
            )
        else:
            # Log rejected trade
            database.insert("rejected_trades", {
                "user_id": trade_request.user_id,
                "symbol": trade_request.symbol,
                "side": trade_request.side,
                "type": trade_request.type,
                "quantity": trade_request.quantity,
                "price": trade_request.price,
                "strategy_id": trade_request.strategy_id,
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            })
        
        # Verify trade was allowed and executed
        assert is_allowed is True
        
        # Verify order was placed on exchange
        exchange.assert_called("place_order")
        
        # Verify trade was stored in database
        database.assert_called("insert")
        
        # Verify portfolio was updated
        updated_portfolio = await portfolio_manager.get_portfolio(1)
        assert updated_portfolio["assets"]["ETH"] == 8.0  # Started with 10, sold 2
        assert updated_portfolio["assets"]["USDT"] > 50000.0  # Increased by ~$6,000


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])