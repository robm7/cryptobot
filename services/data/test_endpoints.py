import pytest
from fastapi.testclient import TestClient
from .collector import app
from .test_auth import TEST_USERS, create_test_token

client = TestClient()

@pytest.fixture
def reader_token():
    return create_test_token(TEST_USERS[0])

@pytest.fixture 
def writer_token():
    return create_test_token(TEST_USERS[1])

@pytest.fixture
def monitoring_token():
    return create_test_token(TEST_USERS[2])

def test_get_subscriptions_with_valid_token(reader_token):
    response = client.get(
        app, "/subscriptions",
        headers={"Authorization": f"Bearer {reader_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json()["symbols"], list)

def test_add_subscription_with_writer_token(writer_token):
    response = client.post(
        app, "/subscriptions",
        headers={"Authorization": f"Bearer {writer_token}"},
        json={"symbol": "XRPUSDT"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_add_subscription_with_reader_token(reader_token):
    response = client.post(
        app, "/subscriptions",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"symbol": "XRPUSDT"}
    )
    assert response.status_code == 403
    assert "Insufficient permissions" in response.text

def test_get_metrics_with_monitoring_token(monitoring_token):
    response = client.get(
        app, "/metrics",
        headers={"Authorization": f"Bearer {monitoring_token}"}
    )
    assert response.status_code == 200
    assert "data_collector_messages_received" in response.text

def test_access_without_token():
    response = client.get(app, "/subscriptions")
    assert response.status_code == 403
    assert "Not authenticated" in response.text

def test_access_with_invalid_token():
    response = client.get(
        app, "/subscriptions",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 403
    assert "Invalid token" in response.text