"""
Integration tests for the enhanced API Key Rotation System

These tests verify that the enhanced KeyManager works correctly with Redis
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
from auth.scheduled_jobs import KeyRotationScheduler
from auth.redis_service import RedisService
from auth.models.audit_log import AuditLog
from fastapi import Request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEnhancedKeyRotationSystem:
    """Test the enhanced API Key Rotation System"""
    
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
        
        # Mock the AuditLog.create_from_request method
        AuditLog.create_from_request = MagicMock()
        
        return session
    
    @pytest.fixture
    def key_manager(self, db_session, redis_client):
        """Create a KeyManager instance with real Redis"""
        # Patch get_redis_connection to return our test Redis client
        with patch('auth.redis_service.get_redis_connection') as mock_get_redis:
            # Create a context manager that returns our Redis client
            mock_context = MagicMock()
            mock_context.__enter__.return_value = redis_client
            mock_get_redis.return_value = mock_context
            
            # Create KeyManager
            manager = KeyManager(db_session)
            
            yield manager
    
    @pytest.fixture
    def rotation_scheduler(self, db_session, key_manager):
        """Create a KeyRotationScheduler instance"""
        scheduler = KeyRotationScheduler(db_session)
        scheduler.key_manager = key_manager
        scheduler.email_service = AsyncMock()
        return scheduler
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock Request object"""
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.headers = {"user-agent": "Test User Agent"}
        return request
    
    @pytest.mark.asyncio
    async def test_create_key_with_enhanced_features(self, key_manager, redis_client, mock_request):
        """Test creating a key with enhanced features"""
        # Create a key with custom permissions and IP restrictions
        user_id = 123
        description = "Enhanced Test Key"
        exchange = "binance"
        permissions = ["read", "trade", "withdraw"]
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange,
            permissions=permissions,
            request=mock_request
        )
        
        # Verify key was created
        assert key_data is not None
        assert key_data["description"] == description
        assert key_data["exchange"] == exchange
        assert key_data["user_id"] == user_id
        assert key_data["permissions"] == permissions
        assert key_data["metadata"]["created_from_ip"] == mock_request.client.host
        
        # Verify key was stored in Redis
        key_id = key_data["id"]
        redis_key = f"{key_manager.KEY_PREFIX}{key_id}"
        stored_data = redis_client.get(redis_key)
        assert stored_data is not None
        
        # Verify key was added to user's keys
        user_keys_key = f"{key_manager.USER_KEYS_PREFIX}{user_id}"
        user_keys = redis_client.smembers(user_keys_key)
        assert key_id in user_keys
        
        # Verify key was added to exchange keys
        exchange_keys_key = f"{key_manager.EXCHANGE_KEYS_PREFIX}{exchange}"
        exchange_keys = redis_client.smembers(exchange_keys_key)
        assert key_id in exchange_keys
        
        # Verify permissions were stored
        permission_key = f"{key_manager.PERMISSION_PREFIX}{key_id}"
        stored_permissions = redis_client.smembers(permission_key)
        for permission in permissions:
            assert permission in stored_permissions
        
        # Verify audit log was created
        AuditLog.create_from_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_key_rotation_with_enhanced_features(self, key_manager, redis_client, mock_request):
        """Test key rotation with enhanced features"""
        # Create a key
        user_id = 123
        description = "Rotation Test Key"
        exchange = "binance"
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange,
            request=mock_request
        )
        key_id = key_data["id"]
        
        # Reset the mock to clear the create_key call
        AuditLog.create_from_request.reset_mock()
        
        # Rotate the key
        new_key = key_manager.rotate_key(
            key_id=key_id,
            user_id=user_id,
            grace_period_hours=24,
            request=mock_request
        )
        
        # Verify new key
        assert new_key is not None
        assert new_key["description"] == description
        assert new_key["exchange"] == exchange
        assert new_key["user_id"] == user_id
        assert new_key["status"] == KeyStatus.ACTIVE
        assert new_key["version"] == 2
        assert new_key["previous_key_id"] == key_id
        assert new_key["metadata"]["rotated_from_ip"] == mock_request.client.host
        
        # Verify old key status
        old_key_data = redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}")
        assert old_key_data is not None
        old_key = json.loads(old_key_data)
        assert old_key["status"] == KeyStatus.ROTATING
        assert "rotated_at" in old_key
        assert "grace_period_ends" in old_key
        assert old_key["next_key_id"] == new_key["id"]
        
        # Verify new key was added to exchange keys
        exchange_keys_key = f"{key_manager.EXCHANGE_KEYS_PREFIX}{exchange}"
        exchange_keys = redis_client.smembers(exchange_keys_key)
        assert new_key["id"] in exchange_keys
        
        # Verify permissions were copied
        permission_key = f"{key_manager.PERMISSION_PREFIX}{new_key['id']}"
        stored_permissions = redis_client.smembers(permission_key)
        for permission in new_key["permissions"]:
            assert permission in stored_permissions
        
        # Verify audit log was created
        AuditLog.create_from_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_key_with_enhanced_features(self, key_manager, redis_client, mock_request):
        """Test revoking a key with enhanced features"""
        # Create a key
        user_id = 123
        description = "Revocation Test Key"
        exchange = "binance"
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange,
            request=mock_request
        )
        key_id = key_data["id"]
        
        # Reset the mock to clear the create_key call
        AuditLog.create_from_request.reset_mock()
        
        # Revoke the key
        reason = "Security policy"
        success = key_manager.revoke_key(
            key_id=key_id,
            user_id=user_id,
            reason=reason,
            request=mock_request
        )
        
        # Verify revocation
        assert success is True
        
        # Verify key status
        key_data = redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}")
        assert key_data is not None
        key = json.loads(key_data)
        assert key["status"] == KeyStatus.REVOKED
        assert "revoked_at" in key
        assert key["revocation_reason"] == reason
        assert key["revoked_by"] == user_id
        assert key["revoked_from_ip"] == mock_request.client.host
        
        # Verify audit log was created
        AuditLog.create_from_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_key_compromised_with_enhanced_features(self, key_manager, redis_client, mock_request):
        """Test marking a key as compromised with enhanced features"""
        # Create a key
        user_id = 123
        description = "Compromise Test Key"
        exchange = "binance"
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange,
            request=mock_request
        )
        key_id = key_data["id"]
        
        # Reset the mock to clear the create_key call
        AuditLog.create_from_request.reset_mock()
        
        # Mark as compromised
        details = "Suspicious activity detected"
        success = key_manager.mark_key_compromised(
            key_id=key_id,
            user_id=user_id,
            details=details,
            request=mock_request
        )
        
        # Verify operation
        assert success is True
        
        # Verify key status
        key_data = redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}")
        assert key_data is not None
        key = json.loads(key_data)
        assert key["status"] == KeyStatus.COMPROMISED
        assert "compromised_at" in key
        assert key["compromise_details"] == details
        assert key["reported_by"] == user_id
        assert key["reported_from_ip"] == mock_request.client.host
        
        # Verify audit log was created with critical severity
        AuditLog.create_from_request.assert_called_once()
        call_args = AuditLog.create_from_request.call_args[1]
        assert call_args["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_validate_key_with_ip_restrictions(self, key_manager, redis_client, mock_request):
        """Test validating a key with IP restrictions"""
        # Create a key with IP restrictions
        user_id = 123
        description = "IP Restricted Key"
        exchange = "binance"
        
        key_data = key_manager.create_key(
            user_id=user_id,
            description=description,
            exchange=exchange,
            request=mock_request
        )
        key_id = key_data["id"]
        api_key = key_data["key"]
        
        # Add IP restrictions
        key_data["ip_restrictions"] = ["10.0.0.1", "192.168.1.2"]
        redis_client.set(f"{key_manager.KEY_PREFIX}{key_id}", json.dumps(key_data))
        
        # Reset the mock to clear the create_key call
        AuditLog.create_from_request.reset_mock()
        
        # Validate with unauthorized IP
        mock_request.client.host = "192.168.1.3"  # Not in allowed IPs
        is_valid, validated_key = key_manager.validate_key(api_key, mock_request)
        
        # Verify validation failed due to IP restriction
        assert is_valid is False
        
        # Verify audit log was created for unauthorized access
        AuditLog.create_from_request.assert_called_once()
        call_args = AuditLog.create_from_request.call_args[1]
        assert call_args["action"] == "api_key_unauthorized_ip"
        assert call_args["severity"] == "high"
        
        # Reset the mock
        AuditLog.create_from_request.reset_mock()
        
        # Validate with authorized IP
        mock_request.client.host = "192.168.1.2"  # In allowed IPs
        is_valid, validated_key = key_manager.validate_key(api_key, mock_request)
        
        # Verify validation succeeded
        assert is_valid is True
        assert validated_key is not None
        assert validated_key["id"] == key_id
        
        # Verify usage tracking
        assert validated_key["usage_count"] == 1
        assert "usage_metadata" in validated_key
        assert "ip_addresses" in validated_key["usage_metadata"]
        assert mock_request.client.host in validated_key["usage_metadata"]["ip_addresses"]
    
    @pytest.mark.asyncio
    async def test_scheduler_expiration_check(self, rotation_scheduler, key_manager, redis_client):
        """Test scheduler expiration check"""
        # Create a key that has already expired
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
        
        # Run expiration check
        await rotation_scheduler.run_expiration_check(interval_seconds=0)
        
        # Verify key was marked as expired
        updated_key = json.loads(redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}"))
        assert updated_key["status"] == KeyStatus.EXPIRED
        assert "expired_at" in updated_key
    
    @pytest.mark.asyncio
    async def test_scheduler_notification_check(self, rotation_scheduler, key_manager, redis_client):
        """Test scheduler notification check"""
        # Create a key expiring soon
        user_id = 123
        key_data = key_manager.create_key(
            user_id=user_id,
            description="Expiring Soon Key",
            exchange="binance",
            expiry_days=30
        )
        key_id = key_data["id"]
        
        # Manually set expiration to 7 days from now (one of the notification thresholds)
        key_data = json.loads(redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}"))
        key_data["expires_at"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
        redis_client.set(f"{key_manager.KEY_PREFIX}{key_id}", json.dumps(key_data))
        
        # Update expiry timestamp in sorted set
        redis_client.zadd(
            key_manager.EXPIRING_KEYS_PREFIX,
            {key_id: (datetime.utcnow() + timedelta(days=7)).timestamp()}
        )
        
        # Mock the User query
        user = MagicMock()
        user.username = "testuser"
        user.email = "test@example.com"
        rotation_scheduler.db.query.return_value.filter.return_value.first.return_value = user
        
        # Run notification check
        await rotation_scheduler.run_notification_check(interval_seconds=0)
        
        # Verify email service was called
        rotation_scheduler.email_service.send_key_expiration_email.assert_called_once()
        call_args = rotation_scheduler.email_service.send_key_expiration_email.call_args[1]
        assert call_args["email"] == "test@example.com"
        assert call_args["username"] == "testuser"
        assert len(call_args["keys"]) == 1
        assert call_args["days_left"] == 7
    
    @pytest.mark.asyncio
    async def test_scheduler_auto_rotation(self, rotation_scheduler, key_manager, redis_client):
        """Test scheduler auto rotation"""
        # Create a key expiring soon
        user_id = 123
        key_data = key_manager.create_key(
            user_id=user_id,
            description="Auto Rotation Key",
            exchange="binance",
            expiry_days=30
        )
        key_id = key_data["id"]
        
        # Manually set expiration to 5 days from now (within auto-rotation threshold)
        key_data = json.loads(redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}"))
        key_data["expires_at"] = (datetime.utcnow() + timedelta(days=5)).isoformat()
        redis_client.set(f"{key_manager.KEY_PREFIX}{key_id}", json.dumps(key_data))
        
        # Update expiry timestamp in sorted set
        redis_client.zadd(
            key_manager.EXPIRING_KEYS_PREFIX,
            {key_id: (datetime.utcnow() + timedelta(days=5)).timestamp()}
        )
        
        # Mock the User query
        user = MagicMock()
        user.username = "testuser"
        user.email = "test@example.com"
        rotation_scheduler.db.query.return_value.filter.return_value.first.return_value = user
        
        # Mock the get_keys_for_rotation method to return our key
        rotation_scheduler.get_keys_for_rotation = AsyncMock(return_value=[key_data])
        
        # Run auto rotation
        await rotation_scheduler.run_auto_rotation(interval_seconds=0)
        
        # Verify email service was called for rotation notification
        rotation_scheduler.email_service.send_key_rotation_email.assert_called_once()
        
        # Verify key was rotated
        user_keys = redis_client.smembers(f"{key_manager.USER_KEYS_PREFIX}{user_id}")
        assert len(user_keys) == 2  # Original key + new key
        
        # Verify original key is now in ROTATING status
        updated_key = json.loads(redis_client.get(f"{key_manager.KEY_PREFIX}{key_id}"))
        assert updated_key["status"] == KeyStatus.ROTATING
        assert "rotated_at" in updated_key
        assert "grace_period_ends" in updated_key
        assert "next_key_id" in updated_key

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])