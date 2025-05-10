"""
Service Lifecycle Controller for CryptoBot.

This module provides the ServiceLifecycleController class, which starts and stops
services in the correct order, manages service initialization and cleanup, handles
graceful shutdown, supports restart of individual services, and implements timeout
handling for service operations.
"""

import logging
import time
import asyncio
import multiprocessing
import signal
from typing import Dict, List, Optional, Any, Callable, Coroutine
import subprocess
import sys
import os

from .registry import ServiceRegistry, ServiceStatus
from .dependency_resolver import DependencyResolver

logger = logging.getLogger(__name__)

class ServiceLifecycleController:
    """
    Controller for service lifecycle.
    
    The ServiceLifecycleController starts and stops services in the correct order,
    manages service initialization and cleanup, handles graceful shutdown, supports
    restart of individual services, and implements timeout handling for service operations.
    """
    
    def __init__(self, registry: ServiceRegistry, dependency_resolver: DependencyResolver):
        """
        Initialize the service lifecycle controller.
        
        Args:
            registry: Service registry
            dependency_resolver: Dependency resolver
        """
        self._registry = registry
        self._dependency_resolver = dependency_resolver
        self._processes: Dict[str, multiprocessing.Process] = {}
        self._start_timeout = 30  # seconds
        self._stop_timeout = 10   # seconds
        logger.info("Service Lifecycle Controller initialized")
    
    def start_service(self, service_name: str) -> bool:
        """
        Start a service.
        
        Args:
            service_name: Name of the service to start
        
        Returns:
            bool: True if the service was started successfully, False otherwise
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is already running
        if self._registry.is_service_running(service_name):
            logger.info(f"Service '{service_name}' is already running")
            return True
        
        # Check if dependencies are satisfied
        if not self._dependency_resolver.can_start_service(service_name):
            logger.error(f"Cannot start service '{service_name}': dependencies not satisfied")
            return False
        
        # Get service metadata
        service = self._registry.get_service(service_name)
        
        # Update service status
        self._registry.update_service_status(service_name, ServiceStatus.STARTING)
        
        try:
            # Import the appropriate module based on service name
            if service_name == "auth":
                from auth.main import app
            elif service_name == "strategy":
                from strategy.main import app
            elif service_name == "data":
                from data.main import app
            elif service_name == "trade":
                from trade.main import app
            elif service_name == "backtest":
                from backtest.main import app
            else:
                logger.error(f"Unknown service: {service_name}")
                self._registry.update_service_status(
                    service_name, 
                    ServiceStatus.ERROR, 
                    f"Unknown service: {service_name}"
                )
                return False
            
            # Configure service
            host = service.config.get("host", "0.0.0.0")
            port = service.config.get("port", 8000)
            workers = service.config.get("workers", 1)
            
            # Update service endpoint
            self._registry.update_service_endpoint(service_name, host, port)
            
            # Create a function to run the service
            def run_service():
                import uvicorn
                uvicorn.run(
                    app,
                    host=host,
                    port=port,
                    workers=workers,
                    log_level="info"
                )
            
            # Start the service in a separate process
            process = multiprocessing.Process(
                target=run_service,
                name=f"{service_name}-service"
            )
            process.start()
            
            # Store the process
            self._processes[service_name] = process
            
            # Update service process ID
            self._registry.update_service_process_id(service_name, process.pid)
            
            # Wait for the service to start
            start_time = time.time()
            while time.time() - start_time < self._start_timeout:
                if self._check_service_health(service_name, host, port):
                    # Service is running
                    self._registry.update_service_status(service_name, ServiceStatus.RUNNING)
                    logger.info(f"Service '{service_name}' started successfully")
                    return True
                
                # Check if the process is still running
                if not process.is_alive():
                    # Process died
                    self._registry.update_service_status(
                        service_name, 
                        ServiceStatus.ERROR, 
                        f"Process died during startup"
                    )
                    logger.error(f"Service '{service_name}' process died during startup")
                    return False
                
                # Wait a bit before checking again
                time.sleep(0.5)
            
            # Timeout
            self._registry.update_service_status(
                service_name, 
                ServiceStatus.ERROR, 
                f"Timeout waiting for service to start"
            )
            logger.error(f"Timeout waiting for service '{service_name}' to start")
            
            # Kill the process
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    process.kill()
            
            return False
            
        except Exception as e:
            # Update service status
            self._registry.update_service_status(
                service_name, 
                ServiceStatus.ERROR, 
                str(e)
            )
            logger.exception(f"Error starting service '{service_name}': {e}")
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """
        Stop a service.
        
        Args:
            service_name: Name of the service to stop
        
        Returns:
            bool: True if the service was stopped successfully, False otherwise
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is running
        if not self._registry.is_service_running(service_name):
            logger.info(f"Service '{service_name}' is not running")
            return True
        
        # Update service status
        self._registry.update_service_status(service_name, ServiceStatus.STOPPING)
        
        # Get the process
        process = self._processes.get(service_name)
        
        if process and process.is_alive():
            # Try to terminate the process gracefully
            process.terminate()
            
            # Wait for the process to terminate
            start_time = time.time()
            while time.time() - start_time < self._stop_timeout:
                if not process.is_alive():
                    # Process terminated
                    break
                
                # Wait a bit before checking again
                time.sleep(0.1)
            
            # If the process is still alive, kill it
            if process.is_alive():
                logger.warning(f"Service '{service_name}' did not terminate gracefully, killing...")
                process.kill()
                process.join()
        
        # Remove the process
        if service_name in self._processes:
            del self._processes[service_name]
        
        # Update service status
        self._registry.update_service_status(service_name, ServiceStatus.STOPPED)
        logger.info(f"Service '{service_name}' stopped")
        
        return True
    
    def restart_service(self, service_name: str) -> bool:
        """
        Restart a service.
        
        Args:
            service_name: Name of the service to restart
        
        Returns:
            bool: True if the service was restarted successfully, False otherwise
        
        Raises:
            ValueError: If the service is not registered
        """
        logger.info(f"Restarting service '{service_name}'...")
        
        # Stop the service
        if not self.stop_service(service_name):
            logger.error(f"Failed to stop service '{service_name}' during restart")
            return False
        
        # Start the service
        if not self.start_service(service_name):
            logger.error(f"Failed to start service '{service_name}' during restart")
            return False
        
        logger.info(f"Service '{service_name}' restarted successfully")
        return True
    
    def start_all_services(self) -> bool:
        """
        Start all registered services in the correct order.
        
        Returns:
            bool: True if all services were started successfully, False otherwise
        """
        logger.info("Starting all services...")
        
        # Get the startup order
        try:
            startup_order = self._dependency_resolver.get_startup_order()
        except Exception as e:
            logger.exception(f"Error determining startup order: {e}")
            return False
        
        # Start services in order
        success = True
        for service_name in startup_order:
            # Skip services that are already running
            if self._registry.is_service_running(service_name):
                continue
            
            # Get service metadata
            service = self._registry.get_service(service_name)
            
            # Skip disabled services
            if not service.config.get("enabled", True):
                logger.info(f"Skipping disabled service '{service_name}'")
                continue
            
            # Start the service
            if not self.start_service(service_name):
                logger.error(f"Failed to start service '{service_name}'")
                success = False
                break
        
        if success:
            logger.info("All services started successfully")
        else:
            logger.error("Failed to start all services")
        
        return success
    
    def stop_all_services(self) -> bool:
        """
        Stop all running services in the correct order.
        
        Returns:
            bool: True if all services were stopped successfully, False otherwise
        """
        logger.info("Stopping all services...")
        
        # Get the shutdown order
        try:
            shutdown_order = self._dependency_resolver.get_shutdown_order()
        except Exception as e:
            logger.exception(f"Error determining shutdown order: {e}")
            return False
        
        # Stop services in order
        success = True
        for service_name in shutdown_order:
            # Skip services that are not running
            if not self._registry.is_service_running(service_name):
                continue
            
            # Stop the service
            if not self.stop_service(service_name):
                logger.error(f"Failed to stop service '{service_name}'")
                success = False
        
        if success:
            logger.info("All services stopped successfully")
        else:
            logger.error("Failed to stop all services")
        
        return success
    
    def _check_service_health(self, service_name: str, host: str, port: int) -> bool:
        """
        Check if a service is healthy.
        
        Args:
            service_name: Name of the service
            host: Host address
            port: Port number
        
        Returns:
            bool: True if the service is healthy, False otherwise
        """
        # For now, just check if the port is open
        import socket
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect((host, port))
            s.close()
            return True
        except:
            return False
    
    def set_start_timeout(self, timeout: int) -> None:
        """
        Set the timeout for starting services.
        
        Args:
            timeout: Timeout in seconds
        """
        self._start_timeout = timeout
    
    def set_stop_timeout(self, timeout: int) -> None:
        """
        Set the timeout for stopping services.
        
        Args:
            timeout: Timeout in seconds
        """
        self._stop_timeout = timeout
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop all services
        self.stop_all_services()
        
        # Clear processes
        self._processes.clear()