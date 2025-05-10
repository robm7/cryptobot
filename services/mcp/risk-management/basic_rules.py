from decimal import Decimal
from typing import Dict
from .interfaces import RiskManagementInterface

class BasicRiskRules(RiskManagementInterface):
    """Basic implementation of risk management rules"""
    
    def __init__(self):
        self.risk_parameters = {
            'max_position_size': Decimal('0.1'),  # 10% of portfolio per position
            'max_portfolio_risk': Decimal('0.3'),  # 30% total portfolio risk
            'position_limits': {}  # Symbol-specific limits
        }
        
    def check_position_size(self, symbol: str, amount: Decimal) -> bool:
        """Check if position size is within risk limits"""
        if symbol in self.risk_parameters['position_limits']:
            return amount <= self.risk_parameters['position_limits'][symbol]
        return amount <= self.risk_parameters['max_position_size']
        
    def check_portfolio_risk(self, positions: Dict[str, Decimal]) -> bool:
        """Check overall portfolio risk exposure"""
        total_exposure = sum(positions.values())
        return total_exposure <= self.risk_parameters['max_portfolio_risk']
        
    def get_risk_parameters(self) -> Dict:
        """Get current risk parameters"""
        return self.risk_parameters.copy()
        
    def update_risk_parameters(self, params: Dict):
        """Update risk parameters"""
        self.risk_parameters.update(params)
        
    def get_position_limits(self) -> Dict[str, Decimal]:
        """Get position size limits per symbol"""
        return self.risk_parameters['position_limits'].copy()