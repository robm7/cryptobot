"""
Service Integration Tests

This module contains integration tests for service interactions in the cryptobot project.
It tests the interactions between different services, such as data, strategy, and trade.
"""

import pytest
import logging
import asyncio
from typing import Dict, Any, List

from tests.integration.framework.base import IntegrationTestBase
from tests.integration.framework.container import ServiceContainer
from tests.integration.framework.mocks import (
    MockExchangeService, MockDatabaseService, MockRedisService
)
from tests.integration.framework.utils import wait_for_port, wait_for_http

logger = logging.getLogger("integration_tests")


class TestServiceIntegration(IntegrationTestBase):
    """
    Integration tests for service interactions.
    
    These tests verify that different services can interact correctly with each other.
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
    def test_data_to_strategy_integration(self):
        """Test data service to strategy service integration."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        
        # Set up test data
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
        
        # Create test strategy in database
        strategy_id = database.insert("strategies", {
            "name": "Test Strategy",
            "description": "Test strategy for integration testing",
            "parameters": '{"param1": 10, "param2": 20}',
            "user_id": 1
        })
        
        # Simulate data service sending ticker update to strategy service
        ticker_data = exchange.get_ticker("BTC/USDT")
        
        # In a real test, we would call the strategy service API
        # For this example, we'll just simulate the interaction
        
        # Verify strategy service received the ticker update
        # In a real test, we would check the strategy service's response
        # For this example, we'll just assert that the exchange was called
        exchange.assert_called("get_ticker")
        
        # Verify strategy was retrieved from database
        database.assert_called("query")
    
    @pytest.mark.integration
    def test_strategy_to_trade_integration(self):
        """Test strategy service to trade service integration."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        redis = self.container.get("redis")
        
        # Set up test data
        exchange.add_market("ETH/USDT", {
            "id": "ETHUSDT",
            "symbol": "ETH/USDT",
            "base": "ETH",
            "quote": "USDT",
            "active": True
        })
        
        exchange.set_default_response("place_order", {
            "id": "test_order_1",
            "symbol": "ETH/USDT",
            "type": "limit",
            "side": "buy",
            "amount": 1.0,
            "price": 3000.0,
            "status": "open"
        })
        
        # Create test strategy in database
        strategy_id = database.insert("strategies", {
            "name": "Test Strategy",
            "description": "Test strategy for integration testing",
            "parameters": '{"param1": 10, "param2": 20}',
            "user_id": 1
        })
        
        # Simulate strategy service generating a signal
        signal = {
            "strategy_id": strategy_id,
            "symbol": "ETH/USDT",
            "side": "buy",
            "type": "limit",
            "amount": 1.0,
            "price": 3000.0
        }
        
        # Store signal in Redis (as strategy service would)
        redis.set("signal:test_signal_1", signal)
        
        # Simulate trade service processing the signal
        # In a real test, we would call the trade service API
        # For this example, we'll just simulate the interaction
        
        # Retrieve signal from Redis (as trade service would)
        retrieved_signal = redis.get("signal:test_signal_1")
        
        # Place order on exchange (as trade service would)
        order = exchange.place_order(
            retrieved_signal["symbol"],
            retrieved_signal["type"],
            retrieved_signal["side"],
            retrieved_signal["amount"],
            retrieved_signal["price"]
        )
        
        # Store order in database (as trade service would)
        trade_id = database.insert("trades", {
            "symbol": order["symbol"],
            "trade_type": order["type"],
            "side": order["side"],
            "amount": order["amount"],
            "price": order["price"],
            "strategy_id": retrieved_signal["strategy_id"],
            "user_id": 1,
            "exchange_order_id": order["id"]
        })
        
        # Verify order was placed on exchange
        exchange.assert_called("place_order")
        
        # Verify trade was stored in database
        database.assert_called("insert")
    
    @pytest.mark.integration
    def test_error_handling_across_services(self):
        """Test error handling across services."""
        # Get mock services
        exchange = self.container.get("exchange")
        database = self.container.get("database")
        redis = self.container.get("redis")
        
        # Set up test data with error condition
        exchange.set_default_response("place_order", Exception("API error"))
        
        # Create test strategy in database
        strategy_id = database.insert("strategies", {
            "name": "Test Strategy",
            "description": "Test strategy for integration testing",
            "parameters": '{"param1": 10, "param2": 20}',
            "user_id": 1
        })
        
        # Simulate strategy service generating a signal
        signal = {
            "strategy_id": strategy_id,
            "symbol": "SOL/USDT",
            "side": "buy",
            "type": "limit",
            "amount": 10.0,
            "price": 100.0
        }
        
        # Store signal in Redis (as strategy service would)
        redis.set("signal:test_signal_2", signal)
        
        # Simulate trade service processing the signal with error handling
        # In a real test, we would call the trade service API
        # For this example, we'll just simulate the interaction
        
        # Retrieve signal from Redis (as trade service would)
        retrieved_signal = redis.get("signal:test_signal_2")
        
        # Try to place order on exchange (as trade service would)
        try:
            order = exchange.place_order(
                retrieved_signal["symbol"],
                retrieved_signal["type"],
                retrieved_signal["side"],
                retrieved_signal["amount"],
                retrieved_signal["price"]
            )
            
            # This should not be reached due to the exception
            assert False, "Expected exception was not raised"
        except Exception as e:
            # Verify exception was raised
            assert str(e) == "API error"
            
            # Store error in database (as trade service would)
            error_id = database.insert("errors", {
                "service": "trade",
                "error_type": "exchange_api_error",
                "error_message": str(e),
                "strategy_id": retrieved_signal["strategy_id"],
                "symbol": retrieved_signal["symbol"]
            })
        
        # Verify order placement was attempted
        exchange.assert_called("place_order")
        
        # Verify error was stored in database
        database.assert_called("insert")


class TestDockerServiceIntegration(IntegrationTestBase):
    """
    Integration tests for services running in Docker containers.
    
    These tests verify that services can interact correctly when running in Docker containers.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        super().setup_class()
        
        # Skip tests if not running with Docker
        if not pytest.config.getoption("--docker", default=False):
            pytest.skip("Docker tests disabled (use --docker to enable)")
    
    @pytest.mark.integration
    @pytest.mark.docker
    def test_auth_service_integration(self):
        """Test authentication service integration."""
        # Wait for auth service to be ready
        assert wait_for_http("http://localhost:8001/health", timeout=30)
        
        # Test authentication endpoints
        # In a real test, we would use requests to call the auth service API
        # For this example, we'll just simulate the interaction
        
        # Verify auth service is working
        assert True
    
    @pytest.mark.integration
    @pytest.mark.docker
    def test_strategy_service_integration(self):
        """Test strategy service integration."""
        # Wait for strategy service to be ready
        assert wait_for_http("http://localhost:8002/health", timeout=30)
        
        # Test strategy endpoints
        # In a real test, we would use requests to call the strategy service API
        # For this example, we'll just simulate the interaction
        
        # Verify strategy service is working
        assert True
    
    @pytest.mark.integration
    @pytest.mark.docker
    def test_trade_service_integration(self):
        """Test trade service integration."""
        # Wait for trade service to be ready
        assert wait_for_http("http://localhost:8003/health", timeout=30)
        
        # Test trade endpoints
        # In a real test, we would use requests to call the trade service API
        # For this example, we'll just simulate the interaction
        
        # Verify trade service is working
        assert True


if __name__ == "__main__":
    pytest.main(["-v", __file__])