"""
Memory Optimizer

This module provides utilities for optimizing memory usage in the Cryptobot system.
It includes functions for memory profiling, leak detection, and optimization.
"""

import gc
import sys
import os
import time
import logging
import threading
import weakref
import functools
import tracemalloc
from typing import Dict, List, Any, Callable, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
import psutil
import objgraph

# Configure logging
logger = logging.getLogger(__name__)

# Memory statistics
memory_stats = {
    "peak_memory_usage": 0,
    "current_memory_usage": 0,
    "memory_growth_rate": 0,
    "gc_collections": [0, 0, 0],  # Counts for each generation
    "object_counts": {},
    "memory_leaks": [],
    "memory_snapshots": []
}

# Memory monitoring settings
memory_monitoring_enabled = False
memory_monitoring_interval = 60  # seconds
memory_monitoring_thread = None
memory_warning_threshold = 0.8  # 80% of available memory
memory_critical_threshold = 0.9  # 90% of available memory

# Tracemalloc settings
tracemalloc_enabled = False

def enable_memory_monitoring(interval: int = 60) -> None:
    """
    Enable memory monitoring.
    
    Args:
        interval: Monitoring interval in seconds
    """
    global memory_monitoring_enabled, memory_monitoring_interval, memory_monitoring_thread
    
    if memory_monitoring_thread and memory_monitoring_thread.is_alive():
        logger.warning("Memory monitoring is already enabled")
        return
    
    memory_monitoring_enabled = True
    memory_monitoring_interval = interval
    
    # Start memory monitoring thread
    memory_monitoring_thread = threading.Thread(
        target=_memory_monitoring_thread,
        daemon=True
    )
    memory_monitoring_thread.start()
    
    logger.info(f"Memory monitoring enabled with interval {interval}s")

def disable_memory_monitoring() -> None:
    """Disable memory monitoring."""
    global memory_monitoring_enabled
    
    memory_monitoring_enabled = False
    
    logger.info("Memory monitoring disabled")

def enable_tracemalloc(nframes: int = 25) -> None:
    """
    Enable tracemalloc for memory leak detection.
    
    Args:
        nframes: Number of frames to capture in stack traces
    """
    global tracemalloc_enabled
    
    if not tracemalloc_enabled:
        tracemalloc.start(nframes)
        tracemalloc_enabled = True
        
        # Take initial snapshot
        memory_stats["memory_snapshots"].append({
            "snapshot": tracemalloc.take_snapshot(),
            "timestamp": datetime.now(),
            "memory_usage": get_memory_usage()
        })
        
        logger.info(f"Tracemalloc enabled with {nframes} frames")

def disable_tracemalloc() -> None:
    """Disable tracemalloc."""
    global tracemalloc_enabled
    
    if tracemalloc_enabled:
        tracemalloc.stop()
        tracemalloc_enabled = False
        
        logger.info("Tracemalloc disabled")

def get_memory_usage() -> Dict[str, Any]:
    """
    Get current memory usage.
    
    Returns:
        Memory usage statistics
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # Get system memory info
    system_memory = psutil.virtual_memory()
    
    return {
        "rss": memory_info.rss,  # Resident Set Size
        "vms": memory_info.vms,  # Virtual Memory Size
        "rss_human": _format_bytes(memory_info.rss),
        "vms_human": _format_bytes(memory_info.vms),
        "percent": process.memory_percent(),
        "system_total": system_memory.total,
        "system_available": system_memory.available,
        "system_percent": system_memory.percent,
        "system_total_human": _format_bytes(system_memory.total),
        "system_available_human": _format_bytes(system_memory.available)
    }

def _format_bytes(bytes: int) -> str:
    """
    Format bytes as a human-readable string.
    
    Args:
        bytes: Number of bytes
        
    Returns:
        Human-readable string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"

def _memory_monitoring_thread() -> None:
    """Thread for monitoring memory usage."""
    global memory_monitoring_enabled, memory_monitoring_interval, memory_stats
    
    # Initialize peak memory usage
    memory_stats["peak_memory_usage"] = get_memory_usage()["rss"]
    
    # Initialize object counts
    memory_stats["object_counts"] = _get_object_counts()
    
    previous_memory_usage = memory_stats["peak_memory_usage"]
    previous_time = time.time()
    
    while memory_monitoring_enabled:
        # Sleep for the monitoring interval
        time.sleep(memory_monitoring_interval)
        
        # Get current memory usage
        memory_usage = get_memory_usage()
        current_memory = memory_usage["rss"]
        memory_stats["current_memory_usage"] = current_memory
        
        # Update peak memory usage
        if current_memory > memory_stats["peak_memory_usage"]:
            memory_stats["peak_memory_usage"] = current_memory
        
        # Calculate memory growth rate
        current_time = time.time()
        time_elapsed = current_time - previous_time
        memory_growth = current_memory - previous_memory_usage
        memory_stats["memory_growth_rate"] = memory_growth / time_elapsed if time_elapsed > 0 else 0
        
        # Update previous values
        previous_memory_usage = current_memory
        previous_time = current_time
        
        # Check memory thresholds
        system_percent = memory_usage["system_percent"] / 100.0  # Convert to 0-1 range
        
        if system_percent >= memory_critical_threshold:
            logger.critical(
                f"Memory usage critical: {system_percent:.1%} of system memory used. "
                f"Process using {memory_usage['rss_human']}"
            )
            
            # Force garbage collection
            gc.collect()
            
            # Take memory snapshot if tracemalloc is enabled
            if tracemalloc_enabled:
                take_memory_snapshot()
                
                # Find memory leaks
                detect_memory_leaks()
        elif system_percent >= memory_warning_threshold:
            logger.warning(
                f"Memory usage high: {system_percent:.1%} of system memory used. "
                f"Process using {memory_usage['rss_human']}"
            )
            
            # Suggest garbage collection
            if gc.get_count()[0] > 10000:
                logger.info("Suggesting garbage collection")
                gc.collect(0)  # Collect youngest generation
        
        # Update GC collection counts
        memory_stats["gc_collections"] = gc.get_count()
        
        # Update object counts periodically (every 10 intervals)
        if int(current_time) % (memory_monitoring_interval * 10) < memory_monitoring_interval:
            new_counts = _get_object_counts()
            
            # Check for significant increases
            for obj_type, count in new_counts.items():
                if obj_type in memory_stats["object_counts"]:
                    old_count = memory_stats["object_counts"][obj_type]
                    increase = count - old_count
                    
                    # Log significant increases (>100% and >1000 objects)
                    if increase > old_count and increase > 1000:
                        logger.warning(f"Significant increase in {obj_type} objects: {old_count} -> {count}")
            
            memory_stats["object_counts"] = new_counts

def _get_object_counts() -> Dict[str, int]:
    """
    Get counts of Python objects by type.
    
    Returns:
        Dictionary of object counts by type
    """
    result = {}
    
    # Get all objects
    objects = gc.get_objects()
    
    # Count objects by type
    for obj in objects:
        obj_type = type(obj).__name__
        
        if obj_type in result:
            result[obj_type] += 1
        else:
            result[obj_type] = 1
    
    return result

def take_memory_snapshot() -> None:
    """Take a memory snapshot for later comparison."""
    if not tracemalloc_enabled:
        logger.warning("Tracemalloc is not enabled, cannot take memory snapshot")
        return
    
    # Take snapshot
    snapshot = tracemalloc.take_snapshot()
    
    # Add to snapshots list
    memory_stats["memory_snapshots"].append({
        "snapshot": snapshot,
        "timestamp": datetime.now(),
        "memory_usage": get_memory_usage()
    })
    
    # Keep only the last 5 snapshots
    if len(memory_stats["memory_snapshots"]) > 5:
        memory_stats["memory_snapshots"].pop(0)
    
    logger.info("Memory snapshot taken")

def detect_memory_leaks() -> List[Dict[str, Any]]:
    """
    Detect memory leaks by comparing snapshots.
    
    Returns:
        List of potential memory leaks
    """
    if not tracemalloc_enabled:
        logger.warning("Tracemalloc is not enabled, cannot detect memory leaks")
        return []
    
    # Need at least 2 snapshots
    if len(memory_stats["memory_snapshots"]) < 2:
        logger.warning("Not enough memory snapshots to detect leaks")
        return []
    
    # Get the two most recent snapshots
    current = memory_stats["memory_snapshots"][-1]["snapshot"]
    previous = memory_stats["memory_snapshots"][-2]["snapshot"]
    
    # Compare snapshots
    top_stats = current.compare_to(previous, 'lineno')
    
    # Filter significant leaks (>100KB)
    leaks = []
    for stat in top_stats[:10]:  # Top 10 differences
        if stat.size_diff > 100 * 1024:  # >100KB
            leak = {
                "file": stat.traceback[0].filename,
                "line": stat.traceback[0].lineno,
                "size": stat.size,
                "size_diff": stat.size_diff,
                "count": stat.count,
                "count_diff": stat.count_diff,
                "traceback": [
                    (frame.filename, frame.lineno) for frame in stat.traceback
                ]
            }
            leaks.append(leak)
            
            logger.warning(
                f"Potential memory leak: {_format_bytes(stat.size_diff)} in "
                f"{stat.traceback[0].filename}:{stat.traceback[0].lineno}"
            )
    
    # Update memory leaks list
    memory_stats["memory_leaks"] = leaks
    
    return leaks

def get_memory_stats() -> Dict[str, Any]:
    """
    Get memory statistics.
    
    Returns:
        Memory statistics
    """
    global memory_stats
    
    stats = memory_stats.copy()
    
    # Add current memory usage
    stats["current_memory_usage_human"] = _format_bytes(stats["current_memory_usage"])
    stats["peak_memory_usage_human"] = _format_bytes(stats["peak_memory_usage"])
    
    # Add current memory usage details
    stats["memory_usage"] = get_memory_usage()
    
    # Add top object counts
    object_counts = stats["object_counts"]
    top_objects = sorted(object_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    stats["top_objects"] = dict(top_objects)
    
    # Add snapshot info without the actual snapshots
    stats["memory_snapshots"] = [
        {
            "timestamp": snapshot["timestamp"],
            "memory_usage": snapshot["memory_usage"]
        }
        for snapshot in stats["memory_snapshots"]
    ]
    
    return stats

def reset_memory_stats() -> None:
    """Reset memory statistics."""
    global memory_stats
    
    # Keep snapshots
    snapshots = memory_stats["memory_snapshots"]
    
    memory_stats = {
        "peak_memory_usage": get_memory_usage()["rss"],
        "current_memory_usage": get_memory_usage()["rss"],
        "memory_growth_rate": 0,
        "gc_collections": gc.get_count(),
        "object_counts": _get_object_counts(),
        "memory_leaks": [],
        "memory_snapshots": snapshots
    }

def optimize_memory() -> Dict[str, Any]:
    """
    Optimize memory usage.
    
    Returns:
        Optimization results
    """
    # Get memory usage before optimization
    before = get_memory_usage()
    
    # Force garbage collection
    gc.collect()
    
    # Get memory usage after optimization
    after = get_memory_usage()
    
    # Calculate memory saved
    memory_saved = before["rss"] - after["rss"]
    
    logger.info(f"Memory optimized: {_format_bytes(memory_saved)} freed")
    
    return {
        "before": before,
        "after": after,
        "memory_saved": memory_saved,
        "memory_saved_human": _format_bytes(memory_saved)
    }

def memory_usage_decorator(func: Callable) -> Callable:
    """
    Decorator for tracking memory usage of a function.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get memory usage before
        gc.collect()  # Force garbage collection to get accurate readings
        before = get_memory_usage()["rss"]
        
        # Call the function
        result = func(*args, **kwargs)
        
        # Get memory usage after
        gc.collect()  # Force garbage collection to get accurate readings
        after = get_memory_usage()["rss"]
        
        # Calculate memory change
        memory_change = after - before
        
        logger.debug(
            f"Memory usage for {func.__name__}: "
            f"{_format_bytes(before)} -> {_format_bytes(after)} "
            f"({_format_bytes(memory_change)})"
        )
        
        return result
    
    return wrapper

def async_memory_usage_decorator(func: Callable) -> Callable:
    """
    Decorator for tracking memory usage of an async function.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get memory usage before
        gc.collect()  # Force garbage collection to get accurate readings
        before = get_memory_usage()["rss"]
        
        # Call the function
        result = await func(*args, **kwargs)
        
        # Get memory usage after
        gc.collect()  # Force garbage collection to get accurate readings
        after = get_memory_usage()["rss"]
        
        # Calculate memory change
        memory_change = after - before
        
        logger.debug(
            f"Memory usage for {func.__name__}: "
            f"{_format_bytes(before)} -> {_format_bytes(after)} "
            f"({_format_bytes(memory_change)})"
        )
        
        return result
    
    return wrapper

def find_reference_cycles() -> List[List[Any]]:
    """
    Find reference cycles that may be preventing garbage collection.
    
    Returns:
        List of reference cycles
    """
    # Force garbage collection
    gc.collect()
    
    # Get objects with reference cycles
    cycles = []
    for obj in gc.get_objects():
        try:
            # Skip common types that are unlikely to be part of cycles
            if isinstance(obj, (str, int, float, bool, type, module)):
                continue
            
            # Find cycles
            cycle = _find_cycle(obj, [])
            if cycle:
                cycles.append(cycle)
        except Exception:
            # Skip objects that can't be processed
            pass
    
    return cycles

def _find_cycle(obj: Any, path: List[Any], max_depth: int = 5) -> Optional[List[Any]]:
    """
    Recursively find reference cycles.
    
    Args:
        obj: Object to check
        path: Current path
        max_depth: Maximum recursion depth
        
    Returns:
        Reference cycle if found, None otherwise
    """
    if len(path) > max_depth:
        return None
    
    if obj in path:
        return path + [obj]
    
    path = path + [obj]
    
    # Check references
    for ref in gc.get_referents(obj):
        try:
            # Skip common types that are unlikely to be part of cycles
            if isinstance(ref, (str, int, float, bool, type, module)):
                continue
            
            cycle = _find_cycle(ref, path, max_depth)
            if cycle:
                return cycle
        except Exception:
            # Skip objects that can't be processed
            pass
    
    return None

def get_largest_objects(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the largest objects in memory.
    
    Args:
        limit: Maximum number of objects to return
        
    Returns:
        List of largest objects
    """
    # Enable tracemalloc if not already enabled
    was_enabled = tracemalloc_enabled
    if not was_enabled:
        enable_tracemalloc()
    
    # Take snapshot
    snapshot = tracemalloc.take_snapshot()
    
    # Get top statistics
    top_stats = snapshot.statistics('lineno')
    
    # Format results
    result = []
    for stat in top_stats[:limit]:
        result.append({
            "file": stat.traceback[0].filename,
            "line": stat.traceback[0].lineno,
            "size": stat.size,
            "size_human": _format_bytes(stat.size),
            "count": stat.count,
            "traceback": [
                (frame.filename, frame.lineno) for frame in stat.traceback
            ]
        })
    
    # Disable tracemalloc if it wasn't enabled before
    if not was_enabled:
        disable_tracemalloc()
    
    return result

def set_memory_warning_threshold(threshold: float) -> None:
    """
    Set the memory warning threshold.
    
    Args:
        threshold: Threshold as a fraction of system memory (0.0-1.0)
    """
    global memory_warning_threshold
    
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    memory_warning_threshold = threshold
    
    logger.info(f"Memory warning threshold set to {threshold:.1%}")

def set_memory_critical_threshold(threshold: float) -> None:
    """
    Set the memory critical threshold.
    
    Args:
        threshold: Threshold as a fraction of system memory (0.0-1.0)
    """
    global memory_critical_threshold
    
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    memory_critical_threshold = threshold
    
    logger.info(f"Memory critical threshold set to {threshold:.1%}")

class MemoryTracker:
    """
    Memory tracker for a specific code block.
    This class provides a context manager for tracking memory usage.
    """
    
    def __init__(self, name: str):
        """
        Initialize a memory tracker.
        
        Args:
            name: Tracker name
        """
        self.name = name
        self.before = 0
        self.after = 0
    
    def __enter__(self):
        """Enter the context manager."""
        # Force garbage collection to get accurate readings
        gc.collect()
        
        # Get memory usage before
        self.before = get_memory_usage()["rss"]
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        # Force garbage collection to get accurate readings
        gc.collect()
        
        # Get memory usage after
        self.after = get_memory_usage()["rss"]
        
        # Calculate memory change
        memory_change = self.after - self.before
        
        logger.debug(
            f"Memory usage for {self.name}: "
            f"{_format_bytes(self.before)} -> {_format_bytes(self.after)} "
            f"({_format_bytes(memory_change)})"
        )

class AsyncMemoryTracker:
    """
    Async memory tracker for a specific code block.
    This class provides an async context manager for tracking memory usage.
    """
    
    def __init__(self, name: str):
        """
        Initialize an async memory tracker.
        
        Args:
            name: Tracker name
        """
        self.name = name
        self.before = 0
        self.after = 0
    
    async def __aenter__(self):
        """Enter the async context manager."""
        # Force garbage collection to get accurate readings
        gc.collect()
        
        # Get memory usage before
        self.before = get_memory_usage()["rss"]
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        # Force garbage collection to get accurate readings
        gc.collect()
        
        # Get memory usage after
        self.after = get_memory_usage()["rss"]
        
        # Calculate memory change
        memory_change = self.after - self.before
        
        logger.debug(
            f"Memory usage for {self.name}: "
            f"{_format_bytes(self.before)} -> {_format_bytes(self.after)} "
            f"({_format_bytes(memory_change)})"
        )