"""
Authentication and Authorization Integration Tests

This module contains integration tests for the authentication and authorization workflow
in the Cryptobot system. It tests user authentication, API key management, and permission checks.
"""

import pytest
import asyncio
import logging
import json
import os
import sys
import jwt
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.framework.base import IntegrationTestBase
from tests.integration.framework.container import ServiceContainer
from tests.integration.framework.mocks import MockDatabaseService, MockRedisService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockAuthService:
    """Mock authentication service for testing"""
    
    def __init__(self, database, redis):
        """Initialize with dependencies"""
        self.database = database
        self.redis = redis
        self.jwt_secret = "test_jwt_secret"
        self.token_expiry = 3600  # 1 hour
        self.refresh_token_expiry = 86400  # 24 hours
        
        # Set up some test users
        self.database.insert("users", {
            "id": 1,
            "username": "test_user",
            "email": "test@example.com",
            "password_hash": self._hash_password("password123"),
            "role": "user",
            "created_at": datetime.now().isoformat()
        })
        
        self.database.insert("users", {
            "id": 2,
            "username": "admin_user",
            "email": "admin@example.com",
            "password_hash": self._hash_password("admin123"),
            "role": "admin",
            "created_at": datetime.now().isoformat()
        })
    
    def _hash_password(self, password):
        """Simple password hashing for testing"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password, password_hash):
        """Verify password against hash"""
        return self._hash_password(password) == password_hash
    
    async def authenticate_user(self, username, password):
        """Authenticate user with username and password"""
        # Find user in database
        user = None
        users = self.database.query("users", {"username": username})
        
        if users and len(users) > 0:
            user = users[0]
        
        if not user:
            return None
        
        # Verify password
        if not self._verify_password(password, user["password_hash"]):
            return None
        
        return user
    
    async def create_tokens(self, user_id):
        """Create access and refresh tokens for user"""
        # Get user from database
        users = self.database.query("users", {"id": user_id})
        
        if not users or len(users) == 0:
            return None, None
        
        user = users[0]
        
        # Create access token
        access_token_payload = {
            "sub": str(user["id"]),
            "username": user["username"],
            "role": user["role"],
            "exp": datetime.now() + timedelta(seconds=self.token_expiry)
        }
        
        access_token = jwt.encode(
            access_token_payload,
            self.jwt_secret,
            algorithm="HS256"
        )
        
        # Create refresh token
        refresh_token_payload = {
            "sub": str(user["id"]),
            "exp": datetime.now() + timedelta(seconds=self.refresh_token_expiry)
        }
        
        refresh_token = jwt.encode(
            refresh_token_payload,
            self.jwt_secret,
            algorithm="HS256"
        )
        
        # Store refresh token in Redis
        self.redis.set(
            f"refresh_token:{user['id']}",
            refresh_token,
            ex=self.refresh_token_expiry
        )
        
        return access_token, refresh_token
    
    async def verify_token(self, token):
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    async def refresh_access_token(self, refresh_token):
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=["HS256"])
            user_id = payload["sub"]
            
            # Check if refresh token is in Redis
            stored_token = self.redis.get(f"refresh_token:{user_id}")
            
            if not stored_token or stored_token != refresh_token:
                return None
            
            # Create new access token
            users = self.database.query("users", {"id": int(user_id)})
            
            if not users or len(users) == 0:
                return None
            
            user = users[0]
            
            access_token_payload = {
                "sub": str(user["id"]),
                "username": user["username"],
                "role": user["role"],
                "exp": datetime.now() + timedelta(seconds=self.token_expiry)
            }
            
            access_token = jwt.encode(
                access_token_payload,
                self.jwt_secret,
                algorithm="HS256"
            )
            
            return access_token
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class MockAPIKeyManager:
    """Mock API key manager for testing"""
    
    def __init__(self, database):
        """Initialize with dependencies"""
        self.database = database
        
        # Set up some test API keys
        self.database.insert("api_keys", {
            "id": 1,
            "user_id": 1,
            "key": "test_api_key_1",
            "secret": "test_api_secret_1",
            "exchange": "binance",
            "permissions": ["read", "trade"],
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "last_used": None,
            "is_active": True
        })
        
        self.database.insert("api_keys", {
            "id": 2,
            "user_id": 1,
            "key": "test_api_key_2",
            "secret": "test_api_secret_2",
            "exchange": "kraken",
            "permissions": ["read"],
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "last_used": None,
            "is_active": True
        })
    
    async def create_api_key(self, user_id, exchange, permissions):
        """Create a new API key for user"""
        import uuid
        
        # Generate key and secret
        key = f"api_{uuid.uuid4().hex[:16]}"
        secret = f"secret_{uuid.uuid4().hex}"
        
        # Store in database
        api_key_id = self.database.insert("api_keys", {
            "user_id": user_id,
            "key": key,
            "secret": secret,
            "exchange": exchange,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "last_used": None,
            "is_active": True
        })
        
        return {
            "id": api_key_id,
            "key": key,
            "secret": secret,
            "exchange": exchange,
            "permissions": permissions
        }
    
    async def verify_api_key(self, key, secret=None):
        """Verify API key and optionally secret"""
        # Find API key in database
        api_keys = self.database.query("api_keys", {"key": key})
        
        if not api_keys or len(api_keys) == 0:
            return None
        
        api_key = api_keys[0]
        
        # Check if key is active
        if not api_key["is_active"]:
            return None
        
        # Check if key has expired
        expires_at = datetime.fromisoformat(api_key["expires_at"])
        if expires_at < datetime.now():
            return None
        
        # Check secret if provided
        if secret and api_key["secret"] != secret:
            return None
        
        # Update last used timestamp
        self.database.update("api_keys", api_key["id"], {
            "last_used": datetime.now().isoformat()
        })
        
        return api_key
    
    async def get_user_api_keys(self, user_id):
        """Get all API keys for user"""
        return self.database.query("api_keys", {"user_id": user_id})
    
    async def revoke_api_key(self, key_id, user_id):
        """Revoke API key"""
        # Find API key in database
        api_keys = self.database.query("api_keys", {"id": key_id})
        
        if not api_keys or len(api_keys) == 0:
            return False
        
        api_key = api_keys[0]
        
        # Check if key belongs to user
        if api_key["user_id"] != user_id:
            return False
        
        # Revoke key
        self.database.update("api_keys", key_id, {
            "is_active": False
        })
        
        return True


class MockPermissionManager:
    """Mock permission manager for testing"""
    
    def __init__(self, database):
        """Initialize with dependencies"""
        self.database = database
        
        # Set up role permissions
        self.role_permissions = {
            "admin": ["read", "write", "trade", "admin"],
            "user": ["read", "write", "trade"],
            "readonly": ["read"]
        }
        
        # Set up resource permissions
        self.resource_permissions = {
            "strategy": {
                "create": ["write"],
                "read": ["read"],
                "update": ["write"],
                "delete": ["write"],
                "execute": ["trade"]
            },
            "trade": {
                "create": ["trade"],
                "read": ["read"],
                "cancel": ["trade"]
            },
            "user": {
                "create": ["admin"],
                "read": ["admin"],
                "update": ["admin"],
                "delete": ["admin"]
            }
        }
    
    async def check_permission(self, user_id, resource, action):
        """Check if user has permission to perform action on resource"""
        # Get user from database
        users = self.database.query("users", {"id": user_id})
        
        if not users or len(users) == 0:
            return False
        
        user = users[0]
        
        # Get user role
        role = user["role"]
        
        # Get role permissions
        if role not in self.role_permissions:
            return False
        
        user_permissions = self.role_permissions[role]
        
        # Get resource permissions
        if resource not in self.resource_permissions:
            return False
        
        resource_actions = self.resource_permissions[resource]
        
        if action not in resource_actions:
            return False
        
        required_permissions = resource_actions[action]
        
        # Check if user has all required permissions
        for permission in required_permissions:
            if permission not in user_permissions:
                return False
        
        return True


class TestAuthIntegration(IntegrationTestBase):
    """
    Integration tests for the authentication and authorization workflow.
    
    These tests verify that the authentication and authorization system works correctly
    with user authentication, API key management, and permission checks.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        super().setup_class()
        
        # Create service container
        cls.container = ServiceContainer()
        
        # Register mock services
        cls.container.register_instance("database", MockDatabaseService("test_db"))
        cls.container.register_instance("redis", MockRedisService("test_redis"))
        
        # Start mock services
        cls.container.get("database").start()
        cls.container.get("redis").start()
        
        # Create auth service
        cls.auth_service = MockAuthService(
            cls.container.get("database"),
            cls.container.get("redis")
        )
        
        # Create API key manager
        cls.api_key_manager = MockAPIKeyManager(cls.container.get("database"))
        
        # Create permission manager
        cls.permission_manager = MockPermissionManager(cls.container.get("database"))
        
        # Add to services started list for cleanup
        cls.services_started = ["database", "redis"]
    
    @classmethod
    def teardown_class(cls):
        """Tear down the test class."""
        # Stop mock services
        for service_name in reversed(cls.services_started):
            service = cls.container.get(service_name)
            service.stop()
        
        # Reset container
        cls.container.reset()
        
        super().teardown_class()
    
    @pytest.mark.integration
    async def test_user_authentication(self):
        """Test user authentication with username and password."""
        # Test successful authentication
        user = await self.auth_service.authenticate_user("test_user", "password123")
        assert user is not None
        assert user["username"] == "test_user"
        assert user["role"] == "user"
        
        # Test failed authentication with wrong password
        user = await self.auth_service.authenticate_user("test_user", "wrong_password")
        assert user is None
        
        # Test failed authentication with non-existent user
        user = await self.auth_service.authenticate_user("non_existent_user", "password123")
        assert user is None
    
    @pytest.mark.integration
    async def test_token_creation_and_verification(self):
        """Test creation and verification of JWT tokens."""
        # Create tokens for user
        access_token, refresh_token = await self.auth_service.create_tokens(1)
        assert access_token is not None
        assert refresh_token is not None
        
        # Verify access token
        payload = await self.auth_service.verify_token(access_token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "test_user"
        assert payload["role"] == "user"
        
        # Verify refresh token
        payload = await self.auth_service.verify_token(refresh_token)
        assert payload is not None
        assert payload["sub"] == "1"
    
    @pytest.mark.integration
    async def test_token_refresh(self):
        """Test refreshing access token with refresh token."""
        # Create tokens for user
        access_token, refresh_token = await self.auth_service.create_tokens(1)
        
        # Refresh access token
        new_access_token = await self.auth_service.refresh_access_token(refresh_token)
        assert new_access_token is not None
        
        # Verify new access token
        payload = await self.auth_service.verify_token(new_access_token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["username"] == "test_user"
        assert payload["role"] == "user"
    
    @pytest.mark.integration
    async def test_api_key_management(self):
        """Test API key management."""
        # Create new API key
        api_key = await self.api_key_manager.create_api_key(
            user_id=1,
            exchange="coinbase",
            permissions=["read", "trade"]
        )
        assert api_key is not None
        assert api_key["exchange"] == "coinbase"
        assert "read" in api_key["permissions"]
        assert "trade" in api_key["permissions"]
        
        # Verify API key
        verified_key = await self.api_key_manager.verify_api_key(
            api_key["key"],
            api_key["secret"]
        )
        assert verified_key is not None
        assert verified_key["exchange"] == "coinbase"
        
        # Get user API keys
        user_keys = await self.api_key_manager.get_user_api_keys(1)
        assert len(user_keys) >= 3  # 2 initial keys + 1 new key
        
        # Revoke API key
        revoked = await self.api_key_manager.revoke_api_key(api_key["id"], 1)
        assert revoked is True
        
        # Verify revoked key
        verified_key = await self.api_key_manager.verify_api_key(
            api_key["key"],
            api_key["secret"]
        )
        assert verified_key is None
    
    @pytest.mark.integration
    async def test_permission_checks(self):
        """Test permission checks for different user roles."""
        # Test admin permissions
        admin_id = 2
        
        # Admin should have permission to create users
        has_permission = await self.permission_manager.check_permission(
            admin_id, "user", "create"
        )
        assert has_permission is True
        
        # Admin should have permission to execute trades
        has_permission = await self.permission_manager.check_permission(
            admin_id, "trade", "create"
        )
        assert has_permission is True
        
        # Test regular user permissions
        user_id = 1
        
        # User should not have permission to create users
        has_permission = await self.permission_manager.check_permission(
            user_id, "user", "create"
        )
        assert has_permission is False
        
        # User should have permission to execute trades
        has_permission = await self.permission_manager.check_permission(
            user_id, "trade", "create"
        )
        assert has_permission is True
        
        # User should have permission to create strategies
        has_permission = await self.permission_manager.check_permission(
            user_id, "strategy", "create"
        )
        assert has_permission is True
    
    @pytest.mark.integration
    async def test_end_to_end_auth_workflow(self):
        """Test end-to-end authentication workflow."""
        # Step 1: User logs in
        user = await self.auth_service.authenticate_user("test_user", "password123")
        assert user is not None
        
        # Step 2: System creates tokens
        access_token, refresh_token = await self.auth_service.create_tokens(user["id"])
        assert access_token is not None
        assert refresh_token is not None
        
        # Step 3: User makes authenticated request
        # Simulate by verifying token and checking permissions
        payload = await self.auth_service.verify_token(access_token)
        assert payload is not None
        
        user_id = int(payload["sub"])
        has_permission = await self.permission_manager.check_permission(
            user_id, "strategy", "create"
        )
        assert has_permission is True
        
        # Step 4: User creates API key for exchange
        api_key = await self.api_key_manager.create_api_key(
            user_id=user_id,
            exchange="binance",
            permissions=["read", "trade"]
        )
        assert api_key is not None
        
        # Step 5: System uses API key for exchange operations
        verified_key = await self.api_key_manager.verify_api_key(
            api_key["key"],
            api_key["secret"]
        )
        assert verified_key is not None
        
        # Step 6: Access token expires, user refreshes
        # Simulate token expiration by creating new refresh
        new_access_token = await self.auth_service.refresh_access_token(refresh_token)
        assert new_access_token is not None
        
        # Step 7: User continues with new access token
        payload = await self.auth_service.verify_token(new_access_token)
        assert payload is not None
        
        user_id = int(payload["sub"])
        has_permission = await self.permission_manager.check_permission(
            user_id, "trade", "create"
        )
        assert has_permission is True


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])