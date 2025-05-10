"""
Strategy Execution Integration Tests

This module contains integration tests for the end-to-end strategy execution workflow
in the Cryptobot system. It tests the full lifecycle from strategy creation to execution
to performance tracking.
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockStrategyService:
    """Mock strategy service for testing"""
    
    def __init__(self, database, redis, exchange):
        """Initialize with dependencies"""
        self.database = database
        self.redis = redis
        self.exchange = exchange
        self.strategies = {}
        self.running_strategies = set()
    
    async def create_strategy(self, user_id, name, description, strategy_type, parameters):
        """Create a new strategy"""
        strategy_id = self.database.insert("strategies", {
            "user_id": user_id,
            "name": name,
            "description": description,
            "type": strategy_type,
            "parameters": json.dumps(parameters),
            "status": "inactive",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        return strategy_id
    
    async def get_strategy(self, strategy_id):
        """Get strategy by ID"""
        strategies = self.database.query("strategies", {"id": strategy_id})
        
        if not strategies or len(strategies) == 0:
            return None
        
        strategy = strategies[0]
        strategy["parameters"] = json.loads(strategy["parameters"])
        
        return strategy
    
    async def update_strategy(self, strategy_id, updates):
        """Update strategy"""
        if "parameters" in updates and isinstance(updates["parameters"], dict):
            updates["parameters"] = json.dumps(updates["parameters"])
        
        updates["updated_at"] = datetime.now().isoformat()
        
        self.database.update("strategies", strategy_id, updates)
        
        return await self.get_strategy(strategy_id)
    
    async def start_strategy(self, strategy_id):
        """Start strategy execution"""
        strategy = await self.get_strategy(strategy_id)
        
        if not strategy:
            return False
        
        # Update strategy status
        await self.update_strategy(strategy_id, {"status": "active"})
        
        # Add to running strategies
        self.running_strategies.add(strategy_id)
        
        # Start strategy execution in background
        asyncio.create_task(self._run_strategy(strategy))
        
        return True
    
    async def stop_strategy(self, strategy_id):
        """Stop strategy execution"""
        if strategy_id not in self.running_strategies:
            return False
        
        # Remove from running strategies
        self.running_strategies.remove(strategy_id)
        
        # Update strategy status
        await self.update_strategy(strategy_id, {"status": "inactive"})
        
        return True
    
    async def _run_strategy(self, strategy):
        """Run strategy execution loop"""
        strategy_id = strategy["id"]
        
        # Create strategy instance based on type
        if strategy["type"] == "mean_reversion":
            from strategies.mean_reversion import MeanReversionStrategy
            strategy_instance = MeanReversionStrategy()
        elif strategy["type"] == "breakout_reset":
            from strategies.breakout_reset import BreakoutResetStrategy
            strategy_instance = BreakoutResetStrategy()
        else:
            logger.error(f"Unknown strategy type: {strategy['type']}")
            await self.stop_strategy(strategy_id)
            return
        
        # Set strategy parameters
        strategy_instance.set_parameters(strategy["parameters"])
        
        # Get symbols from parameters or use default
        symbols = strategy["parameters"].get("symbols", ["BTC/USDT"])
        
        # Run strategy until stopped
        while strategy_id in self.running_strategies:
            try:
                # Get market data for each symbol
                for symbol in symbols:
                    # Get latest ticker
                    ticker = self.exchange.get_ticker(symbol)
                    
                    # Get recent OHLCV data
                    timeframe = strategy["parameters"].get("timeframe", "1h")
                    ohlcv = await self._get_ohlcv_data(symbol, timeframe)
                    
                    # Process data with strategy
                    signal = strategy_instance.process_data(symbol, ticker, ohlcv)
                    
                    # If signal generated, publish to Redis
                    if signal:
                        signal_id = f"signal:{strategy_id}:{int(time.time())}"
                        signal_data = {
                            "strategy_id": strategy_id,
                            "user_id": strategy["user_id"],
                            "symbol": signal["symbol"],
                            "side": signal["side"],
                            "type": signal["type"],
                            "quantity": signal["quantity"],
                            "price": signal["price"],
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        self.redis.set(signal_id, signal_data)
                        
                        # Log signal
                        self.database.insert("strategy_signals", {
                            "strategy_id": strategy_id,
                            "user_id": strategy["user_id"],
                            "symbol": signal["symbol"],
                            "side": signal["side"],
                            "type": signal["type"],
                            "quantity": signal["quantity"],
                            "price": signal["price"],
                            "timestamp": datetime.now().isoformat()
                        })
                
                # Sleep before next iteration
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in strategy execution: {e}")
                await asyncio.sleep(30)  # Longer sleep on error
    
    async def _get_ohlcv_data(self, symbol, timeframe):
        """Get OHLCV data for symbol and timeframe"""
        # In a real implementation, this would fetch from database or API
        # For testing, generate some sample data
        now = datetime.now()
        data = []
        
        for i in range(100):
            timestamp = now - timedelta(hours=i)
            
            if symbol == "BTC/USDT":
                base_price = 50000.0
                volatility = 1000.0
            elif symbol == "ETH/USDT":
                base_price = 3000.0
                volatility = 100.0
            else:
                base_price = 100.0
                volatility = 5.0
            
            import random
            random.seed(i)
            
            price_change = random.uniform(-volatility, volatility)
            close = base_price + price_change
            high = close + random.uniform(0, volatility / 2)
            low = close - random.uniform(0, volatility / 2)
            open_price = close - random.uniform(-volatility / 2, volatility / 2)
            volume = random.uniform(1, 100)
            
            candle = {
                "timestamp": int(timestamp.timestamp() * 1000),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            }
            
            data.append(candle)
        
        return data


class MockTradeService:
    """Mock trade service for testing"""
    
    def __init__(self, database, redis, exchange):
        """Initialize with dependencies"""
        self.database = database
        self.redis = redis
        self.exchange = exchange
        self.signal_processor_running = False
    
    async def start_signal_processor(self):
        """Start signal processor"""
        if self.signal_processor_running:
            return
        
        self.signal_processor_running = True
        asyncio.create_task(self._process_signals())
    
    async def stop_signal_processor(self):
        """Stop signal processor"""
        self.signal_processor_running = False
    
    async def _process_signals(self):
        """Process strategy signals from Redis"""
        while self.signal_processor_running:
            try:
                # Get all signal keys
                signal_keys = self.redis.keys("signal:*")
                
                for key in signal_keys:
                    # Get signal data
                    signal = self.redis.get(key)
                    
                    if not signal:
                        continue
                    
                    # Process signal
                    await self._execute_trade(signal)
                    
                    # Remove processed signal
                    self.redis.delete(key)
                
                # Sleep before next check
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in signal processor: {e}")
                await asyncio.sleep(5)  # Sleep on error
    
    async def _execute_trade(self, signal):
        """Execute trade based on signal"""
        try:
            # Check if we have enough balance
            # In a real implementation, this would check user's portfolio
            
            # Place order on exchange
            order = self.exchange.place_order(
                symbol=signal["symbol"],
                order_type=signal["type"],
                side=signal["side"],
                quantity=signal["quantity"],
                price=signal["price"]
            )
            
            # Record trade in database
            trade_id = self.database.insert("trades", {
                "user_id": signal["user_id"],
                "strategy_id": signal["strategy_id"],
                "symbol": signal["symbol"],
                "side": signal["side"],
                "type": signal["type"],
                "quantity": signal["quantity"],
                "price": signal["price"],
                "exchange_order_id": order["id"],
                "status": order["status"],
                "created_at": datetime.now().isoformat()
            })
            
            return trade_id
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            
            # Record failed trade
            self.database.insert("failed_trades", {
                "user_id": signal["user_id"],
                "strategy_id": signal["strategy_id"],
                "symbol": signal["symbol"],
                "side": signal["side"],
                "type": signal["type"],
                "quantity": signal["quantity"],
                "price": signal["price"],
                "error": str(e),
                "created_at": datetime.now().isoformat()
            })
            
            return None


class MockPerformanceTracker:
    """Mock performance tracker for testing"""
    
    def __init__(self, database):
        """Initialize with dependencies"""
        self.database = database
    
    async def track_strategy_performance(self, strategy_id):
        """Track performance for a strategy"""
        # Get strategy
        strategies = self.database.query("strategies", {"id": strategy_id})
        
        if not strategies or len(strategies) == 0:
            return None
        
        strategy = strategies[0]
        
        # Get trades for strategy
        trades = self.database.query("trades", {"strategy_id": strategy_id})
        
        if not trades:
            return {
                "strategy_id": strategy_id,
                "total_trades": 0,
                "profitable_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "net_profit": 0.0,
                "roi": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "updated_at": datetime.now().isoformat()
            }
        
        # Calculate performance metrics
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t["side"] == "sell" and t["price"] > t.get("entry_price", 0))
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0.0
        
        total_profit = sum(t["price"] * t["quantity"] - t.get("entry_price", 0) * t["quantity"] 
                          for t in trades if t["side"] == "sell" and t["price"] > t.get("entry_price", 0))
        
        total_loss = sum(t.get("entry_price", 0) * t["quantity"] - t["price"] * t["quantity"]
                        for t in trades if t["side"] == "sell" and t["price"] <= t.get("entry_price", 0))
        
        net_profit = total_profit - total_loss
        
        # Calculate ROI (assuming initial capital of $10,000)
        initial_capital = 10000.0
        roi = (net_profit / initial_capital) * 100 if initial_capital > 0 else 0.0
        
        # Simplified Sharpe ratio and max drawdown calculations
        sharpe_ratio = 1.0 if net_profit > 0 else -1.0
        max_drawdown = 5.0 if total_loss > 0 else 0.0
        
        # Store performance metrics
        performance = {
            "strategy_id": strategy_id,
            "total_trades": total_trades,
            "profitable_trades": profitable_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_profit": net_profit,
            "roi": roi,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "updated_at": datetime.now().isoformat()
        }
        
        # Update or insert performance record
        existing = self.database.query("strategy_performance", {"strategy_id": strategy_id})
        
        if existing and len(existing) > 0:
            self.database.update("strategy_performance", existing[0]["id"], performance)
        else:
            self.database.insert("strategy_performance", performance)
        
        return performance


class TestStrategyExecutionIntegration(IntegrationTestBase):
    """
    Integration tests for the end-to-end strategy execution workflow.
    
    These tests verify that the strategy execution system works correctly from
    strategy creation to execution to performance tracking.
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
        
        # Set up exchange market data
        exchange = cls.container.get("exchange")
        
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
        
        exchange.set_default_response("place_order", {
            "id": "test_order_1",
            "symbol": "BTC/USDT",
            "type": "limit",
            "side": "buy",
            "amount": 0.1,
            "price": 50000.0,
            "status": "open"
        })
        
        # Create service instances
        cls.strategy_service = MockStrategyService(
            cls.container.get("database"),
            cls.container.get("redis"),
            cls.container.get("exchange")
        )
        
        cls.trade_service = MockTradeService(
            cls.container.get("database"),
            cls.container.get("redis"),
            cls.container.get("exchange")
        )
        
        cls.performance_tracker = MockPerformanceTracker(
            cls.container.get("database")
        )
        
        # Add to services started list for cleanup
        cls.services_started = ["exchange", "database", "redis"]
    
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
    async def test_strategy_creation_and_configuration(self):
        """Test strategy creation and configuration."""
        # Create a new strategy
        strategy_id = await self.strategy_service.create_strategy(
            user_id=1,
            name="Test Mean Reversion",
            description="Test strategy for integration testing",
            strategy_type="mean_reversion",
            parameters={
                "symbols": ["BTC/USDT"],
                "timeframe": "1h",
                "window": 20,
                "entry_z_score": 2.0,
                "exit_z_score": 0.0,
                "stop_loss_pct": 5.0
            }
        )
        
        assert strategy_id is not None
        
        # Get strategy
        strategy = await self.strategy_service.get_strategy(strategy_id)
        assert strategy is not None
        assert strategy["name"] == "Test Mean Reversion"
        assert strategy["type"] == "mean_reversion"
        assert strategy["parameters"]["window"] == 20
        
        # Update strategy parameters
        updated_strategy = await self.strategy_service.update_strategy(
            strategy_id,
            {
                "parameters": {
                    "symbols": ["BTC/USDT"],
                    "timeframe": "1h",
                    "window": 30,  # Changed from 20 to 30
                    "entry_z_score": 2.5,  # Changed from 2.0 to 2.5
                    "exit_z_score": 0.0,
                    "stop_loss_pct": 5.0
                }
            }
        )
        
        assert updated_strategy is not None
        assert updated_strategy["parameters"]["window"] == 30
        assert updated_strategy["parameters"]["entry_z_score"] == 2.5
    
    @pytest.mark.integration
    async def test_strategy_execution_and_signal_generation(self):
        """Test strategy execution and signal generation."""
        # Create a new strategy
        strategy_id = await self.strategy_service.create_strategy(
            user_id=1,
            name="Test Breakout Reset",
            description="Test strategy for integration testing",
            strategy_type="breakout_reset",
            parameters={
                "symbols": ["BTC/USDT"],
                "timeframe": "1h",
                "breakout_period": 24,
                "reset_period": 12,
                "risk_per_trade": 2.0
            }
        )
        
        assert strategy_id is not None
        
        # Start strategy execution
        started = await self.strategy_service.start_strategy(strategy_id)
        assert started is True
        
        # Wait for strategy to generate signals
        await asyncio.sleep(0.5)
        
        # Check if signals were generated
        signals = self.container.get("database").query("strategy_signals", {"strategy_id": strategy_id})
        
        # Stop strategy execution
        stopped = await self.strategy_service.stop_strategy(strategy_id)
        assert stopped is True
        
        # Verify strategy status
        strategy = await self.strategy_service.get_strategy(strategy_id)
        assert strategy["status"] == "inactive"
    
    @pytest.mark.integration
    async def test_signal_processing_and_trade_execution(self):
        """Test signal processing and trade execution."""
        # Start trade service signal processor
        await self.trade_service.start_signal_processor()
        
        # Create a test signal
        signal_id = "signal:test:1"
        signal_data = {
            "strategy_id": 999,  # Test strategy ID
            "user_id": 1,
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.1,
            "price": 50000.0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store signal in Redis
        self.container.get("redis").set(signal_id, signal_data)
        
        # Wait for signal to be processed
        await asyncio.sleep(1.5)
        
        # Stop signal processor
        await self.trade_service.stop_signal_processor()
        
        # Check if trade was executed
        trades = self.container.get("database").query("trades", {"strategy_id": 999})
        assert len(trades) > 0
        
        # Verify trade details
        trade = trades[0]
        assert trade["symbol"] == "BTC/USDT"
        assert trade["side"] == "buy"
        assert trade["quantity"] == 0.1
        assert trade["price"] == 50000.0
    
    @pytest.mark.integration
    async def test_performance_tracking(self):
        """Test strategy performance tracking."""
        # Create a test strategy
        strategy_id = await self.strategy_service.create_strategy(
            user_id=1,
            name="Test Performance Strategy",
            description="Test strategy for performance tracking",
            strategy_type="mean_reversion",
            parameters={
                "symbols": ["BTC/USDT"],
                "timeframe": "1h",
                "window": 20,
                "entry_z_score": 2.0,
                "exit_z_score": 0.0,
                "stop_loss_pct": 5.0
            }
        )
        
        assert strategy_id is not None
        
        # Create some test trades for the strategy
        # Buy trade
        buy_trade_id = self.container.get("database").insert("trades", {
            "user_id": 1,
            "strategy_id": strategy_id,
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.1,
            "price": 50000.0,
            "exchange_order_id": "test_order_buy",
            "status": "filled",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat()
        })
        
        # Sell trade with profit
        sell_trade_id = self.container.get("database").insert("trades", {
            "user_id": 1,
            "strategy_id": strategy_id,
            "symbol": "BTC/USDT",
            "side": "sell",
            "type": "limit",
            "quantity": 0.1,
            "price": 52000.0,
            "entry_price": 50000.0,
            "exchange_order_id": "test_order_sell",
            "status": "filled",
            "created_at": datetime.now().isoformat()
        })
        
        # Track performance
        performance = await self.performance_tracker.track_strategy_performance(strategy_id)
        
        # Verify performance metrics
        assert performance is not None
        assert performance["strategy_id"] == strategy_id
        assert performance["total_trades"] == 2
        assert performance["profitable_trades"] == 1
        assert performance["win_rate"] == 0.5
        assert performance["total_profit"] > 0
        assert performance["net_profit"] > 0
    
    @pytest.mark.integration
    async def test_end_to_end_strategy_workflow(self):
        """Test end-to-end strategy workflow."""
        # Start trade service signal processor
        await self.trade_service.start_signal_processor()
        
        # Step 1: Create a strategy
        strategy_id = await self.strategy_service.create_strategy(
            user_id=1,
            name="E2E Test Strategy",
            description="End-to-end test strategy",
            strategy_type="mean_reversion",
            parameters={
                "symbols": ["BTC/USDT"],
                "timeframe": "1h",
                "window": 20,
                "entry_z_score": 2.0,
                "exit_z_score": 0.0,
                "stop_loss_pct": 5.0
            }
        )
        
        assert strategy_id is not None
        
        # Step 2: Start strategy execution
        started = await self.strategy_service.start_strategy(strategy_id)
        assert started is True
        
        # Step 3: Wait for strategy to generate signals and trades to be executed
        await asyncio.sleep(1.5)
        
        # Step 4: Stop strategy execution
        stopped = await self.strategy_service.stop_strategy(strategy_id)
        assert stopped is True
        
        # Step 5: Stop trade service signal processor
        await self.trade_service.stop_signal_processor()
        
        # Step 6: Track strategy performance
        performance = await self.performance_tracker.track_strategy_performance(strategy_id)
        assert performance is not None
        
        # Verify the entire workflow
        # Check if signals were generated
        signals = self.container.get("database").query("strategy_signals", {"strategy_id": strategy_id})
        
        # Check if trades were executed
        trades = self.container.get("database").query("trades", {"strategy_id": strategy_id})
        
        # Verify performance metrics were calculated
        assert performance["strategy_id"] == strategy_id
        assert performance["total_trades"] == len(trades)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])