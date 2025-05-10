import pytest
import grpc
from auth_pb2 import KeyRequest
from auth_pb2_grpc import KeyManagementServiceStub
from auth_service.auth_service import serve
import threading
import time
import redis

@pytest.fixture
def security_test_server():
    """Fixture for security test server"""
    redis_client = redis.Redis(host='localhost', port=6379, db=1)  # Use separate DB
    server_thread = threading.Thread(
        target=serve,
        args=(redis_client,),
        kwargs={'port': 50053},
        daemon=True
    )
    server_thread.start()
    time.sleep(1)
    yield redis_client
    redis_client.flushdb()

@pytest.fixture
def security_test_channel():
    """Fixture for security test channel"""
    channel = grpc.insecure_channel('localhost:50053')
    yield channel
    channel.close()

class TestSecurity:
    def test_massive_payload(self, security_test_channel):
        """Test handling of oversized requests"""
        stub = KeyManagementServiceStub(security_test_channel)
        with pytest.raises(grpc.RpcError) as e:
            stub.GetCurrentKey(KeyRequest(extra_data="A" * 1000000))
        assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    def test_invalid_inputs(self, security_test_channel):
        """Test various invalid inputs"""
        stub = KeyManagementServiceStub(security_test_channel)
        
        # Test SQL injection attempt
        with pytest.raises(grpc.RpcError) as e:
            stub.RotateKey(KeyRequest(expire_in_days="1; DROP TABLE keys;"))
        assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

        # Test XSS attempt
        with pytest.raises(grpc.RpcError) as e:
            stub.GetCurrentKey(KeyRequest(extra_data="<script>alert(1)</script>"))
        assert e.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    def test_rate_limiting(self, security_test_server, security_test_channel):
        """Test rate limiting protection"""
        stub = KeyManagementServiceStub(security_test_channel)
        
        # First 10 requests should succeed
        for _ in range(10):
            response = stub.GetCurrentKey(KeyRequest())
            assert response.key_id == ""
        
        # 11th request should be rate limited
        with pytest.raises(grpc.RpcError) as e:
            stub.GetCurrentKey(KeyRequest())
        assert e.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED

    def test_invalid_permissions(self, security_test_server, security_test_channel):
        """Test permission validation"""
        # Setup test key with invalid permissions
        test_key = {
            "id": "sec_test_key",
            "permissions": ["invalid_permission"],
            "is_active": True
        }
        security_test_server.hset("keys:current", mapping=test_key)

        stub = KeyManagementServiceStub(security_test_channel)
        with pytest.raises(grpc.RpcError) as e:
            stub.GetCurrentKey(KeyRequest())
        assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED