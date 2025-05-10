"""
Health Monitor for CryptoBot.

This module provides the HealthMonitor class, which periodically checks service health,
collects performance metrics, detects and reports service failures, supports automatic
restart of failed services, maintains health history for diagnostics, and provides
alerting for critical issues.
"""

import logging
import time
import threading
import psutil
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import os
import socket
import requests
from collections import deque

from .registry import ServiceRegistry, ServiceStatus
from .lifecycle_controller import ServiceLifecycleController

logger = logging.getLogger(__name__)

class HealthCheck:
    """Result of a health check."""
    
    def __init__(self, service_name: str, timestamp: datetime, status: bool, 
                 response_time: float, error_message: Optional[str] = None,
                 metrics: Optional[Dict[str, Any]] = None):
        """
        Initialize a health check result.
        
        Args:
            service_name: Name of the service
            timestamp: Time of the health check
            status: True if the service is healthy, False otherwise
            response_time: Response time in seconds
            error_message: Error message if the service is unhealthy
            metrics: Performance metrics
        """
        self.service_name = service_name
        self.timestamp = timestamp
        self.status = status
        self.response_time = response_time
        self.error_message = error_message
        self.metrics = metrics or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the health check result to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the health check result
        """
        return {
            "service_name": self.service_name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "response_time": self.response_time,
            "error_message": self.error_message,
            "metrics": self.metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HealthCheck':
        """
        Create a health check result from a dictionary.
        
        Args:
            data: Dictionary representation of the health check result
        
        Returns:
            HealthCheck: Health check result
        """
        return cls(
            service_name=data["service_name"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=data["status"],
            response_time=data["response_time"],
            error_message=data["error_message"],
            metrics=data["metrics"]
        )


class HealthMonitor:
    """
    Monitor for service health.
    
    The HealthMonitor periodically checks service health, collects performance metrics,
    detects and reports service failures, supports automatic restart of failed services,
    maintains health history for diagnostics, and provides alerting for critical issues.
    """
    
    def __init__(self, registry: ServiceRegistry, lifecycle_controller: ServiceLifecycleController):
        """
        Initialize the health monitor.
        
        Args:
            registry: Service registry
            lifecycle_controller: Service lifecycle controller
        """
        self._registry = registry
        self._lifecycle_controller = lifecycle_controller
        self._check_interval = 30  # seconds
        self._history_size = 100   # number of health checks to keep per service
        self._health_history: Dict[str, deque] = {}
        self._auto_restart = True
        self._max_restart_attempts = 3
        self._restart_attempts: Dict[str, int] = {}
        self._restart_cooldown = 300  # seconds
        self._last_restart: Dict[str, datetime] = {}
        self._alert_handlers: List[Callable[[str, str], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        logger.info("Health Monitor initialized")
    
    def start(self) -> None:
        """Start the health monitor."""
        if self._running:
            logger.warning("Health Monitor is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Health Monitor started")
    
    def stop(self) -> None:
        """Stop the health monitor."""
        if not self._running:
            logger.warning("Health Monitor is not running")
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health Monitor stopped")
    
    def check_service_health(self, service_name: str) -> HealthCheck:
        """
        Check the health of a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            HealthCheck: Health check result
        
        Raises:
            ValueError: If the service is not registered
        """
        # Get service metadata
        service = self._registry.get_service(service_name)
        
        # Initialize health check result
        timestamp = datetime.now()
        status = False
        response_time = 0.0
        error_message = None
        metrics = {}
        
        # Check if the service is running
        if service.status != ServiceStatus.RUNNING:
            error_message = f"Service is not running (status: {service.status.value})"
            return HealthCheck(
                service_name=service_name,
                timestamp=timestamp,
                status=status,
                response_time=response_time,
                error_message=error_message,
                metrics=metrics
            )
        
        # Check if the process is running
        if service.process_id is not None:
            try:
                process = psutil.Process(service.process_id)
                if not process.is_running():
                    error_message = "Process is not running"
                    return HealthCheck(
                        service_name=service_name,
                        timestamp=timestamp,
                        status=status,
                        response_time=response_time,
                        error_message=error_message,
                        metrics=metrics
                    )
                
                # Collect process metrics
                metrics["cpu_percent"] = process.cpu_percent()
                metrics["memory_percent"] = process.memory_percent()
                metrics["memory_info"] = {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms
                }
                metrics["num_threads"] = process.num_threads()
                metrics["connections"] = len(process.connections())
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                error_message = "Process not found or access denied"
                return HealthCheck(
                    service_name=service_name,
                    timestamp=timestamp,
                    status=status,
                    response_time=response_time,
                    error_message=error_message,
                    metrics=metrics
                )
        
        # Check if the service endpoint is reachable
        if service.host is not None and service.port is not None:
            try:
                # Try to connect to the service
                start_time = time.time()
                
                # First, check if the port is open
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((service.host, service.port))
                s.close()
                
                if result != 0:
                    error_message = f"Port {service.port} is not open"
                    return HealthCheck(
                        service_name=service_name,
                        timestamp=timestamp,
                        status=status,
                        response_time=response_time,
                        error_message=error_message,
                        metrics=metrics
                    )
                
                # Then, try to access the health endpoint
                try:
                    url = f"http://{service.host}:{service.port}/health"
                    response = requests.get(url, timeout=5)
                    response_time = time.time() - start_time
                    
                    if response.status_code == 200:
                        status = True
                        try:
                            # Try to parse the response as JSON
                            health_data = response.json()
                            
                            # Update metrics with health data
                            if isinstance(health_data, dict):
                                metrics.update(health_data)
                        except:
                            # Ignore JSON parsing errors
                            pass
                    else:
                        error_message = f"Health check failed with status code {response.status_code}"
                except requests.RequestException as e:
                    error_message = f"Error accessing health endpoint: {str(e)}"
                    response_time = time.time() - start_time
            except Exception as e:
                error_message = f"Error checking service health: {str(e)}"
        else:
            # No endpoint information available
            error_message = "No endpoint information available"
        
        # Create health check result
        health_check = HealthCheck(
            service_name=service_name,
            timestamp=timestamp,
            status=status,
            response_time=response_time,
            error_message=error_message,
            metrics=metrics
        )
        
        # Store health check in history
        self._add_to_history(service_name, health_check)
        
        # Update service metrics
        self._registry.update_service_metrics(service_name, metrics)
        
        return health_check
    
    def check_all_services_health(self) -> Dict[str, HealthCheck]:
        """
        Check the health of all running services.
        
        Returns:
            Dict[str, HealthCheck]: Dictionary mapping service names to health check results
        """
        results = {}
        
        for service_name in self._registry.get_running_services():
            results[service_name] = self.check_service_health(service_name)
        
        return results
    
    def get_service_health_history(self, service_name: str) -> List[HealthCheck]:
        """
        Get the health history of a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            List[HealthCheck]: List of health check results
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is registered
        self._registry.get_service(service_name)
        
        # Get health history
        if service_name not in self._health_history:
            return []
        
        return list(self._health_history[service_name])
    
    def clear_service_health_history(self, service_name: str) -> None:
        """
        Clear the health history of a service.
        
        Args:
            service_name: Name of the service
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is registered
        self._registry.get_service(service_name)
        
        # Clear health history
        if service_name in self._health_history:
            self._health_history[service_name].clear()
    
    def set_check_interval(self, interval: int) -> None:
        """
        Set the health check interval.
        
        Args:
            interval: Interval in seconds
        """
        self._check_interval = interval
    
    def set_history_size(self, size: int) -> None:
        """
        Set the health history size.
        
        Args:
            size: Number of health checks to keep per service
        """
        self._history_size = size
        
        # Resize existing histories
        for service_name in self._health_history:
            history = self._health_history[service_name]
            while len(history) > size:
                history.popleft()
    
    def set_auto_restart(self, enabled: bool) -> None:
        """
        Enable or disable automatic restart of failed services.
        
        Args:
            enabled: True to enable, False to disable
        """
        self._auto_restart = enabled
    
    def set_max_restart_attempts(self, attempts: int) -> None:
        """
        Set the maximum number of restart attempts.
        
        Args:
            attempts: Maximum number of restart attempts
        """
        self._max_restart_attempts = attempts
    
    def set_restart_cooldown(self, cooldown: int) -> None:
        """
        Set the restart cooldown period.
        
        Args:
            cooldown: Cooldown period in seconds
        """
        self._restart_cooldown = cooldown
    
    def add_alert_handler(self, handler: Callable[[str, str], None]) -> None:
        """
        Add an alert handler.
        
        Args:
            handler: Function that takes a service name and an alert message
        """
        self._alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: Callable[[str, str], None]) -> None:
        """
        Remove an alert handler.
        
        Args:
            handler: Handler to remove
        """
        if handler in self._alert_handlers:
            self._alert_handlers.remove(handler)
    
    def _add_to_history(self, service_name: str, health_check: HealthCheck) -> None:
        """
        Add a health check to the history.
        
        Args:
            service_name: Name of the service
            health_check: Health check result
        """
        if service_name not in self._health_history:
            self._health_history[service_name] = deque(maxlen=self._history_size)
        
        self._health_history[service_name].append(health_check)
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Check all services
                health_results = self.check_all_services_health()
                
                # Handle unhealthy services
                for service_name, health_check in health_results.items():
                    if not health_check.status:
                        self._handle_unhealthy_service(service_name, health_check)
            except Exception as e:
                logger.exception(f"Error in health monitor loop: {e}")
            
            # Wait for the next check
            for _ in range(self._check_interval * 2):  # Check every 0.5 seconds if we should stop
                if not self._running:
                    break
                time.sleep(0.5)
    
    def _handle_unhealthy_service(self, service_name: str, health_check: HealthCheck) -> None:
        """
        Handle an unhealthy service.
        
        Args:
            service_name: Name of the service
            health_check: Health check result
        """
        # Log the issue
        logger.warning(f"Service '{service_name}' is unhealthy: {health_check.error_message}")
        
        # Send alerts
        alert_message = f"Service '{service_name}' is unhealthy: {health_check.error_message}"
        self._send_alert(service_name, alert_message)
        
        # Check if we should restart the service
        if self._auto_restart:
            self._try_restart_service(service_name)
    
    def _try_restart_service(self, service_name: str) -> None:
        """
        Try to restart a service.
        
        Args:
            service_name: Name of the service
        """
        # Check if we've reached the maximum number of restart attempts
        if service_name in self._restart_attempts and self._restart_attempts[service_name] >= self._max_restart_attempts:
            logger.warning(f"Maximum restart attempts reached for service '{service_name}'")
            return
        
        # Check if we're in the cooldown period
        if service_name in self._last_restart:
            elapsed = datetime.now() - self._last_restart[service_name]
            if elapsed.total_seconds() < self._restart_cooldown:
                logger.info(f"In cooldown period for service '{service_name}', not restarting")
                return
        
        # Increment restart attempts
        if service_name not in self._restart_attempts:
            self._restart_attempts[service_name] = 0
        self._restart_attempts[service_name] += 1
        
        # Update last restart time
        self._last_restart[service_name] = datetime.now()
        
        # Log the restart attempt
        logger.info(f"Attempting to restart service '{service_name}' (attempt {self._restart_attempts[service_name]})")
        
        # Restart the service
        try:
            if self._lifecycle_controller.restart_service(service_name):
                logger.info(f"Service '{service_name}' restarted successfully")
                
                # Reset restart attempts on successful restart
                self._restart_attempts[service_name] = 0
                
                # Send alert
                self._send_alert(service_name, f"Service '{service_name}' restarted successfully")
            else:
                logger.error(f"Failed to restart service '{service_name}'")
                
                # Send alert
                self._send_alert(service_name, f"Failed to restart service '{service_name}'")
        except Exception as e:
            logger.exception(f"Error restarting service '{service_name}': {e}")
            
            # Send alert
            self._send_alert(service_name, f"Error restarting service '{service_name}': {str(e)}")
    
    def _send_alert(self, service_name: str, message: str) -> None:
        """
        Send an alert.
        
        Args:
            service_name: Name of the service
            message: Alert message
        """
        for handler in self._alert_handlers:
            try:
                handler(service_name, message)
            except Exception as e:
                logger.exception(f"Error in alert handler: {e}")
    
    def save_health_history(self, file_path: str) -> None:
        """
        Save the health history to a file.
        
        Args:
            file_path: Path to the file
        """
        try:
            # Convert health history to a serializable format
            history_data = {}
            for service_name, history in self._health_history.items():
                history_data[service_name] = [h.to_dict() for h in history]
            
            # Save to file
            with open(file_path, "w") as f:
                json.dump(history_data, f, indent=2)
            
            logger.info(f"Health history saved to {file_path}")
        except Exception as e:
            logger.exception(f"Error saving health history: {e}")
    
    def load_health_history(self, file_path: str) -> None:
        """
        Load the health history from a file.
        
        Args:
            file_path: Path to the file
        """
        try:
            # Load from file
            with open(file_path, "r") as f:
                history_data = json.load(f)
            
            # Convert to health check objects
            for service_name, history in history_data.items():
                if service_name not in self._health_history:
                    self._health_history[service_name] = deque(maxlen=self._history_size)
                
                for item in history:
                    health_check = HealthCheck.from_dict(item)
                    self._health_history[service_name].append(health_check)
            
            logger.info(f"Health history loaded from {file_path}")
        except Exception as e:
            logger.exception(f"Error loading health history: {e}")