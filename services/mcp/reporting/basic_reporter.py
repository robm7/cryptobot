from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
import json
import os
from .interfaces import ReportingInterface

class BasicReporter(ReportingInterface):
    """Basic implementation of reporting system"""
    
    def __init__(self, portfolio_manager=None, trade_executor=None, reconciliation_job=None):
        self.portfolio_manager = portfolio_manager
        self.trade_executor = trade_executor
        self.reconciliation_job = reconciliation_job
        
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
        if not self.reconciliation_job:
            return {
                "error": "Reconciliation job not available",
                "status": "failed"
            }
            
        # Get reconciliation reports from the job
        try:
            # If the reconciliation job has a method to get reports, use it
            if hasattr(self.reconciliation_job, 'get_reports'):
                reports = self.reconciliation_job.get_reports()
            # Otherwise, try to read from the report file
            elif hasattr(self.reconciliation_job, 'report_file') and os.path.exists(self.reconciliation_job.report_file):
                with open(self.reconciliation_job.report_file, 'r') as f:
                    reports = json.load(f)
            else:
                return {
                    "error": "No reconciliation reports available",
                    "status": "failed"
                }
                
            # Filter reports by date range
            filtered_reports = []
            for report in reports:
                report_time = datetime.fromisoformat(report["timestamp"])
                
                if start_date and report_time < start_date:
                    continue
                    
                if end_date and report_time > end_date:
                    continue
                    
                # Apply additional filters if provided
                if filters:
                    match = True
                    for key, value in filters.items():
                        if key in report["result"] and report["result"][key] != value:
                            match = False
                            break
                    if not match:
                        continue
                        
                filtered_reports.append(report)
                
            # Calculate summary statistics
            total_orders = sum(r["result"].get("total_orders", 0) for r in filtered_reports)
            total_mismatches = sum(r["result"].get("mismatched_orders", 0) for r in filtered_reports)
            total_missing = sum(r["result"].get("missing_orders", 0) for r in filtered_reports)
            total_extra = sum(r["result"].get("extra_orders", 0) for r in filtered_reports)
            
            # Calculate average mismatch percentage
            if total_orders > 0:
                avg_mismatch_percentage = total_mismatches / total_orders
            else:
                avg_mismatch_percentage = 0.0
                
            # Count alerts
            alerts_triggered = sum(1 for r in filtered_reports if r["result"].get("alert_triggered", False))
            
            # Format the report
            return {
                "status": "success",
                "period": {
                    "start": start_date.isoformat() if start_date else "all",
                    "end": end_date.isoformat() if end_date else "all"
                },
                "summary": {
                    "total_reports": len(filtered_reports),
                    "total_orders": total_orders,
                    "total_mismatches": total_mismatches,
                    "total_missing": total_missing,
                    "total_extra": total_extra,
                    "avg_mismatch_percentage": avg_mismatch_percentage,
                    "alerts_triggered": alerts_triggered
                },
                "reports": filtered_reports
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "status": "failed"
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