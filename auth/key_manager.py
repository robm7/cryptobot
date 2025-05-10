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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

from redis_service import get_redis_connection
from models.audit_log import AuditLog
from models.user import User
from sqlalchemy.orm import Session

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
    
    # Default settings
    DEFAULT_KEY_EXPIRY_DAYS = 90
    DEFAULT_GRACE_PERIOD_HOURS = 24
    DEFAULT_KEY_LENGTH = 40
    
    def __init__(self, db_session: Session):
        """Initialize the key manager"""
        self.db = db_session
    
    def generate_key(self, length: int = DEFAULT_KEY_LENGTH) -> str:
        """Generate a secure random API key"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_key(self, 
                  user_id: int, 
                  description: str, 
                  exchange: str,
                  is_test: bool = False,
                  expiry_days: int = DEFAULT_KEY_EXPIRY_DAYS) -> Dict[str, Any]:
        """
        Create a new API key
        
        Args:
            user_id: User ID
            description: Key description
            exchange: Exchange name
            is_test: Whether this is a test key
            expiry_days: Days until key expires
            
        Returns:
            Dict containing the new key details
        """
        # Generate a new key
        api_key = self.generate_key()
        key_id = str(uuid.uuid4())
        
        # Calculate expiration
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=expiry_days)
        
        # Create key data
        key_data = {
            "id": key_id,
            "key": api_key,
            "user_id": user_id,
            "description": description,
            "exchange": exchange,
            "is_test": is_test,
            "status": KeyStatus.ACTIVE,
            "version": 1,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": None,
            "permissions": ["read", "trade"] if not is_test else ["read", "trade", "test"]
        }
        
        # Store in Redis
        with get_redis_connection() as conn:
            # Store key data
            conn.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(key_data))
            
            # Add to user's keys
            conn.sadd(f"{self.USER_KEYS_PREFIX}{user_id}", key_id)
            
            # Add to expiring keys sorted set with score as expiration timestamp
            expiry_timestamp = expires_at.timestamp()
            conn.zadd(self.EXPIRING_KEYS_PREFIX, {key_id: expiry_timestamp})
        
        # Log the operation
        self._log_operation(
            user_id=user_id,
            operation="create_key",
            key_id=key_id,
            details={"description": description, "exchange": exchange, "is_test": is_test}
        )
        
        return key_data
    
    def get_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get key data by ID"""
        with get_redis_connection() as conn:
            key_data = conn.get(f"{self.KEY_PREFIX}{key_id}")
            if key_data:
                return json.loads(key_data)
        return None
    
    def get_key_by_value(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get key data by the actual API key value"""
        # This is less efficient but necessary for authentication
        with get_redis_connection() as conn:
            # Get all keys (this could be optimized with a secondary index)
            keys = conn.keys(f"{self.KEY_PREFIX}*")
            
            for key in keys:
                key_data = conn.get(key)
                if key_data:
                    data = json.loads(key_data)
                    if data.get("key") == api_key:
                        return data
        
        return None
    
    def get_user_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all keys for a user"""
        keys = []
        
        with get_redis_connection() as conn:
            # Get all key IDs for user
            key_ids = conn.smembers(f"{self.USER_KEYS_PREFIX}{user_id}")
            
            # Get key data for each ID
            for key_id in key_ids:
                key_data = conn.get(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    keys.append(json.loads(key_data))
        
        return keys
    
    def rotate_key(self, 
                  key_id: str, 
                  user_id: int,
                  grace_period_hours: int = DEFAULT_GRACE_PERIOD_HOURS) -> Dict[str, Any]:
        """
        Rotate an API key with grace period
        
        Args:
            key_id: Key ID to rotate
            user_id: User ID for verification
            grace_period_hours: Hours to keep old key valid
            
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
            "previous_key_id": key_id
        }
        
        # Update old key status
        current_key["status"] = KeyStatus.ROTATING
        current_key["rotated_at"] = created_at.isoformat()
        current_key["grace_period_ends"] = (created_at + timedelta(hours=grace_period_hours)).isoformat()
        current_key["next_key_id"] = new_key_id
        
        # Store in Redis
        with get_redis_connection() as conn:
            # Store new key data
            conn.set(f"{self.KEY_PREFIX}{new_key_id}", json.dumps(new_key_data))
            
            # Update old key data
            conn.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(current_key))
            
            # Add new key to user's keys
            conn.sadd(f"{self.USER_KEYS_PREFIX}{user_id}", new_key_id)
            
            # Add to expiring keys sorted set
            expiry_timestamp = expires_at.timestamp()
            conn.zadd(self.EXPIRING_KEYS_PREFIX, {new_key_id: expiry_timestamp})
            
            # Store version history
            version_key = f"{self.VERSION_PREFIX}{current_key['exchange']}:{user_id}"
            conn.hset(version_key, current_key["version"], key_id)
            conn.hset(version_key, new_key_data["version"], new_key_id)
        
        # Log the operation
        self._log_operation(
            user_id=user_id,
            operation="rotate_key",
            key_id=key_id,
            details={
                "new_key_id": new_key_id, 
                "grace_period_hours": grace_period_hours
            }
        )
        
        return new_key_data
    
    def revoke_key(self, key_id: str, user_id: int, reason: str = "Manual revocation") -> bool:
        """
        Revoke an API key immediately
        
        Args:
            key_id: Key ID to revoke
            user_id: User ID for verification
            reason: Reason for revocation
            
        Returns:
            True if successful
        """
        # Get current key
        current_key = self.get_key(key_id)
        if not current_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Verify user owns the key
        if current_key["user_id"] != user_id:
            raise ValueError("Not authorized to revoke this key")
        
        # Update key status
        current_key["status"] = KeyStatus.REVOKED
        current_key["revoked_at"] = datetime.utcnow().isoformat()
        current_key["revocation_reason"] = reason
        
        # Store in Redis
        with get_redis_connection() as conn:
            conn.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(current_key))
        
        # Log the operation
        self._log_operation(
            user_id=user_id,
            operation="revoke_key",
            key_id=key_id,
            details={"reason": reason}
        )
        
        return True
    
    def mark_key_compromised(self, key_id: str, user_id: int, details: str) -> bool:
        """
        Mark an API key as compromised (emergency revocation)
        
        Args:
            key_id: Key ID to mark as compromised
            user_id: User ID for verification
            details: Details about the compromise
            
        Returns:
            True if successful
        """
        # Get current key
        current_key = self.get_key(key_id)
        if not current_key:
            raise ValueError(f"Key {key_id} not found")
        
        # Verify user owns the key
        if current_key["user_id"] != user_id:
            raise ValueError("Not authorized to mark this key as compromised")
        
        # Update key status
        current_key["status"] = KeyStatus.COMPROMISED
        current_key["compromised_at"] = datetime.utcnow().isoformat()
        current_key["compromise_details"] = details
        
        # Store in Redis
        with get_redis_connection() as conn:
            conn.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(current_key))
        
        # Log the operation with high severity
        self._log_operation(
            user_id=user_id,
            operation="mark_compromised",
            key_id=key_id,
            details={"details": details},
            severity="high"
        )
        
        return True
    
    def get_expiring_keys(self, days_threshold: int = 7) -> List[Dict[str, Any]]:
        """
        Get keys that are expiring soon
        
        Args:
            days_threshold: Days threshold for expiration
            
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
                key_data = conn.get(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    key = json.loads(key_data)
                    # Only include active keys
                    if key["status"] == KeyStatus.ACTIVE:
                        expiring_keys.append(key)
        
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
            # Get keys that have expired
            expired_timestamp = now.timestamp()
            expired_key_ids = conn.zrangebyscore(
                self.EXPIRING_KEYS_PREFIX, 
                0, 
                expired_timestamp
            )
            
            # Process each expired key
            for key_id in expired_key_ids:
                key_data = conn.get(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    key = json.loads(key_data)
                    
                    # Skip already expired/revoked keys
                    if key["status"] in [KeyStatus.EXPIRED, KeyStatus.REVOKED, KeyStatus.COMPROMISED]:
                        continue
                    
                    # Mark as expired
                    key["status"] = KeyStatus.EXPIRED
                    key["expired_at"] = now.isoformat()
                    conn.set(f"{self.KEY_PREFIX}{key_id}", json.dumps(key))
                    
                    # Log the operation
                    self._log_operation(
                        user_id=key["user_id"],
                        operation="expire_key",
                        key_id=key_id,
                        details={"automatic": True}
                    )
                    
                    processed_count += 1
            
            # Process keys with ended grace periods
            all_keys = conn.keys(f"{self.KEY_PREFIX}*")
            for key_name in all_keys:
                key_data = conn.get(key_name)
                if key_data:
                    key = json.loads(key_data)
                    
                    # Check for rotating keys with ended grace periods
                    if key["status"] == KeyStatus.ROTATING and "grace_period_ends" in key:
                        grace_end = datetime.fromisoformat(key["grace_period_ends"])
                        if now > grace_end:
                            # Mark as expired
                            key["status"] = KeyStatus.EXPIRED
                            key["expired_at"] = now.isoformat()
                            conn.set(key_name, json.dumps(key))
                            
                            # Log the operation
                            self._log_operation(
                                user_id=key["user_id"],
                                operation="expire_key",
                                key_id=key["id"],
                                details={"grace_period_ended": True}
                            )
                            
                            processed_count += 1
        
        return processed_count
    
    def validate_key(self, api_key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validate an API key
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (is_valid, key_data)
        """
        key_data = self.get_key_by_value(api_key)
        if not key_data:
            return False, None
        
        # Check key status
        if key_data["status"] in [KeyStatus.ACTIVE, KeyStatus.ROTATING]:
            # Update last used timestamp
            key_data["last_used"] = datetime.utcnow().isoformat()
            
            with get_redis_connection() as conn:
                conn.set(f"{self.KEY_PREFIX}{key_data['id']}", json.dumps(key_data))
            
            return True, key_data
        
        return False, key_data
    
    def get_key_history(self, exchange: str, user_id: int) -> List[Dict[str, Any]]:
        """
        Get version history for keys
        
        Args:
            exchange: Exchange name
            user_id: User ID
            
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
                key_data = conn.get(f"{self.KEY_PREFIX}{key_id}")
                if key_data:
                    history.append(json.loads(key_data))
        
        # Sort by version
        history.sort(key=lambda k: k["version"])
        
        return history
    
    def _log_operation(self, 
                      user_id: int, 
                      operation: str, 
                      key_id: str, 
                      details: Dict[str, Any],
                      severity: str = "normal") -> None:
        """Log an API key operation to the audit log"""
        # Create audit log entry
        log_entry = AuditLog(
            user_id=user_id,
            action=f"api_key_{operation}",
            resource_id=key_id,
            resource_type="api_key",
            details=json.dumps(details),
            severity=severity
        )
        
        # Save to database
        self.db.add(log_entry)
        self.db.commit()
        
        # Log to console as well
        logger.info(f"API Key operation: {operation} on {key_id} by user {user_id}")