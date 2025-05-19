"""
Prometheus Metrics for Trading System

This module defines Prometheus metrics used throughout the trading system.
"""
from prometheus_client import Counter, Gauge, Histogram

# Order Execution Metrics
ORDER_EXECUTION_COUNT = Counter(
    'order_execution_total',
    'Total number of order executions',
    ['exchange', 'symbol', 'side', 'status']
)

ORDER_EXECUTION_LATENCY = Histogram(
    'order_execution_latency_seconds',
    'Order execution latency in seconds',
    ['exchange', 'symbol'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

ORDER_RETRY_COUNT = Counter(
    'order_retry_total',
    'Total number of order execution retries',
    ['exchange', 'symbol']
)

# Circuit Breaker Metrics
CIRCUIT_BREAKER_TRIPS = Counter(
    'circuit_breaker_trips_total',
    'Total number of circuit breaker trips',
    ['exchange']
)

CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Current state of the circuit breaker (0=closed, 1=half-open, 2=open)',
    ['exchange']
)

# Trade Confirmation Metrics
TRADE_CONFIRMATION_STEPS_TOTAL = Counter(
    'trade_confirmation_steps_total',
    'Total number of trade confirmation steps performed',
    ['exchange', 'step', 'status']
)

TRADE_CONFIRMATION_LATENCY = Histogram(
    'trade_confirmation_latency_seconds',
    'Trade confirmation latency in seconds',
    ['exchange'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)

# Reconciliation Metrics
RECONCILIATION_MISMATCH = Gauge(
    'reconciliation_mismatch_percentage',
    'Percentage of orders with mismatches during reconciliation',
    ['exchange']
)

RECONCILIATION_COUNT = Counter(
    'reconciliation_total',
    'Total number of reconciliation operations',
    ['exchange', 'status']
)