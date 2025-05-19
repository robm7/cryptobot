import asyncio
import logging
from services.mcp.order_execution.reliable_executor import ReliableOrderExecutor, CircuitState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_reliable_executor():
    """Simple test to verify ReliableOrderExecutor functionality"""
    # Create executor
    executor = ReliableOrderExecutor()
    
    # Configure executor
    config = {
        'retry': {
            'max_retries': 3,
            'backoff_base': 2.0,
            'initial_delay': 0.1,
            'max_delay': 1.0,
            'retryable_errors': ['timeout', 'rate_limit']
        },
        'circuit_breaker': {
            'error_threshold': 5,
            'warning_threshold': 2,
            'window_size_minutes': 1,
            'cool_down_seconds': 1
        }
    }
    
    await executor.configure(config)
    logger.info("Executor configured successfully")
    
    # Test order execution
    order_params = {
        "symbol": "BTC/USD",
        "side": "buy",
        "type": "limit",
        "amount": 1.0,
        "price": 50000.0
    }
    
    # Patch the _verify_order_execution method to return an awaitable
    original_verify = executor._verify_order_execution
    
    async def mock_verify(order_id, params):
        return True
        
    executor._verify_order_execution = mock_verify
    
    # Execute order
    order_id = await executor.execute_order(order_params)
    logger.info(f"Order executed with ID: {order_id}")
    
    # Get execution stats
    stats = await executor.get_execution_stats()
    logger.info(f"Execution stats: {stats}")
    
    # Test circuit breaker
    logger.info("Testing circuit breaker...")
    for i in range(6):
        executor._record_error("timeout")
    
    circuit_state = executor.circuit_state
    logger.info(f"Circuit state after errors: {circuit_state}")
    
    # Test reconciliation
    logger.info("Testing reconciliation...")
    reconciliation_result = await executor.reconcile_orders()
    logger.info(f"Reconciliation result: {reconciliation_result}")
    
    return {
        "order_id": order_id,
        "stats": stats,
        "circuit_state": circuit_state,
        "reconciliation_result": reconciliation_result
    }

if __name__ == "__main__":
    results = asyncio.run(test_reliable_executor())
    print("\nTest Results:")
    print(f"Order ID: {results['order_id']}")
    print(f"Circuit State: {results['circuit_state']}")
    
    # Handle the case where reconciliation result is None due to circuit breaker
    if results['reconciliation_result'] is None:
        print("Reconciliation: Not performed (circuit breaker open)")
    else:
        print(f"Reconciliation: {results['reconciliation_result']['mismatch_percentage']:.2%} mismatch")
    
    print("Test completed successfully!")