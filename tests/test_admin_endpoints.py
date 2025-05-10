import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auth.main import app
from auth.database import Base, get_db
from auth.models import User, Setting
from auth.schemas import UserCreate

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_test_user(email: str, is_admin: bool = False):
    user_data = {
        "email": email,
        "password": "testpass123",
        "is_admin": is_admin
    }
    return User(**user_data)

def get_auth_token(email: str, password: str = "testpass123"):
    response = client.post(
        "/auth/token",
        data={"username": email, "password": password}
    )
    return response.json()["access_token"]

# Test data
admin_user = create_test_user("admin@test.com", is_admin=True)
regular_user = create_test_user("user@test.com")

# Tests
def test_admin_access_required(test_db):
    # Setup test DB
    db = TestingSessionLocal()
    db.add(admin_user)
    db.add(regular_user)
    db.commit()

    # Get tokens
    admin_token = get_auth_token("admin@test.com")
    user_token = get_auth_token("user@test.com")

    # Test admin endpoint with regular user
    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403

    # Test admin endpoint with admin user
    response = client.get(
        "/admin/users", 
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

def test_user_management(test_db):
    # Setup
    db = TestingSessionLocal()
    db.add(admin_user)
    db.commit()
    token = get_auth_token("admin@test.com")

    # Create user
    new_user = {
        "email": "new@test.com",
        "password": "newpass123",
        "is_active": True
    }
    response = client.post(
        "/admin/users",
        json=new_user,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new@test.com"

    # Get user
    user_id = response.json()["id"]
    response = client.get(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    # Update user
    update_data = {"is_active": False}
    response = client.put(
        f"/admin/users/{user_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Delete user
    response = client.delete(
        f"/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

def test_settings_management(test_db):
    # Setup
    db = TestingSessionLocal()
    db.add(admin_user)
    db.commit()
    token = get_auth_token("admin@test.com")

    # Create setting
    new_setting = {
        "key": "test_setting",
        "value": "test_value",
        "description": "Test setting"
    }
    response = client.post(
        "/admin/settings",
        json=new_setting,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201

    # Update setting
    update_data = {"value": "updated_value"}
    response = client.put(
        "/admin/settings/test_setting",
        json=update_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["value"] == "updated_value"

def test_audit_logs(test_db):
    # Setup
    db = TestingSessionLocal()
    db.add(admin_user)
    db.commit()
    token = get_auth_token("admin@test.com")

    # Get logs
    response = client.get(
        "/admin/logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)