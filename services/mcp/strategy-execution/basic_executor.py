import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from .interfaces import StrategyExecutionInterface

class BasicStrategyExecutor(StrategyExecutionInterface):
    """Basic implementation of strategy execution system"""
    
    def __init__(self):
        self.strategies = {}
        self.active_strategies = set()
        
    async def register_strategy(self, strategy_config: Dict) -> str:
        """Register new trading strategy"""
        strategy_id = str(uuid.uuid4())
        self.strategies[strategy_id] = {
            'config': strategy_config,
            'status': 'registered',
            'created_at': datetime.utcnow(),
            'performance': {
                'total_trades': 0,
                'profit': 0.0,
                'win_rate': 0.0
            }
        }
        return strategy_id
        
    async def start_strategy(self, strategy_id: str) -> bool:
        """Start executing a registered strategy"""
        if strategy_id not in self.strategies:
            return False
            
        self.strategies[strategy_id]['status'] = 'running'
        self.active_strategies.add(strategy_id)
        return True
        
    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop executing a strategy"""
        if strategy_id not in self.strategies:
            return False
            
        self.strategies[strategy_id]['status'] = 'stopped'
        self.active_strategies.discard(strategy_id)
        return True
        
    async def get_strategy_status(self, strategy_id: str) -> Optional[Dict]:
        """Get current status of strategy"""
        if strategy_id not in self.strategies:
            return None
            
        return {
            'status': self.strategies[strategy_id]['status'],
            'config': self.strategies[strategy_id]['config'],
            'created_at': self.strategies[strategy_id]['created_at']
        }
        
    async def get_active_strategies(self) -> List[Dict]:
        """Get list of all active strategies"""
        return [
            {
                'id': strategy_id,
                'config': self.strategies[strategy_id]['config']
            }
            for strategy_id in self.active_strategies
        ]
        
    async def get_strategy_performance(self, strategy_id: str) -> Optional[Dict]:
        """Get performance metrics for strategy"""
        if strategy_id not in self.strategies:
            return None
            
        return self.strategies[strategy_id]['performance'].copy()