"""
Error handling verification tests for the crypto trading bot.
Tests retry mechanisms, circuit breaker functionality, backoff strategies,
and error propagation.
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import patch, AsyncMock, MagicMock, call
from trade.utils.circuit_breaker import CircuitBreaker, CircuitState
from trade.utils.retry import async_retry, RetryExhaustedError

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestException(Exception):
    """Test exception for retry tests"""
    pass

class TestNetworkException(Exception):
    """Test network exception for retry tests"""
    pass

class TestTimeoutException(Exception):
    """Test timeout exception for retry tests"""
    pass

@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing"""
    return CircuitBreaker(
        name="test_circuit",
        error_threshold=3,
        window_seconds=5,
        cool_down=2
    )

@pytest.mark.asyncio
async def test_retry_success():
    """Test successful retry after failures"""
    # Create a mock function that fails twice then succeeds
    mock_func = AsyncMock()
    mock_func.side_effect = [
        TestException("First failure"),
        TestException("Second failure"),
        "success"
    ]
    
    # Apply the retry decorator
    decorated_func = async_retry(
        max_retries=3,
        delay=0.1,
        exceptions=(TestException,)
    )(mock_func)
    
    # Call the decorated function
    result = await decorated_func("test_arg", kwarg="test_kwarg")
    
    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3
    assert result == "success"
    
    # Verify the function was called with the correct arguments
    for call_args in mock_func.call_args_list:
        assert call_args[0][0] == "test_arg"
        assert call_args[1]["kwarg"] == "test_kwarg"

@pytest.mark.asyncio
async def test_retry_exhausted():
    """Test retry exhaustion when all attempts fail"""
    # Create a mock function that always fails
    mock_func = AsyncMock()
    mock_func.side_effect = TestException("Persistent failure")
    
    # Apply the retry decorator
    decorated_func = async_retry(
        max_retries=3,
        delay=0.1,
        exceptions=(TestException,)
    )(mock_func)
    
    # Call the decorated function and expect it to raise RetryExhaustedError
    with pytest.raises(RetryExhaustedError):
        await decorated_func()
    
    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_retry_with_multiple_exceptions():
    """Test retry with multiple exception types"""
    # Create a mock function that fails with different exceptions
    mock_func = AsyncMock()
    mock_func.side_effect = [
        TestNetworkException("Network error"),
        TestTimeoutException("Timeout error"),
        "success"
    ]
    
    # Apply the retry decorator with multiple exception types
    decorated_func = async_retry(
        max_retries=3,
        delay=0.1,
        exceptions=(TestNetworkException, TestTimeoutException)
    )(mock_func)
    
    # Call the decorated function
    result = await decorated_func()
    
    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3
    assert result == "success"

@pytest.mark.asyncio
async def test_retry_with_unexpected_exception():
    """Test retry with an unexpected exception type"""
    # Create a mock function that fails with an unexpected exception
    mock_func = AsyncMock()
    mock_func.side_effect = ValueError("Unexpected error")
    
    # Apply the retry decorator with a different exception type
    decorated_func = async_retry(
        max_retries=3,
        delay=0.1,
        exceptions=(TestException,)
    )(mock_func)
    
    # Call the decorated function and expect it to raise the original exception
    with pytest.raises(ValueError):
        await decorated_func()
    
    # Verify the function was called only once (no retries for unexpected exceptions)
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_retry_exponential_backoff():
    """Test exponential backoff in retry mechanism"""
    # Create a mock function that always fails
    mock_func = AsyncMock()
    mock_func.side_effect = [
        TestException("First failure"),
        TestException("Second failure"),
        TestException("Third failure")
    ]
    
    # Mock asyncio.sleep to track delay times
    sleep_times = []
    
    async def mock_sleep(delay):
        sleep_times.append(delay)
    
    # Apply the retry decorator with a larger delay for more visible backoff
    decorated_func = async_retry(
        max_retries=3,
        delay=0.5,
        exceptions=(TestException,)
    )(mock_func)
    
    # Call the decorated function with mocked sleep
    with patch('asyncio.sleep', mock_sleep), pytest.raises(RetryExhaustedError):
        await decorated_func()
    
    # Verify exponential backoff pattern
    assert len(sleep_times) == 2  # Two retries = two sleeps
    assert sleep_times[1] > sleep_times[0]  # Second delay should be longer
    assert sleep_times[1] == pytest.approx(sleep_times[0] * 2, abs=0.1)  # Should double each time

def test_circuit_breaker_initial_state(circuit_breaker):
    """Test circuit breaker initial state"""
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.error_count == 0
    assert circuit_breaker.last_failure_time is None

def test_circuit_breaker_error_recording(circuit_breaker):
    """Test circuit breaker error recording"""
    # Record errors below the threshold
    for i in range(2):
        circuit_breaker.record_error()
    
    # Verify state is still CLOSED
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.error_count == 2
    assert circuit_breaker.last_failure_time is not None

def test_circuit_breaker_tripping(circuit_breaker):
    """Test circuit breaker tripping when error threshold is reached"""
    # Record errors up to the threshold
    for i in range(3):
        circuit_breaker.record_error()
    
    # Verify state is now OPEN
    assert circuit_breaker.state == CircuitState.OPEN
    assert circuit_breaker.error_count == 3
    assert circuit_breaker.last_failure_time is not None

def test_circuit_breaker_cool_down(circuit_breaker):
    """Test circuit breaker cool down period"""
    # Trip the circuit breaker
    for i in range(3):
        circuit_breaker.record_error()
    
    # Verify state is OPEN
    assert circuit_breaker.state == CircuitState.OPEN
    
    # Check if circuit is open (should be)
    assert circuit_breaker.is_open() is True
    
    # Wait for cool down period
    time.sleep(2.1)  # Just over the 2-second cool down
    
    # Check if circuit is open (should now be HALF_OPEN)
    assert circuit_breaker.is_open() is False
    assert circuit_breaker.state == CircuitState.HALF_OPEN

def test_circuit_breaker_reset(circuit_breaker):
    """Test circuit breaker reset after successful operation"""
    # Trip the circuit breaker
    for i in range(3):
        circuit_breaker.record_error()
    
    # Wait for cool down period
    time.sleep(2.1)
    
    # Check state (should be HALF_OPEN)
    assert circuit_breaker.is_open() is False
    assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    # Record a success
    circuit_breaker.success()
    
    # Verify state is reset to CLOSED
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.error_count == 0
    assert circuit_breaker.last_failure_time is None

def test_circuit_breaker_window_reset(circuit_breaker):
    """Test circuit breaker error window reset"""
    # Record errors but not enough to trip
    for i in range(2):
        circuit_breaker.record_error()
    
    # Verify state is still CLOSED
    assert circuit_breaker.state == CircuitState.CLOSED
    assert circuit_breaker.error_count == 2
    
    # Wait for the window to expire
    time.sleep(5.1)  # Just over the 5-second window
    
    # Record another error
    circuit_breaker.record_error()
    
    # Verify error count was reset and is now 1
    assert circuit_breaker.error_count == 1
    assert circuit_breaker.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_integration_retry_with_circuit_breaker():
    """Test integration of retry mechanism with circuit breaker"""
    # Create a circuit breaker
    circuit = CircuitBreaker(
        name="integration_test",
        error_threshold=3,
        window_seconds=5,
        cool_down=1
    )
    
    # Create a function that uses the circuit breaker
    async def test_function():
        if circuit.is_open():
            raise Exception("Circuit is open")
        
        try:
            # Simulate an operation that might fail
            if test_function.fail:
                test_function.fail = False  # Succeed on retry
                raise TestException("Simulated failure")
            return "success"
        except Exception as e:
            circuit.record_error()
            raise
    
    # Set initial state
    test_function.fail = True
    
    # Apply the retry decorator
    decorated_func = async_retry(
        max_retries=2,
        delay=0.1,
        exceptions=(TestException,)
    )(test_function)
    
    # Call the function - should fail once then succeed
    result = await decorated_func()
    assert result == "success"
    
    # Now trip the circuit breaker
    for i in range(3):
        circuit.record_error()
    
    # Call the function again - should raise because circuit is open
    with pytest.raises(Exception, match="Circuit is open"):
        await decorated_func()
    
    # Wait for cool down
    await asyncio.sleep(1.1)
    
    # Set to succeed on next call
    test_function.fail = False
    
    # Call again - should succeed and reset circuit
    result = await decorated_func()
    assert result == "success"
    
    # Record success to reset circuit
    circuit.success()
    
    # Verify circuit is closed
    assert circuit.state == CircuitState.CLOSED

@pytest.mark.asyncio
async def test_error_propagation():
    """Test proper error propagation with detailed information"""
    # Create a chain of functions that propagate errors
    async def lowest_level():
        raise TestException("Low-level error")
    
    async def mid_level():
        try:
            await lowest_level()
        except TestException as e:
            # Add context and propagate
            raise TestException(f"Mid-level context: {str(e)}") from e
    
    async def high_level():
        try:
            await mid_level()
        except TestException as e:
            # Add context and propagate
            raise TestException(f"High-level context: {str(e)}") from e
    
    # Call the high-level function and capture the exception
    with pytest.raises(TestException) as excinfo:
        await high_level()
    
    # Verify the error message contains all context
    assert "High-level context" in str(excinfo.value)
    assert "Mid-level context" in str(excinfo.value)
    assert "Low-level error" in str(excinfo.value)
    
    # Verify the exception chain
    cause = excinfo.value.__cause__
    assert isinstance(cause, TestException)
    assert "Mid-level context" in str(cause)
    
    # Verify the full chain
    cause_of_cause = cause.__cause__
    assert isinstance(cause_of_cause, TestException)
    assert "Low-level error" in str(cause_of_cause)

@pytest.mark.asyncio
async def test_retry_with_logging(caplog):
    """Test retry mechanism with proper logging"""
    caplog.set_level(logging.INFO)
    
    # Create a mock function that fails then succeeds
    mock_func = AsyncMock()
    mock_func.side_effect = [
        TestException("First failure"),
        "success"
    ]
    
    # Create a logger for the test
    test_logger = logging.getLogger("test_retry_logger")
    
    # Apply the retry decorator
    @async_retry(max_retries=3, delay=0.1, exceptions=(TestException,))
    async def logged_function():
        try:
            return await mock_func()
        except Exception as e:
            test_logger.error(f"Error in function: {e}")
            raise
    
    # Call the function
    result = await logged_function()
    
    # Verify the result
    assert result == "success"
    
    # Verify logging occurred
    assert any("Error in function: First failure" in record.message for record in caplog.records)

@pytest.mark.asyncio
async def test_circuit_breaker_with_multiple_services():
    """Test circuit breaker isolation between different services"""
    # Create circuit breakers for different services
    circuit_a = CircuitBreaker("service_a", error_threshold=2)
    circuit_b = CircuitBreaker("service_b", error_threshold=2)
    
    # Trip circuit A
    circuit_a.record_error()
    circuit_a.record_error()
    
    # Verify circuit A is open but circuit B is closed
    assert circuit_a.state == CircuitState.OPEN
    assert circuit_b.state == CircuitState.CLOSED
    
    # Verify is_open() returns correct values
    assert circuit_a.is_open() is True
    assert circuit_b.is_open() is False

@pytest.mark.asyncio
async def test_retry_with_custom_backoff():
    """Test retry with a custom backoff strategy"""
    # Create a mock function that always fails
    mock_func = AsyncMock()
    mock_func.side_effect = TestException("Failure")
    
    # Mock asyncio.sleep to track delay times
    sleep_times = []
    
    async def mock_sleep(delay):
        sleep_times.append(delay)
    
    # Create a custom backoff function
    def custom_backoff(attempt):
        # Linear backoff instead of exponential
        return 0.1 * attempt
    
    # Apply a custom retry decorator with the custom backoff
    async def custom_retry_decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(1, 4):  # 3 attempts
                try:
                    return await func(*args, **kwargs)
                except TestException:
                    if attempt < 3:  # Don't sleep after last attempt
                        await asyncio.sleep(custom_backoff(attempt))
            raise RetryExhaustedError("Failed after 3 attempts")
        return wrapper
    
    # Apply the custom retry decorator
    decorated_func = await custom_retry_decorator(mock_func)
    
    # Call the decorated function with mocked sleep
    with patch('asyncio.sleep', mock_sleep), pytest.raises(RetryExhaustedError):
        await decorated_func()
    
    # Verify linear backoff pattern
    assert len(sleep_times) == 2  # Two retries = two sleeps
    assert sleep_times[0] == pytest.approx(0.1, abs=0.01)  # First delay = 0.1
    assert sleep_times[1] == pytest.approx(0.2, abs=0.01)  # Second delay = 0.2