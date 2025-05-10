"""
Resource Manager for CryptoBot.

This module provides the ResourceManager class, which monitors resource usage (CPU, memory, disk),
implements resource limits per service, provides resource usage statistics, optimizes resource
allocation, and prevents resource exhaustion.
"""

import logging
import time
import threading
import psutil
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import deque

from .registry import ServiceRegistry, ServiceStatus

logger = logging.getLogger(__name__)

class ResourceUsage:
    """Resource usage information."""
    
    def __init__(self, timestamp: datetime, cpu_percent: float, memory_percent: float,
                 memory_used: int, disk_percent: float, disk_used: int):
        """
        Initialize resource usage information.
        
        Args:
            timestamp: Time of the measurement
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            memory_used: Memory used in bytes
            disk_percent: Disk usage percentage
            disk_used: Disk used in bytes
        """
        self.timestamp = timestamp
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.memory_used = memory_used
        self.disk_percent = disk_percent
        self.disk_used = disk_used
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the resource usage information to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the resource usage information
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used": self.memory_used,
            "disk_percent": self.disk_percent,
            "disk_used": self.disk_used
        }


class ServiceResourceUsage:
    """Resource usage information for a service."""
    
    def __init__(self, service_name: str, timestamp: datetime, cpu_percent: float,
                 memory_percent: float, memory_used: int, num_threads: int,
                 num_connections: int):
        """
        Initialize service resource usage information.
        
        Args:
            service_name: Name of the service
            timestamp: Time of the measurement
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            memory_used: Memory used in bytes
            num_threads: Number of threads
            num_connections: Number of network connections
        """
        self.service_name = service_name
        self.timestamp = timestamp
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.memory_used = memory_used
        self.num_threads = num_threads
        self.num_connections = num_connections
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the service resource usage information to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the service resource usage information
        """
        return {
            "service_name": self.service_name,
            "timestamp": self.timestamp.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_used": self.memory_used,
            "num_threads": self.num_threads,
            "num_connections": self.num_connections
        }


class ResourceLimits:
    """Resource limits for a service."""
    
    def __init__(self, cpu_percent: Optional[float] = None, memory_percent: Optional[float] = None,
                 memory_bytes: Optional[int] = None, num_threads: Optional[int] = None,
                 num_connections: Optional[int] = None):
        """
        Initialize resource limits.
        
        Args:
            cpu_percent: Maximum CPU usage percentage
            memory_percent: Maximum memory usage percentage
            memory_bytes: Maximum memory usage in bytes
            num_threads: Maximum number of threads
            num_connections: Maximum number of network connections
        """
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.memory_bytes = memory_bytes
        self.num_threads = num_threads
        self.num_connections = num_connections
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the resource limits to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the resource limits
        """
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_bytes": self.memory_bytes,
            "num_threads": self.num_threads,
            "num_connections": self.num_connections
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceLimits':
        """
        Create resource limits from a dictionary.
        
        Args:
            data: Dictionary representation of the resource limits
        
        Returns:
            ResourceLimits: Resource limits
        """
        return cls(
            cpu_percent=data.get("cpu_percent"),
            memory_percent=data.get("memory_percent"),
            memory_bytes=data.get("memory_bytes"),
            num_threads=data.get("num_threads"),
            num_connections=data.get("num_connections")
        )


class ResourceManager:
    """
    Manager for system resources.
    
    The ResourceManager monitors resource usage (CPU, memory, disk), implements resource
    limits per service, provides resource usage statistics, optimizes resource allocation,
    and prevents resource exhaustion.
    """
    
    def __init__(self, registry: ServiceRegistry):
        """
        Initialize the resource manager.
        
        Args:
            registry: Service registry
        """
        self._registry = registry
        self._check_interval = 30  # seconds
        self._history_size = 100   # number of measurements to keep
        self._system_usage_history: deque = deque(maxlen=self._history_size)
        self._service_usage_history: Dict[str, deque] = {}
        self._resource_limits: Dict[str, ResourceLimits] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        logger.info("Resource Manager initialized")
    
    def start(self) -> None:
        """Start the resource manager."""
        if self._running:
            logger.warning("Resource Manager is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Resource Manager started")
    
    def stop(self) -> None:
        """Stop the resource manager."""
        if not self._running:
            logger.warning("Resource Manager is not running")
            return
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Resource Manager stopped")
    
    def get_system_resource_usage(self) -> ResourceUsage:
        """
        Get the current system resource usage.
        
        Returns:
            ResourceUsage: System resource usage information
        """
        # Get CPU usage
        cpu_percent = psutil.cpu_percent()
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = memory.used
        
        # Get disk usage
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        disk_percent = disk.percent
        disk_used = disk.used
        
        # Create resource usage object
        usage = ResourceUsage(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used=memory_used,
            disk_percent=disk_percent,
            disk_used=disk_used
        )
        
        # Add to history
        self._system_usage_history.append(usage)
        
        return usage
    
    def get_service_resource_usage(self, service_name: str) -> Optional[ServiceResourceUsage]:
        """
        Get the current resource usage of a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Optional[ServiceResourceUsage]: Service resource usage information, or None if not available
        
        Raises:
            ValueError: If the service is not registered
        """
        # Get service metadata
        service = self._registry.get_service(service_name)
        
        # Check if the service is running
        if service.status != ServiceStatus.RUNNING:
            return None
        
        # Check if the process ID is available
        if service.process_id is None:
            return None
        
        try:
            # Get process information
            process = psutil.Process(service.process_id)
            
            # Get CPU usage
            cpu_percent = process.cpu_percent()
            
            # Get memory usage
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            memory_used = memory_info.rss
            
            # Get thread count
            num_threads = process.num_threads()
            
            # Get connection count
            num_connections = len(process.connections())
            
            # Create service resource usage object
            usage = ServiceResourceUsage(
                service_name=service_name,
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used=memory_used,
                num_threads=num_threads,
                num_connections=num_connections
            )
            
            # Add to history
            if service_name not in self._service_usage_history:
                self._service_usage_history[service_name] = deque(maxlen=self._history_size)
            self._service_usage_history[service_name].append(usage)
            
            # Update service metrics
            self._registry.update_service_metrics(service_name, {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used": memory_used,
                "num_threads": num_threads,
                "num_connections": num_connections
            })
            
            return usage
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
    
    def get_all_services_resource_usage(self) -> Dict[str, Optional[ServiceResourceUsage]]:
        """
        Get the current resource usage of all running services.
        
        Returns:
            Dict[str, Optional[ServiceResourceUsage]]: Dictionary mapping service names to resource usage information
        """
        results = {}
        
        for service_name in self._registry.get_running_services():
            results[service_name] = self.get_service_resource_usage(service_name)
        
        return results
    
    def get_system_resource_usage_history(self) -> List[ResourceUsage]:
        """
        Get the system resource usage history.
        
        Returns:
            List[ResourceUsage]: List of system resource usage measurements
        """
        return list(self._system_usage_history)
    
    def get_service_resource_usage_history(self, service_name: str) -> List[ServiceResourceUsage]:
        """
        Get the resource usage history of a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            List[ServiceResourceUsage]: List of service resource usage measurements
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is registered
        self._registry.get_service(service_name)
        
        # Get usage history
        if service_name not in self._service_usage_history:
            return []
        
        return list(self._service_usage_history[service_name])
    
    def set_resource_limits(self, service_name: str, limits: ResourceLimits) -> None:
        """
        Set resource limits for a service.
        
        Args:
            service_name: Name of the service
            limits: Resource limits
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is registered
        self._registry.get_service(service_name)
        
        # Set limits
        self._resource_limits[service_name] = limits
        logger.info(f"Resource limits set for service '{service_name}'")
    
    def get_resource_limits(self, service_name: str) -> Optional[ResourceLimits]:
        """
        Get the resource limits of a service.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Optional[ResourceLimits]: Resource limits, or None if not set
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is registered
        self._registry.get_service(service_name)
        
        # Get limits
        return self._resource_limits.get(service_name)
    
    def clear_resource_limits(self, service_name: str) -> None:
        """
        Clear the resource limits of a service.
        
        Args:
            service_name: Name of the service
        
        Raises:
            ValueError: If the service is not registered
        """
        # Check if the service is registered
        self._registry.get_service(service_name)
        
        # Clear limits
        if service_name in self._resource_limits:
            del self._resource_limits[service_name]
            logger.info(f"Resource limits cleared for service '{service_name}'")
    
    def check_resource_limits(self, service_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a service is within its resource limits.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Tuple[bool, Optional[str]]: (True if within limits, error message if not)
        
        Raises:
            ValueError: If the service is not registered
        """
        # Get resource limits
        limits = self.get_resource_limits(service_name)
        if limits is None:
            return True, None
        
        # Get resource usage
        usage = self.get_service_resource_usage(service_name)
        if usage is None:
            return True, None
        
        # Check CPU usage
        if limits.cpu_percent is not None and usage.cpu_percent > limits.cpu_percent:
            return False, f"CPU usage ({usage.cpu_percent:.1f}%) exceeds limit ({limits.cpu_percent:.1f}%)"
        
        # Check memory usage (percentage)
        if limits.memory_percent is not None and usage.memory_percent > limits.memory_percent:
            return False, f"Memory usage ({usage.memory_percent:.1f}%) exceeds limit ({limits.memory_percent:.1f}%)"
        
        # Check memory usage (bytes)
        if limits.memory_bytes is not None and usage.memory_used > limits.memory_bytes:
            return False, f"Memory usage ({usage.memory_used} bytes) exceeds limit ({limits.memory_bytes} bytes)"
        
        # Check thread count
        if limits.num_threads is not None and usage.num_threads > limits.num_threads:
            return False, f"Thread count ({usage.num_threads}) exceeds limit ({limits.num_threads})"
        
        # Check connection count
        if limits.num_connections is not None and usage.num_connections > limits.num_connections:
            return False, f"Connection count ({usage.num_connections}) exceeds limit ({limits.num_connections})"
        
        return True, None
    
    def check_all_services_resource_limits(self) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        Check if all services are within their resource limits.
        
        Returns:
            Dict[str, Tuple[bool, Optional[str]]]: Dictionary mapping service names to (within limits, error message)
        """
        results = {}
        
        for service_name in self._registry.get_running_services():
            if service_name in self._resource_limits:
                results[service_name] = self.check_resource_limits(service_name)
        
        return results
    
    def set_check_interval(self, interval: int) -> None:
        """
        Set the resource check interval.
        
        Args:
            interval: Interval in seconds
        """
        self._check_interval = interval
    
    def set_history_size(self, size: int) -> None:
        """
        Set the resource usage history size.
        
        Args:
            size: Number of measurements to keep
        """
        self._history_size = size
        
        # Resize system history
        self._system_usage_history = deque(self._system_usage_history, maxlen=size)
        
        # Resize service histories
        for service_name in self._service_usage_history:
            self._service_usage_history[service_name] = deque(
                self._service_usage_history[service_name], maxlen=size
            )
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                # Get system resource usage
                self.get_system_resource_usage()
                
                # Get service resource usage
                self.get_all_services_resource_usage()
                
                # Check resource limits
                limit_results = self.check_all_services_resource_limits()
                for service_name, (within_limits, error_message) in limit_results.items():
                    if not within_limits:
                        logger.warning(f"Service '{service_name}' exceeds resource limits: {error_message}")
            except Exception as e:
                logger.exception(f"Error in resource monitor loop: {e}")
            
            # Wait for the next check
            for _ in range(self._check_interval * 2):  # Check every 0.5 seconds if we should stop
                if not self._running:
                    break
                time.sleep(0.5)
    
    def get_resource_usage_statistics(self, service_name: Optional[str] = None,
                                     time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """
        Get resource usage statistics.
        
        Args:
            service_name: Name of the service, or None for system statistics
            time_range: Time range to consider, or None for all available data
        
        Returns:
            Dict[str, Any]: Dictionary of statistics
        
        Raises:
            ValueError: If the service is not registered
        """
        if service_name is not None:
            # Check if the service is registered
            self._registry.get_service(service_name)
            
            # Get service usage history
            if service_name not in self._service_usage_history:
                return {}
            
            history = list(self._service_usage_history[service_name])
        else:
            # Get system usage history
            history = list(self._system_usage_history)
        
        # Filter by time range
        if time_range is not None:
            now = datetime.now()
            history = [item for item in history if now - item.timestamp <= time_range]
        
        # If no data, return empty statistics
        if not history:
            return {}
        
        # Calculate statistics
        if service_name is not None:
            # Service statistics
            cpu_values = [item.cpu_percent for item in history]
            memory_percent_values = [item.memory_percent for item in history]
            memory_used_values = [item.memory_used for item in history]
            thread_values = [item.num_threads for item in history]
            connection_values = [item.num_connections for item in history]
            
            return {
                "cpu_percent": {
                    "min": min(cpu_values),
                    "max": max(cpu_values),
                    "avg": sum(cpu_values) / len(cpu_values)
                },
                "memory_percent": {
                    "min": min(memory_percent_values),
                    "max": max(memory_percent_values),
                    "avg": sum(memory_percent_values) / len(memory_percent_values)
                },
                "memory_used": {
                    "min": min(memory_used_values),
                    "max": max(memory_used_values),
                    "avg": sum(memory_used_values) / len(memory_used_values)
                },
                "num_threads": {
                    "min": min(thread_values),
                    "max": max(thread_values),
                    "avg": sum(thread_values) / len(thread_values)
                },
                "num_connections": {
                    "min": min(connection_values),
                    "max": max(connection_values),
                    "avg": sum(connection_values) / len(connection_values)
                }
            }
        else:
            # System statistics
            cpu_values = [item.cpu_percent for item in history]
            memory_percent_values = [item.memory_percent for item in history]
            memory_used_values = [item.memory_used for item in history]
            disk_percent_values = [item.disk_percent for item in history]
            disk_used_values = [item.disk_used for item in history]
            
            return {
                "cpu_percent": {
                    "min": min(cpu_values),
                    "max": max(cpu_values),
                    "avg": sum(cpu_values) / len(cpu_values)
                },
                "memory_percent": {
                    "min": min(memory_percent_values),
                    "max": max(memory_percent_values),
                    "avg": sum(memory_percent_values) / len(memory_percent_values)
                },
                "memory_used": {
                    "min": min(memory_used_values),
                    "max": max(memory_used_values),
                    "avg": sum(memory_used_values) / len(memory_used_values)
                },
                "disk_percent": {
                    "min": min(disk_percent_values),
                    "max": max(disk_percent_values),
                    "avg": sum(disk_percent_values) / len(disk_percent_values)
                },
                "disk_used": {
                    "min": min(disk_used_values),
                    "max": max(disk_used_values),
                    "avg": sum(disk_used_values) / len(disk_used_values)
                }
            }