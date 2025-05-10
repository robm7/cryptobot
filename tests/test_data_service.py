import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from data.main import app
from data.models.ohlcv import OHLCV
import json

client = TestClient(app)

@pytest.fixture
def mock_ohlcv_data():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "open": 50000.0,
        "high": 50500.0,
        "low": 49900.0,
        "close": 50300.0,
        "volume": 100.0,
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "timeframe": "1m"
    }

@pytest.mark.asyncio
async def test_websocket_ohlcv(mock_ohlcv_data):
    # Mock the OHLCV.get_latest method
    original_method = OHLCV.get_latest
    OHLCV.get_latest = lambda *args, **kwargs: mock_ohlcv_data
    
    with client.websocket_connect("/api/v1/data/ws/ohlcv/binance/BTCUSDT/1m") as websocket:
        data = websocket.receive_json()
        assert data == mock_ohlcv_data
    
    # Restore original method
    OHLCV.get_latest = original_method

@pytest.mark.asyncio
async def test_get_historical_ohlcv(mock_ohlcv_data):
    # Mock the OHLCV.get_historical method
    original_method = OHLCV.get_historical
    OHLCV.get_historical = lambda *args, **kwargs: [OHLCV(**mock_ohlcv_data)]
    
    response = client.get(
        "/api/v1/data/ohlcv/binance/BTCUSDT/1m",
        params={
            "start": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "end": datetime.utcnow().isoformat()
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["symbol"] == "BTCUSDT"
    
    # Restore original method
    OHLCV.get_historical = original_method

def test_data_normalization():
    # Test symbol normalization
    assert OHLCV.normalize_symbol("binance", "BTC/USDT") == "BTCUSDT"
    assert OHLCV.normalize_symbol("kraken", "BTC-USDT") == "BTCUSDT"
    
    # Test timeframe normalization
    assert OHLCV.normalize_timeframe("binance", "1min") == "1m"
    assert OHLCV.normalize_timeframe("kraken", "60") == "1h"
    assert OHLCV.normalize_timeframe("coinbase", "1440") == "1d"