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
    Decorator to log execution time of both async and sync functions
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
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
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.4f} seconds with error: {str(e)}")
            raise
    
    # Return appropriate wrapper based on whether the function is async or not
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

def track_metrics(metric_name: str):
    """
    Decorator to track metrics for both async and sync functions
    In production, this would update Prometheus metrics
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            finally:
                execution_time = time.time() - start_time
                # Try to import from the prometheus_metrics module
                try:
                    from trade.utils.prometheus_metrics import (
                        ORDER_EXECUTION_COUNT,
                        ORDER_EXECUTION_LATENCY
                    )
                    
                    # Extract exchange and operation type from args if possible
                    exchange = 'default'
                    operation = 'operation'
                    
                    # Try to extract exchange from self if it's a method
                    if args and hasattr(args[0], 'exchange'):
                        exchange = getattr(args[0], 'exchange', 'default')
                    
                    # Update metrics
                    ORDER_EXECUTION_COUNT.labels(
                        exchange=exchange,
                        symbol='unknown',
                        side='unknown',
                        status='success' if success else 'failed'
                    ).inc()
                    
                    ORDER_EXECUTION_LATENCY.labels(
                        exchange=exchange,
                        symbol='unknown'
                    ).observe(execution_time)
                except ImportError:
                    # Fallback to logging if prometheus metrics not available
                    pass
                
                logger.info(f"Tracked metrics for {metric_name}: success={success}, time={execution_time:.4f}s")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            finally:
                execution_time = time.time() - start_time
                # Try to import from the prometheus_metrics module
                try:
                    from trade.utils.prometheus_metrics import (
                        ORDER_EXECUTION_COUNT,
                        ORDER_EXECUTION_LATENCY
                    )
                    
                    # Extract exchange and operation type from args if possible
                    exchange = 'default'
                    operation = 'operation'
                    
                    # Try to extract exchange from self if it's a method
                    if args and hasattr(args[0], 'exchange'):
                        exchange = getattr(args[0], 'exchange', 'default')
                    
                    # Update metrics
                    ORDER_EXECUTION_COUNT.labels(
                        exchange=exchange,
                        symbol='unknown',
                        side='unknown',
                        status='success' if success else 'failed'
                    ).inc()
                    
                    ORDER_EXECUTION_LATENCY.labels(
                        exchange=exchange,
                        symbol='unknown'
                    ).observe(execution_time)
                except ImportError:
                    # Fallback to logging if prometheus metrics not available
                    pass
                
                logger.info(f"Tracked metrics for {metric_name}: success={success}, time={execution_time:.4f}s")
        
        # Return appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

def circuit_breaker_aware(func):
    """
    Decorator to make functions aware of circuit breaker state
    Assumes the first argument is a class instance with _check_circuit method
    Works with both async and sync functions
    """
    @functools.wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        # Check if circuit breaker allows the operation
        if not self._check_circuit():
            logger.warning(f"Circuit breaker open, rejecting {func.__name__}")
            return None
        
        # Execute the function
        return await func(self, *args, **kwargs)
    
    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs):
        # Check if circuit breaker allows the operation
        if not self._check_circuit():
            logger.warning(f"Circuit breaker open, rejecting {func.__name__}")
            return None
        
        # Execute the function
        return func(self, *args, **kwargs)
    
    # Return appropriate wrapper based on whether the function is async or not
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0,
                       backoff_factor: float = 2.0, max_delay: float = 30.0,
                       retryable_errors: list = None):
    """
    Decorator to retry functions with exponential backoff
    Works with both async and sync functions
    """
    if retryable_errors is None:
        retryable_errors = ["timeout", "rate_limit", "maintenance"]
        
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
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
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            retry_count = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
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
                    time.sleep(delay)
                    
                    # Increase delay for next retry with capping
                    delay = min(delay * backoff_factor, max_delay)
        
        # Return appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator

def alert_on_failure(alert_threshold: int = 3, window_seconds: int = 300):
    """
    Decorator to trigger alerts when a function fails repeatedly
    Works with both async and sync functions
    """
    failure_counts = {}
    failure_timestamps = {}
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
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
                    # Try to use the alerting system if available
                    try:
                        from trade.utils.alerting import AlertManager
                        alert_manager = AlertManager()
                        alert_manager.send_alert(
                            title=f"{func_name} Failure Alert",
                            message=f"{func_name} has failed {len(failure_timestamps[func_name])} times in the last {window_seconds} seconds. Last error: {str(e)}",
                            level="critical",
                            data={"error": str(e), "function": func_name}
                        )
                    except ImportError:
                        # Fallback to logging if alerting system not available
                        pass
                
                # Re-raise the exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            
            # Initialize tracking for this function if needed
            if func_name not in failure_counts:
                failure_counts[func_name] = 0
                failure_timestamps[func_name] = []
            
            try:
                result = func(*args, **kwargs)
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
                    # Try to use the alerting system if available
                    try:
                        from trade.utils.alerting import AlertManager
                        alert_manager = AlertManager()
                        alert_manager.send_alert(
                            title=f"{func_name} Failure Alert",
                            message=f"{func_name} has failed {len(failure_timestamps[func_name])} times in the last {window_seconds} seconds. Last error: {str(e)}",
                            level="critical",
                            data={"error": str(e), "function": func_name}
                        )
                    except ImportError:
                        # Fallback to logging if alerting system not available
                        pass
                
                # Re-raise the exception
                raise
        
        # Return appropriate wrapper based on whether the function is async or not
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator