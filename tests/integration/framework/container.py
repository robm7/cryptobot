"""
Service Container for Integration Tests

This module provides a container for managing service dependencies
and their interactions during integration tests.
"""

import logging
from typing import Dict, Any, Optional, Type, Callable, List, Set
import inspect

logger = logging.getLogger("integration_tests")


class ServiceContainer:
    """
    Container for managing service dependencies and their interactions.
    
    The ServiceContainer manages the lifecycle of services, their dependencies,
    and provides a way to access services during integration tests.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[..., Any]] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._initialized: Set[str] = set()
        logger.info("Initialized ServiceContainer")
    
    def register_factory(
        self, 
        service_name: str, 
        factory: Callable[..., Any],
        dependencies: Optional[List[str]] = None
    ):
        """
        Register a service factory.
        
        Args:
            service_name: Name of the service
            factory: Factory function that creates the service
            dependencies: List of service dependencies
        """
        self._factories[service_name] = factory
        self._dependencies[service_name] = set(dependencies or [])
        logger.info(f"Registered factory for {service_name}")
    
    def register_instance(self, service_name: str, instance: Any):
        """
        Register a service instance.
        
        Args:
            service_name: Name of the service
            instance: Service instance
        """
        self._services[service_name] = instance
        self._initialized.add(service_name)
        logger.info(f"Registered instance for {service_name}")
    
    def get(self, service_name: str) -> Any:
        """
        Get a service instance.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
            RuntimeError: If circular dependency is detected
        """
        # Check if service is already initialized
        if service_name in self._initialized:
            return self._services[service_name]
        
        # Check if service factory exists
        if service_name not in self._factories:
            raise KeyError(f"Service not registered: {service_name}")
        
        # Initialize dependencies first
        self._initialize_dependencies(service_name, set())
        
        # Initialize service
        factory = self._factories[service_name]
        
        # Inspect factory signature to inject dependencies
        sig = inspect.signature(factory)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in self._services:
                kwargs[param_name] = self._services[param_name]
        
        # Create service instance
        instance = factory(**kwargs)
        self._services[service_name] = instance
        self._initialized.add(service_name)
        
        logger.info(f"Initialized service: {service_name}")
        return instance
    
    def _initialize_dependencies(self, service_name: str, visited: Set[str]):
        """
        Initialize service dependencies.
        
        Args:
            service_name: Name of the service
            visited: Set of visited services (for cycle detection)
            
        Raises:
            RuntimeError: If circular dependency is detected
        """
        # Check for circular dependencies
        if service_name in visited:
            path = " -> ".join(visited) + " -> " + service_name
            raise RuntimeError(f"Circular dependency detected: {path}")
        
        # Mark service as visited
        visited.add(service_name)
        
        # Initialize dependencies
        for dependency in self._dependencies.get(service_name, set()):
            if dependency not in self._initialized:
                self._initialize_dependencies(dependency, visited.copy())
                self.get(dependency)
    
    def reset(self):
        """Reset the container, clearing all services."""
        for service_name in list(self._services.keys()):
            service = self._services[service_name]
            if hasattr(service, "close") and callable(service.close):
                try:
                    service.close()
                except Exception as e:
                    logger.warning(f"Error closing service {service_name}: {e}")
        
        self._services.clear()
        self._initialized.clear()
        logger.info("Reset ServiceContainer")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset()


class MockServiceFactory:
    """
    Factory for creating mock services with predefined behaviors.
    """
    
    @staticmethod
    def create_mock_service(
        service_class: Type,
        methods: Optional[Dict[str, Callable]] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Create a mock service.
        
        Args:
            service_class: Service class to mock
            methods: Dictionary of method names to mock functions
            attributes: Dictionary of attribute names to values
            
        Returns:
            Mock service instance
        """
        # Create mock instance
        mock_instance = type(
            f"Mock{service_class.__name__}",
            (service_class,),
            {}
        )()
        
        # Add mock methods
        if methods:
            for method_name, mock_func in methods.items():
                setattr(mock_instance, method_name, mock_func)
        
        # Add mock attributes
        if attributes:
            for attr_name, value in attributes.items():
                setattr(mock_instance, attr_name, value)
        
        logger.info(f"Created mock service: {service_class.__name__}")
        return mock_instance