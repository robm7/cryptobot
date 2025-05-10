from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from decimal import Decimal

class MarketDataInterface(ABC):
    """Abstract base class for market data providers"""
    
    @abstractmethod
    def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to market data for given symbols"""
        pass
        
    @abstractmethod
    def get_latest_price(self, symbol: str) -> Optional[Decimal]:
        """Get latest price for a symbol"""
        pass
        
    @abstractmethod
    def get_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """Get OHLCV data for a symbol"""
        pass
        
    @abstractmethod
    def get_order_book(self, symbol: str, depth: int = 10) -> Dict:
        """Get order book data for a symbol"""
        pass