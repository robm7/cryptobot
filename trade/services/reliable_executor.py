import asyncio
import time
import logging
from typing import List, Callable, Awaitable, Any, Type, Optional, Dict
from decimal import Decimal

from utils.exchange_interface import ExchangeInterface # Assuming this path is correct from trade module
from trade.utils.exceptions import ExchangeError, RateLimitError, ConnectionError, InvalidOrderError, InsufficientFundsError # Added InsufficientFundsError
# Metrics will be used directly in _execute_with_retry
from trade.utils.prometheus_metrics import ORDER_EXECUTION_COUNT, ORDER_EXECUTION_LATENCY, ORDER_RETRY_COUNT, CIRCUIT_BREAKER_TRIPS
from trade.utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError # Import CircuitBreaker

logger = logging.getLogger(__name__)

class RetryConfig:
    def __init__(self, 
                 max_retries: int = 3, 
                 backoff_base_seconds: float = 1.0, 
                 max_backoff_seconds: float = 30.0,
                 # Define retryable exceptions directly, not just strings
                 retryable_exception_types: Optional[List[Type[Exception]]] = None):
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.max_backoff_seconds = max_backoff_seconds
        # Default to common retryable exceptions if none provided
        self.retryable_exception_types = retryable_exception_types or [RateLimitError, ConnectionError]

class ReliableOrderExecutor:
    def __init__(self,
                 exchange_interface: ExchangeInterface,
                 retry_config: Optional[RetryConfig] = None,
                 circuit_breaker_config: Optional[Dict[str, Any]] = None): # Allow passing CB config
        self.exchange = exchange_interface
        self.retry_config = retry_config if retry_config else RetryConfig()
        
        # Initialize Circuit Breaker
        # The name for the circuit breaker could be based on the exchange name
        cb_name = f"{self.exchange.exchange_name}_breaker"
        cb_settings = circuit_breaker_config or {} # Use default CB settings if none provided
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_settings.get('failure_threshold', 5),
            recovery_timeout_seconds=cb_settings.get('recovery_timeout_seconds', 30),
            half_open_attempt_limit=cb_settings.get('half_open_attempt_limit', 1),
            name=cb_name
        )

    async def _execute_with_retry(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        retries = 0
        last_exception = None
        
        # --- Circuit Breaker Check before entering retry loop ---
        # The circuit_breaker.execute method handles the state checking and transitions.
        # We will wrap the entire retryable operation within circuit_breaker.execute.
        
        async def operation_with_retries():
            nonlocal retries # Allow modification of outer scope retries
            nonlocal last_exception # Allow modification of outer scope last_exception
            
            current_retries = 0 # Use a local counter for this attempt through the CB

            while current_retries <= self.retry_config.max_retries:
                start_time = time.monotonic()
                status_label = "success"
                # Corrected indentation for these lines
                exchange_name = self.exchange.exchange_name
                op_symbol = kwargs.get('symbol', args[0] if args and isinstance(args[0], str) else 'unknown')
                op_side = kwargs.get('side', args[1] if len(args) > 1 and isinstance(args[1], str) else 'unknown')
                if 'cancel_order' in func.__name__: op_side = 'cancel'
                if 'get_balances' in func.__name__: op_symbol = 'N/A'; op_side = 'N/A'
                if 'get_open_orders' in func.__name__: op_side = 'N/A'

                try:
                    result = await func(*args, **kwargs)
                    ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                    # self.circuit_breaker.record_success() # Success is recorded by circuit_breaker.execute
                    return result # Successful execution, exit retry loop
                except tuple(self.retry_config.retryable_exception_types) as e:
                    last_exception = e
                    current_retries += 1 # Increment local retry counter
                    retries = current_retries # Sync with outer scope for logging if needed
                    status_label = "failure_retryable"
                    ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                    ORDER_RETRY_COUNT.labels(exchange=exchange_name, symbol=op_symbol).inc()

                    if current_retries > self.retry_config.max_retries:
                        logger.error(f"Max retries ({self.retry_config.max_retries}) exceeded for {func.__name__} on {exchange_name} for {op_symbol}. Last error: {e}")
                        # self.circuit_breaker.record_failure() # Failure is recorded by circuit_breaker.execute
                        raise # Re-raise to be caught by circuit_breaker.execute
                    
                    backoff_time = min(
                        self.retry_config.max_backoff_seconds,
                        self.retry_config.backoff_base_seconds * (2 ** (current_retries - 1))
                    )
                    
                    if isinstance(e, RateLimitError) and e.details and 'retry_after_seconds' in e.details:
                        retry_after = e.details['retry_after_seconds']
                        backoff_time = max(backoff_time, float(retry_after))
                        logger.warning(f"Rate limit hit for {func.__name__} on {exchange_name} for {op_symbol}. Retrying after {backoff_time}s (Retry-After). Attempt {current_retries}/{self.retry_config.max_retries}.")
                    else:
                        logger.warning(f"Retryable error for {func.__name__} on {exchange_name} for {op_symbol}: {e}. Retrying in {backoff_time:.2f}s. Attempt {current_retries}/{self.retry_config.max_retries}.")
                    
                    await asyncio.sleep(backoff_time)
                
                except (InvalidOrderError, InsufficientFundsError) as e: # These are client errors, not service failures
                    status_label = "rejected"
                    ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                    logger.warning(f"Order rejected for {func.__name__} on {exchange_name} for {op_symbol}: {e}")
                    # These errors should not typically cause the circuit breaker to trip,
                    # as they are not indicative of the service itself being unhealthy.
                    # So, we don't call self.circuit_breaker.record_failure() here.
                    raise
                except ExchangeError as e: # Other non-retryable exchange errors (potential service issue)
                    status_label = "failure_exchange"
                    ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                    logger.error(f"Non-retryable exchange error for {func.__name__} on {exchange_name} for {op_symbol}: {e}")
                    # self.circuit_breaker.record_failure() # Failure is recorded by circuit_breaker.execute
                    raise # Re-raise to be caught by circuit_breaker.execute
                except Exception as e:
                    status_label = "failure_unexpected"
                    ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                    logger.exception(f"Unexpected error for {func.__name__} on {exchange_name} for {op_symbol}: {e}")
                    # self.circuit_breaker.record_failure() # Failure is recorded by circuit_breaker.execute
                    raise # Re-raise to be caught by circuit_breaker.execute
                finally:
                    end_time = time.monotonic()
                    latency = end_time - start_time
                    ORDER_EXECUTION_LATENCY.labels(exchange=exchange_name, symbol=op_symbol).observe(latency)
                    logger.debug(f"Attempt for {func.__name__} on {exchange_name} for {op_symbol} took {latency:.4f}s, status: {status_label}")
            
            # If loop finishes due to max_retries
            if last_exception:
                raise last_exception
            # Should be unreachable if logic is correct
            raise ExchangeError("Max retries logic error in operation_with_retries.", exchange=self.exchange.exchange_name)

        try:
            return await self.circuit_breaker.execute(operation_with_retries)
        except CircuitBreakerOpenError as e:
            logger.error(f"CircuitBreakerOpenError for {func.__name__} on {self.exchange.exchange_name}: {e}. Call rejected. Remaining time: {e.remaining_time:.2f}s")
            CIRCUIT_BREAKER_TRIPS.labels(exchange=self.exchange.exchange_name).inc() # Increment trip count when call is rejected
            raise # Re-raise to be handled by the caller
        except Exception as e: # Catch other exceptions that might come from operation_with_retries if CB was not open
            # This ensures any failure that passed through CB (e.g. in HALF_OPEN or first failures in CLOSED)
            # is properly logged if not already. The CB's execute already calls record_failure.
            logger.error(f"Operation {func.__name__} failed after circuit breaker execution: {e}")
            raise


    async def create_order(self, symbol: str, side: str, type: str,
                           amount: Decimal, price: Optional[Decimal] = None,
                           params: Optional[Dict] = None) -> Dict: # Added params back
        logger.info(f"ReliableOrderExecutor: Creating order - Symbol: {symbol}, Side: {side}, Type: {type}, Amount: {amount}, Price: {price}")
        # Pass actual exchange method and its arguments
        return await self._execute_with_retry(
            self.exchange.create_order, # The callable
            symbol=symbol, side=side, type=type, amount=amount, price=price # Args for the callable
            # If self.exchange.create_order takes **params, you would pass them here too.
            # For now, assuming the ExchangeInterface.create_order signature is fixed.
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        logger.info(f"ReliableOrderExecutor: Cancelling order - ID: {order_id}, Symbol: {symbol}")
        return await self._execute_with_retry(
            self.exchange.cancel_order,
            order_id=order_id, symbol=symbol
        )

    async def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        logger.info(f"ReliableOrderExecutor: Getting order status - ID: {order_id}, Symbol: {symbol}")
        return await self._execute_with_retry(
            self.exchange.get_order_status,
            order_id=order_id, symbol=symbol
            # The underlying exchange.get_order_status should handle if symbol is needed or not.
            # The ReliableOrderExecutor shouldn't need to know this.
        )

    async def get_balances(self) -> Dict[str, Decimal]:
        logger.info(f"ReliableOrderExecutor: Getting balances for {self.exchange.exchange_name}")
        return await self._execute_with_retry(self.exchange.get_balances)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        logger.info(f"ReliableOrderExecutor: Getting open orders for {self.exchange.exchange_name}, Symbol: {symbol}")
        return await self._execute_with_retry(self.exchange.get_open_orders, symbol=symbol)
            exchange_name = self.exchange.exchange_name
            
            # Determine symbol and side for labeling, specific to the operation
            # This is a simplification; a more robust way might involve inspecting func signature or kwargs
            op_symbol = kwargs.get('symbol', args[0] if args and isinstance(args[0], str) else 'unknown')
            op_side = kwargs.get('side', args[1] if len(args) > 1 and isinstance(args[1], str) else 'unknown')
            if 'cancel_order' in func.__name__: op_side = 'cancel'
            if 'get_balances' in func.__name__: op_symbol = 'N/A'; op_side = 'N/A'
            if 'get_open_orders' in func.__name__: op_side = 'N/A' # Symbol might be present or None

            try:
                result = await func(*args, **kwargs)
                # If successful, status_label remains "success"
                ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                return result
            except tuple(self.retry_config.retryable_exception_types) as e:
                last_exception = e
                retries += 1
                status_label = "failure_retryable"
                ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                ORDER_RETRY_COUNT.labels(exchange=exchange_name, symbol=op_symbol).inc()

                if retries > self.retry_config.max_retries:
                    logger.error(f"Max retries ({self.retry_config.max_retries}) exceeded for {func.__name__} on {exchange_name} for {op_symbol}. Last error: {e}")
                    raise
                
                backoff_time = min(
                    self.retry_config.max_backoff_seconds,
                    self.retry_config.backoff_base_seconds * (2 ** (retries - 1))
                )
                
                if isinstance(e, RateLimitError) and e.details and 'retry_after_seconds' in e.details:
                    retry_after = e.details['retry_after_seconds']
                    backoff_time = max(backoff_time, float(retry_after))
                    logger.warning(f"Rate limit hit for {func.__name__} on {exchange_name} for {op_symbol}. Retrying after {backoff_time}s (Retry-After). Attempt {retries}/{self.retry_config.max_retries}.")
                else:
                    logger.warning(f"Retryable error for {func.__name__} on {exchange_name} for {op_symbol}: {e}. Retrying in {backoff_time:.2f}s. Attempt {retries}/{self.retry_config.max_retries}.")
                
                await asyncio.sleep(backoff_time)
            
            except (InvalidOrderError, InsufficientFundsError) as e:
                status_label = "rejected"
                ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                logger.warning(f"Order rejected for {func.__name__} on {exchange_name} for {op_symbol}: {e}")
                raise
            except ExchangeError as e:
                status_label = "failure_exchange"
                ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                logger.error(f"Non-retryable exchange error for {func.__name__} on {exchange_name} for {op_symbol}: {e}")
                raise
            except Exception as e:
                status_label = "failure_unexpected"
                ORDER_EXECUTION_COUNT.labels(exchange=exchange_name, symbol=op_symbol, side=op_side, status=status_label).inc()
                logger.exception(f"Unexpected error for {func.__name__} on {exchange_name} for {op_symbol}: {e}")
                raise
            finally:
                # This finally block will execute after each attempt, successful or not.
                # Latency should be recorded for each attempt.
                end_time = time.monotonic()
                latency = end_time - start_time
                ORDER_EXECUTION_LATENCY.labels(exchange=exchange_name, symbol=op_symbol).observe(latency)
                logger.debug(f"Attempt for {func.__name__} on {exchange_name} for {op_symbol} took {latency:.4f}s, status: {status_label}")

        if last_exception: # Should only be reached if loop finishes due to max_retries
            raise last_exception
        raise ExchangeError("Max retries logic error: Should have re-raised last_exception or returned result.", exchange=self.exchange.exchange_name)


    async def create_order(self, symbol: str, side: str, type: str,
                           amount: Decimal, price: Optional[Decimal] = None,
                           params: Optional[Dict] = None) -> Dict:
        logger.info(f"ReliableOrderExecutor: Creating order - Symbol: {symbol}, Side: {side}, Type: {type}, Amount: {amount}, Price: {price}")
        return await self._execute_with_retry(
            self.exchange.create_order,
            symbol=symbol, side=side, type=type, amount=amount, price=price # Pass args directly
        )

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        logger.info(f"ReliableOrderExecutor: Cancelling order - ID: {order_id}, Symbol: {symbol}")
        return await self._execute_with_retry(
            self.exchange.cancel_order,
            order_id=order_id, symbol=symbol
        )

    async def get_order_status(self, order_id: str, symbol: Optional[str] = None) -> Dict:
        logger.info(f"ReliableOrderExecutor: Getting order status - ID: {order_id}, Symbol: {symbol}")
        # Specific handling for Binance requiring symbol, ideally this logic is within BinanceExchange.get_order_status
        if self.exchange.exchange_name.lower() == "binance" and not symbol:
            raise ValueError("Symbol is required for get_order_status on Binance via ReliableOrderExecutor.")
        
        return await self._execute_with_retry(
            self.exchange.get_order_status,
            order_id=order_id, symbol=symbol # Pass symbol, exchange impl can ignore if not needed
        )

    async def get_balances(self) -> Dict[str, Decimal]:
        logger.info(f"ReliableOrderExecutor: Getting balances for {self.exchange.exchange_name}")
        return await self._execute_with_retry(self.exchange.get_balances)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        logger.info(f"ReliableOrderExecutor: Getting open orders for {self.exchange.exchange_name}, Symbol: {symbol}")
        return await self._execute_with_retry(self.exchange.get_open_orders, symbol=symbol)

    # TODO: Implement methods for OCO and Trailing Stop if they are to be made reliable,
    # or decide if they bypass this executor due to exchange-specific handling.
    # For now, they would raise NotImplementedError if called on base ExchangeInterface.