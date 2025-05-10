"""
Rate Limiter

This module provides rate limiting functionality for API requests.
It helps prevent rate limit errors from external services by throttling requests.
"""

import time
import asyncio
import logging
import functools
from typing import Dict, Any, Callable, Optional, Union, Tuple, List, Set
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class RateLimitRule:
    """Rate limit rule configuration"""
    requests_per_second: float
    burst_size: int = 1
    tokens: float = field(default=0.0, init=False)
    last_refill_time: float = field(default_factory=time.time, init=False)
    lock: threading.Lock = field(default_factory=threading.Lock, init=False)

@dataclass
class AsyncRateLimitRule:
    """Async rate limit rule configuration"""
    requests_per_second: float
    burst_size: int = 1
    tokens: float = field(default=0.0, init=False)
    last_refill_time: float = field(default_factory=time.time, init=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

# Rate limit rules by service
rate_limit_rules: Dict[str, RateLimitRule] = {}
async_rate_limit_rules: Dict[str, AsyncRateLimitRule] = {}

# Rate limit statistics
rate_limit_stats = {
    "total_requests": 0,
    "throttled_requests": 0,
    "service_stats": {}
}

def register_rate_limit(service: str, requests_per_second: float, burst_size: int = 1) -> None:
    """
    Register a rate limit rule for a service.
    
    Args:
        service: Service name
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size
    """
    rate_limit_rules[service] = RateLimitRule(
        requests_per_second=requests_per_second,
        burst_size=burst_size,
        tokens=burst_size  # Start with full tokens
    )
    
    # Initialize service stats
    if service not in rate_limit_stats["service_stats"]:
        rate_limit_stats["service_stats"][service] = {
            "total_requests": 0,
            "throttled_requests": 0,
            "average_wait_time": 0,
            "total_wait_time": 0,
            "max_wait_time": 0
        }
    
    logger.info(f"Registered rate limit for {service}: {requests_per_second} req/s, burst size {burst_size}")

def register_async_rate_limit(service: str, requests_per_second: float, burst_size: int = 1) -> None:
    """
    Register an async rate limit rule for a service.
    
    Args:
        service: Service name
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size
    """
    async_rate_limit_rules[service] = AsyncRateLimitRule(
        requests_per_second=requests_per_second,
        burst_size=burst_size,
        tokens=burst_size  # Start with full tokens
    )
    
    # Initialize service stats
    if service not in rate_limit_stats["service_stats"]:
        rate_limit_stats["service_stats"][service] = {
            "total_requests": 0,
            "throttled_requests": 0,
            "average_wait_time": 0,
            "total_wait_time": 0,
            "max_wait_time": 0
        }
    
    logger.info(f"Registered async rate limit for {service}: {requests_per_second} req/s, burst size {burst_size}")

def acquire_token(service: str, wait: bool = True) -> Tuple[bool, float]:
    """
    Acquire a token for a service.
    
    Args:
        service: Service name
        wait: Whether to wait for a token if none are available
        
    Returns:
        Tuple of (success, wait_time)
    """
    global rate_limit_stats
    
    # Update service stats
    if service in rate_limit_stats["service_stats"]:
        rate_limit_stats["service_stats"][service]["total_requests"] += 1
    
    rate_limit_stats["total_requests"] += 1
    
    # Check if service has a rate limit rule
    if service not in rate_limit_rules:
        # No rate limit rule, allow request
        return True, 0.0
    
    rule = rate_limit_rules[service]
    
    with rule.lock:
        # Refill tokens based on time elapsed
        now = time.time()
        time_elapsed = now - rule.last_refill_time
        new_tokens = time_elapsed * rule.requests_per_second
        rule.tokens = min(rule.burst_size, rule.tokens + new_tokens)
        rule.last_refill_time = now
        
        if rule.tokens >= 1.0:
            # Token available, consume it
            rule.tokens -= 1.0
            return True, 0.0
        elif not wait:
            # No token available and not waiting
            if service in rate_limit_stats["service_stats"]:
                rate_limit_stats["service_stats"][service]["throttled_requests"] += 1
            
            rate_limit_stats["throttled_requests"] += 1
            return False, 0.0
        else:
            # Calculate wait time for next token
            wait_time = (1.0 - rule.tokens) / rule.requests_per_second
            
            # Update service stats
            if service in rate_limit_stats["service_stats"]:
                service_stats = rate_limit_stats["service_stats"][service]
                service_stats["throttled_requests"] += 1
                service_stats["total_wait_time"] += wait_time
                service_stats["max_wait_time"] = max(service_stats["max_wait_time"], wait_time)
                service_stats["average_wait_time"] = (
                    service_stats["total_wait_time"] / service_stats["throttled_requests"]
                )
            
            rate_limit_stats["throttled_requests"] += 1
            
            # Wait for token
            time.sleep(wait_time)
            
            # Consume token
            rule.tokens = 0.0
            rule.last_refill_time = time.time()
            
            return True, wait_time

async def acquire_async_token(service: str, wait: bool = True) -> Tuple[bool, float]:
    """
    Acquire a token for a service asynchronously.
    
    Args:
        service: Service name
        wait: Whether to wait for a token if none are available
        
    Returns:
        Tuple of (success, wait_time)
    """
    global rate_limit_stats
    
    # Update service stats
    if service in rate_limit_stats["service_stats"]:
        rate_limit_stats["service_stats"][service]["total_requests"] += 1
    
    rate_limit_stats["total_requests"] += 1
    
    # Check if service has a rate limit rule
    if service not in async_rate_limit_rules:
        # No rate limit rule, allow request
        return True, 0.0
    
    rule = async_rate_limit_rules[service]
    
    async with rule.lock:
        # Refill tokens based on time elapsed
        now = time.time()
        time_elapsed = now - rule.last_refill_time
        new_tokens = time_elapsed * rule.requests_per_second
        rule.tokens = min(rule.burst_size, rule.tokens + new_tokens)
        rule.last_refill_time = now
        
        if rule.tokens >= 1.0:
            # Token available, consume it
            rule.tokens -= 1.0
            return True, 0.0
        elif not wait:
            # No token available and not waiting
            if service in rate_limit_stats["service_stats"]:
                rate_limit_stats["service_stats"][service]["throttled_requests"] += 1
            
            rate_limit_stats["throttled_requests"] += 1
            return False, 0.0
        else:
            # Calculate wait time for next token
            wait_time = (1.0 - rule.tokens) / rule.requests_per_second
            
            # Update service stats
            if service in rate_limit_stats["service_stats"]:
                service_stats = rate_limit_stats["service_stats"][service]
                service_stats["throttled_requests"] += 1
                service_stats["total_wait_time"] += wait_time
                service_stats["max_wait_time"] = max(service_stats["max_wait_time"], wait_time)
                service_stats["average_wait_time"] = (
                    service_stats["total_wait_time"] / service_stats["throttled_requests"]
                )
            
            rate_limit_stats["throttled_requests"] += 1
            
            # Wait for token
            await asyncio.sleep(wait_time)
            
            # Consume token
            rule.tokens = 0.0
            rule.last_refill_time = time.time()
            
            return True, wait_time

def rate_limit(service: str, wait: bool = True) -> Callable:
    """
    Decorator for rate limiting function calls.
    
    Args:
        service: Service name
        wait: Whether to wait for a token if none are available
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            success, wait_time = acquire_token(service, wait)
            
            if not success:
                raise RateLimitExceeded(f"Rate limit exceeded for {service}")
            
            if wait_time > 0:
                logger.debug(f"Rate limited {service} for {wait_time:.2f}s")
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def async_rate_limit(service: str, wait: bool = True) -> Callable:
    """
    Decorator for rate limiting async function calls.
    
    Args:
        service: Service name
        wait: Whether to wait for a token if none are available
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            success, wait_time = await acquire_async_token(service, wait)
            
            if not success:
                raise RateLimitExceeded(f"Rate limit exceeded for {service}")
            
            if wait_time > 0:
                logger.debug(f"Rate limited {service} for {wait_time:.2f}s")
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator

class RateLimitExceeded(Exception):
    """Exception raised when a rate limit is exceeded."""
    pass

def get_rate_limit_stats() -> Dict[str, Any]:
    """
    Get rate limit statistics.
    
    Returns:
        Rate limit statistics
    """
    global rate_limit_stats
    
    stats = rate_limit_stats.copy()
    
    # Calculate throttle rate
    total_requests = stats["total_requests"]
    throttled_requests = stats["throttled_requests"]
    stats["throttle_rate"] = throttled_requests / total_requests if total_requests > 0 else 0
    
    # Add current rate limit rules
    stats["rate_limit_rules"] = {}
    for service, rule in rate_limit_rules.items():
        stats["rate_limit_rules"][service] = {
            "requests_per_second": rule.requests_per_second,
            "burst_size": rule.burst_size,
            "current_tokens": rule.tokens
        }
    
    for service, rule in async_rate_limit_rules.items():
        if service not in stats["rate_limit_rules"]:
            stats["rate_limit_rules"][service] = {
                "requests_per_second": rule.requests_per_second,
                "burst_size": rule.burst_size,
                "current_tokens": rule.tokens
            }
    
    return stats

def reset_rate_limit_stats() -> None:
    """Reset rate limit statistics."""
    global rate_limit_stats
    
    # Keep track of services
    services = list(rate_limit_stats["service_stats"].keys())
    
    # Reset stats
    rate_limit_stats = {
        "total_requests": 0,
        "throttled_requests": 0,
        "service_stats": {}
    }
    
    # Re-initialize service stats
    for service in services:
        rate_limit_stats["service_stats"][service] = {
            "total_requests": 0,
            "throttled_requests": 0,
            "average_wait_time": 0,
            "total_wait_time": 0,
            "max_wait_time": 0
        }

def update_rate_limit(service: str, requests_per_second: float, burst_size: int = 1) -> None:
    """
    Update a rate limit rule for a service.
    
    Args:
        service: Service name
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size
    """
    if service in rate_limit_rules:
        rule = rate_limit_rules[service]
        
        with rule.lock:
            # Refill tokens based on time elapsed
            now = time.time()
            time_elapsed = now - rule.last_refill_time
            new_tokens = time_elapsed * rule.requests_per_second
            current_tokens = min(rule.burst_size, rule.tokens + new_tokens)
            
            # Update rule
            rule.requests_per_second = requests_per_second
            rule.burst_size = burst_size
            rule.tokens = min(current_tokens, burst_size)
            rule.last_refill_time = now
        
        logger.info(f"Updated rate limit for {service}: {requests_per_second} req/s, burst size {burst_size}")
    else:
        # Register new rule
        register_rate_limit(service, requests_per_second, burst_size)

async def update_async_rate_limit(service: str, requests_per_second: float, burst_size: int = 1) -> None:
    """
    Update an async rate limit rule for a service.
    
    Args:
        service: Service name
        requests_per_second: Maximum requests per second
        burst_size: Maximum burst size
    """
    if service in async_rate_limit_rules:
        rule = async_rate_limit_rules[service]
        
        async with rule.lock:
            # Refill tokens based on time elapsed
            now = time.time()
            time_elapsed = now - rule.last_refill_time
            new_tokens = time_elapsed * rule.requests_per_second
            current_tokens = min(rule.burst_size, rule.tokens + new_tokens)
            
            # Update rule
            rule.requests_per_second = requests_per_second
            rule.burst_size = burst_size
            rule.tokens = min(current_tokens, burst_size)
            rule.last_refill_time = now
        
        logger.info(f"Updated async rate limit for {service}: {requests_per_second} req/s, burst size {burst_size}")
    else:
        # Register new rule
        register_async_rate_limit(service, requests_per_second, burst_size)

class RateLimiter:
    """
    Rate limiter for a specific service.
    This class provides a context manager for rate limiting.
    """
    
    def __init__(self, service: str, wait: bool = True):
        """
        Initialize a rate limiter.
        
        Args:
            service: Service name
            wait: Whether to wait for a token if none are available
        """
        self.service = service
        self.wait = wait
        self.wait_time = 0.0
    
    def __enter__(self):
        """Enter the context manager."""
        success, self.wait_time = acquire_token(self.service, self.wait)
        
        if not success:
            raise RateLimitExceeded(f"Rate limit exceeded for {self.service}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        pass

class AsyncRateLimiter:
    """
    Async rate limiter for a specific service.
    This class provides an async context manager for rate limiting.
    """
    
    def __init__(self, service: str, wait: bool = True):
        """
        Initialize an async rate limiter.
        
        Args:
            service: Service name
            wait: Whether to wait for a token if none are available
        """
        self.service = service
        self.wait = wait
        self.wait_time = 0.0
    
    async def __aenter__(self):
        """Enter the async context manager."""
        success, self.wait_time = await acquire_async_token(self.service, self.wait)
        
        if not success:
            raise RateLimitExceeded(f"Rate limit exceeded for {self.service}")
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        pass

def adaptive_rate_limit(service: str, initial_rate: float, burst_size: int = 1) -> None:
    """
    Register an adaptive rate limit for a service.
    The rate limit will be adjusted based on the service's response.
    
    Args:
        service: Service name
        initial_rate: Initial requests per second
        burst_size: Maximum burst size
    """
    register_rate_limit(service, initial_rate, burst_size)
    
    # Start adaptive rate limit thread
    thread = threading.Thread(
        target=_adaptive_rate_limit_thread,
        args=(service, initial_rate, burst_size),
        daemon=True
    )
    thread.start()

def _adaptive_rate_limit_thread(service: str, initial_rate: float, burst_size: int) -> None:
    """
    Thread for adaptive rate limiting.
    
    Args:
        service: Service name
        initial_rate: Initial requests per second
        burst_size: Maximum burst size
    """
    current_rate = initial_rate
    min_rate = initial_rate * 0.1  # Minimum rate is 10% of initial rate
    max_rate = initial_rate * 2.0  # Maximum rate is 200% of initial rate
    
    while True:
        # Sleep for a while
        time.sleep(60)  # Check every minute
        
        # Get service stats
        if service not in rate_limit_stats["service_stats"]:
            continue
        
        service_stats = rate_limit_stats["service_stats"][service]
        
        # Calculate throttle rate
        total_requests = service_stats["total_requests"]
        throttled_requests = service_stats["throttled_requests"]
        throttle_rate = throttled_requests / total_requests if total_requests > 0 else 0
        
        # Adjust rate based on throttle rate
        if throttle_rate > 0.1:
            # Too many throttled requests, decrease rate
            new_rate = max(min_rate, current_rate * 0.9)
        elif throttle_rate < 0.01:
            # Few throttled requests, increase rate
            new_rate = min(max_rate, current_rate * 1.1)
        else:
            # Throttle rate is acceptable, keep current rate
            new_rate = current_rate
        
        # Update rate if changed
        if new_rate != current_rate:
            update_rate_limit(service, new_rate, burst_size)
            current_rate = new_rate
            logger.info(f"Adjusted rate limit for {service} to {new_rate:.2f} req/s")