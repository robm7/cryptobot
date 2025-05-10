"""
API Route Tests for Critical Components

This file contains tests for the API routes of critical components:
1. Order Execution API
2. API Key Management API
3. Authentication API
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app
from auth.main import app as auth_app
from strategy.main import app as strategy_app
from services.mcp.order_execution.reliable_executor import ReliableOrderExecutor, CircuitState
from auth.key_manager import KeyManager, KeyStatus

# Create test clients
auth_client = TestClient(auth_app)
strategy_client = TestClient(strategy_app)

# Mock authentication for tests
def get_test_token(user_id=123, username="testuser", roles=None):
    """Get a test JWT token"""
    if roles is None:
        roles = ["user"]
    
    # In a real test, we would generate a proper JWT
    # For simplicity, we'll just return a mock token
    return "test_token"

# Test fixtures
@pytest.fixture
def auth_headers():
    """Get headers with authentication token"""
    token = get_test_token()
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_key_manager():
    """Mock KeyManager for testing"""
    with patch("auth.routers.api_keys.get_key_manager") as mock:
        manager = MagicMock(spec=KeyManager)
        mock.return_value = manager
        yield manager

@pytest.fixture
def mock_executor():
    """Mock ReliableOrderExecutor for testing"""
    with patch("strategy.routers.strategies.get_order_executor") as mock:
        executor = MagicMock(spec=ReliableOrderExecutor)
        mock.return_value = executor
        yield executor

class TestOrderExecutionAPI:
    """Test Order Execution API routes"""
    
    def test_execute_order(self, auth_headers, mock_executor):
        """Test order execution endpoint"""
        # Mock the execute_order method
        mock_executor.execute_order.return_value = "ORDER_123456789"
        
        # Define order parameters
        order_data = {
            "symbol": "BTC/USD",
            "side": "buy",
            "type": "limit",
            "quantity": 1.0,
            "price": 50000.0
        }
        
        # Make request
        response = strategy_client.post(
            "/strategies/execute-order",
            json=order_data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORDER_123456789"
        assert data["status"] == "success"
        
        # Verify executor was called
        mock_executor.execute_order.assert_called_once_with(order_data)
    
    def test_execute_order_failure(self, auth_headers, mock_executor):
        """Test order execution failure handling"""
        # Mock the execute_order method to return None (failure)
        mock_executor.execute_order.return_value = None
        
        # Define order parameters
        order_data = {
            "symbol": "BTC/USD",
            "side": "buy",
            "type": "limit",
            "quantity": 1.0,
            "price": 50000.0
        }
        
        # Make request
        response = strategy_client.post(
            "/strategies/execute-order",
            json=order_data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "failed" in data["detail"].lower()
    
    def test_cancel_order(self, auth_headers, mock_executor):
        """Test order cancellation endpoint"""
        # Mock the cancel_order method
        mock_executor.cancel_order.return_value = True
        
        # Make request
        response = strategy_client.post(
            "/strategies/cancel-order/ORDER_123456789",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["order_id"] == "ORDER_123456789"
        
        # Verify executor was called
        mock_executor.cancel_order.assert_called_once_with("ORDER_123456789")
    
    def test_get_order_status(self, auth_headers, mock_executor):
        """Test get order status endpoint"""
        # Mock the get_order_status method
        mock_executor.get_order_status.return_value = {
            "status": "filled",
            "filled_qty": 1.0,
            "avg_price": 50000.0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Make request
        response = strategy_client.get(
            "/strategies/order-status/ORDER_123456789",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "filled"
        assert data["filled_qty"] == 1.0
        assert data["avg_price"] == 50000.0
        
        # Verify executor was called
        mock_executor.get_order_status.assert_called_once_with("ORDER_123456789")
    
    def test_get_execution_stats(self, auth_headers, mock_executor):
        """Test get execution stats endpoint"""
        # Mock the get_execution_stats method
        mock_executor.get_execution_stats.return_value = {
            "total_orders": 100,
            "successful_orders": 95,
            "failed_orders": 5,
            "avg_execution_time": 0.5,
            "circuit_breaker_trips": 2,
            "retry_count": 10,
            "circuit_state": CircuitState.CLOSED.value,
            "error_rate_per_minute": 0.2,
            "errors_in_window": 3
        }
        
        # Make request
        response = strategy_client.get(
            "/strategies/execution-stats",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_orders"] == 100
        assert data["successful_orders"] == 95
        assert data["failed_orders"] == 5
        assert data["circuit_state"] == CircuitState.CLOSED.value
        
        # Verify executor was called
        mock_executor.get_execution_stats.assert_called_once()
    
    def test_circuit_breaker_status(self, auth_headers, mock_executor):
        """Test circuit breaker status endpoint"""
        # Mock the circuit_state property
        type(mock_executor).circuit_state = MagicMock(return_value=CircuitState.CLOSED)
        
        # Make request
        response = strategy_client.get(
            "/strategies/circuit-breaker",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == CircuitState.CLOSED.value
        assert data["healthy"] is True

class TestAPIKeyManagementAPI:
    """Test API Key Management API routes"""
    
    def test_create_api_key(self, auth_headers, mock_key_manager):
        """Test create API key endpoint"""
        # Mock the create_key method
        mock_key_manager.create_key.return_value = {
            "id": "key_123456789",
            "key": "test_api_key",
            "description": "Test Key",
            "exchange": "binance",
            "is_test": False,
            "status": KeyStatus.ACTIVE,
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            "permissions": ["read", "trade"]
        }
        
        # Define key parameters
        key_data = {
            "description": "Test Key",
            "exchange": "binance",
            "is_test": False,
            "expiry_days": 90
        }
        
        # Make request
        response = auth_client.post(
            "/api-keys",
            json=key_data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test_api_key"
        assert data["description"] == "Test Key"
        assert data["exchange"] == "binance"
        assert data["status"] == KeyStatus.ACTIVE
        
        # Verify key manager was called
        mock_key_manager.create_key.assert_called_once()
    
    def test_list_api_keys(self, auth_headers, mock_key_manager):
        """Test list API keys endpoint"""
        # Mock the get_user_keys method
        mock_key_manager.get_user_keys.return_value = [
            {
                "id": "key_123456789",
                "key": "test_api_key_1",
                "description": "Test Key 1",
                "exchange": "binance",
                "is_test": False,
                "status": KeyStatus.ACTIVE,
                "version": 1,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                "permissions": ["read", "trade"]
            },
            {
                "id": "key_987654321",
                "key": "test_api_key_2",
                "description": "Test Key 2",
                "exchange": "kraken",
                "is_test": True,
                "status": KeyStatus.ROTATING,
                "version": 2,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                "permissions": ["read", "trade", "test"]
            }
        ]
        
        # Make request
        response = auth_client.get(
            "/api-keys",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) == 2
        assert data["total"] == 2
        
        # Verify key manager was called
        mock_key_manager.get_user_keys.assert_called_once()
    
    def test_rotate_api_key(self, auth_headers, mock_key_manager):
        """Test rotate API key endpoint"""
        # Mock the rotate_key method
        mock_key_manager.rotate_key.return_value = {
            "id": "key_new_123456789",
            "key": "new_test_api_key",
            "description": "Test Key",
            "exchange": "binance",
            "is_test": False,
            "status": KeyStatus.ACTIVE,
            "version": 2,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            "permissions": ["read", "trade"],
            "previous_key_id": "key_123456789"
        }
        
        # Define rotation parameters
        rotation_data = {
            "key_id": "key_123456789",
            "grace_period_hours": 24
        }
        
        # Make request
        response = auth_client.post(
            "/api-keys/rotate",
            json=rotation_data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "new_test_api_key"
        assert data["status"] == KeyStatus.ACTIVE
        assert data["version"] == 2
        assert data["previous_key_id"] == "key_123456789"
        
        # Verify key manager was called
        mock_key_manager.rotate_key.assert_called_once_with(
            key_id="key_123456789",
            user_id=123,  # This would be extracted from the token
            grace_period_hours=24
        )
    
    def test_revoke_api_key(self, auth_headers, mock_key_manager):
        """Test revoke API key endpoint"""
        # Mock the revoke_key method
        mock_key_manager.revoke_key.return_value = True
        
        # Define revocation parameters
        revocation_data = {
            "key_id": "key_123456789",
            "reason": "Testing revocation"
        }
        
        # Make request
        response = auth_client.post(
            "/api-keys/revoke",
            json=revocation_data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["detail"] == "API key revoked successfully"
        
        # Verify key manager was called
        mock_key_manager.revoke_key.assert_called_once_with(
            key_id="key_123456789",
            user_id=123,  # This would be extracted from the token
            reason="Testing revocation"
        )
    
    def test_emergency_revoke_api_key(self, auth_headers, mock_key_manager):
        """Test emergency revoke API key endpoint"""
        # Mock the mark_key_compromised method
        mock_key_manager.mark_key_compromised.return_value = True
        
        # Define compromise parameters
        compromise_data = {
            "key_id": "key_123456789",
            "details": "Key was leaked in a security breach"
        }
        
        # Make request
        response = auth_client.post(
            "/api-keys/emergency-revoke",
            json=compromise_data,
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "compromised" in data["detail"].lower()
        assert "security" in data["security_alert"].lower()
        
        # Verify key manager was called
        mock_key_manager.mark_key_compromised.assert_called_once_with(
            key_id="key_123456789",
            user_id=123,  # This would be extracted from the token
            details="Key was leaked in a security breach"
        )
    
    def test_get_api_key_history(self, auth_headers, mock_key_manager):
        """Test get API key history endpoint"""
        # Mock the get_key_history method
        mock_key_manager.get_key_history.return_value = [
            {
                "id": "key_123456789",
                "key": "test_api_key_1",
                "description": "Test Key",
                "exchange": "binance",
                "is_test": False,
                "status": KeyStatus.EXPIRED,
                "version": 1,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                "permissions": ["read", "trade"]
            },
            {
                "id": "key_new_123456789",
                "key": "test_api_key_2",
                "description": "Test Key",
                "exchange": "binance",
                "is_test": False,
                "status": KeyStatus.ACTIVE,
                "version": 2,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                "permissions": ["read", "trade"],
                "previous_key_id": "key_123456789"
            }
        ]
        
        # Make request
        response = auth_client.get(
            "/api-keys/history/binance",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["exchange"] == "binance"
        assert len(data["versions"]) == 2
        assert data["current_version"] == 2
        
        # Verify key manager was called
        mock_key_manager.get_key_history.assert_called_once_with(
            "binance",
            123  # This would be extracted from the token
        )
    
    def test_get_expiring_api_keys(self, auth_headers, mock_key_manager):
        """Test get expiring API keys endpoint"""
        # Mock the get_expiring_keys method
        mock_key_manager.get_expiring_keys.return_value = [
            {
                "id": "key_123456789",
                "key": "test_api_key",
                "description": "Expiring Key",
                "exchange": "binance",
                "is_test": False,
                "status": KeyStatus.ACTIVE,
                "version": 1,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                "permissions": ["read", "trade"]
            }
        ]
        
        # Make request
        response = auth_client.get(
            "/api-keys/expiring?days=7",
            headers=auth_headers
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["keys"]) == 1
        assert data["days_threshold"] == 7
        
        # Verify key manager was called
        mock_key_manager.get_expiring_keys.assert_called_once_with(days_threshold=7)

class TestAuthenticationAPI:
    """Test Authentication API routes"""
    
    def test_login(self):
        """Test login endpoint"""
        # Define login credentials
        login_data = {
            "username": "testuser",
            "password": "testpassword"
        }
        
        # Mock the authenticate_user function
        with patch("auth.routers.auth.authenticate_user") as mock_auth:
            # Set up the mock to return a user
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_user.mfa_enabled = False
            mock_auth.return_value = mock_user
            
            # Mock the create_token_pair function
            with patch("auth.routers.auth.create_token_pair") as mock_token:
                mock_token.return_value = {
                    "access_token": "test_access_token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "refresh_token": "test_refresh_token",
                    "refresh_token_expires_in": 86400
                }
                
                # Make request
                response = auth_client.post(
                    "/auth/login",
                    data=login_data
                )
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["access_token"] == "test_access_token"
                assert data["token_type"] == "bearer"
                assert data["refresh_token"] == "test_refresh_token"
    
    def test_validate_token(self, auth_headers):
        """Test token validation endpoint"""
        # Mock the get_current_user function
        with patch("auth.routers.auth.get_current_user") as mock_get_user:
            # Set up the mock to return a user
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_user.roles = [MagicMock(name="user"), MagicMock(name="trader")]
            mock_get_user.return_value = mock_user
            
            # Make request
            response = auth_client.get(
                "/auth/validate",
                headers=auth_headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["username"] == "testuser"
            assert "user" in data["roles"]
            assert "trader" in data["roles"]
    
    def test_refresh_token(self):
        """Test refresh token endpoint"""
        # Define refresh request
        refresh_data = {
            "refresh_token": "test_refresh_token"
        }
        
        # Mock the refresh_access_token function
        with patch("auth.routers.auth.refresh_access_token") as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new_test_access_token",
                "token_type": "bearer",
                "expires_in": 3600
            }
            
            # Make request
            response = auth_client.post(
                "/auth/refresh",
                json=refresh_data
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "new_test_access_token"
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 3600

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])