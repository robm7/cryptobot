"""
Service Registry for CryptoBot.

This module provides the ServiceRegistry class, which maintains a registry of all
available services, stores service metadata, tracks service status, and provides
service discovery for inter-service communication.
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """Enum representing the status of a service."""
    REGISTERED = "registered"  # Service is registered but not started
    STARTING = "starting"      # Service is in the process of starting
    RUNNING = "running"        # Service is running
    STOPPING = "stopping"      # Service is in the process of stopping
    STOPPED = "stopped"        # Service is stopped
    ERROR = "error"            # Service encountered an error


@dataclass
class ServiceMetadata:
    """Metadata for a service."""
    name: str
    description: str
    dependencies: Set[str] = field(default_factory=set)
    optional_dependencies: Set[str] = field(default_factory=set)
    status: ServiceStatus = ServiceStatus.REGISTERED
    error_message: Optional[str] = None
    process_id: Optional[int] = None
    host: Optional[str] = None
    port: Optional[int] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    """
    Registry of all available services.
    
    The ServiceRegistry maintains a registry of all available services,
    stores service metadata, tracks service status, and provides service
    discovery for inter-service communication.
    """
    
    def __init__(self):
        """Initialize the service registry."""
        self._services: Dict[str, ServiceMetadata] = {}
        logger.info("Service Registry initialized")
    
    def register_service(self, 
                        name: str, 
                        description: str, 
                        dependencies: Optional[Set[str]] = None,
                        optional_dependencies: Optional[Set[str]] = None,
                        config: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a service with the registry.
        
        Args:
            name: Name of the service
            description: Description of the service
            dependencies: Set of service names that this service depends on
            optional_dependencies: Set of service names that this service optionally depends on
            config: Configuration for the service
        
        Raises:
            ValueError: If a service with the same name is already registered
        """
        if name in self._services:
            raise ValueError(f"Service '{name}' is already registered")
        
        self._services[name] = ServiceMetadata(
            name=name,
            description=description,
            dependencies=dependencies or set(),
            optional_dependencies=optional_dependencies or set(),
            config=config or {}
        )
        
        logger.info(f"Service '{name}' registered")
    
    def unregister_service(self, name: str) -> None:
        """
        Unregister a service from the registry.
        
        Args:
            name: Name of the service to unregister
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        del self._services[name]
        logger.info(f"Service '{name}' unregistered")
    
    def get_service(self, name: str) -> ServiceMetadata:
        """
        Get metadata for a service.
        
        Args:
            name: Name of the service
        
        Returns:
            ServiceMetadata: Metadata for the service
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        return self._services[name]
    
    def get_all_services(self) -> Dict[str, ServiceMetadata]:
        """
        Get metadata for all registered services.
        
        Returns:
            Dict[str, ServiceMetadata]: Dictionary of service metadata
        """
        return self._services.copy()
    
    def get_services_by_status(self, status: ServiceStatus) -> List[ServiceMetadata]:
        """
        Get all services with a specific status.
        
        Args:
            status: Status to filter by
        
        Returns:
            List[ServiceMetadata]: List of service metadata
        """
        return [service for service in self._services.values() if service.status == status]
    
    def update_service_status(self, name: str, status: ServiceStatus, error_message: Optional[str] = None) -> None:
        """
        Update the status of a service.
        
        Args:
            name: Name of the service
            status: New status
            error_message: Error message if status is ERROR
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        self._services[name].status = status
        
        if error_message is not None:
            self._services[name].error_message = error_message
        
        logger.info(f"Service '{name}' status updated to {status.value}")
    
    def update_service_process_id(self, name: str, process_id: int) -> None:
        """
        Update the process ID of a service.
        
        Args:
            name: Name of the service
            process_id: Process ID
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        self._services[name].process_id = process_id
        logger.debug(f"Service '{name}' process ID updated to {process_id}")
    
    def update_service_endpoint(self, name: str, host: str, port: int) -> None:
        """
        Update the endpoint (host and port) of a service.
        
        Args:
            name: Name of the service
            host: Host address
            port: Port number
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        self._services[name].host = host
        self._services[name].port = port
        logger.debug(f"Service '{name}' endpoint updated to {host}:{port}")
    
    def update_service_metrics(self, name: str, metrics: Dict[str, Any]) -> None:
        """
        Update the metrics of a service.
        
        Args:
            name: Name of the service
            metrics: Dictionary of metrics
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        self._services[name].metrics.update(metrics)
        logger.debug(f"Service '{name}' metrics updated")
    
    def get_service_endpoint(self, name: str) -> Optional[tuple]:
        """
        Get the endpoint (host and port) of a service.
        
        Args:
            name: Name of the service
        
        Returns:
            Optional[tuple]: Tuple of (host, port) or None if not set
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        service = self._services[name]
        if service.host is not None and service.port is not None:
            return (service.host, service.port)
        
        return None
    
    def is_service_running(self, name: str) -> bool:
        """
        Check if a service is running.
        
        Args:
            name: Name of the service
        
        Returns:
            bool: True if the service is running, False otherwise
        
        Raises:
            ValueError: If the service is not registered
        """
        if name not in self._services:
            raise ValueError(f"Service '{name}' is not registered")
        
        return self._services[name].status == ServiceStatus.RUNNING
    
    def get_running_services(self) -> List[str]:
        """
        Get the names of all running services.
        
        Returns:
            List[str]: List of service names
        """
        return [name for name, service in self._services.items() 
                if service.status == ServiceStatus.RUNNING]
    
    def clear(self) -> None:
        """Clear the registry."""
        self._services.clear()
        logger.info("Service Registry cleared")