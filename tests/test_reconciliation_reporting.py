"""
Tests for the reconciliation reporting functionality
"""

import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from services.mcp.reporting.basic_reporter import BasicReporter
from services.mcp.order_execution.reconciliation_job import ReconciliationJob

class MockReconciliationJob:
    """Mock implementation of ReconciliationJob for testing"""
    
    def __init__(self, reports=None):
        self.reports = reports or []
        self.report_file = "test_reports.json"
        
    def get_reports(self):
        """Get all reconciliation reports"""
        return self.reports

def test_reconciliation_report_no_job():
    """Test generating reconciliation report with no job"""
    reporter = BasicReporter()
    report = reporter.generate_reconciliation_report()
    
    assert report["status"] == "failed"
    assert "error" in report
    assert "not available" in report["error"]

def test_reconciliation_report_empty():
    """Test generating reconciliation report with empty reports"""
    job = MockReconciliationJob([])
    reporter = BasicReporter(reconciliation_job=job)
    report = reporter.generate_reconciliation_report()
    
    assert report["status"] == "success"
    assert report["summary"]["total_reports"] == 0
    assert report["summary"]["total_orders"] == 0
    assert report["summary"]["total_mismatches"] == 0

def test_reconciliation_report_with_data():
    """Test generating reconciliation report with sample data"""
    # Create sample reports
    now = datetime.now()
    reports = []
    
    # Report 1: No mismatches
    reports.append({
        "timestamp": now.isoformat(),
        "result": {
            "total_orders": 100,
            "matched_orders": 100,
            "mismatched_orders": 0,
            "missing_orders": 0,
            "extra_orders": 0,
            "mismatch_percentage": 0.0,
            "alert_triggered": False,
            "time_period": "daily"
        }
    })
    
    # Report 2: Some mismatches
    reports.append({
        "timestamp": (now - timedelta(days=1)).isoformat(),
        "result": {
            "total_orders": 120,
            "matched_orders": 115,
            "mismatched_orders": 5,
            "missing_orders": 3,
            "extra_orders": 2,
            "mismatch_percentage": 0.042,
            "alert_triggered": True,
            "time_period": "daily"
        }
    })
    
    # Report 3: Older report
    reports.append({
        "timestamp": (now - timedelta(days=7)).isoformat(),
        "result": {
            "total_orders": 90,
            "matched_orders": 88,
            "mismatched_orders": 2,
            "missing_orders": 1,
            "extra_orders": 1,
            "mismatch_percentage": 0.022,
            "alert_triggered": False,
            "time_period": "daily"
        }
    })
    
    job = MockReconciliationJob(reports)
    reporter = BasicReporter(reconciliation_job=job)
    
    # Test with no filters
    report = reporter.generate_reconciliation_report()
    assert report["status"] == "success"
    assert report["summary"]["total_reports"] == 3
    assert report["summary"]["total_orders"] == 310
    assert report["summary"]["total_mismatches"] == 7
    assert report["summary"]["alerts_triggered"] == 1
    
    # Test with date filter
    yesterday = now - timedelta(days=1)
    report = reporter.generate_reconciliation_report(start_date=yesterday)
    assert report["status"] == "success"
    assert report["summary"]["total_reports"] == 2
    assert report["summary"]["total_orders"] == 220
    assert report["summary"]["total_mismatches"] == 5
    
    # Test with end date filter
    three_days_ago = now - timedelta(days=3)
    report = reporter.generate_reconciliation_report(end_date=three_days_ago)
    assert report["status"] == "success"
    assert report["summary"]["total_reports"] == 1
    assert report["summary"]["total_orders"] == 90
    assert report["summary"]["total_mismatches"] == 2

def test_reconciliation_report_from_file():
    """Test generating reconciliation report from file"""
    # Create a temporary file with sample reports
    temp_file = "temp_reports.json"
    
    now = datetime.now()
    reports = [
        {
            "timestamp": now.isoformat(),
            "result": {
                "total_orders": 100,
                "matched_orders": 95,
                "mismatched_orders": 5,
                "missing_orders": 3,
                "extra_orders": 2,
                "mismatch_percentage": 0.05,
                "alert_triggered": True,
                "time_period": "daily"
            }
        }
    ]
    
    with open(temp_file, "w") as f:
        json.dump(reports, f)
    
    try:
        # Create mock job with the temp file
        job = MagicMock()
        job.report_file = temp_file
        job.get_reports.side_effect = AttributeError("No get_reports method")
        
        reporter = BasicReporter(reconciliation_job=job)
        report = reporter.generate_reconciliation_report()
        
        assert report["status"] == "success"
        assert report["summary"]["total_reports"] == 1
        assert report["summary"]["total_orders"] == 100
        assert report["summary"]["total_mismatches"] == 5
        assert report["summary"]["alerts_triggered"] == 1
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])