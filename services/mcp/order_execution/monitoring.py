import functools
import time
import logging
import asyncio
from typing import Callable, Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_execution_time(func):
    """
    Decorator to log execution time of async functions
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.4f} seconds with error: {str(e)}")
            raise
    return wrapper

def track_metrics(metric_name: str):
    """
    Decorator to track metrics for async functions
    In production, this would update Prometheus metrics
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            finally:
                execution_time = time.time() - start_time
                # In production, these would update Prometheus metrics
                # success_counter = Counter(f'{metric_name}_success_total', f'Successful {metric_name} operations')
                # failure_counter = Counter(f'{metric_name}_failure_total', f'Failed {metric_name} operations')
                # latency_histogram = Histogram(f'{metric_name}_latency_seconds', f'{metric_name} operation latency')
                
                # if success:
                #     success_counter.inc()
                # else:
                #     failure_counter.inc()
                # latency_histogram.observe(execution_time)
                
                logger.info(f"Tracked metrics for {metric_name}: success={success}, time={execution_time:.4f}s")
        return wrapper
    return decorator

def circuit_breaker_aware(func):
    """
    Decorator to make functions aware of circuit breaker state
    Assumes the first argument is a class instance with _check_circuit method
    """
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        # Check if circuit breaker allows the operation
        if not self._check_circuit():
            logger.warning(f"Circuit breaker open, rejecting {func.__name__}")
            return None
        
        # Execute the function
        return await func(self, *args, **kwargs)
    return wrapper

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, 
                      backoff_factor: float = 2.0, max_delay: float = 30.0,
                      retryable_errors: list = None):
    """
    Decorator to retry async functions with exponential backoff
    """
    if retryable_errors is None:
        retryable_errors = ["timeout", "rate_limit", "maintenance"]
        
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retry_count = 0
            delay = initial_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_type = type(e).__name__.lower()
                    
                    # Check if we should retry
                    if (retry_count >= max_retries or 
                        not any(err in error_type for err in retryable_errors)):
                        logger.error(f"Max retries exceeded or non-retryable error: {str(e)}")
                        raise
                    
                    # Increment retry count
                    retry_count += 1
                    
                    # Log the retry
                    logger.warning(
                        f"Retrying {func.__name__} after error: {str(e)}. "
                        f"Retry {retry_count}/{max_retries} in {delay:.2f}s"
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(delay)
                    
                    # Increase delay for next retry with capping
                    delay = min(delay * backoff_factor, max_delay)
        return wrapper
    return decorator

def alert_on_failure(alert_threshold: int = 3, window_seconds: int = 300):
    """
    Decorator to trigger alerts when a function fails repeatedly
    """
    failure_counts = {}
    failure_timestamps = {}
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            
            # Initialize tracking for this function if needed
            if func_name not in failure_counts:
                failure_counts[func_name] = 0
                failure_timestamps[func_name] = []
            
            try:
                result = await func(*args, **kwargs)
                # Reset failure count on success
                failure_counts[func_name] = 0
                return result
            except Exception as e:
                # Record failure
                now = time.time()
                failure_counts[func_name] += 1
                failure_timestamps[func_name].append(now)
                
                # Remove timestamps outside the window
                window_start = now - window_seconds
                failure_timestamps[func_name] = [
                    ts for ts in failure_timestamps[func_name] if ts > window_start
                ]
                
                # Check if alert threshold is reached
                if len(failure_timestamps[func_name]) >= alert_threshold:
                    logger.critical(
                        f"ALERT: {func_name} has failed {len(failure_timestamps[func_name])} "
                        f"times in the last {window_seconds} seconds. Last error: {str(e)}"
                    )
                    # In production, this would trigger an actual alert
                    # alert_system.trigger(f"{func_name}_failure", str(e))
                
                # Re-raise the exception
                raise
        return wrapper
    return decorator