from decimal import Decimal
from typing import Dict, List, Optional
import uuid
import json
import os
from datetime import datetime
from pathlib import Path
from services.mcp.order_execution.interfaces import ExchangeInterface

class PaperTradingExchange(ExchangeInterface):
    """Simulated cryptocurrency exchange for paper trading"""
    
    STATE_FILE = "paper_trading_state.json"
    
    def __init__(self, initial_balances: Dict[str, Decimal]):
        self.balances = initial_balances.copy()
        self.orders = {}  # order_id -> order_data
        self.trades = []  # List of executed trades
        self.fee_rate = Decimal('0.002')  # 0.2% taker fee
        self.slippage = Decimal('0.001')  # 0.1% slippage
        self.load_state()
        
    def get_order_history(self, limit: int = 100) -> List[Dict]:
        """Get recent order history"""
        return sorted(
            self.trades,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]

    def save_state(self):
        """Persist current state to file"""
        state = {
            'balances': {k: str(v) for k, v in self.balances.items()},
            'orders': self.orders,
            'trades': self.trades
        }
        Path(self.STATE_FILE).write_text(json.dumps(state))

    def load_state(self):
        """Load persisted state from file"""
        if os.path.exists(self.STATE_FILE):
            state = json.loads(Path(self.STATE_FILE).read_text())
            self.balances = {k: Decimal(v) for k, v in state['balances'].items()}
            self.orders = state.get('orders', {})
            self.trades = state.get('trades', [])
        
    def create_order(
        self,
        symbol: str,
        side: str,
        amount: Decimal,
        price: Decimal,
        order_type: str = "limit"
    ) -> Dict:
        """Create and execute a paper trade order"""
        if side not in ('buy', 'sell'):
            raise ValueError("Invalid order side")
            
        if order_type != "limit":
            raise ValueError("Only limit orders supported")
            
        base, quote = symbol.split('/')
        if base not in self.balances or quote not in self.balances:
            raise ValueError(f"Invalid symbol {symbol}")
            
        order_id = str(uuid.uuid4())
        executed_price = price * (1 + self.slippage if side == 'buy' else 1 - self.slippage)
        fee = amount * executed_price * self.fee_rate
        
        if side == 'buy':
            total_cost = amount * executed_price + fee
            if self.balances[quote] < total_cost:
                raise ValueError("Insufficient quote currency")
                
            self.balances[quote] -= total_cost
            self.balances[base] += amount
            
        else:  # sell
            if self.balances[base] < amount:
                raise ValueError("Insufficient base currency")
                
            self.balances[base] -= amount
            self.balances[quote] += amount * executed_price - fee
            
        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': float(amount),
            'price': float(executed_price),
            'fee': float(fee),
            'status': 'filled',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.orders[order_id] = order
        self.trades.append(order)
        return order