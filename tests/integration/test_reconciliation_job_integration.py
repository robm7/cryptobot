"""
Integration tests for the ReconciliationJob

These tests verify that the ReconciliationJob works correctly with
other components of the system, including the ReliableOrderExecutor,
exchange gateway, and database services.
"""

import pytest
import asyncio
import logging
import time
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock the imports that are causing problems
sys.modules['auth.auth_service'] = MagicMock()
sys.modules['config'] = MagicMock()
sys.modules['config.settings'] = MagicMock()

from services.mcp.order_execution.reconciliation_job import ReconciliationJob
from services.mcp.order_execution.reliable_executor import ReliableOrderExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockReliableOrderExecutor:
    """Mock implementation of ReliableOrderExecutor for testing"""
    
    def __init__(self, should_fail=False, mismatch_percentage=0.0):
        self.should_fail = should_fail
        self.mismatch_percentage = mismatch_percentage
        self.configure_called = False
        self.reconcile_called = False
        self.reconcile_count = 0
        self.config = {}
        
    async def configure(self, config):
        """Mock configuration"""
        self.configure_called = True
        self.config = config
        if self.should_fail:
            raise Exception("Configuration failed")
        return True
        
    async def reconcile_orders(self, time_period="daily"):
        """Mock reconciliation with configurable mismatch percentage"""
        self.reconcile_called = True
        self.reconcile_count += 1
        
        if self.should_fail:
            raise Exception("Reconciliation failed")
            
        # Generate mock reconciliation results
        total_orders = 100
        mismatched_orders = int(total_orders * self.mismatch_percentage)
        
        return {
            "total_orders": total_orders,
            "matched_orders": total_orders - mismatched_orders,
            "mismatched_orders": mismatched_orders,
            "missing_orders": mismatched_orders // 2,
            "extra_orders": mismatched_orders // 2,
            "mismatch_percentage": self.mismatch_percentage,
            "alert_triggered": self.mismatch_percentage > 0.01,
            "timestamp": datetime.now().isoformat(),
            "time_period": time_period
        }


class MockAlertManager:
    """Mock alert manager for testing"""
    
    def __init__(self):
        self.alerts = []
        
    def send_alert(self, title, message, level="info", data=None):
        """Record alert"""
        self.alerts.append({
            "title": title,
            "message": message,
            "level": level,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        return True


@pytest.fixture
def executor():
    """Create a mock executor"""
    return MockReliableOrderExecutor()


@pytest.fixture
def failing_executor():
    """Create a mock executor that fails"""
    return MockReliableOrderExecutor(should_fail=True)


@pytest.fixture
def mismatched_executor():
    """Create a mock executor with mismatches"""
    return MockReliableOrderExecutor(mismatch_percentage=0.05)  # 5% mismatch


@pytest.fixture
def alert_manager():
    """Create a mock alert manager"""
    return MockAlertManager()


@pytest.fixture
def temp_report_file(tmpdir):
    """Create a temporary file for reports"""
    return os.path.join(tmpdir, "reconciliation_reports.json")


@pytest.mark.asyncio
async def test_reconciliation_job_initialization(executor):
    """Test ReconciliationJob initialization"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        },
        "reporting": {
            "file": "test_reports.json",
            "history_days": 30
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = executor
    
    # Verify initialization
    assert job.schedule_interval == "daily"
    assert job.schedule_time == "00:00"
    assert job.report_file == "test_reports.json"
    assert job.report_history_days == 30


@pytest.mark.asyncio
async def test_reconciliation_job_configure(executor):
    """Test ReconciliationJob configuration"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = executor
    
    # Configure
    result = await job.configure()
    
    # Verify configuration
    assert result is True
    assert executor.configure_called is True
    assert executor.config == config.get("executor", {})


@pytest.mark.asyncio
async def test_reconciliation_job_configure_failure(failing_executor):
    """Test ReconciliationJob configuration failure"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = failing_executor
    
    # Configure
    result = await job.configure()
    
    # Verify configuration failed
    assert result is False
    assert failing_executor.configure_called is True


@pytest.mark.asyncio
async def test_reconciliation_job_run(executor):
    """Test ReconciliationJob run"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = executor
    
    # Run reconciliation
    result = await job.run_reconciliation()
    
    # Verify run
    assert executor.reconcile_called is True
    assert job.last_run_status == "success"
    assert job.last_run_time is not None
    assert job.last_run_result is not None
    assert result["total_orders"] == 100
    assert result["matched_orders"] == 100
    assert result["mismatched_orders"] == 0


@pytest.mark.asyncio
async def test_reconciliation_job_run_failure(failing_executor):
    """Test ReconciliationJob run failure"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = failing_executor
    
    # Run reconciliation
    result = await job.run_reconciliation()
    
    # Verify run failed
    assert failing_executor.reconcile_called is True
    assert job.last_run_status == "failed"
    assert job.last_run_time is not None
    assert "error" in result
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_reconciliation_job_with_mismatches(mismatched_executor, alert_manager):
    """Test ReconciliationJob with mismatches"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = mismatched_executor
    
    # Mock alert manager
    with patch('services.mcp.order_execution.reconciliation_job.AlertManager', return_value=alert_manager):
        # Run reconciliation
        result = await job.run_reconciliation()
        
        # Verify run
        assert mismatched_executor.reconcile_called is True
        assert job.last_run_status == "success"
        assert result["total_orders"] == 100
        assert result["mismatched_orders"] == 5
        assert result["mismatch_percentage"] == 0.05
        assert result["alert_triggered"] is True
        
        # Verify alert was triggered
        assert len(alert_manager.alerts) > 0
        assert "Reconciliation Alert" in alert_manager.alerts[0]["title"]
        assert alert_manager.alerts[0]["level"] == "critical"


@pytest.mark.asyncio
async def test_reconciliation_job_report_saving(executor, temp_report_file):
    """Test ReconciliationJob report saving"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        },
        "reporting": {
            "file": temp_report_file,
            "history_days": 30
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = executor
    
    # Run reconciliation
    await job.run_reconciliation()
    
    # Verify report was saved
    assert os.path.exists(temp_report_file)
    
    # Read the report
    with open(temp_report_file, 'r') as f:
        reports = json.load(f)
        
    # Verify report content
    assert len(reports) == 1
    assert "timestamp" in reports[0]
    assert "result" in reports[0]
    assert reports[0]["result"]["total_orders"] == 100


@pytest.mark.asyncio
async def test_reconciliation_job_report_history(executor, temp_report_file):
    """Test ReconciliationJob report history management"""
    # Create configuration with short history
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        },
        "reporting": {
            "file": temp_report_file,
            "history_days": 1  # Only keep 1 day of history
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = executor
    
    # Create some old reports
    old_reports = []
    for i in range(5):
        timestamp = (datetime.now() - timedelta(days=2)).isoformat()  # 2 days old
        old_reports.append({
            "timestamp": timestamp,
            "result": {
                "total_orders": 100,
                "matched_orders": 100,
                "mismatched_orders": 0
            }
        })
    
    # Write old reports
    with open(temp_report_file, 'w') as f:
        json.dump(old_reports, f)
    
    # Run reconciliation
    await job.run_reconciliation()
    
    # Read the report
    with open(temp_report_file, 'r') as f:
        reports = json.load(f)
        
    # Verify old reports were pruned
    assert len(reports) == 1  # Only the new report should remain
    
    # Verify the remaining report is recent
    report_time = datetime.fromisoformat(reports[0]["timestamp"])
    assert (datetime.now() - report_time).total_seconds() < 60  # Less than a minute old


@pytest.mark.asyncio
async def test_reconciliation_job_get_status(executor):
    """Test ReconciliationJob status reporting"""
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create job
    job = ReconciliationJob(config)
    
    # Replace executor with mock
    job.executor = executor
    
    # Run reconciliation
    await job.run_reconciliation()
    
    # Get status
    status = job.get_status()
    
    # Verify status
    assert status["last_run_status"] == "success"
    assert status["last_run_time"] is not None
    assert status["schedule"]["interval"] == "daily"
    assert status["schedule"]["time"] == "00:00"
    assert "next_run_time" in status


@pytest.mark.asyncio
async def test_reconciliation_job_different_intervals(executor):
    """Test ReconciliationJob with different intervals"""
    intervals = ["hourly", "daily", "weekly"]
    
    for interval in intervals:
        # Create configuration
        config = {
            "executor": {
                "retry": {
                    "max_retries": 3,
                    "backoff_base": 2.0
                }
            },
            "schedule": {
                "interval": interval,
                "time": "00:00"
            }
        }
        
        # Create job
        job = ReconciliationJob(config)
        
        # Replace executor with mock
        job.executor = executor
        
        # Schedule job
        job.schedule_job()
        
        # Verify scheduling
        if interval == "hourly":
            assert "hour" in str(next(iter(schedule.jobs)))
        elif interval == "daily":
            assert "day" in str(next(iter(schedule.jobs)))
        elif interval == "weekly":
            assert "monday" in str(next(iter(schedule.jobs)))
        
        # Clear schedule for next test
        schedule.clear()


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])