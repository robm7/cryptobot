"""
Integration Test Framework Base Module

This module provides the base classes and utilities for integration testing.
"""

import asyncio
import logging
import os
import pytest
from typing import Dict, Any, Optional, List, Callable, Type
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_tests")


class IntegrationTestBase:
    """
    Base class for all integration tests.
    
    Provides common functionality for setting up and tearing down test environments,
    managing service dependencies, and asserting on integration behaviors.
    """
    
    # Class variables for configuration
    test_env: str = os.environ.get("TEST_ENV", "test")
    services_started: List[str] = []
    
    @classmethod
    def setup_class(cls):
        """Set up the test class environment"""
        logger.info(f"Setting up integration test environment: {cls.test_env}")
        cls.services_started = []
    
    @classmethod
    def teardown_class(cls):
        """Tear down the test class environment"""
        logger.info(f"Tearing down integration test environment: {cls.test_env}")
        for service in reversed(cls.services_started):
            logger.info(f"Stopping service: {service}")
    
    @staticmethod
    async def wait_for_service(
        check_func: Callable[[], bool], 
        timeout: int = 30, 
        interval: float = 0.5,
        service_name: str = "service"
    ) -> bool:
        """
        Wait for a service to be ready.
        
        Args:
            check_func: Function that returns True when service is ready
            timeout: Maximum time to wait in seconds
            interval: Check interval in seconds
            service_name: Name of the service for logging
            
        Returns:
            True if service is ready, False if timeout occurred
        """
        logger.info(f"Waiting for {service_name} to be ready (timeout: {timeout}s)")
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                if check_func():
                    logger.info(f"{service_name} is ready")
                    return True
            except Exception as e:
                logger.debug(f"Service check failed: {str(e)}")
            
            await asyncio.sleep(interval)
        
        logger.error(f"Timeout waiting for {service_name}")
        return False
    
    @staticmethod
    @asynccontextmanager
    async def service_context(
        setup_func: Callable[[], Any],
        teardown_func: Callable[[Any], None],
        service_name: str = "service"
    ):
        """
        Context manager for service lifecycle.
        
        Args:
            setup_func: Function to set up the service
            teardown_func: Function to tear down the service
            service_name: Name of the service for logging
        """
        logger.info(f"Starting {service_name}")
        service = setup_func()
        try:
            yield service
        finally:
            logger.info(f"Stopping {service_name}")
            teardown_func(service)
    
    @staticmethod
    def assert_successful_interaction(
        source_service: str,
        target_service: str,
        interaction_result: Any,
        expected_result: Any = None
    ):
        """
        Assert that an interaction between services was successful.
        
        Args:
            source_service: Name of the source service
            target_service: Name of the target service
            interaction_result: Result of the interaction
            expected_result: Expected result (if None, just check not None/False)
        """
        logger.info(f"Verifying interaction: {source_service} -> {target_service}")
        
        if expected_result is not None:
            assert interaction_result == expected_result, (
                f"Interaction from {source_service} to {target_service} "
                f"produced unexpected result: {interaction_result}"
            )
        else:
            assert interaction_result, (
                f"Interaction from {source_service} to {target_service} failed"
            )
        
        logger.info(f"Interaction verified: {source_service} -> {target_service}")


class ServiceMock:
    """
    Base class for service mocks.
    
    Provides common functionality for mocking services in integration tests.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.calls: Dict[str, List[Dict[str, Any]]] = {}
        logger.info(f"Initialized mock for {service_name}")
    
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
            "kwargs": kwargs
        })
        
        logger.debug(f"Recorded call to {self.service_name}.{method}")
    
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