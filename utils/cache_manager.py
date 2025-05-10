"""
Cache Manager

This module provides a caching system for the Cryptobot application.
It includes functions for caching API responses, database query results,
and other frequently accessed data.
"""

import time
import json
import hashlib
import logging
import functools
import asyncio
from typing import Dict, Any, Callable, Optional, Union, Tuple, List, Set
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError

# Configure logging
logger = logging.getLogger(__name__)

# Cache statistics
cache_stats = {
    "hits": 0,
    "misses": 0,
    "sets": 0,
    "evictions": 0,
    "errors": 0,
    "cache_size": 0,
    "avg_response_time_cached": 0,
    "avg_response_time_uncached": 0,
    "total_response_time_cached": 0,
    "total_response_time_uncached": 0,
    "total_requests_cached": 0,
    "total_requests_uncached": 0,
}

# Default cache settings
DEFAULT_CACHE_TTL = 300  # 5 minutes
DEFAULT_CACHE_PREFIX = "cryptobot:"
DEFAULT_CACHE_ENABLED = True

# Redis connection
redis_client = None

def initialize_redis(host: str = "localhost", port: int = 6379, db: int = 0, 
                    password: Optional[str] = None, ssl: bool = False) -> None:
    """
    Initialize the Redis connection.
    
    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
        ssl: Whether to use SSL
    """
    global redis_client
    
    try:
        redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            decode_responses=True
        )
        
        # Test connection
        redis_client.ping()
        logger.info(f"Connected to Redis at {host}:{port}")
    except RedisError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        redis_client = None

# In-memory cache for fallback
memory_cache = {}

def get_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from the function arguments.
    
    Args:
        prefix: Cache key prefix
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Cache key
    """
    # Convert args and kwargs to a string
    key_parts = [prefix]
    
    if args:
        key_parts.append(str(args))
    
    if kwargs:
        # Sort kwargs by key to ensure consistent ordering
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(str(sorted_kwargs))
    
    # Join key parts and hash
    key_str = ":".join(key_parts)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    
    return f"{DEFAULT_CACHE_PREFIX}{prefix}:{key_hash}"

def set_cache(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    Set a value in the cache.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
        
    Returns:
        True if successful, False otherwise
    """
    global cache_stats
    
    # Serialize value to JSON
    try:
        serialized_value = json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize value for cache key {key}: {e}")
        cache_stats["errors"] += 1
        return False
    
    # Try to set in Redis
    if redis_client:
        try:
            result = redis_client.setex(key, ttl, serialized_value)
            if result:
                cache_stats["sets"] += 1
                cache_stats["cache_size"] = redis_client.dbsize()
                return True
        except RedisError as e:
            logger.warning(f"Failed to set cache in Redis: {e}")
    
    # Fallback to memory cache
    try:
        memory_cache[key] = {
            "value": serialized_value,
            "expires_at": time.time() + ttl
        }
        cache_stats["sets"] += 1
        cache_stats["cache_size"] = len(memory_cache)
        return True
    except Exception as e:
        logger.error(f"Failed to set cache in memory: {e}")
        cache_stats["errors"] += 1
        return False

def get_cache(key: str) -> Tuple[bool, Any]:
    """
    Get a value from the cache.
    
    Args:
        key: Cache key
        
    Returns:
        Tuple of (success, value)
    """
    global cache_stats
    
    # Try to get from Redis
    if redis_client:
        try:
            value = redis_client.get(key)
            if value:
                try:
                    deserialized_value = json.loads(value)
                    cache_stats["hits"] += 1
                    return True, deserialized_value
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to deserialize value for cache key {key}: {e}")
                    cache_stats["errors"] += 1
        except RedisError as e:
            logger.warning(f"Failed to get cache from Redis: {e}")
    
    # Fallback to memory cache
    if key in memory_cache:
        cache_entry = memory_cache[key]
        
        # Check if expired
        if cache_entry["expires_at"] < time.time():
            del memory_cache[key]
            cache_stats["evictions"] += 1
            cache_stats["misses"] += 1
            return False, None
        
        try:
            deserialized_value = json.loads(cache_entry["value"])
            cache_stats["hits"] += 1
            return True, deserialized_value
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize value for cache key {key}: {e}")
            cache_stats["errors"] += 1
    
    cache_stats["misses"] += 1
    return False, None

def delete_cache(key: str) -> bool:
    """
    Delete a value from the cache.
    
    Args:
        key: Cache key
        
    Returns:
        True if successful, False otherwise
    """
    # Try to delete from Redis
    if redis_client:
        try:
            result = redis_client.delete(key)
            if result:
                # Also delete from memory cache if it exists
                if key in memory_cache:
                    del memory_cache[key]
                return True
        except RedisError as e:
            logger.warning(f"Failed to delete cache from Redis: {e}")
    
    # Fallback to memory cache
    if key in memory_cache:
        del memory_cache[key]
        return True
    
    return False

def clear_cache_by_prefix(prefix: str) -> int:
    """
    Clear all cache entries with a specific prefix.
    
    Args:
        prefix: Cache key prefix
        
    Returns:
        Number of entries cleared
    """
    prefix_with_namespace = f"{DEFAULT_CACHE_PREFIX}{prefix}"
    count = 0
    
    # Try to clear from Redis
    if redis_client:
        try:
            # Get all keys with the prefix
            keys = redis_client.keys(f"{prefix_with_namespace}*")
            
            if keys:
                # Delete all keys
                count = redis_client.delete(*keys)
        except RedisError as e:
            logger.warning(f"Failed to clear cache from Redis: {e}")
    
    # Fallback to memory cache
    keys_to_delete = []
    for key in memory_cache.keys():
        if key.startswith(prefix_with_namespace):
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del memory_cache[key]
        count += 1
    
    return count

def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache statistics
    """
    global cache_stats
    
    stats = cache_stats.copy()
    
    # Calculate hit rate
    total_requests = stats["hits"] + stats["misses"]
    stats["hit_rate"] = stats["hits"] / total_requests if total_requests > 0 else 0
    
    # Calculate average response times
    if stats["total_requests_cached"] > 0:
        stats["avg_response_time_cached"] = stats["total_response_time_cached"] / stats["total_requests_cached"]
    
    if stats["total_requests_uncached"] > 0:
        stats["avg_response_time_uncached"] = stats["total_response_time_uncached"] / stats["total_requests_uncached"]
    
    # Calculate response time improvement
    if stats["avg_response_time_uncached"] > 0:
        stats["response_time_improvement"] = (
            (stats["avg_response_time_uncached"] - stats["avg_response_time_cached"]) / 
            stats["avg_response_time_uncached"]
        )
    else:
        stats["response_time_improvement"] = 0
    
    # Get Redis info if available
    if redis_client:
        try:
            redis_info = redis_client.info()
            stats["redis_used_memory"] = redis_info.get("used_memory_human", "N/A")
            stats["redis_used_memory_peak"] = redis_info.get("used_memory_peak_human", "N/A")
            stats["redis_evicted_keys"] = redis_info.get("evicted_keys", 0)
            stats["redis_connected_clients"] = redis_info.get("connected_clients", 0)
        except RedisError as e:
            logger.warning(f"Failed to get Redis info: {e}")
    
    return stats

def reset_cache_stats() -> None:
    """Reset cache statistics."""
    global cache_stats
    cache_stats = {
        "hits": 0,
        "misses": 0,
        "sets": 0,
        "evictions": 0,
        "errors": 0,
        "cache_size": 0,
        "avg_response_time_cached": 0,
        "avg_response_time_uncached": 0,
        "total_response_time_cached": 0,
        "total_response_time_uncached": 0,
        "total_requests_cached": 0,
        "total_requests_uncached": 0,
    }

def cache_decorator(prefix: str, ttl: int = DEFAULT_CACHE_TTL, 
                   enabled: bool = DEFAULT_CACHE_ENABLED) -> Callable:
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        enabled: Whether caching is enabled
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                # Caching disabled, just call the function
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # Update stats
                global cache_stats
                cache_stats["total_response_time_uncached"] += (end_time - start_time)
                cache_stats["total_requests_uncached"] += 1
                
                return result
            
            # Generate cache key
            cache_key = get_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cache_hit, cached_value = get_cache(cache_key)
            
            if cache_hit:
                # Cache hit, return cached value
                return cached_value
            
            # Cache miss, call the function
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            # Update stats
            global cache_stats
            cache_stats["total_response_time_uncached"] += (end_time - start_time)
            cache_stats["total_requests_uncached"] += 1
            
            # Cache the result
            set_cache(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator

def async_cache_decorator(prefix: str, ttl: int = DEFAULT_CACHE_TTL, 
                         enabled: bool = DEFAULT_CACHE_ENABLED) -> Callable:
    """
    Decorator for caching async function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        enabled: Whether caching is enabled
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not enabled:
                # Caching disabled, just call the function
                start_time = time.time()
                result = await func(*args, **kwargs)
                end_time = time.time()
                
                # Update stats
                global cache_stats
                cache_stats["total_response_time_uncached"] += (end_time - start_time)
                cache_stats["total_requests_uncached"] += 1
                
                return result
            
            # Generate cache key
            cache_key = get_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cache_hit, cached_value = get_cache(cache_key)
            
            if cache_hit:
                # Cache hit, return cached value
                return cached_value
            
            # Cache miss, call the function
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            
            # Update stats
            global cache_stats
            cache_stats["total_response_time_uncached"] += (end_time - start_time)
            cache_stats["total_requests_uncached"] += 1
            
            # Cache the result
            set_cache(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator

class CacheGroup:
    """
    A group of related cache entries.
    This allows for invalidating multiple cache entries at once.
    """
    
    def __init__(self, name: str):
        """
        Initialize a cache group.
        
        Args:
            name: Group name
        """
        self.name = name
        self.keys: Set[str] = set()
    
    def add_key(self, key: str) -> None:
        """
        Add a key to the group.
        
        Args:
            key: Cache key
        """
        self.keys.add(key)
        
        # Store the group membership in Redis if available
        if redis_client:
            try:
                group_key = f"{DEFAULT_CACHE_PREFIX}group:{self.name}"
                redis_client.sadd(group_key, key)
            except RedisError as e:
                logger.warning(f"Failed to add key to group in Redis: {e}")
    
    def invalidate(self) -> int:
        """
        Invalidate all keys in the group.
        
        Returns:
            Number of keys invalidated
        """
        count = 0
        
        # Try to invalidate from Redis
        if redis_client:
            try:
                group_key = f"{DEFAULT_CACHE_PREFIX}group:{self.name}"
                keys = redis_client.smembers(group_key)
                
                if keys:
                    # Delete all keys
                    count = redis_client.delete(*keys)
                    
                    # Delete the group
                    redis_client.delete(group_key)
            except RedisError as e:
                logger.warning(f"Failed to invalidate group from Redis: {e}")
        
        # Fallback to memory cache
        for key in self.keys:
            if key in memory_cache:
                del memory_cache[key]
                count += 1
        
        # Clear the keys set
        self.keys.clear()
        
        return count

# Cache groups
cache_groups: Dict[str, CacheGroup] = {}

def get_cache_group(name: str) -> CacheGroup:
    """
    Get a cache group.
    
    Args:
        name: Group name
        
    Returns:
        Cache group
    """
    if name not in cache_groups:
        cache_groups[name] = CacheGroup(name)
    
    return cache_groups[name]

def invalidate_cache_group(name: str) -> int:
    """
    Invalidate a cache group.
    
    Args:
        name: Group name
        
    Returns:
        Number of keys invalidated
    """
    if name in cache_groups:
        return cache_groups[name].invalidate()
    
    return 0

def cache_with_group_decorator(prefix: str, group: str, ttl: int = DEFAULT_CACHE_TTL, 
                              enabled: bool = DEFAULT_CACHE_ENABLED) -> Callable:
    """
    Decorator for caching function results with a group.
    
    Args:
        prefix: Cache key prefix
        group: Cache group name
        ttl: Time to live in seconds
        enabled: Whether caching is enabled
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not enabled:
                # Caching disabled, just call the function
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # Update stats
                global cache_stats
                cache_stats["total_response_time_uncached"] += (end_time - start_time)
                cache_stats["total_requests_uncached"] += 1
                
                return result
            
            # Generate cache key
            cache_key = get_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cache_hit, cached_value = get_cache(cache_key)
            
            if cache_hit:
                # Cache hit, return cached value
                return cached_value
            
            # Cache miss, call the function
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            # Update stats
            global cache_stats
            cache_stats["total_response_time_uncached"] += (end_time - start_time)
            cache_stats["total_requests_uncached"] += 1
            
            # Cache the result
            set_cache(cache_key, result, ttl)
            
            # Add to cache group
            cache_group = get_cache_group(group)
            cache_group.add_key(cache_key)
            
            return result
        
        return wrapper
    
    return decorator

def async_cache_with_group_decorator(prefix: str, group: str, ttl: int = DEFAULT_CACHE_TTL, 
                                    enabled: bool = DEFAULT_CACHE_ENABLED) -> Callable:
    """
    Decorator for caching async function results with a group.
    
    Args:
        prefix: Cache key prefix
        group: Cache group name
        ttl: Time to live in seconds
        enabled: Whether caching is enabled
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not enabled:
                # Caching disabled, just call the function
                start_time = time.time()
                result = await func(*args, **kwargs)
                end_time = time.time()
                
                # Update stats
                global cache_stats
                cache_stats["total_response_time_uncached"] += (end_time - start_time)
                cache_stats["total_requests_uncached"] += 1
                
                return result
            
            # Generate cache key
            cache_key = get_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cache_hit, cached_value = get_cache(cache_key)
            
            if cache_hit:
                # Cache hit, return cached value
                return cached_value
            
            # Cache miss, call the function
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            
            # Update stats
            global cache_stats
            cache_stats["total_response_time_uncached"] += (end_time - start_time)
            cache_stats["total_requests_uncached"] += 1
            
            # Cache the result
            set_cache(cache_key, result, ttl)
            
            # Add to cache group
            cache_group = get_cache_group(group)
            cache_group.add_key(cache_key)
            
            return result
        
        return wrapper
    
    return decorator