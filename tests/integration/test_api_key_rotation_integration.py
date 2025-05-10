"""
Integration tests for the API Key Rotation System

These tests verify that the KeyManager works correctly with Redis
and other components of the system.
"""

import pytest
import asyncio
import logging
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import json
import uuid
import redis

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from auth.key_manager import KeyManager, KeyStatus
from auth.background_tasks import KeyRotationTasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestRedisIntegration:
    """Test Redis integration with KeyManager"""
    
    @pytest.fixture
    def redis_client(self):
        """Create a Redis client for testing"""
        # Use a dedicated database for testing
        client = redis.Redis(
            host="localhost",
            port=6379,
            db=15,  # Use DB 15 for testing
            decode_responses=True
        )
        
        # Clear the database before each test
        client.flushdb()
        
        yield client
        
        # Clean up after tests
        client.flushdb()
        client.close()
    
    @pytest.fixture
    def db_session(self):
        """Create a mock DB session"""
        session = MagicMock()
        return session
    
    @pytest.fixture
    def key_manager(self, db_session, redis_client):
        """Create a KeyManager instance with real Redis"""
        # Patch get_redis_connection to return our test Redis client
        with patch('auth.key_manager.get_redis_connection') as mock_get_redis:
            # Create a context manager that returns our Redis client
            mock_context = MagicMock()
            mock_context.__enter__.return_value = redis_client
            mock_get_redis.return_value = mock_context
            
            # Create KeyManager
            manager = KeyManager(db_session)
            
            yield manager
    
    @pytest.fixture
    def rotation_tasks(self, db_session, key_manager):
        """Create a KeyRotationTasks instance"""
        tasks = KeyRotationTasks(db_session)
        tasks.key_manager = key_manager
        return tasks
    
    @pytest.mark.asyncio
    async def test_create_and_get_key(self, key_manager, redis_client):
        """Test creating a key and retrieving it from Redis"""
        # Create a key
        user_id = 123
        description = "Test Key"
        exchange = "binance"
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange
        )
        
        # Verify key was created
        assert key_data is not None
        assert key_data["description"] == description
        assert key_data["exchange"] == exchange
        assert key_data["user_id"] == user_id
        
        # Get the key directly from Redis
        key_id = key_data["id"]
        redis_key = f"{key_manager.KEY_PREFIX}{key_id}"
        stored_data = redis_client.get(redis_key)
        
        # Verify data was stored in Redis
        assert stored_data is not None
        stored_key = json.loads(stored_data)
        assert stored_key["id"] == key_id
        assert stored_key["description"] == description
        
        # Verify key was added to user's keys
        user_keys_key = f"{key_manager.USER_KEYS_PREFIX}{user_id}"
        user_keys = redis_client.smembers(user_keys_key)
        assert key_id in user_keys
        
        # Get the key using KeyManager
        retrieved_key = key_manager.get_key(key_id)
        assert retrieved_key is not None
        assert retrieved_key["id"] == key_id
        assert retrieved_key["description"] == description
    
    @pytest.mark.asyncio
    async def test_key_rotation_with_redis(self, key_manager, redis_client):
        """Test key rotation with Redis persistence"""
        # Create a key
        user_id = 123
        description = "Rotation Test Key"
        exchange = "binance"
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange
        )
        key_id = key_data["id"]
        
        # Rotate the key
        new_key = key_manager.rotate_key(
            key_id=key_id,
            user_id=user_id,
            grace_period_hours=24
        )
        
        # Verify new key
        assert new_key is not None
        assert new_key["description"] == description
        assert new_key["exchange"] == exchange
        assert new_key["user_id"] == user_id
        assert new_key["status"] == KeyStatus.ACTIVE
        assert new_key["version"] == 2
        assert new_key["previous_key_id"] == key_id
        
        # Get the old key from Redis
        old_key_data = redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}")
        assert old_key_data is not None
        old_key = json.loads(old_key_data)
        
        # Verify old key status
        assert old_key["status"] == KeyStatus.ROTATING
        assert "rotated_at" in old_key
        assert "grace_period_ends" in old_key
        assert old_key["next_key_id"] == new_key["id"]
        
        # Verify version history in Redis
        version_key = f"{key_manager.VERSION_PREFIX}{exchange}:{user_id}"
        versions = redis_client.hgetall(version_key)
        assert versions["1"] == key_id
        assert versions["2"] == new_key["id"]
        
        # Get user keys
        user_keys = key_manager.get_user_keys(user_id)
        assert len(user_keys) == 2
        
        # Verify key history
        history = key_manager.get_key_history(exchange, user_id)
        assert len(history) == 2
        versions = [k["version"] for k in history]
        assert 1 in versions
        assert 2 in versions
    
    @pytest.mark.asyncio
    async def test_expiring_keys_with_redis(self, key_manager, redis_client):
        """Test expiring keys functionality with Redis"""
        # Create keys with different expiration dates
        user_id = 123
        
        # Key 1: Expires in 5 days
        key1 = key_manager.create_key(
            user_id=user_id,
            description="Expiring Soon",
            exchange="binance",
            expiry_days=5
        )
        
        # Key 2: Expires in 20 days
        key2 = key_manager.create_key(
            user_id=user_id,
            description="Not Expiring Soon",
            exchange="kraken",
            expiry_days=20
        )
        
        # Get keys expiring within 7 days
        expiring_keys = key_manager.get_expiring_keys(days_threshold=7)
        
        # Verify only the first key is returned
        assert len(expiring_keys) == 1
        assert expiring_keys[0]["id"] == key1["id"]
        
        # Verify expiring keys in Redis sorted set
        expiring_keys_set = key_manager.EXPIRING_KEYS_PREFIX
        keys_in_set = redis_client.zrange(expiring_keys_set, 0, -1)
        assert key1["id"] in keys_in_set
        assert key2["id"] in keys_in_set
    
    @pytest.mark.asyncio
    async def test_process_expired_keys(self, key_manager, redis_client):
        """Test processing expired keys"""
        # Create a key
        user_id = 123
        key_data = key_manager.create_key(
            user_id=user_id,
            description="Expired Key",
            exchange="binance",
            expiry_days=30
        )
        key_id = key_data["id"]
        
        # Manually set expiration to the past
        key_data = json.loads(redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}"))
        key_data["expires_at"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        redis_client.set(f"{key_manager.KEY_PREFIX}{key_id}", json.dumps(key_data))
        
        # Update expiry timestamp in sorted set
        redis_client.zadd(
            key_manager.EXPIRING_KEYS_PREFIX,
            {key_id: (datetime.utcnow() - timedelta(days=1)).timestamp()}
        )
        
        # Process expired keys
        processed_count = key_manager.process_expired_keys()
        
        # Verify key was processed
        assert processed_count == 1
        
        # Verify key was marked as expired
        updated_key = key_manager.get_key(key_id)
        assert updated_key["status"] == KeyStatus.EXPIRED
        assert "expired_at" in updated_key
    
    @pytest.mark.asyncio
    async def test_grace_period_expiration(self, key_manager, redis_client):
        """Test grace period expiration"""
        # Create a key
        user_id = 123
        key_data = key_manager.create_key(
            user_id=user_id,
            description="Grace Period Test",
            exchange="binance"
        )
        key_id = key_data["id"]
        
        # Rotate the key with a short grace period
        new_key = key_manager.rotate_key(
            key_id=key_id,
            user_id=user_id,
            grace_period_hours=0.01  # Very short grace period for testing
        )
        
        # Verify old key is in ROTATING state
        old_key = key_manager.get_key(key_id)
        assert old_key["status"] == KeyStatus.ROTATING
        
        # Wait for grace period to end
        await asyncio.sleep(0.02)
        
        # Process expired keys
        processed_count = key_manager.process_expired_keys()
        
        # Verify key was processed
        assert processed_count >= 1
        
        # Verify old key is now EXPIRED
        updated_old_key = key_manager.get_key(key_id)
        assert updated_old_key["status"] == KeyStatus.EXPIRED
    
    @pytest.mark.asyncio
    async def test_background_tasks(self, rotation_tasks, key_manager):
        """Test background tasks for key rotation"""
        # Create keys with different expiration dates
        user_id = 123
        
        # Key 1: Expires in 2 days
        key1 = key_manager.create_key(
            user_id=user_id,
            description="Expiring Very Soon",
            exchange="binance",
            expiry_days=2
        )
        
        # Key 2: Expires in 10 days
        key2 = key_manager.create_key(
            user_id=user_id,
            description="Not Expiring Soon",
            exchange="kraken",
            expiry_days=10
        )
        
        # Mock the email service
        rotation_tasks.email_service = MagicMock()
        rotation_tasks.email_service.send_key_expiration_email = AsyncMock()
        
        # Run expiration check
        await rotation_tasks.run_expiration_check(interval_seconds=0)
        
        # Run notification check
        await rotation_tasks.run_notification_check(interval_seconds=0)
        
        # Verify expiring keys were detected
        expiring_keys = key_manager.get_expiring_keys(days_threshold=7)
        assert len(expiring_keys) == 1
        assert expiring_keys[0]["id"] == key1["id"]
        
        # Test auto-rotation
        with patch.object(rotation_tasks, 'send_rotation_notification', AsyncMock()):
            rotated_count = await rotation_tasks.rotate_expiring_keys(days_threshold=3)
            
            # Verify key was rotated
            assert rotated_count == 1
            
            # Get user keys
            user_keys = key_manager.get_user_keys(user_id)
            
            # Should have 3 keys now (2 original + 1 rotated)
            assert len(user_keys) == 3
            
            # Verify one key is in ROTATING state
            rotating_keys = [k for k in user_keys if k["status"] == KeyStatus.ROTATING]
            assert len(rotating_keys) == 1
            assert rotating_keys[0]["id"] == key1["id"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])