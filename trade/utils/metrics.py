from prometheus_client import Counter, Histogram, Gauge
import time
from typing import Callable, Any
from functools import wraps
from dataclasses import dataclass

@dataclass
class AlertThresholds:
    fill_ratio_warning: float = 0.8
    fill_ratio_critical: float = 0.5
    slippage_warning: float = 0.01  # 1%
    slippage_critical: float = 0.03  # 3%
    error_rate_warning: float = 0.1  # 10%
    error_rate_critical: float = 0.3  # 30%

# Execution metrics
ORDER_EXECUTION_COUNT = Counter(
    'order_execution_total',
    'Total number of order executions',
    ['exchange', 'symbol', 'side', 'status']
)

ORDER_EXECUTION_LATENCY = Histogram(
    'order_execution_latency_seconds',
    'Order execution latency in seconds',
    ['exchange', 'symbol']
)

ORDER_RETRY_COUNT = Counter(
    'order_retry_total',
    'Total number of order retries',
    ['exchange', 'symbol']
)

# Circuit breaker metrics
CIRCUIT_BREAKER_TRIPS = Counter(
    'circuit_breaker_trips_total',
    'Total number of circuit breaker trips',
    ['exchange']
)

CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Current state of circuit breaker (0=closed, 1=open, 2=half_open)',
    ['exchange']
)

# New execution quality metrics
ORDER_EXECUTION_QUALITY = Gauge(
    'order_execution_quality',
    'Order execution quality (1=success, 0=failure)',
    ['exchange', 'symbol', 'order_type']
)

ORDER_FILL_RATIO = Gauge(
    'order_fill_ratio',
    'Ratio of filled amount to requested amount',
    ['exchange', 'symbol']
)

ORDER_SLIPPAGE = Histogram(
    'order_slippage_ratio',
    'Slippage as ratio of requested price',
    ['exchange', 'symbol'],
    buckets=[0.001, 0.005, 0.01, 0.02, 0.05]
)

ALERT_THRESHOLDS = AlertThresholds()

def check_alert_thresholds(metrics: dict) -> list:
    """Check metrics against alert thresholds and return any alerts"""
    alerts = []
    
    if metrics.get('fill_ratio', 1) < ALERT_THRESHOLDS.fill_ratio_critical:
        alerts.append(('CRITICAL', f"Fill ratio below critical threshold: {metrics['fill_ratio']}"))
    elif metrics.get('fill_ratio', 1) < ALERT_THRESHOLDS.fill_ratio_warning:
        alerts.append(('WARNING', f"Fill ratio below warning threshold: {metrics['fill_ratio']}"))
        
    if metrics.get('slippage', 0) > ALERT_THRESHOLDS.slippage_critical:
        alerts.append(('CRITICAL', f"Slippage above critical threshold: {metrics['slippage']}"))
    elif metrics.get('slippage', 0) > ALERT_THRESHOLDS.slippage_warning:
        alerts.append(('WARNING', f"Slippage above warning threshold: {metrics['slippage']}"))
        
    return alerts

def track_metrics(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        exchange = kwargs.get('exchange', 'unknown')
        symbol = kwargs.get('symbol', 'unknown')
        
        try:
            result = await func(*args, **kwargs)
            ORDER_EXECUTION_COUNT.labels(
                exchange=exchange,
                symbol=symbol,
                side=kwargs.get('side', 'unknown'),
                status='success'
            ).inc()
            return result
        except Exception as e:
            ORDER_EXECUTION_COUNT.labels(
                exchange=exchange,
                symbol=symbol,
                side=kwargs.get('side', 'unknown'),
                status='failed'
            ).inc()
            raise
        finally:
            latency = time.time() - start_time
            ORDER_EXECUTION_LATENCY.labels(
                exchange=exchange,
                symbol=symbol
            ).observe(latency)
    
    return wrapper