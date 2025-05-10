import pytest
import grpc
from datetime import datetime, timedelta
from auth_pb2 import KeyRequest, ListKeysRequest, RevokeKeyRequest
from auth_pb2_grpc import KeyManagementServiceStub
from auth_service.auth_service import AuthService, serve
import threading
import time

@pytest.fixture(scope="module")
def grpc_server(redis_client):
    """Fixture to start gRPC test server"""
    server_thread = threading.Thread(
        target=serve,
        args=(redis_client,),
        kwargs={'port': 50052},
        daemon=True
    )
    server_thread.start()
    time.sleep(1)  # Wait for server to start
    yield
    # Server will be stopped when test module completes

@pytest.fixture(scope="module")
def grpc_channel(grpc_server):
    """Fixture for gRPC test channel"""
    channel = grpc.insecure_channel('localhost:50052')
    yield channel
    channel.close()

class TestGrpcEndpoints:
    def test_get_current_key(self, grpc_channel, redis_client):
        """Test GetCurrentKey gRPC endpoint"""
        # Setup test key
        test_key = {
            "id": "int_test_key",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "is_active": True,
            "is_revoked": False,
            "version": 1,
            "permissions": ["read"]
        }
        redis_client.hset("keys:current", mapping=test_key)

        stub = KeyManagementServiceStub(grpc_channel)
        response = stub.GetCurrentKey(KeyRequest())
        assert response.key_id == "int_test_key"
        assert response.is_active is True

    def test_rotate_key(self, grpc_channel):
        """Test RotateKey gRPC endpoint"""
        stub = KeyManagementServiceStub(grpc_channel)
        request = KeyRequest(expire_in_days=30)
        response = stub.RotateKey(request)
        assert response.key_id is not None
        assert response.is_active is True

    def test_list_keys(self, grpc_channel, redis_client):
        """Test ListKeys gRPC endpoint"""
        # Setup test keys
        key1 = {"id": "list_key1", "is_active": True}
        key2 = {"id": "list_key2", "is_active": False}
        redis_client.hset("keys:list_key1", mapping=key1)
        redis_client.hset("keys:list_key2", mapping=key2)

        stub = KeyManagementServiceStub(grpc_channel)
        response = stub.ListKeys(ListKeysRequest())
        assert len(response.keys) == 2
        assert {k.key_id for k in response.keys} == {"list_key1", "list_key2"}

    def test_revoke_key(self, grpc_channel, redis_client):
        """Test RevokeKey gRPC endpoint"""
        # Setup test key
        test_key = {"id": "to_revoke", "is_revoked": False}
        redis_client.hset("keys:to_revoke", mapping=test_key)

        stub = KeyManagementServiceStub(grpc_channel)
        request = RevokeKeyRequest(key_id="to_revoke")
        response = stub.RevokeKey(request)
        assert response.success is True
        assert redis_client.hget("keys:to_revoke", "is_revoked") == "True"