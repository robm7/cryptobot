import redis
import json
import time
from typing import Optional, Dict, Any, Union
from fastapi import Request, HTTPException, status
from contextlib import contextmanager

from config import settings

# Redis connection pool
_redis_pool = None

def get_redis_pool():
    """Get or create a Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    return _redis_pool

@contextmanager
def get_redis_connection():
    """Context manager for getting a Redis connection from the pool"""
    conn = redis.Redis(connection_pool=get_redis_pool())
    try:
        yield conn
    finally:
        conn.close()

class RedisService:
    """Service for Redis operations"""
    
    @staticmethod
    def check_connection() -> bool:
        """Check if Redis connection is working"""
        try:
            with get_redis_connection() as conn:
                conn.ping()
                return True
        except redis.RedisError:
            return False

    @staticmethod
    def add_to_blacklist(token: str, expires_in: int) -> bool:
        """Add a token to the blacklist"""
        try:
            with get_redis_connection() as conn:
                return conn.setex(f"blacklist:{token}", expires_in, "1")
        except redis.RedisError as e:
            print(f"Redis error in add_to_blacklist: {e}")
            return False

    @staticmethod
    def is_blacklisted(token: str) -> bool:
        """Check if a token is blacklisted"""
        try:
            with get_redis_connection() as conn:
                return bool(conn.exists(f"blacklist:{token}"))
        except redis.RedisError as e:
            print(f"Redis error in is_blacklisted: {e}")
            # If we can't check Redis, assume token is valid
            # This is safer than denying all requests when Redis is down
            return False

    @staticmethod
    def acquire_refresh_lock(refresh_token: str, ttl: int = 30) -> bool:
        """Acquire a lock to prevent concurrent refresh token usage"""
        try:
            with get_redis_connection() as conn:
                lock_key = f"refresh_lock:{refresh_token}"
                return bool(conn.set(lock_key, "1", nx=True, ex=ttl))
        except redis.RedisError as e:
            print(f"Redis error in acquire_refresh_lock: {e}")
            # If we can't set a lock, allow the refresh
            return True

    @staticmethod
    def release_refresh_lock(refresh_token: str) -> bool:
        """Release a refresh token lock"""
        try:
            with get_redis_connection() as conn:
                lock_key = f"refresh_lock:{refresh_token}"
                return bool(conn.delete(lock_key))
        except redis.RedisError as e:
            print(f"Redis error in release_refresh_lock: {e}")
            return False

    @staticmethod
    def cache_user(key: str, user: Any, ttl: int = 3600) -> bool:
        """Cache user data in Redis"""
        try:
            with get_redis_connection() as conn:
                # Serialize user data to JSON
                user_data = {
                    "username": user.username,
                    "email": user.email,
                    "hashed_password": user.hashed_password,
                    "disabled": user.disabled,
                    "roles": [role.name for role in user.roles]
                }
                return conn.setex(key, ttl, json.dumps(user_data))
        except redis.RedisError as e:
            print(f"Redis error in cache_user: {e}")
            return False

    @staticmethod
    def get_user(key: str) -> Optional[Any]:
        """Get cached user data from Redis"""
        try:
            with get_redis_connection() as conn:
                user_data = conn.get(key)
                if not user_data:
                    return None
                
                # Deserialize JSON and return user-like object
                data = json.loads(user_data)
                return type('User', (), data)  # Create simple object with attributes
        except redis.RedisError as e:
            print(f"Redis error in get_user: {e}")
            return None

    @staticmethod
    def invalidate_user(key: str) -> bool:
        """Remove user data from cache"""
        try:
            with get_redis_connection() as conn:
                return bool(conn.delete(key))
        except redis.RedisError as e:
            print(f"Redis error in invalidate_user: {e}")
            return False


# Rate limiting implementation using Redis
class RateLimiter:
    """Rate limiter using Redis"""
    
    @staticmethod
    async def check_rate_limit(request: Request, limit: int = None, period: int = 60):
        """
        Check if a request is rate limited
        
        Args:
            request: The FastAPI request object
            limit: Maximum number of requests per period
            period: Time period in seconds
        
        Raises:
            HTTPException: If rate limit is exceeded
        """
        # Use the specified limit or the default from settings
        limit = limit or settings.RATE_LIMIT_PER_MINUTE
        
        # Get client IP address
        client_ip = request.client.host
        
        # Get authorization header if present
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            key = f"rate_limit:{client_ip}:{token}"
        else:
            key = f"rate_limit:{client_ip}"
        
        try:
            with get_redis_connection() as conn:
                current = conn.incr(key)
                # Set expiration on first request
                if current == 1:
                    conn.expire(key, period)
                
                # Get the time to expiration
                ttl = conn.ttl(key)
                
                # Set rate limit headers
                request.state.rate_limit = {
                    "limit": limit,
                    "remaining": max(0, limit - current),
                    "reset": ttl if ttl > 0 else period
                }
                
                # Check if limit is exceeded
                if current > limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded",
                        headers={
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(ttl if ttl > 0 else period),
                            "Retry-After": str(ttl if ttl > 0 else period)
                        }
                    )
        except redis.RedisError as e:
            # Log error but don't block requests if Redis is down
            print(f"Redis error in check_rate_limit: {e}")
            pass  # Allow request to proceed if Redis is unavailable