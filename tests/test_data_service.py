import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from data.main import app
from data.models.ohlcv import OHLCV
import json
from unittest.mock import patch, AsyncMock # Added patch and AsyncMock

client = TestClient(app)

@pytest.fixture(scope="function") # Changed to function scope for cleaner test isolation with mocks
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

@pytest.mark.asyncio
async def test_get_historical_ohlcv_error(mock_ohlcv_data):
    # Mock OHLCV.get_historical to raise an exception
    original_method = OHLCV.get_historical
    OHLCV.get_historical = AsyncMock(side_effect=Exception("Database connection error"))
    
    response = client.get(
        "/api/v1/data/ohlcv/binance/BTCUSDT/1m",
        params={
            "start": (datetime.utcnow() - timedelta(days=1)).isoformat(),
            "end": datetime.utcnow().isoformat()
        }
    )
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"] == "Database connection error"
    
    # Restore original method
    OHLCV.get_historical = original_method

@pytest.mark.asyncio
async def test_get_historical_ohlcv_caching(mock_ohlcv_data):
    with patch('data.routers.data.redis_client') as mock_redis:
        # --- Test Cache Miss ---
        mock_redis.get.return_value = None # Simulate cache miss
        mock_redis.setex = AsyncMock() # Mock setex

        original_get_historical = OHLCV.get_historical
        OHLCV.get_historical = AsyncMock(return_value=[OHLCV(**mock_ohlcv_data)])

        response_miss = client.get("/api/v1/data/ohlcv/binance/BTCUSDT/1h") # Use different timeframe for unique cache key
        assert response_miss.status_code == 200
        data_miss = response_miss.json()
        assert len(data_miss) == 1
        
        OHLCV.get_historical.assert_called_once() # Should be called on miss
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_called_once()

        # --- Test Cache Hit ---
        OHLCV.get_historical.reset_mock() # Reset call count for get_historical
        mock_redis.get.reset_mock()
        mock_redis.setex.reset_mock()

        # Simulate data now being in cache
        cached_value = json.dumps([mock_ohlcv_data]) # Data as it would be stored
        mock_redis.get.return_value = cached_value
        
        response_hit = client.get("/api/v1/data/ohlcv/binance/BTCUSDT/1h") # Same request
        assert response_hit.status_code == 200
        data_hit = response_hit.json()
        assert len(data_hit) == 1
        assert data_hit[0]["symbol"] == "BTCUSDT" # Check if deserialized correctly

        OHLCV.get_historical.assert_not_called() # Should NOT be called on hit
        mock_redis.get.assert_called_once()
        mock_redis.setex.assert_not_called()

        # Restore
        OHLCV.get_historical = original_get_historical


@pytest.mark.asyncio
async def test_websocket_ohlcv_error(mock_ohlcv_data):
    original_method = OHLCV.get_latest
    # Mock OHLCV.get_latest to raise an exception after the first successful call
    call_count = 0
    async def mock_get_latest_with_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_ohlcv_data
        else:
            raise Exception("Simulated data source error")

    OHLCV.get_latest = mock_get_latest_with_error
    
    with client.websocket_connect("/api/v1/data/ws/ohlcv/binance/ETHUSDT/5m") as websocket:
        # First message should be data
        data1 = websocket.receive_json()
        assert data1 == mock_ohlcv_data
        
        # Second attempt by the loop should trigger the error
        data2 = websocket.receive_json() # This will be the error message
        assert "error" in data2
        assert data2["error"] == "Simulated data source error"
    
    OHLCV.get_latest = original_method


def test_data_normalization():
    # Test symbol normalization
    assert OHLCV.normalize_symbol("binance", "BTC/USDT") == "BTCUSDT"
    assert OHLCV.normalize_symbol("kraken", "BTC-USDT") == "BTCUSDT"
    
    # Test timeframe normalization
    assert OHLCV.normalize_timeframe("binance", "1min") == "1m"
    assert OHLCV.normalize_timeframe("kraken", "60") == "1h"
    assert OHLCV.normalize_timeframe("coinbase", "1440") == "1d"