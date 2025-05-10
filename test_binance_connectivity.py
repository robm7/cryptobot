import asyncio
import platform
from trade.utils.exchange import get_exchange

async def test_connectivity():
    exchange = None
    try:
        # Using properly formatted test credentials for Kraken
        exchange = get_exchange(
            exchange_id="kraken",
            api_key="kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg==",
            api_secret="kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg==",
            testnet=True
        )
        
        # Test connectivity using private balance endpoint
        balance = await exchange.get_balance('USD')
        print("Kraken connection successful!")
        print("USD Balance:", balance)
        return True
    except Exception as e:
        print("Connection failed:", str(e))
        return False
    finally:
        if exchange:
            await exchange.close()

if __name__ == "__main__":
    if platform.system() == 'Windows':
        # Use SelectorEventLoop on Windows
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(test_connectivity())
    finally:
        loop.close()