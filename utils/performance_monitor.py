"""
Performance Monitor

This module provides utilities for monitoring and analyzing the performance
of various components in the Cryptobot system.
"""

import time
import logging
import functools
import threading
import asyncio
import statistics
from typing import Dict, List, Any, Callable, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
import json
import os
import psutil

# Configure logging
logger = logging.getLogger(__name__)

# Performance statistics
performance_stats = {
    "function_stats": {},
    "endpoint_stats": {},
    "database_stats": {},
    "exchange_stats": {},
    "system_stats": {
        "cpu_usage": [],
        "memory_usage": [],
        "disk_usage": [],
        "network_usage": []
    },
    "bottlenecks": [],
    "slow_functions": [],
    "slow_endpoints": [],
    "slow_queries": []
}

# Performance monitoring settings
performance_monitoring_enabled = False
performance_monitoring_interval = 60  # seconds
performance_monitoring_thread = None
performance_warning_threshold = 1.0  # 1 second
performance_critical_threshold = 5.0  # 5 seconds

def enable_performance_monitoring(interval: int = 60) -> None:
    """
    Enable performance monitoring.
    
    Args:
        interval: Monitoring interval in seconds
    """
    global performance_monitoring_enabled, performance_monitoring_interval, performance_monitoring_thread
    
    if performance_monitoring_thread and performance_monitoring_thread.is_alive():
        logger.warning("Performance monitoring is already enabled")
        return
    
    performance_monitoring_enabled = True
    performance_monitoring_interval = interval
    
    # Start performance monitoring thread
    performance_monitoring_thread = threading.Thread(
        target=_performance_monitoring_thread,
        daemon=True
    )
    performance_monitoring_thread.start()
    
    logger.info(f"Performance monitoring enabled with interval {interval}s")

def disable_performance_monitoring() -> None:
    """Disable performance monitoring."""
    global performance_monitoring_enabled
    
    performance_monitoring_enabled = False
    
    logger.info("Performance monitoring disabled")

def _performance_monitoring_thread() -> None:
    """Thread for monitoring system performance."""
    global performance_monitoring_enabled, performance_monitoring_interval, performance_stats
    
    while performance_monitoring_enabled:
        # Sleep for the monitoring interval
        time.sleep(performance_monitoring_interval)
        
        # Monitor system performance
        _monitor_system_performance()
        
        # Analyze performance statistics
        _analyze_performance_stats()

def _monitor_system_performance() -> None:
    """Monitor system performance metrics."""
    # Get process
    process = psutil.Process()
    
    # CPU usage
    cpu_percent = process.cpu_percent(interval=1)
    performance_stats["system_stats"]["cpu_usage"].append({
        "timestamp": datetime.now().isoformat(),
        "value": cpu_percent
    })
    
    # Memory usage
    memory_info = process.memory_info()
    performance_stats["system_stats"]["memory_usage"].append({
        "timestamp": datetime.now().isoformat(),
        "value": memory_info.rss
    })
    
    # Disk usage
    disk_io = psutil.disk_io_counters()
    if disk_io:
        performance_stats["system_stats"]["disk_usage"].append({
            "timestamp": datetime.now().isoformat(),
            "read_bytes": disk_io.read_bytes,
            "write_bytes": disk_io.write_bytes
        })
    
    # Network usage
    net_io = psutil.net_io_counters()
    if net_io:
        performance_stats["system_stats"]["network_usage"].append({
            "timestamp": datetime.now().isoformat(),
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv
        })
    
    # Limit the number of data points
    max_data_points = 100
    for key in ["cpu_usage", "memory_usage", "disk_usage", "network_usage"]:
        if len(performance_stats["system_stats"][key]) > max_data_points:
            performance_stats["system_stats"][key] = performance_stats["system_stats"][key][-max_data_points:]

def _analyze_performance_stats() -> None:
    """Analyze performance statistics to identify bottlenecks."""
    # Clear previous bottlenecks
    performance_stats["bottlenecks"] = []
    performance_stats["slow_functions"] = []
    performance_stats["slow_endpoints"] = []
    performance_stats["slow_queries"] = []
    
    # Analyze function performance
    for func_name, stats in performance_stats["function_stats"].items():
        if stats["count"] > 0:
            avg_time = stats["total_time"] / stats["count"]
            
            if avg_time > performance_critical_threshold:
                performance_stats["bottlenecks"].append({
                    "type": "function",
                    "name": func_name,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "severity": "critical"
                })
                performance_stats["slow_functions"].append({
                    "name": func_name,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "max_time": stats["max_time"]
                })
                logger.warning(f"Critical performance bottleneck: Function {func_name} takes {avg_time:.2f}s on average")
            elif avg_time > performance_warning_threshold:
                performance_stats["bottlenecks"].append({
                    "type": "function",
                    "name": func_name,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "severity": "warning"
                })
                performance_stats["slow_functions"].append({
                    "name": func_name,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "max_time": stats["max_time"]
                })
                logger.info(f"Performance warning: Function {func_name} takes {avg_time:.2f}s on average")
    
    # Analyze endpoint performance
    for endpoint, stats in performance_stats["endpoint_stats"].items():
        if stats["count"] > 0:
            avg_time = stats["total_time"] / stats["count"]
            
            if avg_time > performance_critical_threshold:
                performance_stats["bottlenecks"].append({
                    "type": "endpoint",
                    "name": endpoint,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "severity": "critical"
                })
                performance_stats["slow_endpoints"].append({
                    "name": endpoint,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "max_time": stats["max_time"]
                })
                logger.warning(f"Critical performance bottleneck: Endpoint {endpoint} takes {avg_time:.2f}s on average")
            elif avg_time > performance_warning_threshold:
                performance_stats["bottlenecks"].append({
                    "type": "endpoint",
                    "name": endpoint,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "severity": "warning"
                })
                performance_stats["slow_endpoints"].append({
                    "name": endpoint,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "max_time": stats["max_time"]
                })
                logger.info(f"Performance warning: Endpoint {endpoint} takes {avg_time:.2f}s on average")
    
    # Analyze database performance
    for query, stats in performance_stats["database_stats"].items():
        if stats["count"] > 0:
            avg_time = stats["total_time"] / stats["count"]
            
            if avg_time > performance_critical_threshold:
                performance_stats["bottlenecks"].append({
                    "type": "database",
                    "name": query,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "severity": "critical"
                })
                performance_stats["slow_queries"].append({
                    "query": query,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "max_time": stats["max_time"]
                })
                logger.warning(f"Critical performance bottleneck: Query {query} takes {avg_time:.2f}s on average")
            elif avg_time > performance_warning_threshold:
                performance_stats["bottlenecks"].append({
                    "type": "database",
                    "name": query,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "severity": "warning"
                })
                performance_stats["slow_queries"].append({
                    "query": query,
                    "avg_time": avg_time,
                    "count": stats["count"],
                    "max_time": stats["max_time"]
                })
                logger.info(f"Performance warning: Query {query} takes {avg_time:.2f}s on average")
    
    # Sort bottlenecks by average time (descending)
    performance_stats["bottlenecks"].sort(key=lambda x: x["avg_time"], reverse=True)
    performance_stats["slow_functions"].sort(key=lambda x: x["avg_time"], reverse=True)
    performance_stats["slow_endpoints"].sort(key=lambda x: x["avg_time"], reverse=True)
    performance_stats["slow_queries"].sort(key=lambda x: x["avg_time"], reverse=True)

def performance_decorator(func: Callable) -> Callable:
    """
    Decorator for tracking function performance.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get function name
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Initialize function stats if needed
        if func_name not in performance_stats["function_stats"]:
            performance_stats["function_stats"][func_name] = {
                "count": 0,
                "total_time": 0,
                "max_time": 0,
                "min_time": float('inf'),
                "times": []
            }
        
        # Start timer
        start_time = time.time()
        
        # Call the function
        result = func(*args, **kwargs)
        
        # End timer
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Update function stats
        stats = performance_stats["function_stats"][func_name]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["times"].append(execution_time)
        
        # Keep only the last 100 execution times
        if len(stats["times"]) > 100:
            stats["times"] = stats["times"][-100:]
        
        # Log slow functions
        if execution_time > performance_critical_threshold:
            logger.warning(f"Slow function: {func_name} took {execution_time:.2f}s")
        elif execution_time > performance_warning_threshold:
            logger.info(f"Slow function: {func_name} took {execution_time:.2f}s")
        
        return result
    
    return wrapper

def async_performance_decorator(func: Callable) -> Callable:
    """
    Decorator for tracking async function performance.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get function name
        func_name = f"{func.__module__}.{func.__name__}"
        
        # Initialize function stats if needed
        if func_name not in performance_stats["function_stats"]:
            performance_stats["function_stats"][func_name] = {
                "count": 0,
                "total_time": 0,
                "max_time": 0,
                "min_time": float('inf'),
                "times": []
            }
        
        # Start timer
        start_time = time.time()
        
        # Call the function
        result = await func(*args, **kwargs)
        
        # End timer
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Update function stats
        stats = performance_stats["function_stats"][func_name]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["times"].append(execution_time)
        
        # Keep only the last 100 execution times
        if len(stats["times"]) > 100:
            stats["times"] = stats["times"][-100:]
        
        # Log slow functions
        if execution_time > performance_critical_threshold:
            logger.warning(f"Slow function: {func_name} took {execution_time:.2f}s")
        elif execution_time > performance_warning_threshold:
            logger.info(f"Slow function: {func_name} took {execution_time:.2f}s")
        
        return result
    
    return wrapper

def endpoint_performance_decorator(endpoint: str) -> Callable:
    """
    Decorator for tracking endpoint performance.
    
    Args:
        endpoint: Endpoint name
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Initialize endpoint stats if needed
            if endpoint not in performance_stats["endpoint_stats"]:
                performance_stats["endpoint_stats"][endpoint] = {
                    "count": 0,
                    "total_time": 0,
                    "max_time": 0,
                    "min_time": float('inf'),
                    "times": []
                }
            
            # Start timer
            start_time = time.time()
            
            # Call the function
            result = await func(*args, **kwargs)
            
            # End timer
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Update endpoint stats
            stats = performance_stats["endpoint_stats"][endpoint]
            stats["count"] += 1
            stats["total_time"] += execution_time
            stats["max_time"] = max(stats["max_time"], execution_time)
            stats["min_time"] = min(stats["min_time"], execution_time)
            stats["times"].append(execution_time)
            
            # Keep only the last 100 execution times
            if len(stats["times"]) > 100:
                stats["times"] = stats["times"][-100:]
            
            # Log slow endpoints
            if execution_time > performance_critical_threshold:
                logger.warning(f"Slow endpoint: {endpoint} took {execution_time:.2f}s")
            elif execution_time > performance_warning_threshold:
                logger.info(f"Slow endpoint: {endpoint} took {execution_time:.2f}s")
            
            return result
        
        return wrapper
    
    return decorator

def track_database_query(query: str, execution_time: float) -> None:
    """
    Track database query performance.
    
    Args:
        query: Query string
        execution_time: Execution time in seconds
    """
    # Normalize query by removing specific values
    normalized_query = _normalize_query(query)
    
    # Initialize query stats if needed
    if normalized_query not in performance_stats["database_stats"]:
        performance_stats["database_stats"][normalized_query] = {
            "count": 0,
            "total_time": 0,
            "max_time": 0,
            "min_time": float('inf'),
            "times": []
        }
    
    # Update query stats
    stats = performance_stats["database_stats"][normalized_query]
    stats["count"] += 1
    stats["total_time"] += execution_time
    stats["max_time"] = max(stats["max_time"], execution_time)
    stats["min_time"] = min(stats["min_time"], execution_time)
    stats["times"].append(execution_time)
    
    # Keep only the last 100 execution times
    if len(stats["times"]) > 100:
        stats["times"] = stats["times"][-100:]
    
    # Log slow queries
    if execution_time > performance_critical_threshold:
        logger.warning(f"Slow query: {normalized_query} took {execution_time:.2f}s")
    elif execution_time > performance_warning_threshold:
        logger.info(f"Slow query: {normalized_query} took {execution_time:.2f}s")

def _normalize_query(query: str) -> str:
    """
    Normalize a SQL query by removing specific values.
    
    Args:
        query: SQL query
        
    Returns:
        Normalized query
    """
    import re
    
    # Replace numeric literals
    query = re.sub(r'\b\d+\b', '?', query)
    
    # Replace string literals
    query = re.sub(r"'[^']*'", "'?'", query)
    
    # Replace UUID literals
    query = re.sub(r"'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'", "'?'", query)
    
    return query

def track_exchange_request(exchange: str, endpoint: str, execution_time: float) -> None:
    """
    Track exchange API request performance.
    
    Args:
        exchange: Exchange name
        endpoint: API endpoint
        execution_time: Execution time in seconds
    """
    # Create key
    key = f"{exchange}:{endpoint}"
    
    # Initialize exchange stats if needed
    if key not in performance_stats["exchange_stats"]:
        performance_stats["exchange_stats"][key] = {
            "count": 0,
            "total_time": 0,
            "max_time": 0,
            "min_time": float('inf'),
            "times": []
        }
    
    # Update exchange stats
    stats = performance_stats["exchange_stats"][key]
    stats["count"] += 1
    stats["total_time"] += execution_time
    stats["max_time"] = max(stats["max_time"], execution_time)
    stats["min_time"] = min(stats["min_time"], execution_time)
    stats["times"].append(execution_time)
    
    # Keep only the last 100 execution times
    if len(stats["times"]) > 100:
        stats["times"] = stats["times"][-100:]
    
    # Log slow requests
    if execution_time > performance_critical_threshold:
        logger.warning(f"Slow exchange request: {key} took {execution_time:.2f}s")
    elif execution_time > performance_warning_threshold:
        logger.info(f"Slow exchange request: {key} took {execution_time:.2f}s")

def get_performance_stats() -> Dict[str, Any]:
    """
    Get performance statistics.
    
    Returns:
        Performance statistics
    """
    global performance_stats
    
    stats = performance_stats.copy()
    
    # Calculate percentiles for function stats
    for func_name, func_stats in stats["function_stats"].items():
        if func_stats["times"]:
            func_stats["percentiles"] = {
                "50": statistics.median(func_stats["times"]),
                "90": statistics.quantiles(func_stats["times"], n=10)[8],
                "95": statistics.quantiles(func_stats["times"], n=20)[18],
                "99": statistics.quantiles(func_stats["times"], n=100)[98] if len(func_stats["times"]) >= 100 else func_stats["max_time"]
            }
            func_stats["avg_time"] = func_stats["total_time"] / func_stats["count"]
        
        # Remove raw times to reduce size
        func_stats.pop("times", None)
    
    # Calculate percentiles for endpoint stats
    for endpoint, endpoint_stats in stats["endpoint_stats"].items():
        if endpoint_stats["times"]:
            endpoint_stats["percentiles"] = {
                "50": statistics.median(endpoint_stats["times"]),
                "90": statistics.quantiles(endpoint_stats["times"], n=10)[8],
                "95": statistics.quantiles(endpoint_stats["times"], n=20)[18],
                "99": statistics.quantiles(endpoint_stats["times"], n=100)[98] if len(endpoint_stats["times"]) >= 100 else endpoint_stats["max_time"]
            }
            endpoint_stats["avg_time"] = endpoint_stats["total_time"] / endpoint_stats["count"]
        
        # Remove raw times to reduce size
        endpoint_stats.pop("times", None)
    
    # Calculate percentiles for database stats
    for query, query_stats in stats["database_stats"].items():
        if query_stats["times"]:
            query_stats["percentiles"] = {
                "50": statistics.median(query_stats["times"]),
                "90": statistics.quantiles(query_stats["times"], n=10)[8],
                "95": statistics.quantiles(query_stats["times"], n=20)[18],
                "99": statistics.quantiles(query_stats["times"], n=100)[98] if len(query_stats["times"]) >= 100 else query_stats["max_time"]
            }
            query_stats["avg_time"] = query_stats["total_time"] / query_stats["count"]
        
        # Remove raw times to reduce size
        query_stats.pop("times", None)
    
    # Calculate percentiles for exchange stats
    for key, exchange_stats in stats["exchange_stats"].items():
        if exchange_stats["times"]:
            exchange_stats["percentiles"] = {
                "50": statistics.median(exchange_stats["times"]),
                "90": statistics.quantiles(exchange_stats["times"], n=10)[8],
                "95": statistics.quantiles(exchange_stats["times"], n=20)[18],
                "99": statistics.quantiles(exchange_stats["times"], n=100)[98] if len(exchange_stats["times"]) >= 100 else exchange_stats["max_time"]
            }
            exchange_stats["avg_time"] = exchange_stats["total_time"] / exchange_stats["count"]
        
        # Remove raw times to reduce size
        exchange_stats.pop("times", None)
    
    return stats

def reset_performance_stats() -> None:
    """Reset performance statistics."""
    global performance_stats
    
    performance_stats = {
        "function_stats": {},
        "endpoint_stats": {},
        "database_stats": {},
        "exchange_stats": {},
        "system_stats": {
            "cpu_usage": [],
            "memory_usage": [],
            "disk_usage": [],
            "network_usage": []
        },
        "bottlenecks": [],
        "slow_functions": [],
        "slow_endpoints": [],
        "slow_queries": []
    }

def set_performance_warning_threshold(threshold: float) -> None:
    """
    Set the performance warning threshold.
    
    Args:
        threshold: Threshold in seconds
    """
    global performance_warning_threshold
    
    performance_warning_threshold = threshold
    
    logger.info(f"Performance warning threshold set to {threshold}s")

def set_performance_critical_threshold(threshold: float) -> None:
    """
    Set the performance critical threshold.
    
    Args:
        threshold: Threshold in seconds
    """
    global performance_critical_threshold
    
    performance_critical_threshold = threshold
    
    logger.info(f"Performance critical threshold set to {threshold}s")

def save_performance_report(file_path: str) -> None:
    """
    Save a performance report to a file.
    
    Args:
        file_path: File path
    """
    # Get performance stats
    stats = get_performance_stats()
    
    # Create report directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save report
    with open(file_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"Performance report saved to {file_path}")

class PerformanceTracker:
    """
    Performance tracker for a specific code block.
    This class provides a context manager for tracking performance.
    """
    
    def __init__(self, name: str):
        """
        Initialize a performance tracker.
        
        Args:
            name: Tracker name
        """
        self.name = name
        self.start_time = 0
        self.end_time = 0
    
    def __enter__(self):
        """Enter the context manager."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        self.end_time = time.time()
        execution_time = self.end_time - self.start_time
        
        # Initialize function stats if needed
        if self.name not in performance_stats["function_stats"]:
            performance_stats["function_stats"][self.name] = {
                "count": 0,
                "total_time": 0,
                "max_time": 0,
                "min_time": float('inf'),
                "times": []
            }
        
        # Update function stats
        stats = performance_stats["function_stats"][self.name]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["times"].append(execution_time)
        
        # Keep only the last 100 execution times
        if len(stats["times"]) > 100:
            stats["times"] = stats["times"][-100:]
        
        # Log slow operations
        if execution_time > performance_critical_threshold:
            logger.warning(f"Slow operation: {self.name} took {execution_time:.2f}s")
        elif execution_time > performance_warning_threshold:
            logger.info(f"Slow operation: {self.name} took {execution_time:.2f}s")

class AsyncPerformanceTracker:
    """
    Async performance tracker for a specific code block.
    This class provides an async context manager for tracking performance.
    """
    
    def __init__(self, name: str):
        """
        Initialize an async performance tracker.
        
        Args:
            name: Tracker name
        """
        self.name = name
        self.start_time = 0
        self.end_time = 0
    
    async def __aenter__(self):
        """Enter the async context manager."""
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        self.end_time = time.time()
        execution_time = self.end_time - self.start_time
        
        # Initialize function stats if needed
        if self.name not in performance_stats["function_stats"]:
            performance_stats["function_stats"][self.name] = {
                "count": 0,
                "total_time": 0,
                "max_time": 0,
                "min_time": float('inf'),
                "times": []
            }
        
        # Update function stats
        stats = performance_stats["function_stats"][self.name]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["times"].append(execution_time)
        
        # Keep only the last 100 execution times
        if len(stats["times"]) > 100:
            stats["times"] = stats["times"][-100:]
        
        # Log slow operations
        if execution_time > performance_critical_threshold:
            logger.warning(f"Slow operation: {self.name} took {execution_time:.2f}s")
        elif execution_time > performance_warning_threshold:
            logger.info(f"Slow operation: {self.name} took {execution_time:.2f}s")