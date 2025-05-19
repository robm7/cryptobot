import time
import logging
from enum import Enum
from typing import Optional, Callable, Any, Awaitable

# Assuming prometheus_metrics.py is accessible for CIRCUIT_BREAKER_STATE metric
from .prometheus_metrics import CIRCUIT_BREAKER_STATE # Path relative to trade/utils/

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2

class CircuitBreakerOpenError(Exception):
    """Custom exception to indicate the circuit breaker is open."""
    def __init__(self, message="Circuit breaker is open. Call rejected.", remaining_time: float = 0):
        super().__init__(message)
        self.remaining_time = remaining_time

class CircuitBreaker:
    def __init__(self, 
                 failure_threshold: int = 5, # Number of failures to trip
                 recovery_timeout_seconds: int = 30, # Time in OPEN state before moving to HALF_OPEN
                 half_open_attempt_limit: int = 1, # Number of successful attempts in HALF_OPEN to close
                 name: str = "default_breaker"):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_attempt_limit = half_open_attempt_limit
        
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_success_count = 0
        
        self._update_prometheus_metric()
        logger.info(f"CircuitBreaker '{self.name}' initialized: state=CLOSED, threshold={self.failure_threshold}, recovery_timeout={self.recovery_timeout_seconds}s")

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN:
            if self._last_failure_time and (time.monotonic() - self._last_failure_time) > self.recovery_timeout_seconds:
                self._transition_to_half_open()
        return self._state

    def _transition_to_closed(self):
        logger.info(f"CircuitBreaker '{self.name}': Transitioning from {self._state.name} to CLOSED")
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._update_prometheus_metric()

    def _transition_to_open(self):
        logger.warning(f"CircuitBreaker '{self.name}': Transitioning from {self._state.name} to OPEN for {self.recovery_timeout_seconds}s")
        self._state = CircuitBreakerState.OPEN
        self._last_failure_time = time.monotonic()
        self._update_prometheus_metric()

    def _transition_to_half_open(self):
        logger.info(f"CircuitBreaker '{self.name}': Transitioning from OPEN to HALF_OPEN")
        self._state = CircuitBreakerState.HALF_OPEN
        self._half_open_success_count = 0
        self._update_prometheus_metric()

    def _update_prometheus_metric(self):
        # Assuming exchange_name or a general breaker_name is relevant for labels
        # For now, using self.name as the label for the breaker.
        # The CIRCUIT_BREAKER_STATE metric expects 'exchange' as a label.
        # This needs alignment. Let's assume self.name can be the exchange or a related identifier.
        CIRCUIT_BREAKER_STATE.labels(exchange=self.name).set(self._state.value)

    def record_failure(self):
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
        elif self._state == CircuitBreakerState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._transition_to_open()
        logger.debug(f"CircuitBreaker '{self.name}': Failure recorded. Current failure count: {self._failure_count}, State: {self._state.name}")


    def record_success(self):
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.half_open_attempt_limit:
                self._transition_to_closed()
        elif self._state == CircuitBreakerState.CLOSED:
            # Optionally reset failure count on success if desired, or let it decay over time (more complex)
            if self._failure_count > 0:
                 logger.debug(f"CircuitBreaker '{self.name}': Success recorded in CLOSED state. Failures were {self._failure_count}, resetting slightly or consider decay.")
                 # Simple reset on any success in closed state, or implement decay
                 # self._failure_count = 0 
                 # A more robust approach might be a sliding window for failures.
                 # For now, let's not reset on every success in CLOSED to avoid flapping if failures are intermittent.
                 # The primary reset happens when transitioning to CLOSED from HALF_OPEN.
        logger.debug(f"CircuitBreaker '{self.name}': Success recorded. Half-open successes: {self._half_open_success_count}, State: {self._state.name}")


    async def execute(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Executes the given async function if the circuit breaker is not open.
        Records success or failure.
        """
        current_state = self.state # This property access also handles transition from OPEN to HALF_OPEN
        
        if current_state == CircuitBreakerState.OPEN:
            remaining = self.recovery_timeout_seconds - (time.monotonic() - (self._last_failure_time or 0))
            raise CircuitBreakerOpenError(f"CircuitBreaker '{self.name}' is OPEN. Call rejected.", remaining_time=max(0, remaining))

        # If CLOSED or HALF_OPEN, attempt the operation
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e # Re-raise the original exception

# Example usage (conceptual)
# async def my_operation():
#     # Simulate an operation that might fail
#     if random.random() < 0.3:
#         raise ValueError("Simulated failure")
#     return "Operation successful"

# breaker = CircuitBreaker(name="my_api_breaker", failure_threshold=3, recovery_timeout_seconds=10)
# for _ in range(20):
#     try:
#         await breaker.execute(my_operation)
#         print("Call succeeded")
#     except CircuitBreakerOpenError as e:
#         print(e)
#     except ValueError as e:
#         print(f"Operation failed: {e}")
#     await asyncio.sleep(1)