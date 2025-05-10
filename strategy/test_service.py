"""
Minimal test service for validating authentication in the strategy service.
This creates a small FastAPI app that simulates the endpoints with authentication
but without requiring a real database.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from starlette.testclient import TestClient
import logging
from typing import Dict, Any, List

# Import our authentication middleware
from auth_middleware import configure_auth, get_current_user, has_role

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a test FastAPI app
app = FastAPI(title="Strategy Service Test")

# Configure auth middleware
configure_auth(app)

# Dummy data for testing
strategies = [
    {
        "id": 1,
        "name": "Test Strategy 1",
        "description": "Test strategy for authentication testing",
        "parameters": {"param1": "value1"},
        "version": 1,
        "is_active": True
    }
]

# Routes that match our real service but without database dependencies
@app.get("/health")
async def health_check():
    """Health check endpoint that does not require authentication."""
    return {"status": "healthy"}

@app.get("/api/strategies/", response_model=List[Dict[str, Any]])
async def list_strategies(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all strategies (requires authentication)"""
    return strategies

@app.get("/api/strategies/{id}", response_model=Dict[str, Any])
async def get_strategy(
    id: int, 
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a single strategy by ID (requires authentication)"""
    for strategy in strategies:
        if strategy["id"] == id:
            return strategy
    raise HTTPException(status_code=404, detail="Strategy not found")

@app.post("/api/strategies/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Create a new strategy (requires admin or trader role)"""
    new_id = max([s["id"] for s in strategies], default=0) + 1
    new_strategy = {**strategy, "id": new_id, "version": 1, "is_active": True}
    strategies.append(new_strategy)
    return new_strategy

@app.delete("/api/strategies/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    id: int, 
    current_user: Dict[str, Any] = Depends(has_role(["admin"]))
):
    """Delete a strategy (requires admin role)"""
    for i, strategy in enumerate(strategies):
        if strategy["id"] == id:
            strategies.pop(i)
            return None
    raise HTTPException(status_code=404, detail="Strategy not found")

@app.post("/api/strategies/{id}/activate", response_model=Dict[str, Any])
async def activate_strategy(
    id: int, 
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Activate a strategy (requires admin or trader role)"""
    for strategy in strategies:
        if strategy["id"] == id:
            strategy["is_active"] = True
            return strategy
    raise HTTPException(status_code=404, detail="Strategy not found")

@app.post("/api/strategies/{id}/deactivate", response_model=Dict[str, Any])
async def deactivate_strategy(
    id: int, 
    current_user: Dict[str, Any] = Depends(has_role(["admin", "trader"]))
):
    """Deactivate a strategy (requires admin or trader role)"""
    for strategy in strategies:
        if strategy["id"] == id:
            strategy["is_active"] = False
            return strategy
    raise HTTPException(status_code=404, detail="Strategy not found")

# Create a test client for running tests
client = TestClient(app=app)

def test_health_endpoint():
    """Test health endpoint (no auth required)"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    return True

def test_list_strategies_no_auth():
    """Test listing strategies without auth token (should fail)"""
    response = client.get("/api/strategies/")
    assert response.status_code == 401
    return True

def test_with_admin_token():
    """Test admin access to endpoints"""
    import jwt
    from datetime import datetime, timedelta
    
    # Create admin token
    payload = {
        "sub": "admin",
        "roles": ["admin"],
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(payload, "test_secret_key_for_local_testing", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test list strategies
    response = client.get("/api/strategies/", headers=headers)
    assert response.status_code == 200
    
    # Test create strategy
    strategy_data = {
        "name": "Admin Strategy",
        "description": "Created by admin",
        "parameters": {"param1": "value1"}
    }
    response = client.post("/api/strategies/", json=strategy_data, headers=headers)
    assert response.status_code == 201
    created_id = response.json()["id"]
    
    # Test delete strategy (admin only)
    response = client.delete(f"/api/strategies/{created_id}", headers=headers)
    assert response.status_code == 204
    
    return True

def test_with_trader_token():
    """Test trader access to endpoints"""
    import jwt
    from datetime import datetime, timedelta
    
    # Create trader token
    payload = {
        "sub": "trader",
        "roles": ["trader"],
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(payload, "test_secret_key_for_local_testing", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test list strategies
    response = client.get("/api/strategies/", headers=headers)
    assert response.status_code == 200
    
    # Test create strategy (allowed for trader)
    strategy_data = {
        "name": "Trader Strategy",
        "description": "Created by trader",
        "parameters": {"param1": "value1"}
    }
    response = client.post("/api/strategies/", json=strategy_data, headers=headers)
    assert response.status_code == 201
    created_id = response.json()["id"]
    
    # Test delete strategy (should fail for trader)
    response = client.delete(f"/api/strategies/{created_id}", headers=headers)
    assert response.status_code == 403
    
    return True

def test_with_viewer_token():
    """Test viewer access to endpoints"""
    import jwt
    from datetime import datetime, timedelta
    
    # Create viewer token
    payload = {
        "sub": "viewer",
        "roles": ["viewer"],
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(payload, "test_secret_key_for_local_testing", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test list strategies (should succeed)
    response = client.get("/api/strategies/", headers=headers)
    assert response.status_code == 200
    
    # Test create strategy (should fail for viewer)
    strategy_data = {
        "name": "Viewer Strategy",
        "description": "Created by viewer",
        "parameters": {"param1": "value1"}
    }
    response = client.post("/api/strategies/", json=strategy_data, headers=headers)
    assert response.status_code == 403
    
    return True

def run_all_tests():
    """Run all tests"""
    logger.info("Starting authentication tests with test client")
    
    tests = [
        ("Health endpoint", test_health_endpoint),
        ("List without auth", test_list_strategies_no_auth),
        ("Admin role tests", test_with_admin_token),
        ("Trader role tests", test_with_trader_token),
        ("Viewer role tests", test_with_viewer_token)
    ]
    
    results = {}
    for name, test_func in tests:
        logger.info(f"Running test: {name}")
        try:
            passed = test_func()
            results[name] = passed
            logger.info(f"{'✅ PASS' if passed else '❌ FAIL'}: {name}")
        except Exception as e:
            logger.error(f"❌ ERROR in {name}: {str(e)}")
            results[name] = False
    
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
    run_all_tests()