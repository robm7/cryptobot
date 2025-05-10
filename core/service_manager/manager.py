"""
Service Manager for CryptoBot.

This module provides the ServiceManager class, which is the central component
responsible for coordinating all services in the CryptoBot application.
"""

import logging
import os
import json
import signal
import sys
from typing import Dict, List, Optional, Any, Callable, Set

from .registry import ServiceRegistry, ServiceStatus, ServiceMetadata
from .dependency_resolver import DependencyResolver
from .lifecycle_controller import ServiceLifecycleController
from .health_monitor import HealthMonitor
from .resource_manager import ResourceManager
from .ui_adapter import UserInterfaceAdapter

logger = logging.getLogger(__name__)

class ServiceManager:
    """
    Manager for CryptoBot services.
    
    The ServiceManager is the central component responsible for coordinating
    all services in the CryptoBot application. It integrates the Service Registry,
    Dependency Resolver, Service Lifecycle Controller, Health Monitor, Resource Manager,
    and User Interface Adapter.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the service manager.
        
        Args:
            config: Configuration dictionary
        """
        self._config = config
        
        # Initialize components
        self._registry = ServiceRegistry()
        self._dependency_resolver = DependencyResolver(self._registry)
        self._lifecycle_controller = ServiceLifecycleController(self._registry, self._dependency_resolver)
        self._health_monitor = HealthMonitor(self._registry, self._lifecycle_controller)
        self._resource_manager = ResourceManager(self._registry)
        self._ui_adapter = UserInterfaceAdapter(
            self._registry,
            self._lifecycle_controller,
            self._health_monitor,
            self._resource_manager
        )
        
        # Register signal handlers
        self._register_signal_handlers()
        
        logger.info("Service Manager initialized")
    
    def start(self) -> None:
        """Start the service manager."""
        logger.info("Starting Service Manager...")
        
        # Register services
        self._register_services()
        
        # Start health monitor
        self._health_monitor.start()
        
        # Start resource manager
        self._resource_manager.start()
        
        # Start management API if enabled
        if self._config.get("management_api", {}).get("enabled", True):
            host = self._config.get("management_api", {}).get("host", "0.0.0.0")
            port = self._config.get("management_api", {}).get("port", 8080)
            self._ui_adapter.start_api(host, port)
        
        # Start services if auto_start is enabled
        if self._config.get("auto_start", True):
            self._lifecycle_controller.start_all_services()
        
        logger.info("Service Manager started")
    
    def stop(self) -> None:
        """Stop the service manager."""
        logger.info("Stopping Service Manager...")
        
        # Stop services
        self._lifecycle_controller.stop_all_services()
        
        # Stop management API
        self._ui_adapter.stop_api()
        
        # Stop resource manager
        self._resource_manager.stop()
        
        # Stop health monitor
        self._health_monitor.stop()
        
        logger.info("Service Manager stopped")
    
    def get_registry(self) -> ServiceRegistry:
        """
        Get the service registry.
        
        Returns:
            ServiceRegistry: Service registry
        """
        return self._registry
    
    def get_dependency_resolver(self) -> DependencyResolver:
        """
        Get the dependency resolver.
        
        Returns:
            DependencyResolver: Dependency resolver
        """
        return self._dependency_resolver
    
    def get_lifecycle_controller(self) -> ServiceLifecycleController:
        """
        Get the service lifecycle controller.
        
        Returns:
            ServiceLifecycleController: Service lifecycle controller
        """
        return self._lifecycle_controller
    
    def get_health_monitor(self) -> HealthMonitor:
        """
        Get the health monitor.
        
        Returns:
            HealthMonitor: Health monitor
        """
        return self._health_monitor
    
    def get_resource_manager(self) -> ResourceManager:
        """
        Get the resource manager.
        
        Returns:
            ResourceManager: Resource manager
        """
        return self._resource_manager
    
    def get_ui_adapter(self) -> UserInterfaceAdapter:
        """
        Get the user interface adapter.
        
        Returns:
            UserInterfaceAdapter: User interface adapter
        """
        return self._ui_adapter
    
    def handle_cli_command(self, command: str, args: List[str]) -> str:
        """
        Handle a CLI command.
        
        Args:
            command: Command name
            args: Command arguments
        
        Returns:
            str: Command output
        """
        return self._ui_adapter.handle_cli_command(command, args)
    
    def _register_services(self) -> None:
        """Register services from configuration."""
        logger.info("Registering services...")
        
        # Get services from configuration
        services_config = self._config.get("services", {})
        
        # Register each service
        for service_name, service_config in services_config.items():
            # Skip if service is not enabled
            if not service_config.get("enabled", True):
                logger.info(f"Skipping disabled service '{service_name}'")
                continue
            
            # Get service description
            description = service_config.get("description", f"{service_name.capitalize()} service")
            
            # Get service dependencies
            dependencies = set(service_config.get("dependencies", []))
            optional_dependencies = set(service_config.get("optional_dependencies", []))
            
            # Register the service
            self._registry.register_service(
                name=service_name,
                description=description,
                dependencies=dependencies,
                optional_dependencies=optional_dependencies,
                config=service_config
            )
            
            # Set resource limits if specified
            if "resource_limits" in service_config:
                from .resource_manager import ResourceLimits
                
                limits = ResourceLimits(
                    cpu_percent=service_config["resource_limits"].get("cpu_percent"),
                    memory_percent=service_config["resource_limits"].get("memory_percent"),
                    memory_bytes=service_config["resource_limits"].get("memory_bytes"),
                    num_threads=service_config["resource_limits"].get("num_threads"),
                    num_connections=service_config["resource_limits"].get("num_connections")
                )
                
                self._resource_manager.set_resource_limits(service_name, limits)
        
        logger.info(f"Registered {len(self._registry.get_all_services())} services")
    
    def _register_signal_handlers(self) -> None:
        """Register signal handlers."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            self.stop()
            sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    @classmethod
    def from_config_file(cls, config_path: str) -> 'ServiceManager':
        """
        Create a service manager from a configuration file.
        
        Args:
            config_path: Path to the configuration file
        
        Returns:
            ServiceManager: Service manager
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            json.JSONDecodeError: If the configuration file is not valid JSON
        """
        # Check if the file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found")
        
        # Load the configuration
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Create the service manager
        return cls(config)