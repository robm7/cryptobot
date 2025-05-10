"""
Mock Services for Integration Tests

This module provides mock implementations of services for integration testing.
"""

import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, Callable, Type, Union, Set
from unittest.mock import MagicMock, AsyncMock
import threading
import queue
from contextlib import contextmanager

logger = logging.getLogger("integration_tests")


class MockService:
    """
    Base class for mock services.
    
    Provides common functionality for mocking services in integration tests.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.calls: Dict[str, List[Dict[str, Any]]] = {}
        self.responses: Dict[str, List[Any]] = {}
        self.default_responses: Dict[str, Any] = {}
        self.is_running = False
        self.error_rate = 0.0  # Probability of simulated errors
        
        logger.info(f"Initialized mock service: {service_name}")
    
    def start(self):
        """Start the mock service."""
        self.is_running = True
        logger.info(f"Started mock service: {self.service_name}")
    
    def stop(self):
        """Stop the mock service."""
        self.is_running = False
        logger.info(f"Stopped mock service: {self.service_name}")
    
    def reset(self):
        """Reset the mock service state."""
        self.calls.clear()
        self.responses.clear()
        logger.info(f"Reset mock service: {self.service_name}")
    
    def record_call(self, method: str, *args, **kwargs):
        """
        Record a method call.
        
        Args:
            method: Method name
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if method not in self.calls:
            self.calls[method] = []
        
        self.calls[method].append({
            "args": args,
            "kwargs": kwargs,
            "timestamp": time.time()
        })
        
        logger.debug(f"Recorded call to {self.service_name}.{method}")
    
    def add_response(self, method: str, response: Any):
        """
        Add a response for a method.
        
        Args:
            method: Method name
            response: Response value
        """
        if method not in self.responses:
            self.responses[method] = []
        
        self.responses[method].append(response)
        logger.debug(f"Added response for {self.service_name}.{method}")
    
    def set_default_response(self, method: str, response: Any):
        """
        Set a default response for a method.
        
        Args:
            method: Method name
            response: Default response value
        """
        self.default_responses[method] = response
        logger.debug(f"Set default response for {self.service_name}.{method}")
    
    def get_next_response(self, method: str) -> Any:
        """
        Get the next response for a method.
        
        Args:
            method: Method name
            
        Returns:
            Response value
        """
        # Check if we should simulate an error
        if self.error_rate > 0 and random.random() < self.error_rate:
            raise Exception(f"Simulated error in {self.service_name}.{method}")
        
        # Get response from queue if available
        if method in self.responses and self.responses[method]:
            return self.responses[method].pop(0)
        
        # Otherwise return default response
        if method in self.default_responses:
            return self.default_responses[method]
        
        # No response configured
        logger.warning(f"No response configured for {self.service_name}.{method}")
        return None
    
    def get_calls(self, method: str) -> List[Dict[str, Any]]:
        """
        Get recorded calls for a method.
        
        Args:
            method: Method name
            
        Returns:
            List of recorded calls
        """
        return self.calls.get(method, [])
    
    def assert_called(self, method: str, times: Optional[int] = None):
        """
        Assert that a method was called.
        
        Args:
            method: Method name
            times: Expected number of calls (if None, just check > 0)
        """
        calls = self.get_calls(method)
        
        if times is not None:
            assert len(calls) == times, (
                f"Expected {times} calls to {self.service_name}.{method}, "
                f"got {len(calls)}"
            )
        else:
            assert len(calls) > 0, (
                f"Expected at least one call to {self.service_name}.{method}, "
                f"got none"
            )
    
    def assert_not_called(self, method: str):
        """
        Assert that a method was not called.
        
        Args:
            method: Method name
        """
        calls = self.get_calls(method)
        assert len(calls) == 0, (
            f"Expected no calls to {self.service_name}.{method}, "
            f"got {len(calls)}"
        )
    
    def assert_called_with(self, method: str, *args, **kwargs):
        """
        Assert that a method was called with specific arguments.
        
        Args:
            method: Method name
            *args: Expected positional arguments
            **kwargs: Expected keyword arguments
        """
        calls = self.get_calls(method)
        
        assert len(calls) > 0, (
            f"Expected at least one call to {self.service_name}.{method}, "
            f"got none"
        )
        
        for call in calls:
            if call["args"] == args and all(
                call["kwargs"].get(k) == v for k, v in kwargs.items()
            ):
                return
        
        raise AssertionError(
            f"No matching call to {self.service_name}.{method} with "
            f"args={args}, kwargs={kwargs}"
        )
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class MockExchangeService(MockService):
    """
    Mock implementation of an exchange service.
    
    Provides mock implementations of common exchange operations.
    """
    
    def __init__(self, exchange_name: str = "mock_exchange"):
        super().__init__(f"exchange_{exchange_name}")
        self.exchange_name = exchange_name
        self.markets: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.balances: Dict[str, float] = {}
        self.order_id_counter = 1
        
        # Set default responses
        self.set_default_response("get_markets", {})
        self.set_default_response("get_ticker", {"last": 50000.0})
        self.set_default_response("get_balance", 0.0)
        
        logger.info(f"Initialized mock exchange service: {exchange_name}")
    
    def add_market(self, symbol: str, market_data: Dict[str, Any]):
        """
        Add a market.
        
        Args:
            symbol: Market symbol
            market_data: Market data
        """
        self.markets[symbol] = market_data
        logger.debug(f"Added market {symbol} to {self.exchange_name}")
    
    def add_balance(self, currency: str, amount: float):
        """
        Add a balance.
        
        Args:
            currency: Currency code
            amount: Balance amount
        """
        self.balances[currency] = amount
        logger.debug(f"Added balance {amount} {currency} to {self.exchange_name}")
    
    def get_markets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get markets.
        
        Returns:
            Dictionary of markets
        """
        self.record_call("get_markets")
        return self.get_next_response("get_markets") or self.markets
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker for a symbol.
        
        Args:
            symbol: Market symbol
            
        Returns:
            Ticker data
        """
        self.record_call("get_ticker", symbol)
        return self.get_next_response("get_ticker") or {"last": 50000.0}
    
    def get_balance(self, currency: str) -> float:
        """
        Get balance for a currency.
        
        Args:
            currency: Currency code
            
        Returns:
            Balance amount
        """
        self.record_call("get_balance", currency)
        return self.get_next_response("get_balance") or self.balances.get(currency, 0.0)
    
    def place_order(
        self, 
        symbol: str, 
        order_type: str, 
        side: str, 
        amount: float, 
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order.
        
        Args:
            symbol: Market symbol
            order_type: Order type (limit, market)
            side: Order side (buy, sell)
            amount: Order amount
            price: Order price (required for limit orders)
            
        Returns:
            Order data
        """
        self.record_call("place_order", symbol, order_type, side, amount, price)
        
        # Check for configured response
        response = self.get_next_response("place_order")
        if response is not None:
            return response
        
        # Generate order ID
        order_id = str(self.order_id_counter)
        self.order_id_counter += 1
        
        # Create order
        order = {
            "id": order_id,
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "amount": amount,
            "price": price,
            "status": "open",
            "timestamp": time.time()
        }
        
        self.orders[order_id] = order
        logger.debug(f"Placed order {order_id} on {self.exchange_name}")
        
        return order
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order data
        """
        self.record_call("cancel_order", order_id)
        
        # Check for configured response
        response = self.get_next_response("cancel_order")
        if response is not None:
            return response
        
        # Check if order exists
        if order_id not in self.orders:
            raise Exception(f"Order not found: {order_id}")
        
        # Cancel order
        order = self.orders[order_id]
        order["status"] = "canceled"
        
        logger.debug(f"Canceled order {order_id} on {self.exchange_name}")
        return order
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Get an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order data
        """
        self.record_call("get_order", order_id)
        
        # Check for configured response
        response = self.get_next_response("get_order")
        if response is not None:
            return response
        
        # Check if order exists
        if order_id not in self.orders:
            raise Exception(f"Order not found: {order_id}")
        
        return self.orders[order_id]


class MockDatabaseService(MockService):
    """
    Mock implementation of a database service.
    
    Provides mock implementations of common database operations.
    """
    
    def __init__(self, db_name: str = "mock_db"):
        super().__init__(f"database_{db_name}")
        self.db_name = db_name
        self.tables: Dict[str, List[Dict[str, Any]]] = {}
        self.queries: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized mock database service: {db_name}")
    
    def create_table(self, table_name: str):
        """
        Create a table.
        
        Args:
            table_name: Table name
        """
        if table_name not in self.tables:
            self.tables[table_name] = []
            logger.debug(f"Created table {table_name} in {self.db_name}")
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Insert data into a table.
        
        Args:
            table_name: Table name
            data: Data to insert
            
        Returns:
            Row ID
        """
        self.record_call("insert", table_name, data)
        
        # Check for configured response
        response = self.get_next_response("insert")
        if response is not None:
            return response
        
        # Create table if it doesn't exist
        if table_name not in self.tables:
            self.create_table(table_name)
        
        # Add row ID if not provided
        if "id" not in data:
            data["id"] = len(self.tables[table_name]) + 1
        
        # Insert data
        self.tables[table_name].append(data)
        logger.debug(f"Inserted data into {table_name} in {self.db_name}")
        
        return data["id"]
    
    def update(self, table_name: str, row_id: int, data: Dict[str, Any]) -> bool:
        """
        Update data in a table.
        
        Args:
            table_name: Table name
            row_id: Row ID
            data: Data to update
            
        Returns:
            True if successful, False otherwise
        """
        self.record_call("update", table_name, row_id, data)
        
        # Check for configured response
        response = self.get_next_response("update")
        if response is not None:
            return response
        
        # Check if table exists
        if table_name not in self.tables:
            return False
        
        # Find row
        for i, row in enumerate(self.tables[table_name]):
            if row.get("id") == row_id:
                # Update data
                self.tables[table_name][i].update(data)
                logger.debug(f"Updated data in {table_name} in {self.db_name}")
                return True
        
        return False
    
    def delete(self, table_name: str, row_id: int) -> bool:
        """
        Delete data from a table.
        
        Args:
            table_name: Table name
            row_id: Row ID
            
        Returns:
            True if successful, False otherwise
        """
        self.record_call("delete", table_name, row_id)
        
        # Check for configured response
        response = self.get_next_response("delete")
        if response is not None:
            return response
        
        # Check if table exists
        if table_name not in self.tables:
            return False
        
        # Find row
        for i, row in enumerate(self.tables[table_name]):
            if row.get("id") == row_id:
                # Delete row
                del self.tables[table_name][i]
                logger.debug(f"Deleted data from {table_name} in {self.db_name}")
                return True
        
        return False
    
    def query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Query results
        """
        self.record_call("query", query, params)
        
        # Record query
        self.queries.append({
            "query": query,
            "params": params,
            "timestamp": time.time()
        })
        
        # Check for configured response
        response = self.get_next_response("query")
        if response is not None:
            return response
        
        # Simple query parsing (very limited)
        query = query.strip().lower()
        
        if query.startswith("select"):
            # Extract table name (very naive)
            from_parts = query.split("from")
            if len(from_parts) < 2:
                return []
            
            table_parts = from_parts[1].strip().split()
            if not table_parts:
                return []
            
            table_name = table_parts[0]
            
            # Return all rows from table
            if table_name in self.tables:
                return self.tables[table_name]
        
        # Default empty result
        return []


class MockRedisService(MockService):
    """
    Mock implementation of a Redis service.
    
    Provides mock implementations of common Redis operations.
    """
    
    def __init__(self, name: str = "mock_redis"):
        super().__init__(f"redis_{name}")
        self.name = name
        self.data: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        
        logger.info(f"Initialized mock Redis service: {name}")
    
    def get(self, key: str) -> Any:
        """
        Get a value.
        
        Args:
            key: Key
            
        Returns:
            Value
        """
        self.record_call("get", key)
        
        # Check for configured response
        response = self.get_next_response("get")
        if response is not None:
            return response
        
        # Check expiry
        if key in self.expiry and self.expiry[key] < time.time():
            # Key has expired
            del self.data[key]
            del self.expiry[key]
            return None
        
        return self.data.get(key)
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Set a value.
        
        Args:
            key: Key
            value: Value
            ex: Expiry time in seconds
            
        Returns:
            True if successful
        """
        self.record_call("set", key, value, ex)
        
        # Check for configured response
        response = self.get_next_response("set")
        if response is not None:
            return response
        
        # Set value
        self.data[key] = value
        
        # Set expiry
        if ex is not None:
            self.expiry[key] = time.time() + ex
        elif key in self.expiry:
            del self.expiry[key]
        
        return True
    
    def delete(self, key: str) -> bool:
        """
        Delete a value.
        
        Args:
            key: Key
            
        Returns:
            True if successful, False if key doesn't exist
        """
        self.record_call("delete", key)
        
        # Check for configured response
        response = self.get_next_response("delete")
        if response is not None:
            return response
        
        # Delete key
        if key in self.data:
            del self.data[key]
            
            if key in self.expiry:
                del self.expiry[key]
            
            return True
        
        return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists.
        
        Args:
            key: Key
            
        Returns:
            True if key exists, False otherwise
        """
        self.record_call("exists", key)
        
        # Check for configured response
        response = self.get_next_response("exists")
        if response is not None:
            return response
        
        # Check expiry
        if key in self.expiry and self.expiry[key] < time.time():
            # Key has expired
            del self.data[key]
            del self.expiry[key]
            return False
        
        return key in self.data
    
    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a value.
        
        Args:
            key: Key
            amount: Amount to increment
            
        Returns:
            New value
        """
        self.record_call("incr", key, amount)
        
        # Check for configured response
        response = self.get_next_response("incr")
        if response is not None:
            return response
        
        # Check if key exists
        if key not in self.data:
            self.data[key] = 0
        
        # Increment value
        try:
            self.data[key] = int(self.data[key]) + amount
        except (ValueError, TypeError):
            self.data[key] = amount
        
        return self.data[key]


class MockServiceFactory:
    """
    Factory for creating mock services.
    """
    
    @staticmethod
    def create_exchange(name: str = "mock_exchange") -> MockExchangeService:
        """
        Create a mock exchange service.
        
        Args:
            name: Exchange name
            
        Returns:
            Mock exchange service
        """
        return MockExchangeService(name)
    
    @staticmethod
    def create_database(name: str = "mock_db") -> MockDatabaseService:
        """
        Create a mock database service.
        
        Args:
            name: Database name
            
        Returns:
            Mock database service
        """
        return MockDatabaseService(name)
    
    @staticmethod
    def create_redis(name: str = "mock_redis") -> MockRedisService:
        """
        Create a mock Redis service.
        
        Args:
            name: Redis name
            
        Returns:
            Mock Redis service
        """
        return MockRedisService(name)
    
    @staticmethod
    def create_custom_service(
        service_class: Type,
        methods: Dict[str, Callable],
        name: str = "mock_service"
    ) -> MockService:
        """
        Create a custom mock service.
        
        Args:
            service_class: Service class
            methods: Dictionary of method names to mock functions
            name: Service name
            
        Returns:
            Mock service
        """
        # Create mock service
        service = MockService(name)
        
        # Add methods
        for method_name, mock_func in methods.items():
            setattr(service, method_name, mock_func)
        
        return service