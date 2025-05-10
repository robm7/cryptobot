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

def test_create_strategy(client):
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

def test_get_strategy(client, db):
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

def test_delete_strategy(client, db):
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

def test_activate_deactivate_strategy(client, db):
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

def test_get_strategy_versions(client, db):
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