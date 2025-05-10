from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Optional

class StrategyExecutionInterface(ABC):
    """Abstract base class for strategy execution systems"""
    
    @abstractmethod
    def register_strategy(self, strategy_config: Dict) -> str:
        """Register new trading strategy"""
        pass
        
    @abstractmethod
    def start_strategy(self, strategy_id: str) -> bool:
        """Start executing a registered strategy"""
        pass
        
    @abstractmethod
    def stop_strategy(self, strategy_id: str) -> bool:
        """Stop executing a strategy"""
        pass
        
    @abstractmethod
    def get_strategy_status(self, strategy_id: str) -> Optional[Dict]:
        """Get current status of strategy"""
        pass
        
    @abstractmethod
    def get_active_strategies(self) -> List[Dict]:
        """Get list of all active strategies"""
        pass
        
    @abstractmethod
    def get_strategy_performance(self, strategy_id: str) -> Optional[Dict]:
        """Get performance metrics for strategy"""
        pass