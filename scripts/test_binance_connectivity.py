import asyncio
from trade.utils.exchange import get_exchange
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connectivity():
    """Test connectivity to Binance testnet"""
    exchange = None
    try:
        # Initialize exchange with testnet=True
        exchange = get_exchange("binance", testnet=True)
        
        # Test basic API call
        btc_price = await exchange.get_ticker("BTC/USDT")
        logger.info(f"BTC/USDT price: {btc_price}")
        
        # Test balance check
        balance = await exchange.get_balance("USDT")
        logger.info(f"USDT balance: {balance}")
        
        return True
    except Exception as e:
        logger.error(f"Connectivity test failed: {str(e)}")
        return False
    finally:
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    result = asyncio.run(test_connectivity())
    if result:
        logger.info("Binance testnet connectivity verified successfully")
    else:
        logger.error("Binance testnet connectivity test failed")