import pytest
import grpc
import grpc.aio # For async if needed, but server here is sync
from concurrent import futures
from unittest.mock import MagicMock, patch

# Assuming auth_service and generated pb2 files are in python path
# Adjust imports based on your project structure
from auth_service.auth_pb2 import GetCurrentKeyRequest, KeyResponse
from auth_service.auth_pb2_grpc import KeyManagementServiceStub, add_KeyManagementServiceServicer_to_server
from auth_service.auth_service import AuthService # The servicer class
from auth_service.key_manager import KeyManager # To mock its methods

@pytest.fixture(scope="module")
def grpc_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
    yield server
    server.stop(0)

@pytest.fixture(scope="module")
def mock_key_manager_instance():
    # This mock will be used by the AuthService servicer
    km_mock = MagicMock(spec=KeyManager)
    return km_mock

@pytest.fixture(scope="module")
def grpc_stub(grpc_server, mock_key_manager_instance):
    # Mock redis_client for AuthService, or ensure KeyManager mock doesn't need it
    mock_redis = MagicMock()
    auth_servicer = AuthService(redis_client=mock_redis, key_manager=mock_key_manager_instance)
    add_KeyManagementServiceServicer_to_server(auth_servicer, grpc_server)
    
    port = grpc_server.add_insecure_port('[::]:0') # Use a random available port
    grpc_server.start()
    
    channel = grpc.insecure_channel(f'localhost:{port}')
    stub = KeyManagementServiceStub(channel)
    yield stub
    channel.close()

def test_get_current_key_success(grpc_stub, mock_key_manager_instance):
    expected_key_data = {
        "id": "test_key_id_123",
        "created_at": "2023-01-01T00:00:00Z",
        "expires_at": "2023-01-31T00:00:00Z",
        "is_active": True,
        "is_revoked": False,
        "version": "v1",
        "permissions": ["read", "trade"]
    }
    mock_key_manager_instance.get_current_key.return_value = expected_key_data
    
    request = GetCurrentKeyRequest() # Assuming it's an empty request message
    response = grpc_stub.GetCurrentKey(request)

    assert response.key_id == expected_key_data["id"]
    assert response.created_at == expected_key_data["created_at"]
    assert response.expires_at == expected_key_data["expires_at"]
    assert response.is_active == expected_key_data["is_active"]
    assert response.is_revoked == expected_key_data["is_revoked"]
    assert response.version == expected_key_data["version"]
    assert list(response.permissions) == expected_key_data["permissions"]
    mock_key_manager_instance.get_current_key.assert_called_once()

def test_get_current_key_not_found(grpc_stub, mock_key_manager_instance):
    mock_key_manager_instance.get_current_key.return_value = None # Simulate no active key

    request = GetCurrentKeyRequest()
    try:
        grpc_stub.GetCurrentKey(request)
        pytest.fail("GetCurrentKey should have raised an RPCError for NOT_FOUND")
    except grpc.RpcError as e:
        assert e.code() == grpc.StatusCode.NOT_FOUND
        assert "No active key found" in e.details()
    
    mock_key_manager_instance.get_current_key.assert_called_once()

# --- Tests for RotateKey RPC ---
def test_rotate_key_success(grpc_stub, mock_key_manager_instance):
    old_key_id = "old_key_123"
    new_key_id = "new_key_456"
    new_key_data = {
        "id": new_key_id,
        "created_at": "2023-02-01T00:00:00Z",
        "expires_at": "2023-03-01T00:00:00Z",
        "is_active": True,
        "is_revoked": False,
        "version": "v2",
        "permissions": ["read", "trade"]
    }
    # Mock rotate_keys to return the ID of the new key
    mock_key_manager_instance.rotate_keys.return_value = new_key_id
    # Mock get_key to return the data for the new key
    mock_key_manager_instance.get_key.return_value = new_key_data

    # The RotateKeyRequest in auth.proto might take old_key_id or other params
    # Assuming RotateKeyRequest has 'key_id_to_rotate' and 'expire_in_days'
    # From auth_service.py: self.key_manager.rotate_keys(request.expire_in_days)
    # This implies the gRPC request might not need old_key_id if KeyManager handles current key rotation.
    # Let's assume the gRPC request takes `expire_in_days` as per the servicer.
    # The servicer's `RotateKey` calls `self.key_manager.rotate_keys(request.expire_in_days)`
    # This `key_manager.rotate_keys` is not defined in the `KeyManager` snippet we have.
    # The `KeyManager` has `rotate_key(self, old_key: str, ...)`
    # This indicates a mismatch or an unshown method in KeyManager.
    # For testing the gRPC endpoint as written in auth_service.py, we mock `key_manager.rotate_keys`.
    
    from auth_service.auth_pb2 import RotateKeyRequest # Import the request message
    request = RotateKeyRequest(expire_in_days=30)
    response = grpc_stub.RotateKey(request)

    assert response.key_id == new_key_data["id"]
    assert response.version == new_key_data["version"]
    mock_key_manager_instance.rotate_keys.assert_called_once_with(30)
    mock_key_manager_instance.get_key.assert_called_once_with(new_key_id)


def test_rotate_key_failure_key_manager_exception(grpc_stub, mock_key_manager_instance):
    mock_key_manager_instance.rotate_keys.side_effect = Exception("Rotation failed in KeyManager")

    from auth_service.auth_pb2 import RotateKeyRequest
    request = RotateKeyRequest(expire_in_days=30)
    try:
        grpc_stub.RotateKey(request)
        pytest.fail("RotateKey should have raised RpcError for INTERNAL")
    except grpc.RpcError as e:
        assert e.code() == grpc.StatusCode.INTERNAL
        assert "Rotation failed in KeyManager" in e.details()
    
    mock_key_manager_instance.rotate_keys.assert_called_once_with(30)

# --- Tests for ListKeys RPC ---
def test_list_keys_success(grpc_stub, mock_key_manager_instance):
    key1_data = {
        "id": "key1", "created_at": "2023-01-01T00:00:00Z", "expires_at": "2023-02-01T00:00:00Z",
        "is_active": True, "is_revoked": False, "version": "v1", "permissions": ["read"]
    }
    key2_data = {
        "id": "key2", "created_at": "2023-01-15T00:00:00Z", "expires_at": "2023-02-15T00:00:00Z",
        "is_active": False, "is_revoked": True, "version": "v1", "permissions": ["read", "write"]
    }
    mock_key_manager_instance.get_all_keys.return_value = [key1_data, key2_data]

    from auth_service.auth_pb2 import ListKeysRequest # Import request message
    request = ListKeysRequest() # Assuming it's an empty request
    response = grpc_stub.ListKeys(request)

    assert len(response.keys) == 2
    assert response.keys[0].key_id == key1_data["id"]
    assert response.keys[0].is_active == key1_data["is_active"]
    assert response.keys[1].key_id == key2_data["id"]
    assert response.keys[1].is_revoked == key2_data["is_revoked"]
    assert list(response.keys[1].permissions) == key2_data["permissions"]
    mock_key_manager_instance.get_all_keys.assert_called_once()

def test_list_keys_empty(grpc_stub, mock_key_manager_instance):
    mock_key_manager_instance.get_all_keys.return_value = []
    
    from auth_service.auth_pb2 import ListKeysRequest
    request = ListKeysRequest()
    response = grpc_stub.ListKeys(request)

    assert len(response.keys) == 0
    mock_key_manager_instance.get_all_keys.assert_called_once()

# --- Tests for RevokeKey RPC ---
def test_revoke_key_success(grpc_stub, mock_key_manager_instance):
    key_to_revoke = "key_to_revoke_789"
    mock_key_manager_instance.revoke_key.return_value = True # Simulate successful revocation

    from auth_service.auth_pb2 import RevokeKeyRequest # Import request message
    request = RevokeKeyRequest(key_id=key_to_revoke)
    response = grpc_stub.RevokeKey(request)

    assert response.success is True
    mock_key_manager_instance.revoke_key.assert_called_once_with(key_to_revoke)

def test_revoke_key_failure_not_found_or_error(grpc_stub, mock_key_manager_instance):
    key_to_revoke = "key_not_found_xyz"
    mock_key_manager_instance.revoke_key.return_value = False # Simulate key not found or failed to revoke

    from auth_service.auth_pb2 import RevokeKeyRequest
    request = RevokeKeyRequest(key_id=key_to_revoke)
    response = grpc_stub.RevokeKey(request)

    assert response.success is False
    mock_key_manager_instance.revoke_key.assert_called_once_with(key_to_revoke)

def test_revoke_key_key_manager_exception(grpc_stub, mock_key_manager_instance):
    key_to_revoke = "key_exception_abc"
    # The servicer's RevokeKey doesn't explicitly catch exceptions from key_manager.revoke_key
    # It directly returns its boolean. If key_manager.revoke_key raised an exception,
    # the gRPC framework would likely turn it into an INTERNAL error.
    # For this test, we'll assume key_manager.revoke_key returns bool as per its signature.
    # If we wanted to test an exception from key_manager.revoke_key propagating:
    mock_key_manager_instance.reset_mock() # Reset from previous calls in other tests
    key_to_revoke_exception = "key_exception_scenario_actual"
    mock_key_manager_instance.revoke_key.side_effect = Exception("Simulated DB error during revoke")
    
    from auth_service.auth_pb2 import RevokeKeyRequest # Ensure import
    request_exception = RevokeKeyRequest(key_id=key_to_revoke_exception)
    try:
        grpc_stub.RevokeKey(request_exception)
        pytest.fail("RevokeKey should have raised RpcError for an internal KeyManager exception")
    except grpc.RpcError as e:
        # The servicer for RevokeKey directly returns the boolean from key_manager.revoke_key.
        # It does not have a try-except block for this call.
        # Thus, an exception from key_manager.revoke_key would be caught by the gRPC framework
        # and likely result in an UNKNOWN or INTERNAL error status.
        assert e.code() in [grpc.StatusCode.UNKNOWN, grpc.StatusCode.INTERNAL]
        # The details might be generic like "Exception iterating responses: Simulated DB error during revoke"
        # or just the error message if the framework passes it through.
        assert "Simulated DB error during revoke" in e.details()
    mock_key_manager_instance.revoke_key.assert_called_once_with(key_to_revoke_exception)

# --- Tests for GetExpiringKeys RPC ---
def test_get_expiring_keys_success(grpc_stub, mock_key_manager_instance):
    expiring_key_data = [{
        "id": "exp_key1", "created_at": "2023-01-01T00:00:00Z", "expires_at": "2023-01-05T00:00:00Z",
        "is_active": True, "is_revoked": False, "version": "v1", "permissions": ["read"]
    }]
    mock_key_manager_instance.get_upcoming_expirations.return_value = expiring_key_data

    from auth_service.auth_pb2 import GetExpiringKeysRequest # Import request message
    request = GetExpiringKeysRequest(days=7) # Example days
    response = grpc_stub.GetExpiringKeys(request)

    assert len(response.keys) == 1
    assert response.keys[0].key_id == expiring_key_data[0]["id"]
    assert response.keys[0].expires_at == expiring_key_data[0]["expires_at"]
    mock_key_manager_instance.get_upcoming_expirations.assert_called_once_with(7)

def test_get_expiring_keys_none_found(grpc_stub, mock_key_manager_instance):
    mock_key_manager_instance.get_upcoming_expirations.return_value = []

    from auth_service.auth_pb2 import GetExpiringKeysRequest
    request = GetExpiringKeysRequest(days=3)
    response = grpc_stub.GetExpiringKeys(request)

    assert len(response.keys) == 0
    mock_key_manager_instance.get_upcoming_expirations.assert_called_once_with(3)

def test_get_expiring_keys_key_manager_exception(grpc_stub, mock_key_manager_instance):
    mock_key_manager_instance.get_upcoming_expirations.side_effect = Exception("Failed to query expirations")

    from auth_service.auth_pb2 import GetExpiringKeysRequest
    request = GetExpiringKeysRequest(days=5)
    try:
        grpc_stub.GetExpiringKeys(request)
        pytest.fail("GetExpiringKeys should have raised RpcError for INTERNAL")
    except grpc.RpcError as e:
        assert e.code() == grpc.StatusCode.INTERNAL
        assert "Failed to query expirations" in e.details()
    mock_key_manager_instance.get_upcoming_expirations.assert_called_once_with(5)