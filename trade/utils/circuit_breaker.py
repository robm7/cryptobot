import time
from typing import Dict, Optional
import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        error_threshold: int = 5,
        window_seconds: int = 60,
        cool_down: int = 300
    ):
        self.name = name
        self.error_threshold = error_threshold
        self.window_seconds = window_seconds
        self.cool_down = cool_down
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[float] = None
        self.error_count = 0
        self.window_start = time.time()

    def record_error(self):
        current_time = time.time()
        
        # Reset window if expired
        if current_time - self.window_start > self.window_seconds:
            self.error_count = 0
            self.window_start = current_time
        
        self.error_count += 1
        self.last_failure_time = current_time
        
        # Check if we should trip
        if (self.error_count >= self.error_threshold and 
            self.state != CircuitState.OPEN):
            self._trip()

    def _trip(self):
        logger.warning(f"Circuit breaker '{self.name}' tripped to OPEN state")
        self.state = CircuitState.OPEN
        self.last_failure_time = time.time()

    def is_open(self) -> bool:
        if self.state == CircuitState.OPEN:
            # Check if cool down period has elapsed
            if time.time() - self.last_failure_time > self.cool_down:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN state")
                return False
            return True
        return False

    def success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' reset to CLOSED state")
            self.state = CircuitState.CLOSED
            self.error_count = 0
            self.last_failure_time = None