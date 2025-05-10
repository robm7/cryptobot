from datetime import datetime
from typing import Dict, List
from decimal import Decimal
from .interfaces import ReportingInterface

class BasicReporter(ReportingInterface):
    """Basic implementation of reporting system"""
    
    def __init__(self, portfolio_manager=None, trade_executor=None):
        self.portfolio_manager = portfolio_manager
        self.trade_executor = trade_executor
        
    def generate_performance_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate performance report for given date range"""
        if not self.portfolio_manager:
            return {}
            
        metrics = self.portfolio_manager.get_performance_metrics()
        return {
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_return': metrics['total_return'],
            'current_value': metrics['current_value'],
            'annualized_return': self._calculate_annualized_return(start_date, end_date, metrics['total_return'])
        }
        
    def generate_trade_history_report(self, filters: Dict = None) -> List[Dict]:
        """Generate trade history report with optional filters"""
        if not self.trade_executor:
            return []
            
        trades = self.trade_executor.get_trade_history()
        if filters:
            trades = self._filter_trades(trades, filters)
        return trades
        
    def generate_risk_report(self) -> Dict:
        """Generate risk assessment report"""
        if not self.portfolio_manager:
            return {}
            
        return self.portfolio_manager.get_risk_metrics()
        
    def generate_execution_report(self) -> Dict:
        """Generate order execution quality report"""
        if not self.trade_executor:
            return {}
            
        return {
            'execution_quality': 1.0,  # Would calculate from actual execution
            'slippage': Decimal('0.0'),
            'fill_rate': 1.0
        }
        
    def export_report(self, report_data: Dict, format: str) -> bool:
        """Export report in specified format (csv, pdf, etc)"""
        # Basic implementation - would integrate with export services
        return True
        
    def _calculate_annualized_return(self, start_date, end_date, total_return):
        """Calculate annualized return from period return"""
        days = (end_date - start_date).days
        if days <= 0:
            return 0.0
        return (1 + total_return) ** (365.25/days) - 1
        
    def _filter_trades(self, trades, filters):
        """Apply filters to trade history"""
        filtered = []
        for trade in trades:
            match = True
            for key, value in filters.items():
                if trade.get(key) != value:
                    match = False
                    break
            if match:
                filtered.append(trade)
        return filtered