import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from strategy.main import app
from strategy.models.strategy import Base, Strategy, StrategyVersion
from database.db import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

@pytest.fixture
def mock_auth_user(mocker):
    """Mocks get_current_user to return a specific user."""
    def _mock_auth_user_fn(user_payload={"user_id": 1, "roles": ["trader"]}):
        return mocker.patch('strategy.routers.strategies.get_current_user', return_value=user_payload)
    return _mock_auth_user_fn

@pytest.fixture
def mock_auth_role(mocker):
    """Mocks has_role dependency."""
    def _mock_auth_role_fn(user_payload_for_role_check={"user_id": 1, "roles": ["trader"]}):
        # This mock assumes has_role will be called with the user from get_current_user
        # For simplicity, we'll just ensure get_current_user is also mocked if has_role is used.
        # A more direct mock of has_role itself might be complex due to it being a dependency factory.
        # Instead, we ensure the user passed to has_role (via get_current_user) has the desired roles.
        return mocker.patch('strategy.routers.strategies.get_current_user', return_value=user_payload_for_role_check)
    return _mock_auth_role_fn


def test_create_strategy(client, mock_auth_role): # Added mock_auth_role
    # Simulate a user with 'trader' or 'admin' role
    mock_auth_role({"user_id": 1, "roles": ["trader"]})
    response = client.post(
        "/strategies/",
        json={
            "name": "Test Strategy",
            "description": "Test description",
            "parameters": {"param1": "value1"},
            "version": 1
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Strategy"
    assert data["version"] == 1
    assert data["is_active"] is True

def test_get_strategy(client, db, mock_auth_user): # Added mock_auth_user
    mock_auth_user() # Default user
    # Create test strategy
    strategy = Strategy(
        name="Test Strategy",
        description="Test description",
        parameters={"param1": "value1"},
        version=1
    )
    db.add(strategy)
    db.commit()

    response = client.get(f"/strategies/{strategy.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == strategy.id
    assert data["name"] == "Test Strategy"
    # It should also return versions if any
    assert "versions" in data

def test_list_strategies(client, db):
    # Create some strategies
    s1 = Strategy(name="Active Strat 1", description="Test", parameters={"p": "1"}, version=1, is_active=True)
    s2 = Strategy(name="Inactive Strat", description="Test", parameters={"p": "2"}, version=1, is_active=False)
    s3 = Strategy(name="Active Strat 2", description="Test", parameters={"p": "3"}, version=1, is_active=True)
    db.add_all([s1, s2, s3])
    db.commit()

    # Test default (active_only=True)
    response_active = client.get("/strategies/")
    assert response_active.status_code == 200
    data_active = response_active.json()
    assert len(data_active) == 2
    assert {s["name"] for s in data_active} == {"Active Strat 1", "Active Strat 2"}

    # Test active_only=False
    response_all = client.get("/strategies/?active_only=false")
    assert response_all.status_code == 200
    data_all = response_all.json()
    assert len(data_all) == 3
    assert {s["name"] for s in data_all} == {"Active Strat 1", "Inactive Strat", "Active Strat 2"}

    # Test active_only=True explicitly
    response_active_explicit = client.get("/strategies/?active_only=true")
    assert response_active_explicit.status_code == 200
    data_active_explicit = response_active_explicit.json()
    assert len(data_active_explicit) == 2

def test_update_strategy(client, db):
    # Create test strategy
    strategy = Strategy(
        name="Test Strategy",
        description="Test description",
        parameters={"param1": "value1"},
        version=1
    )
    db.add(strategy)
    db.commit()

    response = client.put(
        f"/strategies/{strategy.id}",
        json={
            "name": "Updated Strategy",
            "parameters": {"param1": "value2"}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Strategy"
    assert data["version"] == 2  # Version should increment

def test_delete_strategy(client, db, mock_auth_role): # Added mock_auth_role
    mock_auth_role({"user_id": 1, "roles": ["admin"]}) # Needs admin role
    strategy = Strategy(
        name="Test Strategy",
        description="Test description",
        parameters={"param1": "value1"},
        version=1
    )
    db.add(strategy)
    db.commit()

    response = client.delete(f"/strategies/{strategy.id}")
    assert response.status_code == 204

    # Verify deletion
    response = client.get(f"/strategies/{strategy.id}")
    assert response.status_code == 404

def test_activate_deactivate_strategy(client, db, mock_auth_role): # Added mock_auth_role
    mock_auth_role({"user_id": 1, "roles": ["trader"]}) # Needs trader or admin
    strategy = Strategy(
        name="Test Strategy",
        description="Test description",
        parameters={"param1": "value1"},
        version=1,
        is_active=False
    )
    db.add(strategy)
    db.commit()

    # Activate
    response = client.post(f"/strategies/{strategy.id}/activate")
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    # Deactivate
    response = client.post(f"/strategies/{strategy.id}/deactivate")
    assert response.status_code == 200
    assert response.json()["is_active"] is False

def test_get_strategy_versions(client, db, mock_auth_user): # Added mock_auth_user
    mock_auth_user() # Default user
    strategy = Strategy(
        name="Test Strategy",
        description="Test description",
        parameters={"param1": "value1"},
        version=1
    )
    db.add(strategy)
    db.commit()

    # Add versions
    version1 = StrategyVersion(
        strategy_id=strategy.id,
        version=1,
        parameters={"param1": "value1"}
    )
    version2 = StrategyVersion(
        strategy_id=strategy.id,
        version=2,
        parameters={"param1": "value2"}
    )
    db.add_all([version1, version2])
    db.commit()

    response = client.get(f"/strategies/{strategy.id}/versions")
    assert response.status_code == 200
    versions = response.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2  # Should be ordered by version desc

def test_validation_errors(client):
    # Test name too short
    response = client.post(
        "/strategies/",
        json={
            "name": "A",
            "parameters": {"param1": "value1"}
        }
    )
    assert response.status_code == 422

    # Test too many parameters
    params = {f"param{i}": f"value{i}" for i in range(21)}
    response = client.post(
        "/strategies/",
        json={
            "name": "Test Strategy",
            "parameters": params
        }
    )
    assert response.status_code == 422

# --- Tests for Authentication and Authorization ---

def test_list_strategies_unauthorized(client):
    # No mock_auth_user, so get_current_user would fail if not handled by default test client behavior for Depends(oauth2_scheme)
    # FastAPI's TestClient typically doesn't run the actual auth flow unless specifically configured.
    # The router has `dependencies=[Depends(oauth2_scheme)]` which should trigger auth.
    # If oauth2_scheme is not overridden, it might try to validate a missing token.
    # For robust testing, we'd mock the dependency `get_current_user` to raise HTTPException(401)
    # or ensure the TestClient doesn't bypass the top-level dependency.
    # For now, let's assume the top-level dependency handles it.
    # If get_db is overridden but oauth2_scheme is not, it might behave unexpectedly.
    # The `dependencies=[Depends(oauth2_scheme)]` on the router should cause a 401 if no token is provided.
    # However, the individual route dependencies like `Depends(get_current_user)` are more specific.
    
    # To properly test this, we'd need to ensure `get_current_user` is NOT successfully mocked.
    # This is tricky with fixture-based mocking if other tests rely on it being mocked.
    # A better approach might be to have separate client fixtures for auth tests.
    
    # Let's test a route that requires a specific role and ensure it fails without the role.
    # For example, delete_strategy requires 'admin'.
    response = client.delete("/strategies/999") # No auth headers, or wrong role
    assert response.status_code == 401 # Expecting 401 due to oauth2_scheme dependency on router

def test_delete_strategy_forbidden(client, db, mock_auth_role):
    # User has 'trader' role, but 'admin' is required for delete
    mock_auth_role({"user_id": 1, "roles": ["trader"]})
    
    strategy = Strategy(name="ToDelete", description="Test", parameters={"p": "1"}, version=1)
    db.add(strategy)
    db.commit()

    response = client.delete(f"/strategies/{strategy.id}")
    assert response.status_code == 403 # Forbidden due to insufficient role
    data = response.json()
    assert "Not enough permissions" in data.get("detail", "") # Message from has_role

def test_create_strategy_forbidden(client, mock_auth_role):
    # User has 'viewer' role, but 'trader' or 'admin' is required
    mock_auth_role({"user_id": 1, "roles": ["viewer"]})
    
    response = client.post(
        "/strategies/",
        json={
            "name": "Forbidden Strategy",
            "description": "Test description",
            "parameters": {"param1": "value1"},
            "version": 1
        }
    )
    assert response.status_code == 403
    data = response.json()
    assert "Not enough permissions" in data.get("detail", "")