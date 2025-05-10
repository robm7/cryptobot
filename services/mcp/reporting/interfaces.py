from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

class ReportingInterface(ABC):
    """Abstract base class for reporting systems"""
    
    @abstractmethod
    def generate_performance_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate performance report for given date range"""
        pass
        
    @abstractmethod
    def generate_trade_history_report(self, filters: Dict = None) -> List[Dict]:
        """Generate trade history report with optional filters"""
        pass
        
    @abstractmethod
    def generate_risk_report(self) -> Dict:
        """Generate risk assessment report"""
        pass
        
    @abstractmethod
    def generate_execution_report(self) -> Dict:
        """Generate order execution quality report"""
        pass
        
    @abstractmethod
    def export_report(self, report_data: Dict, format: str) -> bool:
        """Export report in specified format (csv, pdf, etc)"""
        pass