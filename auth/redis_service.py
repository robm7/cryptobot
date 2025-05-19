import redis
import json
import time
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Dict, Any, Union, List, Tuple
from fastapi import Request, HTTPException, status
from contextlib import contextmanager

from config import settings as global_settings_module # Alias to avoid confusion

# Redis connection pool
_redis_pool = None
# Encryption key
_encryption_key = None

def get_redis_pool():
    """Get or create a Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(
            host=global_settings_module.settings.REDIS_HOST,
            port=global_settings_module.settings.REDIS_PORT,
            db=global_settings_module.settings.REDIS_DB,
            password=global_settings_module.settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_timeout=global_settings_module.settings.REDIS_TIMEOUT,
            socket_keepalive=True,
            health_check_interval=30,
            retry_on_timeout=True,
            max_connections=global_settings_module.settings.REDIS_MAX_CONNECTIONS
        )
    return _redis_pool

def get_encryption_key():
    """Get or create the encryption key for sensitive data"""
    global _encryption_key
    if _encryption_key is None:
        # Use environment variable or settings for the encryption key
        key_material = global_settings_module.settings.ENCRYPTION_KEY.encode()
        salt = global_settings_module.settings.ENCRYPTION_SALT.encode()
        
        # Derive a key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_material))
        _encryption_key = Fernet(key)
    
    return _encryption_key

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    if not data:
        return data
    
    key = get_encryption_key()
    return key.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    if not encrypted_data:
        return encrypted_data
    
    key = get_encryption_key()
    return key.decrypt(encrypted_data.encode()).decode()

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
    
    # Key prefixes for different data types
    KEY_PREFIX = "api_key:"
    SESSION_PREFIX = "session:"
    CACHE_PREFIX = "cache:"
    BACKUP_PREFIX = "backup:"
    
    # Default TTL values (in seconds)
    DEFAULT_KEY_TTL = 90 * 24 * 60 * 60  # 90 days
    DEFAULT_SESSION_TTL = 24 * 60 * 60   # 24 hours
    DEFAULT_CACHE_TTL = 60 * 60          # 1 hour
    
    @staticmethod
    def check_connection() -> bool:
        """Check if Redis connection is working"""
        try:
            with get_redis_connection() as conn:
                conn.ping()
                return True
        except redis.RedisError as e:
            print(f"Redis connection error: {e}")
            return False
    
    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """Get Redis health status"""
        try:
            start_time = time.time()
            with get_redis_connection() as conn:
                conn.ping()
                latency = time.time() - start_time
                info = conn.info()
                return {
                    "status": "healthy",
                    "latency_ms": round(latency * 1000, 2),
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2)
                }
        except redis.RedisError as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

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


    @staticmethod
    def store_encrypted(key: str, value: str, ttl: int = None) -> bool:
        """Store encrypted data in Redis"""
        try:
            encrypted_value = encrypt_data(value)
            with get_redis_connection() as conn:
                if ttl:
                    return conn.setex(key, ttl, encrypted_value)
                else:
                    return conn.set(key, encrypted_value)
        except Exception as e:
            print(f"Error storing encrypted data: {e}")
            return False
    
    @staticmethod
    def get_encrypted(key: str) -> Optional[str]:
        """Get and decrypt data from Redis"""
        try:
            with get_redis_connection() as conn:
                value = conn.get(key)
                if value:
                    return decrypt_data(value)
                return None
        except Exception as e:
            print(f"Error retrieving encrypted data: {e}")
            return None
    
    @staticmethod
    def store_json(key: str, data: Dict[str, Any], ttl: int = None) -> bool:
        """Store JSON data in Redis"""
        try:
            # Encrypt sensitive fields
            if "key" in data:
                data["key"] = encrypt_data(data["key"])
            
            json_data = json.dumps(data)
            with get_redis_connection() as conn:
                if ttl:
                    return conn.setex(key, ttl, json_data)
                else:
                    return conn.set(key, json_data)
        except Exception as e:
            print(f"Error storing JSON data: {e}")
            return False
    
    @staticmethod
    def get_json(key: str) -> Optional[Dict[str, Any]]:
        """Get JSON data from Redis"""
        try:
            with get_redis_connection() as conn:
                data = conn.get(key)
                if data:
                    json_data = json.loads(data)
                    # Decrypt sensitive fields
                    if "key" in json_data and json_data["key"]:
                        json_data["key"] = decrypt_data(json_data["key"])
                    return json_data
                return None
        except Exception as e:
            print(f"Error retrieving JSON data: {e}")
            return None
    
    @staticmethod
    def create_backup(key: str) -> bool:
        """Create a backup of a key"""
        try:
            with get_redis_connection() as conn:
                value = conn.get(key)
                if value:
                    backup_key = f"{RedisService.BACKUP_PREFIX}{key}:{int(time.time())}"
                    conn.set(backup_key, value)
                    # Set expiry for backup (30 days)
                    conn.expire(backup_key, 30 * 24 * 60 * 60)
                    return True
                return False
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    @staticmethod
    def get_backups(key: str, limit: int = 5) -> List[Tuple[str, str]]:
        """Get backups for a key"""
        try:
            with get_redis_connection() as conn:
                backup_pattern = f"{RedisService.BACKUP_PREFIX}{key}:*"
                backup_keys = conn.keys(backup_pattern)
                
                # Sort by timestamp (newest first)
                backup_keys.sort(reverse=True)
                
                # Limit the number of backups
                backup_keys = backup_keys[:limit]
                
                # Get values
                backups = []
                for bk in backup_keys:
                    timestamp = bk.split(":")[-1]
                    value = conn.get(bk)
                    backups.append((timestamp, value))
                
                return backups
        except Exception as e:
            print(f"Error retrieving backups: {e}")
            return []

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
        limit = limit or global_settings_module.settings.RATE_LIMIT_PER_MINUTE
        
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
                # Use pipeline for atomic operations
                pipe = conn.pipeline()
                pipe.incr(key)
                pipe.ttl(key)
                current, ttl = pipe.execute()
                
                # Set expiration on first request or if TTL is -1 (no expiry)
                if current == 1 or ttl == -1:
                    conn.expire(key, period)
                    ttl = period
                
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