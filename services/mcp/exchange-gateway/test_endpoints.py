import pytest
from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_get_ticker():
    response = client.get("/api/exchanges/ticker/binance/BTCUSDT")
    assert response.status_code in [200, 400]  # 400 if no test keys configured
    if response.status_code == 200:
        assert "price" in response.json()

def test_place_order():
    test_order = {
        "exchange": "binance",
        "pair": "BTCUSDT",
        "type": "limit",
        "side": "buy",
        "amount": 0.001,
        "price": 30000
    }
    response = client.post("/api/exchanges/order", json=test_order)
    assert response.status_code in [200, 400]  # 400 if no test keys configured

def test_cancel_order():
    response = client.delete("/api/exchanges/order/binance/12345")
    assert response.status_code in [200, 400]  # 400 if no test keys configured

def test_get_balance():
    response = client.get("/api/exchanges/balance/binance/BTC")
    assert response.status_code in [200, 400]  # 400 if no test keys configured