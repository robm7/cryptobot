import time
import functools
from typing import Callable, Any, Awaitable
import logging

# Assuming prometheus_metrics.py is in the same directory or accessible via path
from .prometheus_metrics import ORDER_EXECUTION_COUNT, ORDER_EXECUTION_LATENCY, ORDER_RETRY_COUNT 
# Import specific exceptions to distinguish failures
from trade.utils.exceptions import ExchangeError, RateLimitError, ConnectionError, InvalidOrderError, InsufficientFundsError 


logger = logging.getLogger(__name__)

def monitor_execution(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    A decorator to monitor the execution of an exchange operation.
    It records latency, success/failure counts.
    It assumes the decorated function is an async method of a class
    that has an 'exchange' attribute with an 'exchange_name' property.
    It also assumes 'symbol' might be passed in kwargs or args.
    """
    @functools.wraps(func)
    async def wrapper(self_instance: Any, *args: Any, **kwargs: Any) -> Any:
        start_time = time.monotonic()
        status = "success" # Assume success initially
        exchange_name = getattr(getattr(self_instance, 'exchange', None), 'exchange_name', 'unknown_exchange')
        
        # Try to determine symbol and side from args or kwargs for better labeling
        symbol = kwargs.get('symbol', args[0] if args else 'unknown_symbol')
        side = kwargs.get('side', args[1] if len(args) > 1 else 'unknown_side')
        
        # If symbol is not the first arg, try to find it by name in kwargs or other args
        if symbol == 'unknown_symbol':
            for arg in args:
                if isinstance(arg, str) and ('/' in arg or '-' in arg): # Basic check for a symbol format
                    symbol = arg
                    break
        
        if side == 'unknown_side': # For cancel_order, side might not be direct
             if 'cancel_order' in func.__name__:
                 side = 'cancel' # Special side for cancel operations

        try:
            result = await func(self_instance, *args, **kwargs)
            # ORDER_EXECUTION_COUNT status will be 'success'
        except (InvalidOrderError, InsufficientFundsError) as e:
            status = "rejected" # Specific type of failure - client error, not necessarily exchange down
            logger.warning(f"Order execution rejected for {func.__name__} on {exchange_name} for {symbol}: {e}")
            ORDER_EXECUTION_COUNT.labels(
                exchange=exchange_name, 
                symbol=symbol, 
                side=side, 
                status=status
            ).inc()
            raise # Re-raise the exception
        except (RateLimitError, ConnectionError) as e:
            status = "failure_retryable" # Failure that might be retried
            logger.warning(f"Retryable failure during {func.__name__} on {exchange_name} for {symbol}: {e}")
            ORDER_EXECUTION_COUNT.labels(
                exchange=exchange_name, 
                symbol=symbol, 
                side=side, 
                status=status
            ).inc()
            raise # Re-raise for retry logic to handle
        except ExchangeError as e: # Other non-retryable exchange errors
            status = "failure_exchange"
            logger.error(f"Exchange error during {func.__name__} on {exchange_name} for {symbol}: {e}")
            ORDER_EXECUTION_COUNT.labels(
                exchange=exchange_name, 
                symbol=symbol, 
                side=side, 
                status=status
            ).inc()
            raise
        except Exception as e:
            status = "failure_unexpected"
            logger.exception(f"Unexpected error during {func.__name__} on {exchange_name} for {symbol}: {e}")
            ORDER_EXECUTION_COUNT.labels(
                exchange=exchange_name, 
                symbol=symbol, 
                side=side, 
                status=status
            ).inc()
            raise
        else:
            # Only increment success if no exception was raised
             ORDER_EXECUTION_COUNT.labels(
                exchange=exchange_name, 
                symbol=symbol, 
                side=side, 
                status=status # This will be "success"
            ).inc()
        finally:
            end_time = time.monotonic()
            latency = end_time - start_time
            ORDER_EXECUTION_LATENCY.labels(exchange=exchange_name, symbol=symbol).observe(latency)
            logger.debug(f"Execution of {func.__name__} on {exchange_name} for {symbol} took {latency:.4f}s, status: {status}")

        return result
    return wrapper

# Note: ORDER_RETRY_COUNT would be incremented within the retry logic itself,
# not typically in this outer monitoring decorator.