import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Assuming auth-service is in the python path or adjust as needed
from auth_service.main import create_app, KeyManager 

# Use a consistent test Redis client mock across tests
@pytest.fixture
def mock_redis_client():
    redis_mock = MagicMock()
    # Default mock behaviors (can be overridden in tests)
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.sadd.return_value = 1
    redis_mock.smembers.return_value = set()
    redis_mock.hset.return_value = 1
    redis_mock.delete.return_value = 1
    redis_mock.ping.return_value = True
    return redis_mock

@pytest.fixture
def key_manager(mock_redis_client):
    return KeyManager(redis_client=mock_redis_client)

@pytest.fixture
def client(mock_redis_client, key_manager):
    # Patch get_redis_client to use our mock during app creation
    with patch('auth_service.main.get_redis_client', return_value=mock_redis_client):
        app = create_app(redis_client=mock_redis_client, key_manager=key_manager)
        app.config['TESTING'] = True 
        # Add any other necessary test configurations
        # For example, if there's an ADMIN_SERVICE_API_KEY for emergency_revoke
        # app.config['ADMIN_SERVICE_API_KEY'] = "test_admin_key" 
        # os.environ["ADMIN_SERVICE_API_KEY"] = "test_admin_key" # If using os.getenv
        with app.test_client() as client:
            yield client

# --- Test Data ---
USER_ID_1 = "user123"
USER_ID_2 = "user456"
SAMPLE_KEY_VALUE_1 = f"sk_{USER_ID_1}_1672531200" # Example: Jan 1, 2023
SAMPLE_KEY_DATA_1 = {
    'value': SAMPLE_KEY_VALUE_1,
    'version': "v1",
    'permissions': ["read", "write"],
    'created_at': (datetime.utcnow() - timedelta(days=10)).isoformat(),
    'expires_at': (datetime.utcnow() + timedelta(days=20)).isoformat(),
    'is_active': True,
    'rotation_status': 'active',
    'audit_log': [{'timestamp': datetime.utcnow().isoformat(), 'action': 'created', 'details': 'Test key'}]
}

# --- Tests for /api/keys/current ---
def test_get_current_key_success(client, mock_redis_client):
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1}
    mock_redis_client.get.return_value = json.dumps(SAMPLE_KEY_DATA_1)
    
    response = client.get('/api/keys/current', headers={'X-User-ID': USER_ID_1})
    assert response.status_code == 200
    data = response.json
    assert data['value'] == SAMPLE_KEY_VALUE_1
    assert data['is_active'] is True

def test_get_current_key_no_active_key(client, mock_redis_client):
    inactive_key_data = {**SAMPLE_KEY_DATA_1, 'is_active': False}
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1}
    mock_redis_client.get.return_value = json.dumps(inactive_key_data)

    response = client.get('/api/keys/current', headers={'X-User-ID': USER_ID_1})
    assert response.status_code == 404
    assert 'No active key found' in response.json['error']

def test_get_current_key_no_user_id_header(client):
    response = client.get('/api/keys/current')
    assert response.status_code == 401 # Unauthorized from werkzeug
    assert 'User ID required' in response.json['message'] # Assuming Unauthorized maps to this message

# --- Tests for POST /api/keys/rotate ---
def test_rotate_key_success(client, mock_redis_client, key_manager):
    # Setup: Ensure an active key exists for the user
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1}
    mock_redis_client.get.side_effect = lambda key_path: json.dumps(SAMPLE_KEY_DATA_1) if key_path == f"keys:{SAMPLE_KEY_VALUE_1}" else None
    
    # Mock the key_manager.generate_key to return a predictable new key
    # and key_manager.rotate_key to simulate its internal logic correctly
    # For simplicity, we'll mock the direct outcome of key_manager.rotate_key
    new_generated_key = f"sk_{USER_ID_1}_9999999999"
    with patch.object(key_manager, 'rotate_key', return_value=new_generated_key) as mock_rotate:
        response = client.post('/api/keys/rotate', headers={'X-User-ID': USER_ID_1})
        
        assert response.status_code == 200
        data = response.json
        assert 'new_key' in data
        assert data['new_key'] == new_generated_key
        mock_rotate.assert_called_once_with(SAMPLE_KEY_VALUE_1) # Check it tried to rotate the correct key

def test_rotate_key_no_active_key(client, mock_redis_client, key_manager):
    mock_redis_client.smembers.return_value = set() # No keys for user
    
    with patch.object(key_manager, 'rotate_key') as mock_rotate: # Ensure it's not called
        response = client.post('/api/keys/rotate', headers={'X-User-ID': USER_ID_1})
        assert response.status_code == 400
        assert 'No active key to rotate' in response.json['error']
        mock_rotate.assert_not_called()

def test_rotate_key_key_manager_failure(client, mock_redis_client, key_manager):
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1}
    mock_redis_client.get.return_value = json.dumps(SAMPLE_KEY_DATA_1)

    with patch.object(key_manager, 'rotate_key', side_effect=ValueError("Rotation failed internally")) as mock_rotate:
        response = client.post('/api/keys/rotate', headers={'X-User-ID': USER_ID_1})
        # The Flask route currently doesn't catch exceptions from key_manager.rotate_key specifically,
        # it would likely result in a 500 if not handled.
        # For a more robust test, the route should handle this.
        # Assuming a generic error handler might turn it into a 500 or a specific error.
        # Let's assume for now the route is simple and might 500.
        # If the route had try/except around key_manager.rotate_key:
        # assert response.status_code == 400 or response.status_code == 500
        # assert "Rotation failed internally" in response.json.get('error', response.json.get('message', ''))
        # For now, just assert the mock was called.
        # This test highlights a potential improvement area in the route's error handling.
        with pytest.raises(ValueError): # If the route doesn't catch it, the test client will see it
             client.post('/api/keys/rotate', headers={'X-User-ID': USER_ID_1})
        mock_rotate.assert_called_once()

# --- Tests for POST /api/keys/revoke-current ---
def test_revoke_current_key_success(client, mock_redis_client, key_manager):
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1}
    mock_redis_client.get.return_value = json.dumps(SAMPLE_KEY_DATA_1) # Active key

    with patch.object(key_manager, 'revoke_key', return_value=True) as mock_revoke:
        response = client.post('/api/keys/revoke-current', headers={'X-User-ID': USER_ID_1})
        assert response.status_code == 200
        data = response.json
        assert data['status'] == 'revoked'
        mock_revoke.assert_called_once_with(SAMPLE_KEY_VALUE_1)

def test_revoke_current_key_no_active_key(client, mock_redis_client, key_manager):
    mock_redis_client.smembers.return_value = set() # No keys for user
    
    with patch.object(key_manager, 'revoke_key') as mock_revoke:
        response = client.post('/api/keys/revoke-current', headers={'X-User-ID': USER_ID_1})
        assert response.status_code == 400
        assert 'No active key to revoke' in response.json['error']
        mock_revoke.assert_not_called()

def test_revoke_current_key_manager_failure(client, mock_redis_client, key_manager):
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1}
    mock_redis_client.get.return_value = json.dumps(SAMPLE_KEY_DATA_1)

    with patch.object(key_manager, 'revoke_key', return_value=False) as mock_revoke_fails: # Simulate revoke returning False
        # This scenario depends on how the route handles a False return from key_manager.revoke_key
        # The current route doesn't explicitly check the boolean return of key_manager.revoke_key
        # and would return 200 {'status': 'revoked'} regardless if no exception is raised.
        # This test highlights that the route might need to check the return.
        # For now, let's assume it proceeds and returns 200.
        response = client.post('/api/keys/revoke-current', headers={'X-User-ID': USER_ID_1})
        assert response.status_code == 200
        assert response.json['status'] == 'revoked' # As per current route logic
        mock_revoke_fails.assert_called_once()

    with patch.object(key_manager, 'revoke_key', side_effect=Exception("Revocation DB error")) as mock_revoke_exception:
        # If key_manager.revoke_key raises an exception, the route's generic try/except
        # in auth_service/main.py for Flask routes is not shown, but typically it would lead to 500.
        # Let's assume a general error handler in Flask might convert it.
        # For now, we test that the call was made and an exception would propagate if not caught by route.
        with pytest.raises(Exception): # If route doesn't catch it
            client.post('/api/keys/revoke-current', headers={'X-User-ID': USER_ID_1})
        mock_revoke_exception.assert_called_once()

# --- Tests for POST /api/keys/revoke-all ---
def test_revoke_all_keys_success(client, key_manager): # Removed mock_redis_client as key_manager is mocked
    # Mock key_manager.revoke_all_keys directly
    with patch.object(key_manager, 'revoke_all_keys', return_value=2) as mock_revoke_all:
        response = client.post('/api/keys/revoke-all', headers={'X-User-ID': USER_ID_1})
        assert response.status_code == 200
        data = response.json
        assert data['revoked_count'] == 2
        mock_revoke_all.assert_called_once_with(USER_ID_1, emergency=True) # Route calls with emergency=True

def test_revoke_all_keys_no_user_id(client):
    response = client.post('/api/keys/revoke-all')
    assert response.status_code == 401
    assert 'User ID required' in response.json['message']

def test_revoke_all_keys_manager_failure(client, key_manager):
    with patch.object(key_manager, 'revoke_all_keys', side_effect=Exception("Mass revoke failed")) as mock_revoke_all:
        # Assuming the route does not specifically catch this exception from key_manager
        with pytest.raises(Exception): # Or a more specific one if the route wraps it
            client.post('/api/keys/revoke-all', headers={'X-User-ID': USER_ID_1})
        mock_revoke_all.assert_called_once()

# --- Tests for POST /api/keys/settings ---
def test_save_settings_success(client, mock_redis_client):
    settings_payload = {"auto_rotate_days": 30, "notify_before_expiry_days": 7}
    
    response = client.post('/api/keys/settings',
                           headers={'X-User-ID': USER_ID_1},
                           json=settings_payload)
    assert response.status_code == 200
    data = response.json
    assert data['status'] == 'saved'
    mock_redis_client.hset.assert_called_once_with(f"user:{USER_ID_1}:settings", mapping=settings_payload)

def test_save_settings_no_user_id(client):
    response = client.post('/api/keys/settings', json={"auto_rotate_days": 30})
    assert response.status_code == 401
    assert 'User ID required' in response.json['message']

def test_save_settings_no_payload(client):
    response = client.post('/api/keys/settings', headers={'X-User-ID': USER_ID_1})
    # Flask's request.get_json() returns None if content type is not application/json or data is empty/invalid
    # The route redis_client.hset(..., mapping=settings) would then likely fail if settings is None.
    # This depends on Flask's default error handling or if the route has specific checks.
    # Assuming it might lead to a BadRequest (400) or InternalServerError (500) if not handled.
    # For now, let's expect a 400 as it's bad input.
    assert response.status_code == 400 # Or 500 if hset fails with None
    # Add more specific error message check if the route provides one for empty/invalid JSON

def test_save_settings_redis_failure(client, mock_redis_client):
    mock_redis_client.hset.side_effect = Exception("Redis unavailable")
    settings_payload = {"auto_rotate_days": 30}

    # The route doesn't have specific try/except for redis_client.hset
    # So an exception here would likely lead to a 500 Internal Server Error from Flask
    with pytest.raises(Exception): # Or a more specific one if Flask wraps it
        client.post('/api/keys/settings',
                    headers={'X-User-ID': USER_ID_1},
                    json=settings_payload)
    mock_redis_client.hset.assert_called_once()

# --- Tests for GET /api/keys/history ---
def test_get_key_history_success(client, mock_redis_client):
    key2_value = f"sk_{USER_ID_1}_1672617600" # Jan 2, 2023
    key2_data = {
        'value': key2_value, 'version': "v1", 'permissions': ["read"],
        'created_at': (datetime.utcnow() - timedelta(days=5)).isoformat(), # Newer
        'expires_at': (datetime.utcnow() + timedelta(days=25)).isoformat(),
        'is_active': False, 'rotation_status': 'revoked',
        'audit_log': [{'timestamp': (datetime.utcnow() - timedelta(days=5)).isoformat(), 'action': 'created', 'details': 'Test key 2'}]
    }
    # SAMPLE_KEY_DATA_1 is older (created 10 days ago)
    
    mock_redis_client.smembers.return_value = {SAMPLE_KEY_VALUE_1, key2_value}
    
    def get_side_effect(key_path):
        if key_path == f"keys:{SAMPLE_KEY_VALUE_1}":
            return json.dumps(SAMPLE_KEY_DATA_1)
        if key_path == f"keys:{key2_value}":
            return json.dumps(key2_data)
        return None
    mock_redis_client.get.side_effect = get_side_effect
    
    response = client.get('/api/keys/history', headers={'X-User-ID': USER_ID_1})
    assert response.status_code == 200
    data = response.json
    assert 'history' in data
    assert len(data['history']) == 2
    # Route sorts by created_at desc
    assert data['history'][0]['value'] == key2_value # Newer key (5 days ago) should be first
    assert data['history'][1]['value'] == SAMPLE_KEY_VALUE_1 # Older key (10 days ago) second

def test_get_key_history_no_keys(client, mock_redis_client):
    mock_redis_client.smembers.return_value = set() # No keys for user
    response = client.get('/api/keys/history', headers={'X-User-ID': USER_ID_1})
    assert response.status_code == 200
    data = response.json
    assert 'history' in data
    assert len(data['history']) == 0

def test_get_key_history_no_user_id(client):
    response = client.get('/api/keys/history')
    assert response.status_code == 401
    assert 'User ID required' in response.json['message']

# --- Tests for POST /api/keys/emergency-revoke ---
def test_emergency_revoke_success(client, mock_redis_client, key_manager):
    # Setup admin auth (simplified for this test)
    # In a real scenario, this would involve mocking JWT or another auth mechanism
    # For now, we assume the os.getenv("ADMIN_SERVICE_API_KEY") is set in the test environment
    # or we patch the check within the route.
    # Let's patch os.getenv for this specific test.
    with patch('os.getenv') as mock_os_getenv:
        mock_os_getenv.side_effect = lambda key, default=None: "test_admin_key" if key == "ADMIN_SERVICE_API_KEY" else default

        target_user_id = USER_ID_2
        key_to_revoke = f"sk_{target_user_id}_somekey"
        key_data_to_revoke = {**SAMPLE_KEY_DATA_1, "value": key_to_revoke, "is_active": True}

        mock_redis_client.smembers.return_value = {key_to_revoke}
        mock_redis_client.get.return_value = json.dumps(key_data_to_revoke)
        mock_redis_client.set.return_value = True # For updating the key

        # Mock the _notify method on the key_manager instance
        with patch.object(key_manager, '_notify') as mock_notify:
            response = client.post('/api/keys/emergency-revoke', headers={
                'X-Admin-User-ID': 'admin_user', # As used in the route's simplified check
                'X-Admin-API-Key': 'test_admin_key', # As used in the route's simplified check
                'X-Target-User-ID': target_user_id
            })

            assert response.status_code == 200
            data = response.json
            assert data['revoked_count'] == 1
            assert data['target_user_id'] == target_user_id
            
            # Check that redis.set was called to update the key (mark as inactive, add audit)
            # The args for set would be (key_path, json_string_of_updated_key_data)
            # We can check it was called, specific args are harder without more complex mocking here.
            mock_redis_client.set.assert_called()
            # Check that notify was called
            mock_notify.assert_called_once_with('emergency_revoked', {
                'user_id': target_user_id,
                'revoked_keys': [key_to_revoke],
                'admin_user_id': 'admin_user'
            })


def test_emergency_revoke_unauthorized_not_admin(client):
    with patch('os.getenv', return_value="wrong_admin_key"): # Simulate wrong admin key
        response = client.post('/api/keys/emergency-revoke', headers={
            'X-Admin-User-ID': 'not_admin',
            'X-Admin-API-Key': 'wrong_key',
            'X-Target-User-ID': USER_ID_1
        })
        assert response.status_code == 401 # Unauthorized
        assert 'Admin privileges required' in response.json['message']

def test_emergency_revoke_missing_target_user_id(client):
    with patch('os.getenv', return_value="test_admin_key"):
        response = client.post('/api/keys/emergency-revoke', headers={
            'X-Admin-User-ID': 'admin_user',
            'X-Admin-API-Key': 'test_admin_key'
            # Missing X-Target-User-ID
        })
        assert response.status_code == 400 # Bad Request
        assert 'Target User ID (X-Target-User-ID) required' in response.json['message']