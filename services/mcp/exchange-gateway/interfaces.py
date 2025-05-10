from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime

class ExchangeInterface(ABC):
    """Abstract base class for exchange gateways"""
    
    @abstractmethod
    def get_balances(self) -> Dict[str, Decimal]:
        """Get current account balances"""
        pass
        
    @abstractmethod
    def get_ticker(self, symbol: str) -> Dict:
        """Get current market price for symbol"""
        pass
        
    @abstractmethod
    def create_order(self, symbol: str, side: str, 
                   quantity: Decimal, price: Optional[Decimal] = None) -> str:
        """Create new order and return order ID"""
        pass
        
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel existing order"""
        pass
        
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict:
        """Get current order status"""
        pass
        
    @abstractmethod
    def get_ohlcv(self, symbol: str, interval: str, 
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None) -> List[Dict]:
        """Get historical OHLCV data"""
        pass