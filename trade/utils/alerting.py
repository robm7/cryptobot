from prometheus_client import start_http_server
from typing import Dict, Optional
import time
import logging
from .metrics import (
    ORDER_EXECUTION_COUNT,
    ORDER_EXECUTION_LATENCY,
    ORDER_RETRY_COUNT,
    CIRCUIT_BREAKER_TRIPS
)

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self, port: int = 8000):
        self.port = port
        self.thresholds = {
            'error_rate': 0.1,  # 10% error rate threshold
            'latency_p99': 2.0,  # 2 seconds P99 latency
            'retry_rate': 0.2,   # 20% retry rate threshold
            'circuit_trips': 3   # 3 circuit trips per hour
        }
        self.metrics_server_started = False

    def start_metrics_server(self):
        if not self.metrics_server_started:
            start_http_server(self.port)
            self.metrics_server_started = True
            logger.info(f"Metrics server started on port {self.port}")

    def check_thresholds(self) -> Dict[str, bool]:
        """Check all alert thresholds and return status"""
        alerts = {
            'high_error_rate': self._check_error_rate(),
            'high_latency': self._check_latency(),
            'high_retry_rate': self._check_retry_rate(),
            'frequent_circuit_trips': self._check_circuit_trips()
        }
        return alerts

    def _check_error_rate(self) -> bool:
        success_count = ORDER_EXECUTION_COUNT.labels(status='success')._value.get()
        fail_count = ORDER_EXECUTION_COUNT.labels(status='failed')._value.get()
        total = success_count + fail_count
        
        if total == 0:
            return False
            
        error_rate = fail_count / total
        if error_rate > self.thresholds['error_rate']:
            logger.warning(f"High error rate detected: {error_rate:.2%}")
            return True
        return False

    def _check_latency(self) -> bool:
        # Simplified check - in production would use proper quantiles
        avg_latency = ORDER_EXECUTION_LATENCY._sum.get() / max(1, ORDER_EXECUTION_LATENCY._count.get())
        if avg_latency > self.thresholds['latency_p99'] * 0.7:  # Using 70% of P99 as proxy
            logger.warning(f"High latency detected: {avg_latency:.2f}s")
            return True
        return False

    def _check_retry_rate(self) -> bool:
        retry_count = ORDER_RETRY_COUNT._value.get()
        order_count = ORDER_EXECUTION_COUNT._value.get()
        
        if order_count == 0:
            return False
            
        retry_rate = retry_count / order_count
        if retry_rate > self.thresholds['retry_rate']:
            logger.warning(f"High retry rate detected: {retry_rate:.2%}")
            return True
        return False

    def _check_circuit_trips(self) -> bool:
        trip_count = CIRCUIT_BREAKER_TRIPS._value.get()
        if trip_count > self.thresholds['circuit_trips']:
            logger.warning(f"Frequent circuit trips detected: {trip_count}")
            return True
        return False

    def run_monitoring(self, interval: int = 60):
        """Run continuous monitoring of thresholds"""
        self.start_metrics_server()
        while True:
            alerts = self.check_thresholds()
            if any(alerts.values()):
                logger.warning(f"Alert conditions detected: {alerts}")
            time.sleep(interval)