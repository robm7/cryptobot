"""
Test script for protected endpoints in the Strategy Service

This script tests:
1. Authentication requirement on protected endpoints
2. Role-based access control
3. Successful operations with valid authentication
"""

import requests
import jwt
import json
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8000"  # Update with your service URL
SECRET_KEY = "test_secret_key_for_local_testing"

def create_test_token(username="test_user", roles=None, expire_minutes=30):
    """Create a test JWT token for authentication testing"""
    if roles is None:
        roles = ["admin", "trader"]
        
    payload = {
        "sub": username,
        "roles": roles,
        "token_type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=expire_minutes),
        "jti": f"test-{int(time.time())}"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def test_health_endpoint():
    """Test unauthenticated health endpoint"""
    url = f"{BASE_URL}/health"
    logger.info(f"Testing health endpoint: {url}")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        logger.info("✅ Health endpoint works (no auth required)")
        return True
    else:
        logger.error(f"❌ Health endpoint failed: {response.status_code} - {response.text}")
        return False

def test_list_strategies_without_auth():
    """Test listing strategies without authentication (should fail)"""
    url = f"{BASE_URL}/api/strategies/"
    logger.info(f"Testing list strategies without auth: {url}")
    
    response = requests.get(url)
    
    if response.status_code == 401:
        logger.info("✅ Authentication required as expected")
        return True
    else:
        logger.error(f"❌ Expected 401, got: {response.status_code} - {response.text}")
        return False

def test_list_strategies_with_auth():
    """Test listing strategies with authentication"""
    url = f"{BASE_URL}/api/strategies/"
    token = create_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info(f"Testing list strategies with auth: {url}")
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        logger.info(f"✅ List strategies successful with auth: {response.text[:100]}...")
        return True
    else:
        logger.error(f"❌ List strategies failed: {response.status_code} - {response.text}")
        return False

def test_create_strategy_with_viewer_role():
    """Test creating strategy with viewer role (should fail)"""
    url = f"{BASE_URL}/api/strategies/"
    token = create_test_token(username="viewer_user", roles=["viewer"])
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "name": "Test Strategy",
        "description": "A test strategy",
        "parameters": {"param1": "value1"}
    }
    
    logger.info(f"Testing create strategy with viewer role: {url}")
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 403:
        logger.info("✅ Authorization check working as expected (viewer can't create)")
        return True
    else:
        logger.error(f"❌ Expected 403, got: {response.status_code} - {response.text}")
        return False

def test_create_strategy_with_trader_role():
    """Test creating strategy with trader role (should succeed)"""
    url = f"{BASE_URL}/api/strategies/"
    token = create_test_token(username="trader_user", roles=["trader"])
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "name": f"Test Strategy {int(time.time())}",  # Unique name
        "description": "A test strategy created by trader",
        "parameters": {"param1": "value1"}
    }
    
    logger.info(f"Testing create strategy with trader role: {url}")
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 201:
        logger.info(f"✅ Create strategy successful with trader role: {response.text[:100]}...")
        # Return the created strategy ID for later tests
        return response.json().get("id")
    else:
        logger.error(f"❌ Create strategy failed: {response.status_code} - {response.text}")
        return None

def test_delete_strategy_with_trader_role(strategy_id):
    """Test deleting strategy with trader role (should fail)"""
    if not strategy_id:
        logger.warning("Skipping delete test - no strategy ID")
        return False
        
    url = f"{BASE_URL}/api/strategies/{strategy_id}"
    token = create_test_token(username="trader_user", roles=["trader"])
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info(f"Testing delete strategy with trader role: {url}")
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 403:
        logger.info("✅ Authorization check working as expected (trader can't delete)")
        return True
    else:
        logger.error(f"❌ Expected 403, got: {response.status_code} - {response.text}")
        return False

def test_delete_strategy_with_admin_role(strategy_id):
    """Test deleting strategy with admin role (should succeed)"""
    if not strategy_id:
        logger.warning("Skipping delete test - no strategy ID")
        return False
        
    url = f"{BASE_URL}/api/strategies/{strategy_id}"
    token = create_test_token(username="admin_user", roles=["admin"])
    headers = {"Authorization": f"Bearer {token}"}
    
    logger.info(f"Testing delete strategy with admin role: {url}")
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 204:
        logger.info("✅ Delete strategy successful with admin role")
        return True
    else:
        logger.error(f"❌ Delete strategy failed: {response.status_code} - {response.text}")
        return False

def run_all_tests():
    """Run all endpoint tests and report results"""
    logger.info("Starting endpoint tests with authentication")
    
    results = {}
    
    # Test health (no auth)
    results["health"] = test_health_endpoint()
    
    # Test authentication requirement
    results["auth_required"] = test_list_strategies_without_auth()
    
    # Test with authentication
    results["list_with_auth"] = test_list_strategies_with_auth()
    
    # Test role-based authorization
    results["viewer_cant_create"] = test_create_strategy_with_viewer_role()
    
    # Create a strategy as trader
    strategy_id = test_create_strategy_with_trader_role()
    results["trader_can_create"] = strategy_id is not None
    
    # Test trader can't delete
    results["trader_cant_delete"] = test_delete_strategy_with_trader_role(strategy_id)
    
    # Test admin can delete
    results["admin_can_delete"] = test_delete_strategy_with_admin_role(strategy_id)
    
    # Print summary
    logger.info("\n===== TEST RESULTS =====")
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n🎉 All authentication tests passed!")
    else:
        logger.error("\n❌ Some tests failed. Review logs for details.")
    
    return all_passed

if __name__ == "__main__":
    import sys
    sys.exit(0 if run_all_tests() else 1)