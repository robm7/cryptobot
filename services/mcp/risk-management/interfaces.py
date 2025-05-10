from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List

class RiskManagementInterface(ABC):
    """Abstract base class for risk management systems"""
    
    @abstractmethod
    def check_position_size(self, symbol: str, amount: Decimal) -> bool:
        """Check if position size is within risk limits"""
        pass
        
    @abstractmethod
    def check_portfolio_risk(self, positions: Dict[str, Decimal]) -> bool:
        """Check overall portfolio risk exposure"""
        pass
        
    @abstractmethod
    def get_risk_parameters(self) -> Dict:
        """Get current risk parameters"""
        pass
        
    @abstractmethod
    def update_risk_parameters(self, params: Dict):
        """Update risk parameters"""
        pass
        
    @abstractmethod
    def get_position_limits(self) -> Dict[str, Decimal]:
        """Get position size limits per symbol"""
        pass