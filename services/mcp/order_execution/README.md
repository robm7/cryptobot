# Order Execution Module

This module provides reliable order execution capabilities for the Cryptobot trading system. It implements several reliability patterns to ensure robust trading operations even in the face of network issues, exchange outages, and other failure scenarios.

## Key Features

- **Retry Logic with Exponential Backoff**: Automatically retries failed operations with increasing delays
- **Circuit Breaker Pattern**: Prevents cascading failures by stopping operations during high error rates
- **Enhanced Trade Confirmation**: Multi-step verification process for trade execution
- **Monitoring & Alerting**: Comprehensive metrics and alerting for execution performance
- **Reconciliation**: Daily batch reconciliation to ensure all orders are properly accounted for

## Components

### Interfaces

- `OrderExecutionInterface`: Abstract base class defining the interface for order execution

### Implementations

- `BasicOrderExecutor`: Simple implementation with basic retry logic
- `ReliableOrderExecutor`: Enhanced implementation with all reliability features

### Monitoring

- Decorators for tracking execution metrics
- Circuit breaker state monitoring
- Error rate tracking and alerting

## Usage

### Basic Usage

```python
from services.mcp.order_execution import ReliableOrderExecutor

# Initialize executor
executor = ReliableOrderExecutor()

# Configure with custom settings
config = {
    "retry": {
        "max_retries": 5,
        "backoff_base": 1.5,
        "initial_delay": 0.5,
        "max_delay": 10.0
    },
    "circuit_breaker": {
        "error_threshold": 20,
        "warning_threshold": 5,
        "window_size_minutes": 5,
        "cool_down_seconds": 30
    }
}
await executor.configure(config)

# Execute an order
order_params = {
    "symbol": "BTC/USD",
    "side": "buy",
    "type": "limit",
    "amount": 0.1,
    "price": 50000.0
}
order_id = await executor.execute_order(order_params)

# Check order status
status = await executor.get_order_status(order_id)

# Cancel an order
success = await executor.cancel_order(order_id)

# Get execution statistics
stats = await executor.get_execution_stats()

# Run reconciliation
reconciliation_result = await executor.reconcile_orders()
```

### Circuit Breaker States

The circuit breaker has three states:

1. **CLOSED**: Normal operation, all requests are processed
2. **OPEN**: High error rate detected, requests are rejected
3. **HALF-OPEN**: Testing if system has recovered, allows limited requests

The circuit breaker automatically transitions between states based on error rates and cool-down periods.

### Monitoring Decorators

The module includes several decorators for monitoring:

- `@log_execution_time`: Logs execution time of functions
- `@track_metrics`: Tracks metrics for functions (success, failure, latency)
- `@circuit_breaker_aware`: Makes functions aware of circuit breaker state
- `@alert_on_failure`: Triggers alerts when functions fail repeatedly

## Examples

See the `examples` directory for complete usage examples:

- `reliable_executor_example.py`: Demonstrates basic usage of the ReliableOrderExecutor

## Integration

This module is designed to be integrated with:

1. Exchange gateway services for actual order execution
2. Monitoring systems (Prometheus/Grafana) for metrics and alerting
3. Portfolio management services for trade verification
4. Database services for order persistence and reconciliation

## Configuration

The ReliableOrderExecutor can be configured with the following parameters:

### Retry Configuration

- `max_retries`: Maximum number of retry attempts
- `backoff_base`: Base multiplier for exponential backoff
- `initial_delay`: Initial delay in seconds before first retry
- `max_delay`: Maximum delay in seconds between retries
- `retryable_errors`: List of error types that should trigger retries

### Circuit Breaker Configuration

- `error_threshold`: Errors per minute to trip the circuit breaker
- `warning_threshold`: Errors per minute to trigger a warning
- `window_size_minutes`: Time window for error tracking
- `cool_down_seconds`: Time before testing if system has recovered