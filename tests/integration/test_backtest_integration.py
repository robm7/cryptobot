"""
Backtesting Integration Tests

This module contains integration tests for the backtesting workflow in the Cryptobot system.
It tests the interactions between historical data, strategy execution, and performance analysis.
"""

import pytest
import asyncio
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.framework.base import IntegrationTestBase
from tests.integration.framework.container import ServiceContainer
from tests.integration.framework.mocks import MockDatabaseService, MockRedisService

# Import backtest-related modules
from backtest.schemas.backtest import BacktestRequest, BacktestResult
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout_reset import BreakoutResetStrategy
from utils.backtest import BacktestEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockHistoricalDataService:
    """Mock historical data service for testing"""
    
    def __init__(self):
        """Initialize with sample data"""
        self.data = {}
        self._generate_sample_data()
    
    def _generate_sample_data(self):
        """Generate sample OHLCV data for testing"""
        # Generate 30 days of hourly data for BTC/USDT
        symbol = "BTC/USDT"
        timeframe = "1h"
        
        start_time = datetime.now() - timedelta(days=30)
        
        data = []
        price = 50000.0
        
        for i in range(30 * 24):  # 30 days of hourly data
            timestamp = start_time + timedelta(hours=i)
            unix_ts = int(timestamp.timestamp() * 1000)
            
            # Create some price movement
            price_change = (((i % 24) - 12) / 12) * 500  # Daily cycle
            price += price_change
            
            # Add some randomness
            import random
            random.seed(i)
            price += random.uniform(-200, 200)
            
            high = price + random.uniform(50, 150)
            low = price - random.uniform(50, 150)
            open_price = price - random.uniform(-100, 100)
            
            candle = {
                "timestamp": unix_ts,
                "open": open_price,
                "high": high,
                "low": low,
                "close": price,
                "volume": random.uniform(1, 10)
            }
            
            data.append(candle)
        
        self.data[(symbol, timeframe)] = data
        
        # Also generate data for ETH/USDT
        symbol = "ETH/USDT"
        data = []
        price = 3000.0
        
        for i in range(30 * 24):
            timestamp = start_time + timedelta(hours=i)
            unix_ts = int(timestamp.timestamp() * 1000)
            
            price_change = (((i % 24) - 12) / 12) * 30
            price += price_change
            
            import random
            random.seed(i + 1000)  # Different seed for ETH
            price += random.uniform(-15, 15)
            
            high = price + random.uniform(5, 15)
            low = price - random.uniform(5, 15)
            open_price = price - random.uniform(-10, 10)
            
            candle = {
                "timestamp": unix_ts,
                "open": open_price,
                "high": high,
                "low": low,
                "close": price,
                "volume": random.uniform(10, 100)
            }
            
            data.append(candle)
        
        self.data[(symbol, timeframe)] = data
    
    async def get_historical_data(self, symbol, timeframe, start_time, end_time):
        """Get historical data for a symbol and timeframe"""
        if (symbol, timeframe) not in self.data:
            return []
        
        # Filter data by time range
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        filtered_data = [
            candle for candle in self.data[(symbol, timeframe)]
            if start_ts <= candle["timestamp"] <= end_ts
        ]
        
        return filtered_data


class TestBacktestIntegration(IntegrationTestBase):
    """
    Integration tests for the backtesting workflow.
    
    These tests verify that the backtesting system works correctly with
    historical data, strategy execution, and performance analysis.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        super().setup_class()
        
        # Create service container
        cls.container = ServiceContainer()
        
        # Register mock services
        cls.container.register_instance("database", MockDatabaseService("test_db"))
        cls.container.register_instance("redis", MockRedisService("test_redis"))
        cls.container.register_instance("historical_data", MockHistoricalDataService())
        
        # Start mock services
        cls.container.get("database").start()
        cls.container.get("redis").start()
        
        # Add to services started list for cleanup
        cls.services_started = ["database", "redis"]
    
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
    async def test_mean_reversion_backtest(self):
        """Test backtesting with Mean Reversion strategy."""
        # Get mock services
        database = self.container.get("database")
        historical_data = self.container.get("historical_data")
        
        # Create backtest engine
        backtest_engine = BacktestEngine()
        
        # Create strategy instance
        strategy = MeanReversionStrategy()
        strategy.set_parameters({
            "window": 20,
            "entry_z_score": 2.0,
            "exit_z_score": 0.0,
            "stop_loss_pct": 5.0
        })
        
        # Create backtest request
        request = BacktestRequest(
            strategy_name="mean_reversion",
            strategy_parameters={
                "window": 20,
                "entry_z_score": 2.0,
                "exit_z_score": 0.0,
                "stop_loss_pct": 5.0
            },
            symbols=["BTC/USDT"],
            timeframe="1h",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            initial_capital=10000.0
        )
        
        # Mock the historical data retrieval
        async def mock_get_data(symbol, timeframe, start_date, end_date):
            return await historical_data.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
        
        # Run backtest
        with patch.object(backtest_engine, '_get_historical_data', side_effect=mock_get_data):
            result = await backtest_engine.run_backtest(request, strategy)
            
            # Verify backtest completed
            assert result is not None
            assert isinstance(result, BacktestResult)
            
            # Verify backtest results
            assert result.strategy_name == "mean_reversion"
            assert result.symbols == ["BTC/USDT"]
            assert result.timeframe == "1h"
            assert result.initial_capital == 10000.0
            assert result.final_capital > 0
            
            # Verify trades were generated
            assert len(result.trades) > 0
            
            # Verify performance metrics
            assert result.metrics is not None
            assert "total_return" in result.metrics
            assert "sharpe_ratio" in result.metrics
            assert "max_drawdown" in result.metrics
            
            # Store result in database
            database.insert("backtest_results", result.dict())
            
            # Verify database was called
            database.assert_called("insert")
    
    @pytest.mark.integration
    async def test_breakout_reset_backtest(self):
        """Test backtesting with Breakout Reset strategy."""
        # Get mock services
        database = self.container.get("database")
        historical_data = self.container.get("historical_data")
        
        # Create backtest engine
        backtest_engine = BacktestEngine()
        
        # Create strategy instance
        strategy = BreakoutResetStrategy()
        strategy.set_parameters({
            "breakout_period": 24,
            "reset_period": 12,
            "risk_per_trade": 2.0
        })
        
        # Create backtest request
        request = BacktestRequest(
            strategy_name="breakout_reset",
            strategy_parameters={
                "breakout_period": 24,
                "reset_period": 12,
                "risk_per_trade": 2.0
            },
            symbols=["ETH/USDT"],
            timeframe="1h",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            initial_capital=10000.0
        )
        
        # Mock the historical data retrieval
        async def mock_get_data(symbol, timeframe, start_date, end_date):
            return await historical_data.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
        
        # Run backtest
        with patch.object(backtest_engine, '_get_historical_data', side_effect=mock_get_data):
            result = await backtest_engine.run_backtest(request, strategy)
            
            # Verify backtest completed
            assert result is not None
            assert isinstance(result, BacktestResult)
            
            # Verify backtest results
            assert result.strategy_name == "breakout_reset"
            assert result.symbols == ["ETH/USDT"]
            assert result.timeframe == "1h"
            assert result.initial_capital == 10000.0
            assert result.final_capital > 0
            
            # Verify trades were generated
            assert len(result.trades) > 0
            
            # Verify performance metrics
            assert result.metrics is not None
            assert "total_return" in result.metrics
            assert "sharpe_ratio" in result.metrics
            assert "max_drawdown" in result.metrics
            
            # Store result in database
            database.insert("backtest_results", result.dict())
            
            # Verify database was called
            database.assert_called("insert")
    
    @pytest.mark.integration
    async def test_multi_symbol_backtest(self):
        """Test backtesting with multiple symbols."""
        # Get mock services
        database = self.container.get("database")
        historical_data = self.container.get("historical_data")
        
        # Create backtest engine
        backtest_engine = BacktestEngine()
        
        # Create strategy instance
        strategy = MeanReversionStrategy()
        strategy.set_parameters({
            "window": 20,
            "entry_z_score": 2.0,
            "exit_z_score": 0.0,
            "stop_loss_pct": 5.0
        })
        
        # Create backtest request with multiple symbols
        request = BacktestRequest(
            strategy_name="mean_reversion",
            strategy_parameters={
                "window": 20,
                "entry_z_score": 2.0,
                "exit_z_score": 0.0,
                "stop_loss_pct": 5.0
            },
            symbols=["BTC/USDT", "ETH/USDT"],
            timeframe="1h",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            initial_capital=10000.0
        )
        
        # Mock the historical data retrieval
        async def mock_get_data(symbol, timeframe, start_date, end_date):
            return await historical_data.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
        
        # Run backtest
        with patch.object(backtest_engine, '_get_historical_data', side_effect=mock_get_data):
            result = await backtest_engine.run_backtest(request, strategy)
            
            # Verify backtest completed
            assert result is not None
            assert isinstance(result, BacktestResult)
            
            # Verify backtest results
            assert result.strategy_name == "mean_reversion"
            assert set(result.symbols) == set(["BTC/USDT", "ETH/USDT"])
            assert result.timeframe == "1h"
            assert result.initial_capital == 10000.0
            assert result.final_capital > 0
            
            # Verify trades were generated for both symbols
            assert len(result.trades) > 0
            
            # Check if trades exist for both symbols
            btc_trades = [t for t in result.trades if t.symbol == "BTC/USDT"]
            eth_trades = [t for t in result.trades if t.symbol == "ETH/USDT"]
            
            assert len(btc_trades) > 0
            assert len(eth_trades) > 0
            
            # Verify performance metrics
            assert result.metrics is not None
            assert "total_return" in result.metrics
            assert "sharpe_ratio" in result.metrics
            assert "max_drawdown" in result.metrics
            
            # Store result in database
            database.insert("backtest_results", result.dict())
            
            # Verify database was called
            database.assert_called("insert")
    
    @pytest.mark.integration
    async def test_backtest_parameter_optimization(self):
        """Test backtesting with parameter optimization."""
        # Get mock services
        database = self.container.get("database")
        historical_data = self.container.get("historical_data")
        
        # Create backtest engine
        backtest_engine = BacktestEngine()
        
        # Define parameter ranges for optimization
        parameter_ranges = {
            "window": [10, 20, 30],
            "entry_z_score": [1.5, 2.0, 2.5],
            "exit_z_score": [0.0, 0.5],
            "stop_loss_pct": [5.0]
        }
        
        # Generate all parameter combinations
        import itertools
        param_combinations = []
        
        keys = list(parameter_ranges.keys())
        values = list(parameter_ranges.values())
        
        for combination in itertools.product(*values):
            params = dict(zip(keys, combination))
            param_combinations.append(params)
        
        # Run backtest for each parameter combination
        results = []
        
        for params in param_combinations:
            # Create strategy instance with parameters
            strategy = MeanReversionStrategy()
            strategy.set_parameters(params)
            
            # Create backtest request
            request = BacktestRequest(
                strategy_name="mean_reversion",
                strategy_parameters=params,
                symbols=["BTC/USDT"],
                timeframe="1h",
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now(),
                initial_capital=10000.0
            )
            
            # Mock the historical data retrieval
            async def mock_get_data(symbol, timeframe, start_date, end_date):
                return await historical_data.get_historical_data(
                    symbol, timeframe, start_date, end_date
                )
            
            # Run backtest
            with patch.object(backtest_engine, '_get_historical_data', side_effect=mock_get_data):
                result = await backtest_engine.run_backtest(request, strategy)
                results.append((params, result))
        
        # Find best parameter set based on total return
        best_params, best_result = max(results, key=lambda x: x[1].metrics["total_return"])
        
        # Verify optimization completed
        assert len(results) == len(param_combinations)
        assert best_result is not None
        
        # Store best result in database
        database.insert("backtest_optimizations", {
            "strategy_name": "mean_reversion",
            "best_parameters": best_params,
            "metrics": best_result.metrics,
            "timestamp": datetime.now().isoformat()
        })
        
        # Verify database was called
        database.assert_called("insert")


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])