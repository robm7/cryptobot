import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from auth_pb2 import KeyResponse, ListKeysResponse, RevokeKeyResponse
from auth_service.auth_service import AuthService

class TestAuthService:
    def test_get_current_key_success(self, auth_service, redis_client):
        """Test successful current key retrieval"""
        test_key = {
            "id": "test123",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "is_active": True,
            "is_revoked": False,
            "version": 1,
            "permissions": ["read", "write"]
        }
        redis_client.hset("keys:current", mapping=test_key)
        
        response = auth_service.GetCurrentKey(None, None)
        assert isinstance(response, KeyResponse)
        assert response.key_id == "test123"
        assert response.is_active is True

    def test_get_current_key_not_found(self, auth_service):
        """Test current key not found case"""
        mock_context = MagicMock()
        response = auth_service.GetCurrentKey(None, mock_context)
        assert isinstance(response, KeyResponse)
        assert mock_context.set_code.called_with(grpc.StatusCode.NOT_FOUND)

    def test_rotate_key_success(self, auth_service):
        """Test successful key rotation"""
        mock_context = MagicMock()
        request = MagicMock()
        request.expire_in_days = 30
        
        response = auth_service.RotateKey(request, mock_context)
        assert isinstance(response, KeyResponse)
        assert response.key_id is not None
        assert response.is_active is True

    def test_rotate_key_failure(self, auth_service):
        """Test key rotation failure"""
        mock_context = MagicMock()
        request = MagicMock()
        request.expire_in_days = 30
        
        # Force error by making key_manager return None
        auth_service.key_manager.rotate_keys = MagicMock(return_value=None)
        
        response = auth_service.RotateKey(request, mock_context)
        assert isinstance(response, KeyResponse)
        assert mock_context.set_code.called_with(grpc.StatusCode.INTERNAL)

    def test_list_keys(self, auth_service, redis_client):
        """Test listing all keys"""
        # Setup test keys
        key1 = {"id": "key1", "is_active": True}
        key2 = {"id": "key2", "is_active": False}
        redis_client.hset("keys:key1", mapping=key1)
        redis_client.hset("keys:key2", mapping=key2)
        
        response = auth_service.ListKeys(None, None)
        assert isinstance(response, ListKeysResponse)
        assert len(response.keys) == 2
        assert {k.key_id for k in response.keys} == {"key1", "key2"}

    def test_revoke_key(self, auth_service, redis_client):
        """Test key revocation"""
        test_key = {"id": "revokeme", "is_revoked": False}
        redis_client.hset("keys:revokeme", mapping=test_key)
        
        request = MagicMock()
        request.key_id = "revokeme"
        response = auth_service.RevokeKey(request, None)
        
        assert isinstance(response, RevokeKeyResponse)
        assert response.success is True
        assert redis_client.hget("keys:revokeme", "is_revoked") == "True"