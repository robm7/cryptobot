import asyncio
import time
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, List, Any
from enum import Enum
from .interfaces import OrderExecutionInterface
from .monitoring import log_execution_time, track_metrics, circuit_breaker_aware, alert_on_failure

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = 'closed'      # Normal operation
    OPEN = 'open'          # Failing, not accepting requests
    HALF_OPEN = 'half_open'  # Testing if system has recovered


class RetryConfig:
    """Configuration for retry logic"""
    def __init__(self):
        self.max_retries: int = 3
        self.backoff_base: float = 2.0
        self.initial_delay: float = 1.0
        self.max_delay: float = 30.0
        self.retryable_errors: List[str] = ["timeout", "rate_limit", "maintenance"]


class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    def __init__(self):
        self.error_threshold: int = 30  # Errors per minute to trip
        self.warning_threshold: int = 10  # Errors per minute for warning
        self.window_size_minutes: int = 5  # Time window for error tracking
        self.cool_down_seconds: int = 60  # Time before testing circuit again


class ReliableOrderExecutor(OrderExecutionInterface):
    """
    Enhanced implementation of order execution with reliability patterns:
    - Exponential backoff retry
    - Circuit breaker
    - Enhanced trade confirmation
    - Monitoring metrics
    """
    
    def __init__(self):
        # Stats tracking
        self.stats = {
            'total_orders': 0,
            'successful_orders': 0,
            'failed_orders': 0,
            'avg_execution_time': 0,
            'circuit_breaker_trips': 0,
            'retry_count': 0
        }
        self.execution_times = []
        
        # Error tracking for circuit breaker
        self.errors = []
        self.error_timestamps = []
        
        # Circuit breaker state
        self.circuit_state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
        
        # Configuration
        self.retry_config = RetryConfig()
        self.circuit_config = CircuitBreakerConfig()
        
        # Prometheus metrics would be initialized here in production
        # self.execution_success = Counter('execution_success_total', 'Successful order executions')
        # self.execution_failure = Counter('execution_failure_total', 'Failed order executions')
        # self.execution_latency = Histogram('execution_latency_seconds', 'Order execution latency')
        # self.circuit_state_metric = Gauge('circuit_breaker_state', 'Circuit breaker state')
        
        logger.info("ReliableOrderExecutor initialized")
    
    @circuit_breaker_aware
    @track_metrics("order_execution")
    @log_execution_time
    @alert_on_failure(alert_threshold=5, window_seconds=300)
    async def execute_order(self, order_params: Dict) -> Optional[str]:
        """Execute order with enhanced retry logic and circuit breaker"""
        start_time = time.time()
        retry_delay = self.retry_config.initial_delay
        
        for attempt in range(self.retry_config.max_retries):
            try:
                # Simulate order execution - would integrate with exchange gateway
                order_id = f"ORDER_{int(time.time() * 1000)}"
                
                # Record metrics
                self.stats['total_orders'] += 1
                self.stats['successful_orders'] += 1
                
                exec_time = time.time() - start_time
                self.execution_times.append(exec_time)
                self.stats['avg_execution_time'] = sum(self.execution_times) / len(self.execution_times)
                
                # In production, update Prometheus metrics
                # self.execution_success.inc()
                # self.execution_latency.observe(exec_time)
                
                # Perform enhanced trade confirmation
                await self._verify_order_execution(order_id, order_params)
                
                return order_id
                
            except Exception as e:
                error_type = str(type(e).__name__)
                logger.error(f"Order execution failed (attempt {attempt+1}): {str(e)}")
                
                # Record error for circuit breaker
                self._record_error(error_type)
                
                # Check if error is retryable
                if error_type.lower() not in self.retry_config.retryable_errors:
                    logger.error(f"Non-retryable error: {error_type}")
                    self.stats['failed_orders'] += 1
                    # self.execution_failure.inc()
                    return None
                
                # Last attempt
                if attempt == self.retry_config.max_retries - 1:
                    self.stats['failed_orders'] += 1
                    # self.execution_failure.inc()
                    return None
                
                # Exponential backoff with max delay cap
                self.stats['retry_count'] += 1
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * self.retry_config.backoff_base,
                    self.retry_config.max_delay
                )
    
    @circuit_breaker_aware
    @track_metrics("order_cancellation")
    @log_execution_time
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel order with retry logic"""
        retry_delay = self.retry_config.initial_delay
        
        for attempt in range(self.retry_config.max_retries):
            try:
                # Simulate cancellation - would integrate with exchange gateway
                # In production, this would call the exchange API
                
                logger.info(f"Order {order_id} cancelled successfully")
                return True
                
            except Exception as e:
                error_type = str(type(e).__name__)
                logger.error(f"Order cancellation failed (attempt {attempt+1}): {str(e)}")
                
                # Record error for circuit breaker
                self._record_error(error_type)
                
                # Last attempt
                if attempt == self.retry_config.max_retries - 1:
                    return False
                
                # Exponential backoff
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * self.retry_config.backoff_base,
                    self.retry_config.max_delay
                )
        
        return False
    
    @circuit_breaker_aware
    @track_metrics("order_status")
    @log_execution_time
    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status with retry logic"""
        retry_delay = self.retry_config.initial_delay
        
        for attempt in range(self.retry_config.max_retries):
            try:
                # Simulate status check - would integrate with exchange gateway
                return {
                    'status': 'filled',
                    'filled_qty': Decimal('1.0'),
                    'avg_price': Decimal('50000.0'),
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                error_type = str(type(e).__name__)
                logger.error(f"Order status check failed (attempt {attempt+1}): {str(e)}")
                
                # Record error for circuit breaker
                self._record_error(error_type)
                
                # Last attempt
                if attempt == self.retry_config.max_retries - 1:
                    return None
                
                # Exponential backoff
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * self.retry_config.backoff_base,
                    self.retry_config.max_delay
                )
        
        return None
    
    @log_execution_time
    async def get_execution_stats(self) -> Dict:
        """Get execution performance statistics"""
        stats = self.stats.copy()
        stats['circuit_state'] = self.circuit_state.value
        
        # Add error rate calculation
        now = datetime.now()
        window_start = now - timedelta(minutes=self.circuit_config.window_size_minutes)
        
        # Count errors in the current window
        recent_errors = [ts for ts in self.error_timestamps 
                         if ts > window_start]
        
        stats['error_rate_per_minute'] = len(recent_errors) / self.circuit_config.window_size_minutes
        stats['errors_in_window'] = len(recent_errors)
        
        return stats
    
    @log_execution_time
    async def configure(self, config: Dict) -> bool:
        """Configure execution parameters"""
        try:
            # Configure retry settings
            if 'retry' in config:
                retry_config = config['retry']
                if 'max_retries' in retry_config:
                    self.retry_config.max_retries = retry_config['max_retries']
                if 'backoff_base' in retry_config:
                    self.retry_config.backoff_base = retry_config['backoff_base']
                if 'initial_delay' in retry_config:
                    self.retry_config.initial_delay = retry_config['initial_delay']
                if 'max_delay' in retry_config:
                    self.retry_config.max_delay = retry_config['max_delay']
                if 'retryable_errors' in retry_config:
                    self.retry_config.retryable_errors = retry_config['retryable_errors']
            
            # Configure circuit breaker settings
            if 'circuit_breaker' in config:
                cb_config = config['circuit_breaker']
                if 'error_threshold' in cb_config:
                    self.circuit_config.error_threshold = cb_config['error_threshold']
                if 'warning_threshold' in cb_config:
                    self.circuit_config.warning_threshold = cb_config['warning_threshold']
                if 'window_size_minutes' in cb_config:
                    self.circuit_config.window_size_minutes = cb_config['window_size_minutes']
                if 'cool_down_seconds' in cb_config:
                    self.circuit_config.cool_down_seconds = cb_config['cool_down_seconds']
            
            logger.info("ReliableOrderExecutor configured successfully")
            return True
            
        except Exception as e:
            logger.error(f"Configuration failed: {str(e)}")
            return False
    
    def _check_circuit(self) -> bool:
        """
        Check circuit breaker state
        Returns True if circuit is closed or half-open (allowing test requests)
        """
        now = datetime.now()
        
        # If circuit is open, check if cool-down period has elapsed
        if self.circuit_state == CircuitState.OPEN:
            cool_down_time = self.last_state_change + timedelta(seconds=self.circuit_config.cool_down_seconds)
            
            if now >= cool_down_time:
                # Transition to half-open to test if system has recovered
                self.circuit_state = CircuitState.HALF_OPEN
                self.last_state_change = now
                logger.info("Circuit breaker state changed to HALF-OPEN")
                # self.circuit_state_metric.set(1)  # 1 for HALF-OPEN
                return True
            return False
            
        # If circuit is half-open, allow the request but will be closely monitored
        if self.circuit_state == CircuitState.HALF_OPEN:
            return True
            
        # If circuit is closed, check error rate
        window_start = now - timedelta(minutes=self.circuit_config.window_size_minutes)
        recent_errors = [ts for ts in self.error_timestamps if ts > window_start]
        error_rate = len(recent_errors) / self.circuit_config.window_size_minutes
        
        # Check if error rate exceeds threshold
        if error_rate >= self.circuit_config.error_threshold:
            self.circuit_state = CircuitState.OPEN
            self.last_state_change = now
            self.stats['circuit_breaker_trips'] += 1
            logger.warning(f"Circuit breaker OPENED due to error rate: {error_rate} errors/minute")
            # self.circuit_state_metric.set(2)  # 2 for OPEN
            return False
            
        # Check if error rate exceeds warning threshold
        if error_rate >= self.circuit_config.warning_threshold:
            logger.warning(f"Error rate warning: {error_rate} errors/minute")
            
        return True
    
    def _record_error(self, error_type: str) -> None:
        """Record error for circuit breaker tracking"""
        now = datetime.now()
        self.errors.append(error_type)
        self.error_timestamps.append(now)
        
        # Prune old errors outside the window
        window_start = now - timedelta(minutes=self.circuit_config.window_size_minutes)
        self.error_timestamps = [ts for ts in self.error_timestamps if ts > window_start]
        self.errors = self.errors[-len(self.error_timestamps):]
    
    @log_execution_time
    async def _verify_order_execution(self, order_id: str, order_params: Dict) -> bool:
        """
        Enhanced trade confirmation process:
        1. Immediate execution receipt (already done by getting order_id)
        2. Order book validation
        3. Fill confirmation
        4. Portfolio impact check
        """
        try:
            # Step 2: Order book validation
            # In production, this would verify the order appears in the order book
            logger.info(f"Order {order_id} validated in order book")
            
            # Step 3: Fill confirmation
            # In production, this would poll until the order is filled or timeout
            order_status = await self.get_order_status(order_id)
            if not order_status or order_status.get('status') != 'filled':
                logger.warning(f"Order {order_id} fill confirmation failed")
                return False
                
            logger.info(f"Order {order_id} fill confirmed")
            
            # Step 4: Portfolio impact check
            # In production, this would verify the balance changes match the order
            # This would typically call a portfolio service
            logger.info(f"Order {order_id} portfolio impact verified")
            
            return True
            
        except Exception as e:
            logger.error(f"Order verification failed: {str(e)}")
            return False
    
    @track_metrics("order_reconciliation")
    @log_execution_time
    @alert_on_failure(alert_threshold=1, window_seconds=86400)  # Alert on first failure within a day
    async def reconcile_orders(self, time_period: str = "daily") -> Dict[str, Any]:
        """
        Daily batch reconciliation process to verify all orders
        are properly accounted for
        """
        logger.info(f"Starting {time_period} order reconciliation")
        
        # In production, this would:
        # 1. Get all orders from local database for the period
        # 2. Get all orders from exchange for the period
        # 3. Compare and identify discrepancies
        # 4. Generate alerts for mismatches > 0.1%
        
        # Simulate reconciliation result
        reconciliation_result = {
            "total_orders": 100,
            "matched_orders": 99,
            "mismatched_orders": 1,
            "missing_orders": 0,
            "extra_orders": 0,
            "mismatch_percentage": 0.01,
            "alert_triggered": False
        }
        
        # Check if mismatch exceeds threshold
        if reconciliation_result["mismatch_percentage"] > 0.001:  # 0.1%
            reconciliation_result["alert_triggered"] = True
            logger.warning(f"Order reconciliation mismatch exceeds threshold: {reconciliation_result['mismatch_percentage']:.2%}")
            # In production, this would trigger an alert
        
        return reconciliation_result