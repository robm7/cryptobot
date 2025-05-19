"""
Order Execution Module for Cryptobot

This module provides reliable order execution capabilities with enhanced
reliability patterns such as retry logic, circuit breaker, and reconciliation.
"""

from .interfaces import OrderExecutionInterface
from .basic_executor import BasicOrderExecutor
from .reliable_executor import ReliableOrderExecutor, CircuitState
from .monitoring import (
    log_execution_time,
    track_metrics,
    circuit_breaker_aware,
    alert_on_failure,
    retry_with_backoff
)

__all__ = [
    'OrderExecutionInterface',
    'BasicOrderExecutor',
    'ReliableOrderExecutor',
    'CircuitState',
    'log_execution_time',
    'track_metrics',
    'circuit_breaker_aware',
    'alert_on_failure',
    'retry_with_backoff'
]