import asyncio
import time
from unittest.mock import patch, MagicMock

import pytest
from trade.utils.websocket import BinanceWebSocket

@pytest.fixture
def mock_ws():
    with patch('aiohttp.ClientSession.ws_connect') as mock_connect:
        mock_ws = MagicMock()
        mock_connect.return_value = mock_ws
        yield mock_ws

@pytest.mark.asyncio
async def test_rate_limiting(mock_ws):
    """Test rate limiting behavior"""
    ws = BinanceWebSocket()
    
    # Mock rate limit headers
    mock_ws.receive.return_value = MagicMock(
        type=MagicMock(TEXT=True),
        data=json.dumps({'stream': 'test', 'data': {}})
    )
    
    # Exhaust rate limit
    for _ in range(10):
        await ws.subscribe('test_stream', lambda x: None)
    
    # Should hit rate limit
    start_time = time.time()
    await ws.subscribe('test_stream', lambda x: None)
    assert time.time() - start_time >= 1.0  # Should have delayed

@pytest.mark.asyncio
async def test_circuit_breaker(mock_ws):
    """Test circuit breaker state transitions"""
    ws = BinanceWebSocket()
    
    # Force connection errors
    mock_ws.receive.side_effect = Exception("Test error")
    
    # Should trip circuit after multiple failures
    for _ in range(5):
        try:
            await ws.subscribe('test_stream', lambda x: None)
        except:
            pass
    
    assert ws._circuit_state == 'open'
    
    # Should reset after timeout
    ws._circuit_reset_time = time.time() - 1
    await ws.subscribe('test_stream', lambda x: None)
    assert ws._circuit_state == 'half-open'

@pytest.mark.asyncio
async def test_metrics_collection(mock_ws):
    """Test metrics are properly collected"""
    ws = BinanceWebSocket()
    
    # Trigger rate limit
    for _ in range(11):
        await ws.subscribe('test_stream', lambda x: None)
    
    # Check metrics were updated
    assert ws._metrics['rate_limit_events']._metrics[('test_stream',)]._value > 0
    
    # Check circuit state metrics
    assert ws._metrics['circuit_state']._metrics[('closed',)]._value == 1