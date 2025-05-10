from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional

class OrderExecutionInterface(ABC):
    """Abstract base class for order execution systems"""
    
    @abstractmethod
    def execute_order(self, order_params: Dict) -> Optional[str]:
        """Execute trade order with given parameters"""
        pass
        
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order"""
        pass
        
    @abstractmethod
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get current status of order"""
        pass
        
    @abstractmethod
    def get_execution_stats(self) -> Dict:
        """Get execution performance statistics"""
        pass
        
    @abstractmethod
    def configure(self, config: Dict) -> bool:
        """Configure execution parameters"""
        pass