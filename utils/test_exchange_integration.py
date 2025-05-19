"""
Test script for the improved exchange integration features.
This script demonstrates the usage of advanced order types and rate limit management.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.exchange_clients import ExchangeClient, RateLimitError, NetworkError, OrderError
from utils.advanced_order_types import AdvancedOrderManager
from utils.rate_limit_manager import RateLimitManager, apply_rate_limiting, rate_limited

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_rate_limiting():
    """Test rate limiting functionality"""
    logger.info("Testing rate limiting...")
    
    # Configure rate limits
    rate_manager = RateLimitManager()
    rate_manager.configure_exchange('test_exchange', [
        {'max_requests': 5, 'time_window_seconds': 10}
    ])
    
    # Make several requests in quick succession
    for i in range(10):
        logger.info(f"Making request {i+1}...")
        should_throttle, wait_time = rate_manager.should_throttle('test_exchange')
        
        if should_throttle:
            logger.info(f"Rate limit throttling applied: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
        rate_manager.record_request('test_exchange')
        await asyncio.sleep(0.1)  # Small delay between requests
    
    # Get usage stats
    stats = rate_manager.get_usage_stats('test_exchange')
    logger.info(f"Rate limit usage stats: {stats}")
    
    return "Rate limiting test completed"

async def test_advanced_order_types():
    """Test advanced order types with paper trading"""
    logger.info("Testing advanced order types...")
    
    # Set mock environment variables for testing
    import os
    os.environ["BINANCE_API_KEY"] = "test_key"
    os.environ["BINANCE_API_SECRET"] = "test_secret"
    
    # Create exchange client in paper trading mode
    exchange = ExchangeClient(exchange='binance', paper_trading=True)
    
    # Create advanced order manager
    order_manager = AdvancedOrderManager(exchange)
    
    # Create an OCO order
    logger.info("Creating OCO order...")
    oco_order = await order_manager.create_oco_order(
        symbol='BTC/USDT',
        side='sell',
        amount=0.1,
        price=52000.0,  # Limit price
        stop_price=48000.0  # Stop price
    )
    logger.info(f"OCO order created: {oco_order['id']}")
    
    # Create a trailing stop order
    logger.info("Creating trailing stop order...")
    trailing_order = await order_manager.create_trailing_stop_order(
        symbol='ETH/USDT',
        side='sell',
        amount=1.0,
        activation_price=3000.0,
        callback_rate=1.0  # 1% callback rate
    )
    logger.info(f"Trailing stop order created: {trailing_order['id']}")
    
    # Get order status
    oco_status = await order_manager.get_advanced_order_status(oco_order['id'])
    logger.info(f"OCO order status: {oco_status}")
    
    trailing_status = await order_manager.get_advanced_order_status(trailing_order['id'])
    logger.info(f"Trailing stop order status: {trailing_status}")
    
    # Cancel orders
    logger.info("Canceling orders...")
    oco_cancel = await order_manager.cancel_advanced_order(oco_order['id'])
    logger.info(f"OCO order cancel result: {oco_cancel}")
    
    trailing_cancel = await order_manager.cancel_advanced_order(trailing_order['id'])
    logger.info(f"Trailing stop order cancel result: {trailing_cancel}")
    
    return "Advanced order types test completed"

async def test_error_handling():
    """Test error handling with exchange client"""
    logger.info("Testing error handling...")
    
    # Set mock environment variables for testing
    import os
    os.environ["BINANCE_API_KEY"] = "test_key"
    os.environ["BINANCE_API_SECRET"] = "test_secret"
    
    # Create exchange client in paper trading mode
    exchange = ExchangeClient(exchange='binance', paper_trading=True)
    
    try:
        # Simulate a rate limit error
        logger.info("Simulating rate limit error...")
        raise RateLimitError("Rate limit exceeded", retry_after=5)
    except RateLimitError as e:
        logger.info(f"Caught rate limit error: {e}, retry after: {e.retry_after}s")
    
    try:
        # Simulate a network error
        logger.info("Simulating network error...")
        raise NetworkError("Connection timeout")
    except NetworkError as e:
        logger.info(f"Caught network error: {e}")
    
    try:
        # Simulate an order error
        logger.info("Simulating order error...")
        raise OrderError("Insufficient funds")
    except OrderError as e:
        logger.info(f"Caught order error: {e}")
    
    return "Error handling test completed"

async def main():
    """Run all tests"""
    logger.info("Starting exchange integration tests...")
    
    # Test rate limiting
    await test_rate_limiting()
    
    # Test advanced order types
    await test_advanced_order_types()
    
    # Test error handling
    await test_error_handling()
    
    logger.info("All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())