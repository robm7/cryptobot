import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from services.mcp.order_execution.reconciliation_job import ReconciliationJob
from services.mcp.order_execution.alert_manager import ReconciliationAlertManager

@pytest.fixture
def mock_alert_manager():
    """Create a mock ReconciliationAlertManager for testing"""
    mock = MagicMock(spec=ReconciliationAlertManager)
    # Make send_alert an AsyncMock to handle async calls
    mock.send_alert = AsyncMock()
    return mock

@pytest.fixture
def mock_executor():
    """Create a mock ReliableOrderExecutor for testing"""
    mock = MagicMock()
    mock.configure = AsyncMock(return_value=True)
    mock.reconcile_orders = AsyncMock(return_value={
        "total_orders": 100,
        "matched_orders": 95,
        "mismatched_orders": 5,
        "missing_orders": [{"id": "order1"}, {"id": "order2"}],
        "extra_orders": [{"id": "order3"}, {"id": "order4"}, {"id": "order5"}],
        "mismatch_percentage": 0.05,
        "alert_triggered": True
    })
    return mock

@pytest.fixture
def reconciliation_job(mock_executor, mock_alert_manager):
    """Create a ReconciliationJob instance with mocked dependencies"""
    with patch('services.mcp.order_execution.reconciliation_job.ReliableOrderExecutor', 
               return_value=mock_executor):
        job = ReconciliationJob({
            "schedule": {
                "interval": "daily",
                "time": "00:00"
            },
            "reporting": {
                "file": "test_reports.json",
                "history_days": 7
            },
            "alerting": {
                "thresholds": {
                    "mismatch_percentage": 0.01,
                    "missing_orders": 2,
                    "extra_orders": 2
                },
                "notification_users": ["user1", "user2"],
                "dashboard_url": "http://test.dashboard/reconciliation"
            }
        })
        
        # Replace the auto-created alert manager with our mock
        job.alert_manager = mock_alert_manager
        
        return job

@pytest.mark.asyncio
async def test_configure(reconciliation_job, mock_executor):
    """Test the configure method"""
    result = await reconciliation_job.configure()
    
    assert result is True
    mock_executor.configure.assert_called_once_with(reconciliation_job.executor_config)

@pytest.mark.asyncio
async def test_run_reconciliation_success(reconciliation_job, mock_executor, mock_alert_manager):
    """Test successful reconciliation with alerts"""
    # Run reconciliation
    result = await reconciliation_job.run_reconciliation()
    
    # Verify executor was called
    mock_executor.reconcile_orders.assert_called_once_with(reconciliation_job.schedule_interval)
    
    # Verify result was stored
    assert reconciliation_job.last_run_status == "success"
    assert reconciliation_job.last_run_result == result
    
    # Verify alert was sent
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert call_args["level"] in ["warning", "error", "critical"]  # Depends on thresholds
    assert "Order Reconciliation Alert" in call_args["title"]
    assert isinstance(call_args["message"], str)
    assert call_args["details"] == result
    assert call_args["recipients"] == ["user1", "user2"]

@pytest.mark.asyncio
async def test_run_reconciliation_failure(reconciliation_job, mock_executor, mock_alert_manager):
    """Test reconciliation failure with error alert"""
    # Make the executor raise an exception
    error_message = "Connection error"
    mock_executor.reconcile_orders.side_effect = Exception(error_message)
    
    # Run reconciliation
    result = await reconciliation_job.run_reconciliation()
    
    # Verify status was updated
    assert reconciliation_job.last_run_status == "failed"
    assert "error" in reconciliation_job.last_run_result
    
    # Verify error alert was sent
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert call_args["level"] == "error"
    assert "Failed" in call_args["title"]
    assert error_message in call_args["message"]
    assert call_args["recipients"] == ["user1", "user2"]

@pytest.mark.asyncio
async def test_determine_alert_severity(reconciliation_job):
    """Test alert severity determination based on thresholds"""
    # Test case: Critical severity (3x threshold)
    result = {
        "mismatch_percentage": reconciliation_job.alert_thresholds["mismatch_percentage"] * 3.5,
        "missing_orders": ["order1", "order2", "order3", "order4", "order5", "order6"],
        "extra_orders": ["order7", "order8", "order9", "order10", "order11", "order12"]
    }
    severity = reconciliation_job._determine_alert_severity(result)
    assert severity == "critical"
    
    # Test case: Error severity (2x threshold)
    result = {
        "mismatch_percentage": reconciliation_job.alert_thresholds["mismatch_percentage"] * 2.5,
        "missing_orders": ["order1", "order2", "order3", "order4"],
        "extra_orders": ["order5", "order6", "order7", "order8"]
    }
    severity = reconciliation_job._determine_alert_severity(result)
    assert severity == "error"
    
    # Test case: Warning severity (1x threshold)
    result = {
        "mismatch_percentage": reconciliation_job.alert_thresholds["mismatch_percentage"] * 1.5,
        "missing_orders": ["order1", "order2"],
        "extra_orders": ["order3", "order4"]
    }
    severity = reconciliation_job._determine_alert_severity(result)
    assert severity == "warning"
    
    # Test case: Info severity (below threshold)
    result = {
        "mismatch_percentage": reconciliation_job.alert_thresholds["mismatch_percentage"] * 0.5,
        "missing_orders": ["order1"],
        "extra_orders": ["order2"]
    }
    severity = reconciliation_job._determine_alert_severity(result)
    assert severity == "info"

@pytest.mark.asyncio
async def test_format_alert_message(reconciliation_job):
    """Test alert message formatting"""
    result = {
        "mismatch_percentage": 0.05,
        "missing_orders": ["order1", "order2", "order3"],
        "extra_orders": ["order4", "order5"],
        "total_orders": 100
    }
    
    message = reconciliation_job._format_alert_message(result)
    
    # Verify message contains key information
    assert "3 missing orders" in message
    assert "2 extra orders" in message
    assert "5.00%" in message
    assert "100 total orders" in message
    assert reconciliation_job.dashboard_url in message

@pytest.mark.asyncio
async def test_save_report(reconciliation_job, tmp_path):
    """Test report saving functionality"""
    # Set up a temporary report file
    report_file = tmp_path / "test_reports.json"
    reconciliation_job.report_file = str(report_file)
    
    # Create a test result
    result = {
        "total_orders": 100,
        "matched_orders": 95,
        "mismatched_orders": 5,
        "missing_orders": ["order1", "order2"],
        "extra_orders": ["order3", "order4", "order5"],
        "mismatch_percentage": 0.05
    }
    
    # Save the report
    reconciliation_job._save_report(result)
    
    # Verify the report was saved
    assert report_file.exists()
    
    # Read the saved report
    with open(report_file, 'r') as f:
        reports = json.load(f)
    
    # Verify report content
    assert len(reports) == 1
    assert "timestamp" in reports[0]
    assert reports[0]["result"] == result

@pytest.mark.asyncio
async def test_get_status(reconciliation_job):
    """Test getting job status"""
    # Set up test data
    reconciliation_job.last_run_time = datetime.now()
    reconciliation_job.last_run_status = "success"
    reconciliation_job.last_run_result = {"total_orders": 100}
    
    # Get status
    status = reconciliation_job.get_status()
    
    # Verify status content
    assert "last_run_time" in status
    assert status["last_run_status"] == "success"
    assert status["last_run_result"] == {"total_orders": 100}
    assert "next_run_time" in status
    assert "schedule" in status
    assert status["schedule"]["interval"] == "daily"
    assert status["schedule"]["time"] == "00:00"