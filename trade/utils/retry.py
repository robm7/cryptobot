import asyncio
import functools
from typing import Callable, Type, Tuple, Optional
import time
from math import pow

class RetryExhaustedError(Exception):
    """All retry attempts were exhausted"""
    pass

def async_retry(max_retries: int = 3, delay: float = 1, 
               exceptions: Tuple[Type[Exception]] = (Exception,)):
    """
    Async retry decorator with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Base delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * pow(2, attempt - 1)
                        await asyncio.sleep(wait_time)
            
            raise RetryExhaustedError(
                f"Failed after {max_retries} attempts"
            ) from last_exception
        return wrapper
    return decorator