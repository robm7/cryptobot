import pytest
from flask import jsonify
from auth.auth_service import token_required, refresh_token_required

def test_token_required_decorator(client, auth_headers, mock_redis):
    """Test the token_required decorator with valid token"""
    try:
        # Disable testing mode for rate limiting
        client.application.config['TESTING'] = False
        
        # Configure Redis mock
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = 1
        
        # Test with valid token
        response = client.get('/api/protected/route', headers=auth_headers)
    finally:
        # Restore testing mode
        client.application.config['TESTING'] = True
    assert response.status_code == 200
    assert isinstance(response.json, dict)  # Verify JSON response

    # Test without token
    response = client.get('/api/protected/route')
    assert response.status_code == 401
    assert "error" in response.json  # Verify error structure
    assert "token" in response.json["error"].lower()  # Verify token error

    # Verify Redis was called for rate limiting
    mock_redis.incr.assert_called_once()

def test_token_required_testing_mode(client, mock_redis):
    """Test token_required decorator in testing mode"""
    try:
        # Explicitly enable testing mode
        client.application.config['TESTING'] = True
        
        # Test with testing token
        response = client.get(
            '/api/protected/route',
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 200
        assert isinstance(response.json, dict)
        assert "test_user" in str(response.json)  # More flexible check

        # Verify Redis wasn't called in testing mode
        mock_redis.incr.assert_not_called()
        mock_redis.exists.assert_not_called()
    finally:
        # Ensure testing mode is restored
        client.application.config['TESTING'] = True

def test_refresh_token_required_decorator(client, mock_redis):
    """Test the refresh_token_required decorator"""
    try:
        # Configure Redis mock
        mock_redis.exists.return_value = False
        
        # Ensure testing mode is enabled
        client.application.config['TESTING'] = True
        
        # Test with refresh token in testing mode
        response = client.get(
            '/api/auth/refresh',
            headers={'Authorization': 'Bearer valid.refresh.token'}
        )
        assert response.status_code == 200
        assert isinstance(response.json, dict)
        assert "test_user" in str(response.json)

        # Verify Redis wasn't called in testing mode
        mock_redis.exists.assert_not_called()

        # Test with access token (should fail)
        response = client.get(
            '/api/auth/refresh',
            headers={'Authorization': 'Bearer invalid.token.type'}
        )
        assert response.status_code == 401
        assert "error" in response.json
        assert "refresh" in response.json["error"].lower()
    finally:
        # Restore testing mode
        client.application.config['TESTING'] = True

def test_rate_limiting(client, mock_redis):
    """Test rate limiting functionality of token_required"""
    try:
        # Configure Redis mock
        mock_redis.incr.return_value = 1  # Simulate successful increment
        mock_redis.ttl.return_value = 60  # Simulate TTL exists
        mock_redis.exists.return_value = False
        
        # Disable testing mode for rate limiting
        client.application.config['TESTING'] = False

        # Make multiple requests - should all pass with test token
        for i in range(5):
            response = client.get(
                '/api/protected/route',
                headers={'Authorization': 'Bearer testing.token'}
            )
            assert response.status_code == 200
            assert isinstance(response.json, dict)
            assert "test_user" in str(response.json)
            
        # Verify rate limiting was called for each request
        assert mock_redis.incr.call_count == 5
        mock_redis.expire.assert_called()
        mock_redis.ttl.assert_called()

        # Test burst requests
        mock_redis.incr.return_value = 101  # Simulate rate limit exceeded
        response = client.get(
            '/api/protected/route',
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 429
        assert "Too many requests" in response.json["error"]

        # Test different IPs
        mock_redis.incr.return_value = 1  # Reset counter
        response = client.get(
            '/api/protected/route',
            headers={'Authorization': 'Bearer testing.token'},
            environ_base={'REMOTE_ADDR': '192.168.1.2'}
        )
        assert response.status_code == 200
    finally:
        # Restore testing mode
        client.application.config['TESTING'] = True

def test_session_tracking(client, mock_redis):
    """Test session tracking functionality"""
    try:
        # Configure Redis mock
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = 1
        
        # Disable testing mode
        client.application.config['TESTING'] = False

        # Make requests with different tokens (simulating different sessions)
        tokens = [f"token_{i}" for i in range(3)]
        
        for token in tokens:
            response = client.get(
                '/api/protected/route',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert response.status_code == 200

        # Verify all sessions were tracked
        assert mock_redis.incr.call_count == 3
    finally:
        # Restore testing mode
        client.application.config['TESTING'] = True

def test_token_type_validation(client):
    """Test decorator validates token types correctly"""
    # Test access token in refresh endpoint
    response = client.get(
        '/api/auth/refresh',
        headers={'Authorization': 'Bearer access.token'}
    )
    assert response.status_code == 401
    assert "refresh" in response.json["error"].lower()

    # Test refresh token in regular endpoint
    response = client.get(
        '/api/protected/route',
        headers={'Authorization': 'Bearer refresh.token'}
    )
    assert response.status_code == 401
    assert "access" in response.json["error"].lower()

def test_mfa_required_decorator(client, auth_headers, mock_redis):
    """Test the mfa_required decorator"""
    try:
        # Configure Redis mock
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = 1
        
        # Test with valid token but no MFA
        response = client.get('/api/mfa/protected/route', headers=auth_headers)
        assert response.status_code == 403
        assert "MFA" in response.json["error"]
        
        # Test with valid token and MFA
        auth_headers['X-MFA-Verified'] = 'true'
        response = client.get('/api/mfa/protected/route', headers=auth_headers)
        assert response.status_code == 200
        
        # Test admin route with MFA enforcement
        response = client.get('/api/admin/protected/route', headers=auth_headers)
        assert response.status_code == 403
        assert "MFA" in response.json["error"]
        
        # Test admin with MFA enabled
        auth_headers['X-Admin-MFA-Verified'] = 'true'
        response = client.get('/api/admin/protected/route', headers=auth_headers)
        assert response.status_code == 200
    finally:
        # Clean up headers
        if 'X-MFA-Verified' in auth_headers:
            del auth_headers['X-MFA-Verified']
        if 'X-Admin-MFA-Verified' in auth_headers:
            del auth_headers['X-Admin-MFA-Verified']

def test_totp_verification(client, mock_redis):
    """Test TOTP verification flow"""
    try:
        # Setup MFA
        response = client.post(
            '/api/auth/mfa/setup',
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 200
        assert "qr_code" in response.json
        assert "manual_entry_code" in response.json
        
        # Verify with invalid code
        response = client.post(
            '/api/auth/mfa/verify',
            json={'code': '123456'},
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 401
        assert "invalid" in response.json["error"].lower()
        
        # Verify with valid code (mocked)
        mock_redis.exists.return_value = True
        response = client.post(
            '/api/auth/mfa/verify',
            json={'code': '000000'},
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 200
        assert "enabled" in response.json["message"].lower()
    finally:
        # Clean up
        mock_redis.exists.return_value = False

def test_backup_codes(client, mock_redis):
    """Test backup code generation and validation"""
    try:
        # Generate backup codes
        response = client.post(
            '/api/auth/mfa/backup-codes',
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 200
        assert len(response.json["codes"]) == 10
        
        # Try to use a backup code
        mock_redis.exists.return_value = True
        response = client.post(
            '/api/auth/mfa/verify',
            json={'code': response.json["codes"][0], 'is_backup': True},
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 200
        assert "backup" in response.json["message"].lower()
        
        # Verify code is now invalid
        response = client.post(
            '/api/auth/mfa/verify',
            json={'code': response.json["codes"][0], 'is_backup': True},
            headers={'Authorization': 'Bearer testing.token'}
        )
        assert response.status_code == 401
        assert "invalid" in response.json["error"].lower()
    finally:
        mock_redis.exists.return_value = False

def test_admin_mfa_enforcement(client, mock_redis):
    """Test admin MFA enforcement"""
    try:
        # Configure Redis mock
        mock_redis.exists.return_value = False
        
        # Test admin endpoint without MFA
        response = client.get(
            '/api/admin/sensitive/operation',
            headers={'Authorization': 'Bearer admin.token'}
        )
        assert response.status_code == 403
        assert "MFA" in response.json["error"]
        
        # Test with MFA
        headers = {
            'Authorization': 'Bearer admin.token',
            'X-Admin-MFA-Verified': 'true'
        }
        response = client.get(
            '/api/admin/sensitive/operation',
            headers=headers
        )
        assert response.status_code == 200
    finally:
        mock_redis.exists.return_value = False