import pytest
from unittest.mock import AsyncMock, patch
from trade.utils.retry import async_retry, is_retryable_error, RetryConfig
import asyncio

# Prevent pytest from loading any conftest.py
def pytest_configure(config):
    config.option.importmode = "importlib"

@pytest.mark.asyncio
async def test_async_retry_success():
    mock_func = AsyncMock(return_value="success")
    
    @async_retry(RetryConfig(max_retries=2))
    async def test_func():
        return await mock_func()
    
    result = await test_func()
    assert result == "success"
    mock_func.assert_called_once()

@pytest.mark.asyncio
async def test_async_retry_failure():
    mock_func = AsyncMock(side_effect=Exception("test error"))
    
    @async_retry(RetryConfig(max_retries=2))
    async def test_func():
        return await mock_func()
    
    with pytest.raises(Exception, match="test error"):
        await test_func()
    
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_async_retry_backoff():
    mock_func = AsyncMock(side_effect=[Exception(), Exception(), "success"])
    
    @async_retry(RetryConfig(max_retries=2, initial_delay=0.1))
    async def test_func():
        return await mock_func()
    
    with patch('asyncio.sleep') as mock_sleep:
        await test_func()
        assert mock_sleep.call_count == 2
        assert mock_sleep.call_args_list[0][0][0] == pytest.approx(0.1)
        assert mock_sleep.call_args_list[1][0][0] == pytest.approx(0.2)

def test_is_retryable_error():
    assert is_retryable_error(Exception("timeout error")) is True
    assert is_retryable_error(Exception("rate limit exceeded")) is True
    assert is_retryable_error(Exception("429 too many requests")) is True
    assert is_retryable_error(Exception("invalid order")) is False