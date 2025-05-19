"""
API Key Rotation System - Key Manager

This module provides the core functionality for API key rotation with:
- Zero-downtime key rotation with grace periods
- Versioned key transitions with full history
- Emergency revocation with audit trails
- Comprehensive audit logging for all operations
- Automated expiration notifications
"""

import json
import time
import secrets
import string
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import uuid
from fastapi import Request, HTTPException, status
from services.mcp.order_execution.monitoring import (
    log_execution_time,
    track_metrics,
    alert_on_failure,
    retry_with_backoff
)

from .redis_service import get_redis_connection, RedisService # Corrected import
from .models.audit_log import AuditLog # Corrected import
from .models.user import User # Corrected import
from sqlalchemy.orm import Session
from .config import settings # Corrected import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeyStatus(str, Enum):
    """API Key status enum"""
    ACTIVE = "active"           # Current active key
    ROTATING = "rotating"       # New key during rotation (grace period)
    EXPIRED = "expired"         # Key that has been rotated out
    REVOKED = "revoked"         # Key that was manually revoked
    COMPROMISED = "compromised" # Key that was marked as compromised
    SUSPENDED = "suspended"     # Temporarily suspended key
    PENDING = "pending"         # Pending activation (requires approval)


class KeyManager:
    """
    Core API Key Manager with rotation logic
    
    Features:
    - Grace period support for zero-downtime rotation
    - Version history tracking
    - Audit logging for all operations
    - Emergency revocation
    """
    
    # Redis key prefixes
    KEY_PREFIX = "api_key:"
    VERSION_PREFIX = "api_key_version:"
    USER_KEYS_PREFIX = "user_keys:"
    EXPIRING_KEYS_PREFIX = "expiring_keys:"
    EXCHANGE_KEYS_PREFIX = "exchange_keys:"
    PERMISSION_PREFIX = "key_permission:"
    ROTATION_SCHEDULE_PREFIX = "rotation_schedule:"
    
    # Default settings from config
    DEFAULT_KEY_EXPIRY_DAYS = settings.API_KEY_DEFAULT_EXPIRY_DAYS
    DEFAULT_GRACE_PERIOD_HOURS = settings.API_KEY_ROTATION_GRACE_PERIOD_HOURS
    DEFAULT_KEY_LENGTH = settings.API_KEY_LENGTH
    
    def __init__(self, db_session: Session):
        """Initialize the key manager"""
        self.db = db_session
        self.redis_service = RedisService()
    
    def generate_key(self, length: int = DEFAULT_KEY_LENGTH) -> str:
        """Generate a secure random API key"""
        # Use a more secure method with a prefix for key type identification
        prefix = "ak"  # api key prefix
        # Generate random bytes and encode as hex
        random_part = secrets.token_hex(length // 2)
        # Add a checksum
        checksum = hashlib.sha256(random_part.encode()).hexdigest()[:4]
        # Combine parts
        return f"{prefix}_{random_part}_{checksum}"
    
    def create_key(self,
        user_id: int,
        description: str,
        exchange: str,
        is_test: bool = False,
        permissions: List[str] = None,
        expiry_days: int = DEFAULT_KEY_EXPIRY_DAYS,
        require_approval: bool = False,
        request: Request = None,
        key_length: int = DEFAULT_KEY_LENGTH) -> Dict[str, Any]:
        """
        Create a new API key
        
        Args:
            user_id: User ID
            description: Key description
            exchange: Exchange name
            is_test: Whether this is a test key
            permissions: List of permissions for this key
            expiry_days: Days until key expires
            require_approval: Whether this key requires approval before activation
            request: FastAPI request object for audit logging
            
        Returns:
            Dict containing the new key details
        """
        # Generate a new key
        api_key = self.generate_key()
        key_id = str(uuid.uuid4())
        
        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expiry_days)
        
        # Set default permissions if not provided
        if permissions is None:
            permissions = ["read", "trade"] if not is_test else ["read", "trade", "test"]
        
        # Set initial status
        initial_status = KeyStatus.PENDING if require_approval else KeyStatus.ACTIVE
        
        # Create key data
        key_data = {
            "id": key_id,
            "key": api_key,
            "user_id": user_id,
            "description": description,
            "exchange": exchange,
            "is_test": is_test,
            "status": initial_status,
            "version": 1,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": None,
            "permissions": permissions,
            "ip_restrictions": [],
            "usage_count": 0,
            "rotation_schedule": None,
            "metadata": {
                "created_from_ip": request.client.host if request else None,
                "user_agent": request.headers.get("user-agent") if request else None
            }
        }
        
        # Create a backup before storing
        self.redis_service.create_backup(f"{self.KEY_PREFIX}{key_id}")
        
        # Store in Redis using the enhanced Redis service
        with get_redis_connection() as conn:
            # Use pipeline for atomic operations
            pipe = conn.pipeline()
            
            # Store key data with encryption for sensitive fields
            pipe.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(key_data))
            
            # Add to user's keys
            pipe.sadd(f"{self.USER_KEYS_PREFIX}{user_id}", key_id)
            
            # Add to exchange keys set
            pipe.sadd(f"{self.EXCHANGE_KEYS_PREFIX}{exchange}", key_id)
            
            # Add to expiring keys sorted set with score as expiration timestamp
            expiry_timestamp = expires_at.timestamp()
            pipe.zadd(self.EXPIRING_KEYS_PREFIX, {key_id: expiry_timestamp})
            
            # Store permissions in a separate set for faster permission checks
            for permission in permissions:
                pipe.sadd(f"{self.PERMISSION_PREFIX}{key_id}", permission)
            
            # Execute all commands
            pipe.execute()
        
        # Log the operation with enhanced audit logging
        AuditLog.create_from_request(
            db_session=self.db,
            user_id=user_id,
            action="api_key_create",
            resource_type="api_key",
            resource_id=key_id,
            details={
                "description": description,
                "exchange": exchange,
                "is_test": is_test,
                "permissions": permissions,
                "expiry_days": expiry_days,
                "require_approval": require_approval
            },
            request=request,
            severity="normal",
            status="success"
        )
        
        return key_data
    
    def get_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get key data by ID"""
        # Use the enhanced Redis service for getting JSON data with decryption
        return self.redis_service.get_json(f"{self.KEY_PREFIX}{key_id}")
    
    def get_key_by_value(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get key data by the actual API key value"""
        # This is less efficient but necessary for authentication
        # Use a hash of the API key as a secondary index for faster lookups
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with get_redis_connection() as conn:
            # Check if we have a mapping from hash to key_id
            key_id = conn.get(f"api_key_hash:{api_key_hash}")
            
            if key_id:
                # Get the key data directly
                return self.get_key(key_id)
            
            # Fallback to scanning all keys (slower)
            keys = conn.keys(f"{self.KEY_PREFIX}*")
            
            for key in keys:
                key_data = self.redis_service.get_json(key)
                if key_data and key_data.get("key") == api_key:
                    # Store the hash mapping for future lookups
                    key_id = key_data["id"]
                    conn.set(f"api_key_hash:{api_key_hash}", key_id)
                    return key_data
        
        return None
    
    def get_user_keys(self, user_id: int, include_expired: bool = False) -> List[Dict[str, Any]]:
        """
        Get all keys for a user
        
        Args:
            user_id: User ID
            include_expired: Whether to include expired keys
            
        Returns:
            List of key data dictionaries
        """
        keys = []
        
        with get_redis_connection() as conn:
            # Get all key IDs for user
            key_ids = conn.smembers(f"{self.USER_KEYS_PREFIX}{user_id}")
            
            # Get key data for each ID
            for key_id in key_ids:
                key_data = self.redis_service.get_json(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    # Filter out expired keys if not requested
                    if not include_expired and key_data["status"] == KeyStatus.EXPIRED:
                        continue
                    keys.append(key_data)
        
        # Sort by creation date (newest first)
        keys.sort(key=lambda k: k["created_at"], reverse=True)
        return keys
    
    def get_exchange_keys(self, exchange: str, include_expired: bool = False) -> List[Dict[str, Any]]:
        """
        Get all keys for an exchange
        
        Args:
            exchange: Exchange name
            include_expired: Whether to include expired keys
            
        Returns:
            List of key data dictionaries
        """
        keys = []
        
        with get_redis_connection() as conn:
            # Get all key IDs for exchange
            key_ids = conn.smembers(f"{self.EXCHANGE_KEYS_PREFIX}{exchange}")
            
            # Get key data for each ID
            for key_id in key_ids:
                key_data = self.redis_service.get_json(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    # Filter out expired keys if not requested
                    if not include_expired and key_data["status"] == KeyStatus.EXPIRED:
                        continue
                    keys.append(key_data)
        
        # Sort by creation date (newest first)
        keys.sort(key=lambda k: k["created_at"], reverse=True)
        return keys
    
    def rotate_key(self,
                  key_id: str,
                  user_id: int,
                  grace_period_hours: int = DEFAULT_GRACE_PERIOD_HOURS,
                  request: Request = None) -> Dict[str, Any]:
        """
        Rotate an API key with grace period
        
        Args:
            key_id: Key ID to rotate
            user_id: User ID for verification
            grace_period_hours: Hours to keep old key valid
            request: FastAPI request object for audit logging
            
        Returns:
            Dict containing the new key details
        """
        # Get current key
        current_key = self.get_key(key_id)
        if not current_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Verify user owns the key
        if current_key["user_id"] != user_id:
            raise ValueError("Not authorized to rotate this key")
        
        # Check if key is active
        if current_key["status"] != KeyStatus.ACTIVE:
            raise ValueError(f"Cannot rotate key with status {current_key['status']}")
        
        # Create backups before modifying
        self.redis_service.create_backup(f"{self.KEY_PREFIX}{key_id}")
        
        # Generate new key
        new_api_key = self.generate_key()
        new_key_id = str(uuid.uuid4())
        
        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = datetime.fromisoformat(current_key["expires_at"])  # Keep same expiry
        
        # Create new key data
        new_key_data = {
            "id": new_key_id,
            "key": new_api_key,
            "user_id": user_id,
            "description": current_key["description"],
            "exchange": current_key["exchange"],
            "is_test": current_key["is_test"],
            "status": KeyStatus.ACTIVE,
            "version": current_key["version"] + 1,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": None,
            "permissions": current_key["permissions"],
            "ip_restrictions": current_key.get("ip_restrictions", []),
            "usage_count": 0,
            "rotation_schedule": current_key.get("rotation_schedule"),
            "previous_key_id": key_id,
            "metadata": {
                "rotated_from_ip": request.client.host if request else None,
                "user_agent": request.headers.get("user-agent") if request else None,
                "previous_key_id": key_id
            }
        }
        
        # Update old key status
        current_key["status"] = KeyStatus.ROTATING
        current_key["rotated_at"] = created_at.isoformat()
        current_key["grace_period_ends"] = (created_at + timedelta(hours=grace_period_hours)).isoformat()
        current_key["next_key_id"] = new_key_id
        
        # Store in Redis
        with get_redis_connection() as conn:
            # Use pipeline for atomic operations
            pipe = conn.pipeline()
            
            # Store new key data
            pipe.set(f"{self.KEY_PREFIX}{new_key_id}", json.dumps(new_key_data))
            
            # Update old key data
            pipe.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(current_key))
            
            # Add new key to user's keys
            pipe.sadd(f"{self.USER_KEYS_PREFIX}{user_id}", new_key_id)
            
            # Add new key to exchange keys
            pipe.sadd(f"{self.EXCHANGE_KEYS_PREFIX}{current_key['exchange']}", new_key_id)
            
            # Add to expiring keys sorted set
            expiry_timestamp = expires_at.timestamp()
            pipe.zadd(self.EXPIRING_KEYS_PREFIX, {new_key_id: expiry_timestamp})
            
            # Store version history
            version_key = f"{self.VERSION_PREFIX}{current_key['exchange']}:{user_id}"
            pipe.hset(version_key, current_key["version"], key_id)
            pipe.hset(version_key, new_key_data["version"], new_key_id)
            
            # Copy permissions to new key
            for permission in current_key["permissions"]:
                pipe.sadd(f"{self.PERMISSION_PREFIX}{new_key_id}", permission)
            
            # Create hash mapping for faster lookups
            api_key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()
            pipe.set(f"api_key_hash:{api_key_hash}", new_key_id)
            
            # Execute all commands
            pipe.execute()
        
        # Log the operation with enhanced audit logging
        AuditLog.create_from_request(
            db_session=self.db,
            user_id=user_id,
            action="api_key_rotate",
            resource_type="api_key",
            resource_id=key_id,
            details={
                "new_key_id": new_key_id,
                "grace_period_hours": grace_period_hours,
                "exchange": current_key["exchange"],
                "version": new_key_data["version"]
            },
            request=request,
            severity="normal",
            status="success"
        )
        
        return new_key_data
    
    @log_execution_time
    @track_metrics("api_key_revocation")
    @alert_on_failure(alert_threshold=3, window_seconds=300)
    def revoke_key(self, key_id: str, user_id: int, reason: str = "Manual revocation", request: Request = None) -> bool:
        """
        Revoke an API key immediately
        
        Args:
            key_id: Key ID to revoke
            user_id: User ID for verification
            reason: Reason for revocation
            request: FastAPI request object for audit logging
            
        Returns:
            True if successful
        """
        # Get current key
        current_key = self.get_key(key_id)
        if not current_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Verify user owns the key or has admin permissions
        if current_key["user_id"] != user_id and not self._user_has_admin_permission(user_id):
            raise ValueError("Not authorized to revoke this key")
        
        # Create backup before modifying
        self.redis_service.create_backup(f"{self.KEY_PREFIX}{key_id}")
        
        # Update key status
        current_key["status"] = KeyStatus.REVOKED
        current_key["revoked_at"] = datetime.utcnow().isoformat()
        current_key["revocation_reason"] = reason
        current_key["revoked_by"] = user_id
        if request:
            current_key["revoked_from_ip"] = request.client.host
        
        # Store in Redis
        with get_redis_connection() as conn:
            conn.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(current_key))
        
        # Log the operation with enhanced audit logging
        AuditLog.create_from_request(
            db_session=self.db,
            user_id=user_id,
            action="api_key_revoke",
            resource_type="api_key",
            resource_id=key_id,
            details={
                "reason": reason,
                "exchange": current_key["exchange"],
                "key_owner": current_key["user_id"]
            },
            request=request,
            severity="high",  # Revocation is a high-severity action
            status="success"
        )
        
        return True
    
    def _user_has_admin_permission(self, user_id: int) -> bool:
        """
        Check if a user has admin permissions
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has admin permissions
        """
        try:
            # Get user from database
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Check if user has admin role
            return any(role.name == "admin" for role in user.roles)
        except Exception as e:
            logger.error(f"Error checking admin permissions: {str(e)}")
            return False
    
    @log_execution_time
    @track_metrics("api_key_compromise")
    @alert_on_failure(alert_threshold=1, window_seconds=300)  # Lower threshold for compromise events
    def mark_key_compromised(self, key_id: str, user_id: int, details: str, request: Request = None) -> bool:
        """
        Mark an API key as compromised (emergency revocation)
        
        Args:
            key_id: Key ID to mark as compromised
            user_id: User ID for verification
            details: Details about the compromise
            request: FastAPI request object for audit logging
            
        Returns:
            True if successful
        """
        # Get current key
        current_key = self.get_key(key_id)
        if not current_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Verify user owns the key or has admin/security permissions
        if current_key["user_id"] != user_id and not self._user_has_admin_permission(user_id):
            raise ValueError("Not authorized to mark this key as compromised")
        
        # Create backup before modifying
        self.redis_service.create_backup(f"{self.KEY_PREFIX}{key_id}")
        
        # Update key status
        current_key["status"] = KeyStatus.COMPROMISED
        current_key["compromised_at"] = datetime.utcnow().isoformat()
        current_key["compromise_details"] = details
        current_key["reported_by"] = user_id
        if request:
            current_key["reported_from_ip"] = request.client.host
        
        # Store in Redis
        with get_redis_connection() as conn:
            # Use pipeline for atomic operations
            pipe = conn.pipeline()
            
            # Store updated key data
            pipe.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(current_key))
            
            # Execute all commands
            pipe.execute()
        
        # Log the operation with enhanced audit logging
        AuditLog.create_from_request(
            db_session=self.db,
            user_id=user_id,
            action="api_key_compromised",
            resource_type="api_key",
            resource_id=key_id,
            details={
                "details": details,
                "exchange": current_key["exchange"],
                "key_owner": current_key["user_id"]
            },
            request=request,
            severity="critical",  # Compromise is a critical-severity action
            status="success"
        )
        
        return True
    
    def get_expiring_keys(self, days_threshold: int = 7, include_rotating: bool = False) -> List[Dict[str, Any]]:
        """
        Get keys that are expiring soon
        
        Args:
            days_threshold: Days threshold for expiration
            include_rotating: Whether to include keys in rotation
            
        Returns:
            List of expiring keys
        """
        expiring_keys = []
        threshold_timestamp = (datetime.utcnow() + timedelta(days=days_threshold)).timestamp()
        
        with get_redis_connection() as conn:
            # Get keys expiring before threshold
            key_ids = conn.zrangebyscore(
                self.EXPIRING_KEYS_PREFIX,
                0,
                threshold_timestamp
            )
            
            # Get key data for each ID
            for key_id in key_ids:
                key_data = self.redis_service.get_json(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    # Filter by status
                    valid_statuses = [KeyStatus.ACTIVE]
                    if include_rotating:
                        valid_statuses.append(KeyStatus.ROTATING)
                    
                    if key_data["status"] in valid_statuses:
                        # Calculate days until expiration
                        expires_at = datetime.fromisoformat(key_data["expires_at"])
                        days_left = (expires_at - datetime.utcnow()).days
                        key_data["days_until_expiration"] = days_left
                        
                        expiring_keys.append(key_data)
        
        # Sort by expiration date (soonest first)
        expiring_keys.sort(key=lambda k: k["expires_at"])
        return expiring_keys
    
    def process_expired_keys(self) -> int:
        """
        Process expired keys and grace periods
        
        Returns:
            Number of keys processed
        """
        processed_count = 0
        now = datetime.utcnow()
        
        with get_redis_connection() as conn:
            # Use pipeline for atomic operations
            pipe = conn.pipeline()
            
            # Get keys that have expired
            expired_timestamp = now.timestamp()
            expired_key_ids = conn.zrangebyscore(
                self.EXPIRING_KEYS_PREFIX,
                0,
                expired_timestamp
            )
            
            # Process each expired key
            for key_id in expired_key_ids:
                key_data = self.redis_service.get_json(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    # Skip already expired/revoked keys
                    if key["status"] in [KeyStatus.EXPIRED, KeyStatus.REVOKED, KeyStatus.COMPROMISED]:
                        continue
                    
                    # Create backup before modifying
                    self.redis_service.create_backup(f"{self.KEY_PREFIX}{key_id}")
                    
                    # Mark as expired
                    key_data["status"] = KeyStatus.EXPIRED
                    key_data["expired_at"] = now.isoformat()
                    pipe.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(key_data))
                    
                    # Log the operation with enhanced audit logging
                    AuditLog.create_from_request(
                        db_session=self.db,
                        user_id=key_data["user_id"],
                        action="api_key_expire",
                        resource_type="api_key",
                        resource_id=key_id,
                        details={
                            "automatic": True,
                            "exchange": key_data["exchange"]
                        },
                        severity="normal",
                        status="success"
                    )
                    
                    processed_count += 1
            
            # Process keys with ended grace periods
            all_keys = conn.keys(f"{self.KEY_PREFIX}*")
            for key_name in all_keys:
                key_data = self.redis_service.get_json(key_name)
                if key_data:
                    # Check for rotating keys with ended grace periods
                    if key_data["status"] == KeyStatus.ROTATING and "grace_period_ends" in key_data:
                        grace_end = datetime.fromisoformat(key_data["grace_period_ends"])
                        if now > grace_end:
                            # Create backup before modifying
                            self.redis_service.create_backup(key_name)
                            
                            # Mark as expired
                            key_data["status"] = KeyStatus.EXPIRED
                            key_data["expired_at"] = now.isoformat()
                            pipe.set(key_name, json.dumps(key_data))
                            
                            # Log the operation with enhanced audit logging
                            AuditLog.create_from_request(
                                db_session=self.db,
                                user_id=key_data["user_id"],
                                action="api_key_expire",
                                resource_type="api_key",
                                resource_id=key_data["id"],
                                details={
                                    "grace_period_ended": True,
                                    "exchange": key_data["exchange"]
                                },
                                severity="normal",
                                status="success"
                            )
                            
                            processed_count += 1
            
            # Execute all commands
            pipe.execute()
        
        return processed_count
    
    @log_execution_time
    @track_metrics("api_key_validation")
    @retry_with_backoff(max_retries=3, retryable_errors=["timeout", "connection"])
    def validate_key(self, api_key: str, request: Request = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an API key
        
        Args:
            api_key: The API key to validate
            request: FastAPI request object for tracking usage
            
        Returns:
            Tuple of (is_valid, key_data)
        """
        key_data = self.get_key_by_value(api_key)
        if not key_data:
            # Log failed validation attempt if request is provided
            if request:
                logger.warning(f"Failed API key validation attempt from IP: {request.client.host}")
            return False, None
        
        # Check key status
        if key_data["status"] in [KeyStatus.ACTIVE, KeyStatus.ROTATING]:
            # Update last used timestamp and usage count
            key_data["last_used"] = datetime.utcnow().isoformat()
            key_data["usage_count"] = key_data.get("usage_count", 0) + 1
            
            # Track usage metadata if request is provided
            if request:
                # Initialize usage_metadata if it doesn't exist
                if "usage_metadata" not in key_data:
                    key_data["usage_metadata"] = {}
                
                # Track IP addresses
                if "ip_addresses" not in key_data["usage_metadata"]:
                    key_data["usage_metadata"]["ip_addresses"] = []
                
                client_ip = request.client.host
                if client_ip not in key_data["usage_metadata"]["ip_addresses"]:
                    key_data["usage_metadata"]["ip_addresses"].append(client_ip)
                
                # Check IP restrictions if configured
                if key_data.get("ip_restrictions") and client_ip not in key_data["ip_restrictions"]:
                    logger.warning(f"API key {key_data['id']} used from unauthorized IP: {client_ip}")
                    # Log the unauthorized access attempt
                    AuditLog.create_from_request(
                        db_session=self.db,
                        user_id=key_data["user_id"],
                        action="api_key_unauthorized_ip",
                        resource_type="api_key",
                        resource_id=key_data["id"],
                        details={
                            "ip_address": client_ip,
                            "allowed_ips": key_data["ip_restrictions"]
                        },
                        request=request,
                        severity="high",
                        status="failure"
                    )
                    return False, key_data
            
            # Store updated key data
            with get_redis_connection() as conn:
                conn.set(f"{self.KEY_PREFIX}{key_data['id']}", json.dumps(key_data))
            
            return True, key_data
        
        return False, key_data
    
    def get_key_history(self, exchange: str, user_id: int, include_details: bool = True) -> List[Dict[str, Any]]:
        """
        Get version history for keys
        
        Args:
            exchange: Exchange name
            user_id: User ID
            include_details: Whether to include full key details or just summary
            
        Returns:
            List of key versions
        """
        history = []
        
        with get_redis_connection() as conn:
            # Get version history
            version_key = f"{self.VERSION_PREFIX}{exchange}:{user_id}"
            versions = conn.hgetall(version_key)
            
            # Get key data for each version
            for version, key_id in versions.items():
                key_data = self.redis_service.get_json(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    if not include_details:
                        # Create a summary version with less sensitive data
                        summary = {
                            "id": key_data["id"],
                            "version": key_data["version"],
                            "status": key_data["status"],
                            "created_at": key_data["created_at"],
                            "expires_at": key_data["expires_at"],
                            "description": key_data["description"]
                        }
                        history.append(summary)
                    else:
                        # Mask the actual key value for security
                        if "key" in key_data and key_data["key"]:
                            key_value = key_data["key"]
                            if len(key_value) > 8:
                                key_data["key"] = key_value[:4] + "*" * (len(key_value) - 8) + key_value[-4:]
                            else:
                                key_data["key"] = "*" * len(key_value)
                        
                        history.append(key_data)
        
        # Sort by version
        history.sort(key=lambda k: k["version"])
        
        return history
    
    def _log_operation(self,
                      user_id: int,
                      operation: str,
                      key_id: str,
                      details: Dict[str, Any],
                      severity: str = "normal",
                      request: Request = None,
                      status: str = "success") -> None:
        """
        Log an API key operation to the audit log
        
        This is a legacy method that uses the enhanced AuditLog class
        New code should use AuditLog.create_from_request directly
        """
        # Create audit log entry using the enhanced AuditLog class
        AuditLog.create_from_request(
            db_session=self.db,
            user_id=user_id,
            action=f"api_key_{operation}",
            resource_type="api_key",
            resource_id=key_id,
            details=details,
            request=request,
            severity=severity,
            status=status
        )
        
        # Log to console as well
        logger.info(f"API Key operation: {operation} on {key_id} by user {user_id}")