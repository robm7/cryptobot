"""
Unit tests for the API Key Rotation System
"""

import unittest
import json
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.key_manager import KeyManager, KeyStatus
from auth.redis_service import get_redis_connection

class MockRedis:
    """Mock Redis for testing"""
    
    def __init__(self):
        self.data = {}
        self.sets = {}
        self.sorted_sets = {}
        self.hashes = {}
    
    def set(self, key, value):
        self.data[key] = value
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def keys(self, pattern):
        import fnmatch
        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]
    
    def sadd(self, key, value):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(value)
        return 1
    
    def smembers(self, key):
        return self.sets.get(key, set())
    
    def zadd(self, key, mapping):
        if key not in self.sorted_sets:
            self.sorted_sets[key] = {}
        self.sorted_sets[key].update(mapping)
        return len(mapping)
    
    def zrangebyscore(self, key, min_score, max_score):
        if key not in self.sorted_sets:
            return []
        return [k for k, v in self.sorted_sets[key].items() if min_score <= v <= max_score]
    
    def hset(self, key, field, value):
        if key not in self.hashes:
            self.hashes[key] = {}
        self.hashes[key][field] = value
        return 1
    
    def hgetall(self, key):
        return self.hashes.get(key, {})
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return 1
        return 0

class TestKeyManager(unittest.TestCase):
    """Test cases for KeyManager"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock Redis
        self.redis_mock = MockRedis()
        self.redis_patcher = patch('auth.key_manager.get_redis_connection')
        self.redis_mock_context = self.redis_patcher.start()
        self.redis_mock_context.return_value.__enter__.return_value = self.redis_mock
        
        # Mock DB session
        self.db_mock = MagicMock()
        
        # Create KeyManager instance
        self.key_manager = KeyManager(self.db_mock)
        
        # Test user
        self.user_id = 123
        self.exchange = "binance"
        self.description = "Test API Key"
    
    def tearDown(self):
        """Clean up after tests"""
        self.redis_patcher.stop()
    
    def test_create_key(self):
        """Test creating a new API key"""
        # Create key
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        
        # Verify key data
        self.assertIsNotNone(key_data)
        self.assertEqual(key_data["description"], self.description)
        self.assertEqual(key_data["exchange"], self.exchange)
        self.assertEqual(key_data["user_id"], self.user_id)
        self.assertEqual(key_data["status"], KeyStatus.ACTIVE)
        self.assertEqual(key_data["version"], 1)
        
        # Verify key was stored in Redis
        key_id = key_data["id"]
        redis_key = f"{self.key_manager.KEY_PREFIX}{key_id}"
        stored_data = self.redis_mock.get(redis_key)
        self.assertIsNotNone(stored_data)
        
        # Verify key was added to user's keys
        user_keys_key = f"{self.key_manager.USER_KEYS_PREFIX}{self.user_id}"
        user_keys = self.redis_mock.smembers(user_keys_key)
        self.assertIn(key_id, user_keys)
        
        # Verify key was added to expiring keys
        self.assertIn(key_id, self.redis_mock.sorted_sets.get(self.key_manager.EXPIRING_KEYS_PREFIX, {}))
        
        # Verify audit log was created
        self.db_mock.add.assert_called_once()
        self.db_mock.commit.assert_called_once()
    
    def test_get_key(self):
        """Test getting a key by ID"""
        # Create key
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        key_id = key_data["id"]
        
        # Get key
        retrieved_key = self.key_manager.get_key(key_id)
        
        # Verify key data
        self.assertIsNotNone(retrieved_key)
        self.assertEqual(retrieved_key["id"], key_id)
        self.assertEqual(retrieved_key["description"], self.description)
        self.assertEqual(retrieved_key["exchange"], self.exchange)
        self.assertEqual(retrieved_key["user_id"], self.user_id)
    
    def test_get_user_keys(self):
        """Test getting all keys for a user"""
        # Create multiple keys
        key1 = self.key_manager.create_key(
            user_id=self.user_id,
            description="Key 1",
            exchange="binance"
        )
        key2 = self.key_manager.create_key(
            user_id=self.user_id,
            description="Key 2",
            exchange="kraken"
        )
        
        # Get user keys
        user_keys = self.key_manager.get_user_keys(self.user_id)
        
        # Verify keys
        self.assertEqual(len(user_keys), 2)
        key_ids = [k["id"] for k in user_keys]
        self.assertIn(key1["id"], key_ids)
        self.assertIn(key2["id"], key_ids)
    
    def test_rotate_key(self):
        """Test rotating a key"""
        # Create key
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        key_id = key_data["id"]
        
        # Rotate key
        new_key = self.key_manager.rotate_key(
            key_id=key_id,
            user_id=self.user_id,
            grace_period_hours=24
        )
        
        # Verify new key
        self.assertIsNotNone(new_key)
        self.assertNotEqual(new_key["id"], key_id)
        self.assertEqual(new_key["description"], self.description)
        self.assertEqual(new_key["exchange"], self.exchange)
        self.assertEqual(new_key["user_id"], self.user_id)
        self.assertEqual(new_key["status"], KeyStatus.ACTIVE)
        self.assertEqual(new_key["version"], 2)
        self.assertEqual(new_key["previous_key_id"], key_id)
        
        # Verify old key was updated
        old_key = self.key_manager.get_key(key_id)
        self.assertEqual(old_key["status"], KeyStatus.ROTATING)
        self.assertIsNotNone(old_key.get("rotated_at"))
        self.assertIsNotNone(old_key.get("grace_period_ends"))
        self.assertEqual(old_key["next_key_id"], new_key["id"])
        
        # Verify version history
        version_key = f"{self.key_manager.VERSION_PREFIX}{self.exchange}:{self.user_id}"
        versions = self.redis_mock.hashes.get(version_key, {})
        self.assertEqual(versions.get("1"), key_id)
        self.assertEqual(versions.get("2"), new_key["id"])
    
    def test_revoke_key(self):
        """Test revoking a key"""
        # Create key
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        key_id = key_data["id"]
        
        # Revoke key
        reason = "Testing revocation"
        success = self.key_manager.revoke_key(
            key_id=key_id,
            user_id=self.user_id,
            reason=reason
        )
        
        # Verify revocation
        self.assertTrue(success)
        
        # Verify key was updated
        key = self.key_manager.get_key(key_id)
        self.assertEqual(key["status"], KeyStatus.REVOKED)
        self.assertIsNotNone(key.get("revoked_at"))
        self.assertEqual(key["revocation_reason"], reason)
    
    def test_mark_key_compromised(self):
        """Test marking a key as compromised"""
        # Create key
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        key_id = key_data["id"]
        
        # Mark as compromised
        details = "Security breach"
        success = self.key_manager.mark_key_compromised(
            key_id=key_id,
            user_id=self.user_id,
            details=details
        )
        
        # Verify operation
        self.assertTrue(success)
        
        # Verify key was updated
        key = self.key_manager.get_key(key_id)
        self.assertEqual(key["status"], KeyStatus.COMPROMISED)
        self.assertIsNotNone(key.get("compromised_at"))
        self.assertEqual(key["compromise_details"], details)
    
    def test_get_expiring_keys(self):
        """Test getting keys that are expiring soon"""
        # Create keys with different expiration dates
        # Key 1: Expires in 5 days
        key1 = self.key_manager.create_key(
            user_id=self.user_id,
            description="Expiring Soon",
            exchange="binance",
            expiry_days=5
        )
        
        # Key 2: Expires in 20 days
        key2 = self.key_manager.create_key(
            user_id=self.user_id,
            description="Not Expiring Soon",
            exchange="kraken",
            expiry_days=20
        )
        
        # Get keys expiring within 7 days
        expiring_keys = self.key_manager.get_expiring_keys(days_threshold=7)
        
        # Verify only the first key is returned
        self.assertEqual(len(expiring_keys), 1)
        self.assertEqual(expiring_keys[0]["id"], key1["id"])
    
    def test_process_expired_keys(self):
        """Test processing expired keys"""
        # Create a key that has already expired
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description="Expired Key",
            exchange=self.exchange,
            expiry_days=30
        )
        key_id = key_data["id"]
        
        # Manually set expiration to the past
        key_data = json.loads(self.redis_mock.get(f"{self.key_manager.KEY_PREFIX}{key_id}"))
        key_data["expires_at"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        self.redis_mock.set(f"{self.key_manager.KEY_PREFIX}{key_id}", json.dumps(key_data))
        
        # Update expiry timestamp in sorted set
        self.redis_mock.sorted_sets[self.key_manager.EXPIRING_KEYS_PREFIX][key_id] = (
            datetime.utcnow() - timedelta(days=1)
        ).timestamp()
        
        # Process expired keys
        processed_count = self.key_manager.process_expired_keys()
        
        # Verify key was processed
        self.assertEqual(processed_count, 1)
        
        # Verify key was marked as expired
        key = self.key_manager.get_key(key_id)
        self.assertEqual(key["status"], KeyStatus.EXPIRED)
        self.assertIsNotNone(key.get("expired_at"))
    
    def test_validate_key(self):
        """Test validating an API key"""
        # Create key
        key_data = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        api_key = key_data["key"]
        
        # Validate key
        is_valid, validated_key = self.key_manager.validate_key(api_key)
        
        # Verify validation
        self.assertTrue(is_valid)
        self.assertIsNotNone(validated_key)
        self.assertEqual(validated_key["id"], key_data["id"])
        
        # Verify last_used was updated
        self.assertIsNotNone(validated_key.get("last_used"))
        
        # Test invalid key
        is_valid, validated_key = self.key_manager.validate_key("invalid_key")
        self.assertFalse(is_valid)
        self.assertIsNone(validated_key)
    
    def test_get_key_history(self):
        """Test getting key version history"""
        # Create initial key
        key1 = self.key_manager.create_key(
            user_id=self.user_id,
            description=self.description,
            exchange=self.exchange
        )
        
        # Rotate key twice
        key2 = self.key_manager.rotate_key(
            key_id=key1["id"],
            user_id=self.user_id
        )
        
        key3 = self.key_manager.rotate_key(
            key_id=key2["id"],
            user_id=self.user_id
        )
        
        # Get key history
        history = self.key_manager.get_key_history(self.exchange, self.user_id)
        
        # Verify history
        self.assertEqual(len(history), 3)
        versions = [k["version"] for k in history]
        self.assertIn(1, versions)
        self.assertIn(2, versions)
        self.assertIn(3, versions)

if __name__ == "__main__":
    unittest.main()