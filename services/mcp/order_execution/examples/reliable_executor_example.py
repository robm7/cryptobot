#!/usr/bin/env python
"""
Example script demonstrating how to use the ReliableOrderExecutor

This script shows how to:
1. Initialize the ReliableOrderExecutor
2. Configure it with custom settings
3. Execute orders with the enhanced reliability features
4. Handle circuit breaker states
5. Run order reconciliation
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from services.mcp.order_execution.reliable_executor import ReliableOrderExecutor, CircuitState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("order_execution.log")
    ]
)
logger = logging.getLogger(__name__)

async def execute_sample_orders(executor):
    """Execute a series of sample orders"""
    # Sample order parameters
    orders = [
        {
            "symbol": "BTC/USD",
            "side": "buy",
            "type": "limit",
            "amount": 0.1,
            "price": 50000.0
        },
        {
            "symbol": "ETH/USD",
            "side": "buy",
            "type": "limit",
            "amount": 1.0,
            "price": 3000.0
        },
        {
            "symbol": "SOL/USD",
            "side": "sell",
            "type": "limit",
            "amount": 10.0,
            "price": 100.0
        }
    ]
    
    order_ids = []
    
    # Execute each order
    for order in orders:
        logger.info(f"Executing order: {order}")
        order_id = await executor.execute_order(order)
        
        if order_id:
            order_ids.append(order_id)
            logger.info(f"Order executed successfully: {order_id}")
        else:
            logger.error(f"Failed to execute order: {order}")
    
    return order_ids

async def check_order_statuses(executor, order_ids):
    """Check the status of each order"""
    for order_id in order_ids:
        logger.info(f"Checking status for order: {order_id}")
        status = await executor.get_order_status(order_id)
        
        if status:
            logger.info(f"Order status: {status}")
        else:
            logger.error(f"Failed to get status for order: {order_id}")

async def cancel_sample_order(executor, order_id):
    """Cancel a sample order"""
    logger.info(f"Cancelling order: {order_id}")
    result = await executor.cancel_order(order_id)
    
    if result:
        logger.info(f"Order cancelled successfully: {order_id}")
    else:
        logger.error(f"Failed to cancel order: {order_id}")

async def print_execution_stats(executor):
    """Print execution statistics"""
    stats = await executor.get_execution_stats()
    logger.info("Execution Statistics:")
    logger.info(json.dumps(stats, indent=2, default=str))

async def run_reconciliation(executor):
    """Run order reconciliation process"""
    logger.info("Running order reconciliation")
    result = await executor.reconcile_orders()
    logger.info(f"Reconciliation result: {json.dumps(result, indent=2)}")
    
    if result.get("alert_triggered", False):
        logger.warning("Reconciliation triggered an alert!")

async def main():
    """Main function demonstrating ReliableOrderExecutor usage"""
    logger.info("Initializing ReliableOrderExecutor")
    
    # Initialize executor
    executor = ReliableOrderExecutor()
    
    # Configure with custom settings
    config = {
        "retry": {
            "max_retries": 5,
            "backoff_base": 1.5,
            "initial_delay": 0.5,
            "max_delay": 10.0,
            "retryable_errors": ["timeout", "rate_limit", "maintenance", "server_error"]
        },
        "circuit_breaker": {
            "error_threshold": 20,
            "warning_threshold": 5,
            "window_size_minutes": 5,
            "cool_down_seconds": 30
        }
    }
    
    logger.info("Configuring executor with custom settings")
    await executor.configure(config)
    
    try:
        # Execute sample orders
        order_ids = await execute_sample_orders(executor)
        
        # Check order statuses
        await check_order_statuses(executor, order_ids)
        
        # Cancel one order (if any were created)
        if order_ids:
            await cancel_sample_order(executor, order_ids[0])
        
        # Print execution statistics
        await print_execution_stats(executor)
        
        # Run reconciliation
        await run_reconciliation(executor)
        
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")
    
    # Print final statistics
    await print_execution_stats(executor)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())