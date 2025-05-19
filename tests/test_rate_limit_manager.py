import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from utils.rate_limit_manager import (
    RateLimitRule,
    RateLimitManager,
    apply_rate_limiting,
    rate_limited
)

@pytest.fixture
def rate_limit_rule():
    """Create a rate limit rule for testing"""
    return RateLimitRule(max_requests=10, time_window_seconds=60)

@pytest.fixture
def rate_limit_manager():
    """Create a rate limit manager for testing"""
    manager = RateLimitManager()
    # Reset to clean state for testing
    manager.exchange_limits = {}
    manager.endpoint_limits = {}
    manager.error_counts = {}
    manager.backoff_multipliers = {}
    return manager

def test_rate_limit_rule_initialization(rate_limit_rule):
    """Test rate limit rule initialization"""
    assert rate_limit_rule.max_requests == 10
    assert rate_limit_rule.time_window_seconds == 60
    assert rate_limit_rule.weight_multiplier == 1.0
    assert isinstance(rate_limit_rule.requests, deque)
    assert rate_limit_rule.requests.maxlen == 10

def test_rate_limit_rule_record_request(rate_limit_rule):
    """Test recording requests in a rate limit rule"""
    # Record a request
    rate_limit_rule.record_request()
    
    # Verify request was recorded
    assert len(rate_limit_rule.requests) == 1
    timestamp, weight = rate_limit_rule.requests[0]
    assert isinstance(timestamp, float)
    assert weight == 1.0
    
    # Record a request with custom weight
    rate_limit_rule.record_request(weight=2.5)
    
    # Verify request was recorded with correct weight
    assert len(rate_limit_rule.requests) == 2
    _, weight = rate_limit_rule.requests[1]
    assert weight == 2.5

def test_rate_limit_rule_get_usage(rate_limit_rule):
    """Test getting usage statistics from a rate limit rule"""
    # No requests yet
    count, percentage = rate_limit_rule.get_usage()
    assert count == 0
    assert percentage == 0.0
    
    # Record some requests
    for _ in range(5):
        rate_limit_rule.record_request()
    
    # Check usage
    count, percentage = rate_limit_rule.get_usage()
    assert count == 5
    assert percentage == 50.0
    
    # Record requests with different weights
    rate_limit_rule.requests.clear()
    rate_limit_rule.record_request(weight=2.0)
    rate_limit_rule.record_request(weight=3.0)
    
    # Check usage with weights
    count, percentage = rate_limit_rule.get_usage()
    assert count == 2
    assert percentage == 50.0  # (2.0 + 3.0) / 10 * 100

def test_rate_limit_rule_should_throttle(rate_limit_rule):
    """Test throttling logic in rate limit rule"""
    # No requests yet
    should_throttle, wait_time = rate_limit_rule.should_throttle()
    assert not should_throttle
    assert wait_time == 0
    
    # Record requests up to 70% of limit
    for _ in range(7):
        rate_limit_rule.record_request()
    
    # Should not throttle yet
    should_throttle, wait_time = rate_limit_rule.should_throttle()
    assert not should_throttle
    assert wait_time == 0
    
    # Record more requests to exceed 80% threshold
    for _ in range(2):
        rate_limit_rule.record_request()
    
    # Should throttle now
    should_throttle, wait_time = rate_limit_rule.should_throttle()
    assert should_throttle
    assert wait_time > 0
    assert wait_time <= 30  # Max half the window size

def test_rate_limit_manager_singleton():
    """Test that RateLimitManager is a singleton"""
    manager1 = RateLimitManager()
    manager2 = RateLimitManager()
    assert manager1 is manager2

def test_rate_limit_manager_configure_exchange(rate_limit_manager):
    """Test configuring exchange-wide limits"""
    # Configure a new exchange
    rate_limit_manager.configure_exchange('test_exchange', [
        {'max_requests': 100, 'time_window_seconds': 60},
        {'max_requests': 1000, 'time_window_seconds': 3600}
    ])
    
    # Verify configuration
    assert 'test_exchange' in rate_limit_manager.exchange_limits
    assert len(rate_limit_manager.exchange_limits['test_exchange']) == 2
    
    rule1 = rate_limit_manager.exchange_limits['test_exchange'][0]
    assert rule1.max_requests == 100
    assert rule1.time_window_seconds == 60
    
    rule2 = rate_limit_manager.exchange_limits['test_exchange'][1]
    assert rule2.max_requests == 1000
    assert rule2.time_window_seconds == 3600

def test_rate_limit_manager_configure_endpoint(rate_limit_manager):
    """Test configuring endpoint-specific limits"""
    # Configure an endpoint
    rate_limit_manager.configure_endpoint(
        'test_exchange', 'order', 20, 60, 2.0
    )
    
    # Verify configuration
    assert 'test_exchange' in rate_limit_manager.endpoint_limits
    assert 'order' in rate_limit_manager.endpoint_limits['test_exchange']
    
    rule = rate_limit_manager.endpoint_limits['test_exchange']['order']
    assert rule.max_requests == 20
    assert rule.time_window_seconds == 60
    assert rule.weight_multiplier == 2.0

def test_rate_limit_manager_record_request(rate_limit_manager):
    """Test recording requests in the manager"""
    # Configure exchange and endpoint
    rate_limit_manager.configure_exchange('test_exchange', [
        {'max_requests': 100, 'time_window_seconds': 60}
    ])
    rate_limit_manager.configure_endpoint(
        'test_exchange', 'order', 20, 60, 2.0
    )
    
    # Record a request
    rate_limit_manager.record_request('test_exchange', 'order', 1.0)
    
    # Verify request was recorded in both exchange and endpoint rules
    exchange_rule = rate_limit_manager.exchange_limits['test_exchange'][0]
    endpoint_rule = rate_limit_manager.endpoint_limits['test_exchange']['order']
    
    assert len(exchange_rule.requests) == 1
    assert len(endpoint_rule.requests) == 1
    
    # Endpoint should record with weight multiplier
    _, weight = endpoint_rule.requests[0]
    assert weight == 2.0  # 1.0 * 2.0

def test_rate_limit_manager_record_error(rate_limit_manager):
    """Test recording errors for backoff strategy"""
    # Record an error
    rate_limit_manager.record_error('test_exchange', 'rate_limit')
    
    # Verify error was recorded
    assert 'test_exchange' in rate_limit_manager.error_counts
    assert len(rate_limit_manager.error_counts['test_exchange']) == 1
    
    # Verify backoff multiplier was increased
    assert 'test_exchange' in rate_limit_manager.backoff_multipliers
    assert rate_limit_manager.backoff_multipliers['test_exchange'] > 1.0

def test_rate_limit_manager_reset_backoff(rate_limit_manager):
    """Test resetting backoff multiplier"""
    # Set a backoff multiplier
    rate_limit_manager.backoff_multipliers['test_exchange'] = 5.0
    
    # Reset backoff
    rate_limit_manager.reset_backoff('test_exchange')
    
    # Verify backoff was reduced but not reset completely
    assert rate_limit_manager.backoff_multipliers['test_exchange'] < 5.0
    
    # Multiple resets should eventually reach 1.0
    for _ in range(10):
        rate_limit_manager.reset_backoff('test_exchange')
    
    assert rate_limit_manager.backoff_multipliers['test_exchange'] == 1.0

def test_rate_limit_manager_should_throttle(rate_limit_manager):
    """Test throttling logic in the manager"""
    # Configure exchange and endpoint
    rate_limit_manager.configure_exchange('test_exchange', [
        {'max_requests': 10, 'time_window_seconds': 60}
    ])
    
    # No requests yet
    should_throttle, wait_time = rate_limit_manager.should_throttle('test_exchange')
    assert not should_throttle
    assert wait_time == 0
    
    # Record requests up to 90% of limit
    for _ in range(9):
        rate_limit_manager.record_request('test_exchange')
    
    # Should throttle now
    should_throttle, wait_time = rate_limit_manager.should_throttle('test_exchange')
    assert should_throttle
    assert wait_time > 0
    
    # Test with backoff multiplier
    rate_limit_manager.backoff_multipliers['test_exchange'] = 2.0
    _, wait_time_with_backoff = rate_limit_manager.should_throttle('test_exchange')
    assert wait_time_with_backoff > wait_time  # Should be doubled

def test_rate_limit_manager_get_usage_stats(rate_limit_manager):
    """Test getting usage statistics"""
    # Configure exchange and endpoint
    rate_limit_manager.configure_exchange('test_exchange', [
        {'max_requests': 100, 'time_window_seconds': 60}
    ])
    rate_limit_manager.configure_endpoint(
        'test_exchange', 'order', 20, 60, 2.0
    )
    
    # Record some requests
    for _ in range(5):
        rate_limit_manager.record_request('test_exchange', 'order')
    
    # Record an error
    rate_limit_manager.record_error('test_exchange', 'rate_limit')
    
    # Get usage stats
    stats = rate_limit_manager.get_usage_stats('test_exchange')
    
    # Verify stats
    assert stats['exchange_id'] == 'test_exchange'
    assert len(stats['limits']) == 1
    assert stats['limits'][0]['current_count'] == 5
    assert stats['limits'][0]['usage_percentage'] == 5.0
    
    assert 'order' in stats['endpoints']
    assert stats['endpoints']['order']['current_count'] == 5
    assert stats['endpoints']['order']['usage_percentage'] == 50.0  # 5 * 2.0 / 20 * 100
    
    assert stats['errors']['count'] == 1
    assert stats['errors']['rate_limit_errors'] == 1
    assert stats['backoff_multiplier'] > 1.0

@pytest.mark.asyncio
async def test_apply_rate_limiting():
    """Test apply_rate_limiting function"""
    # Create a manager with a strict limit for testing
    manager = RateLimitManager()
    manager.configure_exchange('test_exchange', [
        {'max_requests': 5, 'time_window_seconds': 60}
    ])
    
    # Record requests up to the limit
    for _ in range(4):
        manager.record_request('test_exchange')
    
    # Next request should throttle
    start_time = time.time()
    await apply_rate_limiting('test_exchange')
    elapsed = time.time() - start_time
    
    # Should have waited some time
    assert elapsed > 0.1

@pytest.mark.asyncio
async def test_rate_limited_decorator():
    """Test rate_limited decorator"""
    # Create a test async function
    @rate_limited('test_exchange', 'test_endpoint')
    async def test_function():
        return "success"
    
    # Create a manager with a strict limit for testing
    manager = RateLimitManager()
    manager.configure_exchange('test_exchange', [
        {'max_requests': 5, 'time_window_seconds': 60}
    ])
    
    # Record requests up to the limit
    for _ in range(4):
        manager.record_request('test_exchange')
    
    # Call the decorated function
    start_time = time.time()
    result = await test_function()
    elapsed = time.time() - start_time
    
    # Should have waited some time and returned the correct result
    assert elapsed > 0.1
    assert result == "success"
    
    # Test error handling
    @rate_limited('test_exchange', 'test_endpoint')
    async def failing_function():
        raise Exception("rate limit exceeded")
    
    # Reset backoff multiplier
    manager.backoff_multipliers['test_exchange'] = 1.0
    
    # Call the failing function
    with pytest.raises(Exception):
        await failing_function()
    
    # Should have recorded the error and increased backoff
    assert manager.backoff_multipliers['test_exchange'] > 1.0