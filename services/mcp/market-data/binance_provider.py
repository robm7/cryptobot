import asyncio
from decimal import Decimal
from typing import Dict, List, Optional
import aiohttp
from .interfaces import MarketDataInterface

class BinanceMarketData(MarketDataInterface):
    """Market data provider for Binance exchange"""
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.subscribed_symbols = set()
        
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to market data for given symbols"""
        self.subscribed_symbols.update(symbols)
        return True
        
    async def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price for a symbol"""
        if symbol not in self.subscribed_symbols:
            return None
            
        url = f"{self.BASE_URL}/ticker/price?symbol={symbol}"
        async with self.session.get(url) as response:
            data = await response.json()
            return Decimal(data['price'])
            
    async def get_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """Get OHLCV data for a symbol"""
        if symbol not in self.subscribed_symbols:
            return []
            
        url = f"{self.BASE_URL}/klines?symbol={symbol}&interval={timeframe}&limit={limit}"
        async with self.session.get(url) as response:
            data = await response.json()
            return [{
                'open': Decimal(item[1]),
                'high': Decimal(item[2]),
                'low': Decimal(item[3]),
                'close': Decimal(item[4]),
                'volume': Decimal(item[5]),
                'timestamp': item[0]
            } for item in data]
            
    async def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        """Get order book data for a symbol"""
        if symbol not in self.subscribed_symbols:
            return {}
            
        url = f"{self.BASE_URL}/depth?symbol={symbol}&limit={depth}"
        async with self.session.get(url) as response:
            return await response.json()
            
    async def close(self):
        """Clean up resources"""
        await self.session.close()