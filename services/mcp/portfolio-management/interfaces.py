from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List

class PortfolioManagementInterface(ABC):
    """Abstract base class for portfolio management systems"""
    
    @abstractmethod
    def get_portfolio_value(self) -> Decimal:
        """Get total portfolio value across all assets"""
        pass
        
    @abstractmethod
    def get_asset_allocation(self) -> Dict[str, Decimal]:
        """Get current asset allocation percentages"""
        pass
        
    @abstractmethod
    def get_performance_metrics(self) -> Dict:
        """Get portfolio performance metrics"""
        pass
        
    @abstractmethod
    def rebalance_portfolio(self, target_allocation: Dict[str, Decimal]) -> bool:
        """Rebalance portfolio to target allocation"""
        pass
        
    @abstractmethod
    def get_trade_history(self) -> List[Dict]:
        """Get history of all portfolio trades"""
        pass
        
    @abstractmethod
    def get_risk_metrics(self) -> Dict:
        """Get portfolio risk metrics"""
        pass