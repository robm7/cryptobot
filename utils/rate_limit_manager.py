"""
Rate limit management for cryptocurrency exchange API calls.
This module provides tools to track and manage API rate limits to avoid
hitting exchange-imposed limits and implement backoff strategies.
"""

import time
import logging
import asyncio
from typing import Dict, List, Tuple, Optional, Callable, Any
from collections import deque
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

class RateLimitRule:
    """Represents a single rate limit rule (e.g., 1200 requests per minute)"""
    
    def __init__(self, max_requests: int, time_window_seconds: int, weight_multiplier: float = 1.0):
        """
        Initialize a rate limit rule.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window_seconds: Time window in seconds
            weight_multiplier: Weight multiplier for this rule (some endpoints count more)
        """
        self.max_requests = max_requests
        self.time_window_seconds = time_window_seconds
        self.weight_multiplier = weight_multiplier
        self.requests = deque(maxlen=max_requests)
    
    def record_request(self, weight: float = 1.0):
        """Record a request with the given weight"""
        self.requests.append((time.time(), weight * self.weight_multiplier))
    
    def get_usage(self) -> Tuple[int, float]:
        """
        Get current usage statistics.
        
        Returns:
            Tuple of (request_count, usage_percentage)
        """
        now = time.time()
        window_start = now - self.time_window_seconds
        
        # Count requests and weights in the current window
        valid_requests = [(ts, weight) for ts, weight in self.requests if ts > window_start]
        request_count = len(valid_requests)
        total_weight = sum(weight for _, weight in valid_requests)
        
        # Calculate usage percentage based on weight
        usage_percentage = (total_weight / self.max_requests) * 100
        
        return request_count, usage_percentage
    
    def should_throttle(self) -> Tuple[bool, float]:
        """
        Check if requests should be throttled based on this rule.
        
        Returns:
            Tuple of (should_throttle, wait_time_seconds)
        """
        now = time.time()
        window_start = now - self.time_window_seconds
        
        # Get valid requests in the current window
        valid_requests = [(ts, weight) for ts, weight in self.requests if ts > window_start]
        
        if not valid_requests:
            return False, 0
            
        total_weight = sum(weight for _, weight in valid_requests)
        
        # If we're over 80% of the limit, start throttling
        if total_weight >= 0.8 * self.max_requests:
            # Calculate time until oldest request expires from window
            oldest_timestamp = min(ts for ts, _ in valid_requests)
            wait_time = oldest_timestamp + self.time_window_seconds - now
            
            # Ensure wait time is reasonable
            wait_time = max(0.1, min(wait_time, self.time_window_seconds / 2))
            return True, wait_time
            
        return False, 0

class RateLimitManager:
    """
    Manages rate limits for multiple exchanges and endpoints.
    Implements adaptive throttling and backoff strategies.
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure only one instance of RateLimitManager exists"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RateLimitManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the rate limit manager"""
        if self._initialized:
            return
            
        self._initialized = True
        self.exchange_limits = {}
        self.endpoint_limits = {}
        self.error_counts = {}
        self.backoff_multipliers = {}
        
        # Default rate limits for common exchanges
        self._configure_default_limits()
        
        logger.info("RateLimitManager initialized")
    
    def _configure_default_limits(self):
        """Configure default rate limits for common exchanges"""
        # Binance limits
        self.exchange_limits['binance'] = [
            RateLimitRule(1200, 60),    # 1200 requests per minute
            RateLimitRule(48000, 3600)  # 48000 requests per hour
        ]
        
        # Binance endpoint-specific limits
        self.endpoint_limits['binance'] = {
            'order': RateLimitRule(50, 10, 2.0),  # Order endpoints have higher weight
            'klines': RateLimitRule(300, 60),     # OHLCV data
            'ticker': RateLimitRule(600, 60)      # Ticker data
        }
        
        # Kraken limits
        self.exchange_limits['kraken'] = [
            RateLimitRule(60, 60),     # 60 requests per minute
            RateLimitRule(1000, 3600)  # 1000 requests per hour
        ]
        
        # Kraken endpoint-specific limits
        self.endpoint_limits['kraken'] = {
            'order': RateLimitRule(15, 60, 2.0),  # Order endpoints have higher weight
            'trades': RateLimitRule(30, 60)       # Trade history
        }
        
        # Coinbase Pro limits
        self.exchange_limits['coinbasepro'] = [
            RateLimitRule(30, 60),     # 30 requests per minute
            RateLimitRule(500, 3600)   # 500 requests per hour
        ]
    
    def configure_exchange(self, exchange_id: str, limits: List[Dict]):
        """
        Configure rate limits for a specific exchange.
        
        Args:
            exchange_id: Exchange identifier (e.g., 'binance')
            limits: List of limit configurations
                [{'max_requests': 1200, 'time_window_seconds': 60}, ...]
        """
        self.exchange_limits[exchange_id] = [
            RateLimitRule(limit['max_requests'], limit['time_window_seconds'])
            for limit in limits
        ]
        logger.info(f"Configured rate limits for {exchange_id}: {limits}")
    
    def configure_endpoint(self, exchange_id: str, endpoint: str, 
                         max_requests: int, time_window_seconds: int, 
                         weight_multiplier: float = 1.0):
        """
        Configure rate limits for a specific endpoint.
        
        Args:
            exchange_id: Exchange identifier (e.g., 'binance')
            endpoint: Endpoint identifier (e.g., 'order', 'ticker')
            max_requests: Maximum requests allowed in the time window
            time_window_seconds: Time window in seconds
            weight_multiplier: Weight multiplier for this endpoint
        """
        if exchange_id not in self.endpoint_limits:
            self.endpoint_limits[exchange_id] = {}
            
        self.endpoint_limits[exchange_id][endpoint] = RateLimitRule(
            max_requests, time_window_seconds, weight_multiplier
        )
        logger.info(f"Configured endpoint limit for {exchange_id}/{endpoint}: "
                   f"{max_requests} requests per {time_window_seconds}s "
                   f"(weight: {weight_multiplier})")
    
    def record_request(self, exchange_id: str, endpoint: str = None, weight: float = 1.0):
        """
        Record an API request for rate limiting purposes.
        
        Args:
            exchange_id: Exchange identifier
            endpoint: Optional endpoint identifier
            weight: Request weight (some endpoints count more toward limits)
        """
        # Record for exchange-wide limits
        if exchange_id in self.exchange_limits:
            for rule in self.exchange_limits[exchange_id]:
                rule.record_request(weight)
        
        # Record for endpoint-specific limits
        if endpoint and exchange_id in self.endpoint_limits:
            if endpoint in self.endpoint_limits[exchange_id]:
                self.endpoint_limits[exchange_id][endpoint].record_request(weight)
    
    def record_error(self, exchange_id: str, error_type: str = 'rate_limit'):
        """
        Record an API error for backoff strategy.
        
        Args:
            exchange_id: Exchange identifier
            error_type: Type of error (e.g., 'rate_limit', 'server_error')
        """
        now = time.time()
        
        if exchange_id not in self.error_counts:
            self.error_counts[exchange_id] = deque(maxlen=100)
            
        self.error_counts[exchange_id].append((now, error_type))
        
        # Increase backoff multiplier for this exchange
        if exchange_id not in self.backoff_multipliers:
            self.backoff_multipliers[exchange_id] = 1.0
            
        # Exponential backoff, capped at 10x
        self.backoff_multipliers[exchange_id] = min(
            self.backoff_multipliers[exchange_id] * 1.5,
            10.0
        )
        
        logger.warning(f"Recorded {error_type} error for {exchange_id}, "
                      f"backoff multiplier now {self.backoff_multipliers[exchange_id]}")
    
    def reset_backoff(self, exchange_id: str):
        """
        Reset backoff multiplier after successful requests.
        
        Args:
            exchange_id: Exchange identifier
        """
        if exchange_id in self.backoff_multipliers:
            # Gradually reduce backoff multiplier
            self.backoff_multipliers[exchange_id] = max(
                1.0,
                self.backoff_multipliers[exchange_id] * 0.8
            )
    
    def should_throttle(self, exchange_id: str, endpoint: str = None) -> Tuple[bool, float]:
        """
        Check if requests should be throttled based on current usage.
        
        Args:
            exchange_id: Exchange identifier
            endpoint: Optional endpoint identifier
            
        Returns:
            Tuple of (should_throttle, wait_time_seconds)
        """
        max_wait_time = 0
        should_throttle = False
        
        # Check exchange-wide limits
        if exchange_id in self.exchange_limits:
            for rule in self.exchange_limits[exchange_id]:
                throttle, wait_time = rule.should_throttle()
                if throttle:
                    should_throttle = True
                    max_wait_time = max(max_wait_time, wait_time)
        
        # Check endpoint-specific limits
        if endpoint and exchange_id in self.endpoint_limits:
            if endpoint in self.endpoint_limits[exchange_id]:
                throttle, wait_time = self.endpoint_limits[exchange_id][endpoint].should_throttle()
                if throttle:
                    should_throttle = True
                    max_wait_time = max(max_wait_time, wait_time)
        
        # Apply backoff multiplier if there have been errors
        if exchange_id in self.backoff_multipliers and self.backoff_multipliers[exchange_id] > 1.0:
            max_wait_time *= self.backoff_multipliers[exchange_id]
        
        return should_throttle, max_wait_time
    
    def get_usage_stats(self, exchange_id: str) -> Dict:
        """
        Get current usage statistics for an exchange.
        
        Args:
            exchange_id: Exchange identifier
            
        Returns:
            Dict with usage statistics
        """
        stats = {
            'exchange_id': exchange_id,
            'limits': [],
            'endpoints': {},
            'errors': {
                'count': 0,
                'rate_limit_errors': 0,
                'recent_errors': []
            },
            'backoff_multiplier': self.backoff_multipliers.get(exchange_id, 1.0)
        }
        
        # Exchange-wide limits
        if exchange_id in self.exchange_limits:
            for i, rule in enumerate(self.exchange_limits[exchange_id]):
                count, percentage = rule.get_usage()
                stats['limits'].append({
                    'rule_id': i,
                    'max_requests': rule.max_requests,
                    'time_window_seconds': rule.time_window_seconds,
                    'current_count': count,
                    'usage_percentage': percentage
                })
        
        # Endpoint-specific limits
        if exchange_id in self.endpoint_limits:
            for endpoint, rule in self.endpoint_limits[exchange_id].items():
                count, percentage = rule.get_usage()
                stats['endpoints'][endpoint] = {
                    'max_requests': rule.max_requests,
                    'time_window_seconds': rule.time_window_seconds,
                    'weight_multiplier': rule.weight_multiplier,
                    'current_count': count,
                    'usage_percentage': percentage
                }
        
        # Error statistics
        if exchange_id in self.error_counts:
            now = time.time()
            minute_ago = now - 60
            
            # Count recent errors
            recent_errors = [
                (ts, error_type) for ts, error_type in self.error_counts[exchange_id]
                if ts > minute_ago
            ]
            
            stats['errors']['count'] = len(self.error_counts[exchange_id])
            stats['errors']['rate_limit_errors'] = sum(
                1 for _, error_type in self.error_counts[exchange_id]
                if error_type == 'rate_limit'
            )
            stats['errors']['recent_errors'] = len(recent_errors)
            
        return stats

async def apply_rate_limiting(exchange_id: str, endpoint: str = None, weight: float = 1.0):
    """
    Apply rate limiting before making an API call.
    This function should be called before making any exchange API request.
    
    Args:
        exchange_id: Exchange identifier
        endpoint: Optional endpoint identifier
        weight: Request weight
        
    Returns:
        None, but may sleep if throttling is needed
    """
    rate_limit_manager = RateLimitManager()
    should_throttle, wait_time = rate_limit_manager.should_throttle(exchange_id, endpoint)
    
    if should_throttle:
        logger.warning(f"Rate limiting applied for {exchange_id}/{endpoint}: "
                      f"waiting {wait_time:.2f}s")
        await asyncio.sleep(wait_time)
    
    # Record this request
    rate_limit_manager.record_request(exchange_id, endpoint, weight)

def rate_limited(exchange_id: str, endpoint: str = None, weight: float = 1.0):
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        exchange_id: Exchange identifier
        endpoint: Optional endpoint identifier
        weight: Request weight
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            await apply_rate_limiting(exchange_id, endpoint, weight)
            try:
                result = await func(*args, **kwargs)
                # Reset backoff on success
                RateLimitManager().reset_backoff(exchange_id)
                return result
            except Exception as e:
                # Record error for backoff strategy
                error_type = 'rate_limit' if 'rate limit' in str(e).lower() else 'other'
                RateLimitManager().record_error(exchange_id, error_type)
                raise
        return wrapper
    return decorator