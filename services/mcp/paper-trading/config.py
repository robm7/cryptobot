from decimal import Decimal
from typing import Dict

class PaperTradingConfig:
    """Configuration for paper trading exchange"""
    
    def __init__(self):
        self.initial_balances: Dict[str, Decimal] = {
            'BTC': Decimal('1.0'),
            'ETH': Decimal('10.0'),
            'USDT': Decimal('10000.0'),
            'BNB': Decimal('100.0')
        }
        
        self.supported_pairs = [
            'BTC/USDT',
            'ETH/USDT',
            'BNB/USDT',
            'ETH/BTC'
        ]