import pytest
from decimal import Decimal
from main import app
from fastapi.testclient import TestClient
from config import PaperTradingConfig
from __init__ import PaperTradingExchange

client = TestClient(app)

@pytest.fixture
def exchange():
    config = PaperTradingConfig()
    return PaperTradingExchange(config.initial_balances)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "balances" in data
    assert "open_orders" in data

def test_create_buy_order(exchange):
    order = exchange.create_order(
        symbol="BTC/USDT",
        side="buy",
        amount=Decimal('0.1'),
        price=Decimal('50000')
    )
    assert order["status"] == "filled"
    assert order["side"] == "buy"
    assert Decimal(str(order["amount"])) == Decimal('0.1')
    assert Decimal(str(order["price"])) > Decimal('50000')  # includes slippage