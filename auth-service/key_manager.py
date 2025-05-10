import json
import time
import uuid
import redis
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable

class KeyManager:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.notification_callbacks: List[Callable[[Dict], None]] = []
        self.redis = redis_client
        self.current_key_prefix = "current_key:"
        self.key_prefix = "api_key:"
        self.expiring_keys_set = "expiring_keys"

    def generate_key(self) -> str:
        return str(uuid.uuid4())

    def rotate_keys(self, expire_in_days: int) -> str:
        # Get current key before rotation
        current_key = self.get_current_key()
        
        # Generate new key
        new_key_id = self.generate_key()
        created_at = datetime.utcnow().isoformat()
        expires_at = (datetime.utcnow() + timedelta(days=expire_in_days)).isoformat()
        
        # Create key data structure
        key_data = {
            "id": new_key_id,
            "created_at": created_at,
            "expires_at": expires_at,
            "is_active": True,
            "is_revoked": False,
            "version": (current_key["version"] + 1) if current_key else 1,
            "permissions": ["*"]  # Default to all permissions
        }

        # Store new key
        self.redis.set(f"{self.key_prefix}{new_key_id}", json.dumps(key_data))
        
        # Set expiration
        self.redis.expireat(
            f"{self.key_prefix}{new_key_id}", 
            int(datetime.fromisoformat(expires_at).timestamp())
        )
        
        # Add to expiring keys set
        self.redis.zadd(
            self.expiring_keys_set,
            {new_key_id: datetime.fromisoformat(expires_at).timestamp()}
        )

        # Mark as current key
        self.redis.set(self.current_key_prefix, new_key_id)

        # Deactivate old key if exists
        if current_key:
            current_key["is_active"] = False
            self.redis.set(
                f"{self.key_prefix}{current_key['id']}", 
                json.dumps(current_key)
            )

        return new_key_id

    def get_current_key(self) -> Optional[Dict]:
        current_key_id = self.redis.get(self.current_key_prefix)
        if not current_key_id:
            return None
        return self.get_key(current_key_id.decode())

    def get_key(self, key_id: str) -> Optional[Dict]:
        key_data = self.redis.get(f"{self.key_prefix}{key_id}")
        if not key_data:
            return None
        return json.loads(key_data)

    def get_all_keys(self) -> List[Dict]:
        keys = []
        for key in self.redis.scan_iter(f"{self.key_prefix}*"):
            key_data = self.redis.get(key)
            if key_data:
                keys.append(json.loads(key_data))
        return keys

    def revoke_key(self, key_id: str) -> bool:
        key = self.get_key(key_id)
        if not key:
            return False
        
        key["is_revoked"] = True
        key["is_active"] = False
        self.redis.set(f"{self.key_prefix}{key_id}", json.dumps(key))
        return True

    def get_upcoming_expirations(self, days: int) -> List[Dict]:
        now = time.time()
        max_timestamp = now + (days * 24 * 60 * 60)
        
        key_ids = self.redis.zrangebyscore(
            self.expiring_keys_set,
            now,
            max_timestamp
        )
        
        return [self.get_key(key_id.decode()) for key_id in key_ids]

    def get_key_permissions(self, key_id: str) -> List[str]:
        key = self.get_key(key_id)
        if not key:
            return []
        return key.get("permissions", [])

    def update_key_permissions(self, key_id: str, permissions: List[str]) -> bool:
        key = self.get_key(key_id)
        if not key:
            return False
        
        key["permissions"] = permissions
        self.redis.set(f"{self.key_prefix}{key_id}", json.dumps(key))
        return True

    def add_notification_callback(self, callback: Callable[[Dict], None]) -> None:
        """Add callback to be notified of key events"""
        self.notification_callbacks.append(callback)

    def _notify(self, key_data: Dict, event_type: str) -> None:
        """Notify all registered callbacks"""
        for callback in self.notification_callbacks:
            try:
                callback({
                    **key_data,
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"Notification callback failed: {e}")

    def schedule_rotation(self, days: int, hours_before: int = 24) -> None:
        """Schedule automatic key rotation"""
        def rotation_job():
            new_key_id = self.rotate_keys(days)
            new_key = self.get_key(new_key_id)
            self._notify(new_key, "rotation")

        # Schedule rotation
        schedule.every(days).days.do(rotation_job)

        # Schedule expiration notifications
        def check_expirations():
            expiring = self.get_upcoming_expirations(hours_before/24)
            for key in expiring:
                self._notify(key, "expiration_warning")

        schedule.every().hour.do(check_expirations)

    def validate_key(self, key_id: str, required_permission: str = None) -> bool:
        key = self.get_key(key_id)
        if not key:
            return False
        
        # Check if key is active and not revoked
        if not key.get("is_active", False) or key.get("is_revoked", False):
            return False
        
        # Check if key is expired
        if datetime.fromisoformat(key["expires_at"]) < datetime.utcnow():
            return False
        
        # Check permission if specified
        if required_permission:
            permissions = key.get("permissions", [])
            if "*" not in permissions and required_permission not in permissions:
                return False

        return True