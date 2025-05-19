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
    def generate_reconciliation_report(self, start_date: datetime = None, end_date: datetime = None,
                                      filters: Dict = None) -> Dict:
        """
        Generate reconciliation report showing order matching between local records and exchange data
        
        Args:
            start_date: Optional start date for filtering reports
            end_date: Optional end date for filtering reports
            filters: Optional additional filters (e.g., symbol, exchange)
            
        Returns:
            Dict containing reconciliation statistics and detailed mismatch information
        """
        pass
        
    @abstractmethod
    def export_report(self, report_data: Dict, format: str) -> bool:
        """Export report in specified format (csv, pdf, etc)"""
        pass