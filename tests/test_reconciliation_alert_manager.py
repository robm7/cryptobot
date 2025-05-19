import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from services.mcp.order_execution.alert_manager import ReconciliationAlertManager
from services.notification.service import NotificationService, NotificationChannel
from trade.utils.alerting import AlertManager

@pytest.fixture
def mock_alert_manager():
    """Create a mock AlertManager for testing"""
    mock = MagicMock(spec=AlertManager)
    mock.send_alert = MagicMock()
    return mock

@pytest.fixture
def mock_notification_service():
    """Create a mock NotificationService for testing"""
    mock = MagicMock(spec=NotificationService)
    mock.send_notification = AsyncMock()
    mock.add_template = MagicMock()
    return mock

@pytest.fixture
def reconciliation_alert_manager(mock_alert_manager, mock_notification_service):
    """Create a ReconciliationAlertManager with mocked dependencies"""
    with patch('services.mcp.order_execution.alert_manager.AlertManager', 
               return_value=mock_alert_manager):
        manager = ReconciliationAlertManager(
            notification_service=mock_notification_service,
            min_level="warning",
            dashboard_url="http://test.dashboard/reconciliation"
        )
        return manager

@pytest.mark.asyncio
async def test_send_mismatch_alert(reconciliation_alert_manager, mock_alert_manager, mock_notification_service):
    """Test sending a mismatch alert"""
    # Test parameters
    time_period = "daily"
    total_orders = 100
    mismatched_orders = 5
    missing_orders = 2
    extra_orders = 3
    user_ids = ["user1", "user2"]
    channels = [NotificationChannel.EMAIL]
    
    # Call the method
    await reconciliation_alert_manager.send_mismatch_alert(
        time_period=time_period,
        total_orders=total_orders,
        mismatched_orders=mismatched_orders,
        missing_orders=missing_orders,
        extra_orders=extra_orders,
        user_ids=user_ids,
        channels=channels
    )
    
    # Verify AlertManager was called
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert "Reconciliation Mismatch Alert" in call_args["title"]
    assert str(mismatched_orders) in call_args["message"]
    assert call_args["level"] == "warning"  # Based on 5% mismatch rate
    
    # Verify NotificationService was called for each user
    assert mock_notification_service.send_notification.call_count == len(user_ids)
    
    # Verify notification parameters for first user
    call_args = mock_notification_service.send_notification.call_args_list[0][1]
    assert call_args["user_id"] == user_ids[0]
    assert call_args["template_name"] == "reconciliation_mismatch_alert"
    assert call_args["context"]["total_orders"] == total_orders
    assert call_args["context"]["mismatched_orders"] == mismatched_orders
    assert call_args["force_channel"] == channels[0]

@pytest.mark.asyncio
async def test_send_failure_alert(reconciliation_alert_manager, mock_alert_manager, mock_notification_service):
    """Test sending a failure alert"""
    # Test parameters
    error_message = "Connection timeout"
    user_ids = ["user1", "user2"]
    channels = [NotificationChannel.SMS]
    
    # Call the method
    await reconciliation_alert_manager.send_failure_alert(
        error_message=error_message,
        user_ids=user_ids,
        channels=channels
    )
    
    # Verify AlertManager was called
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert "Reconciliation Process Failed" in call_args["title"]
    assert error_message in call_args["message"]
    assert call_args["level"] == "error"
    
    # Verify NotificationService was called for each user
    assert mock_notification_service.send_notification.call_count == len(user_ids)
    
    # Verify notification parameters for first user
    call_args = mock_notification_service.send_notification.call_args_list[0][1]
    assert call_args["user_id"] == user_ids[0]
    assert call_args["template_name"] == "reconciliation_failure_alert"
    assert call_args["context"]["error_message"] == error_message
    assert call_args["force_channel"] == channels[0]

@pytest.mark.asyncio
async def test_send_summary(reconciliation_alert_manager, mock_alert_manager, mock_notification_service):
    """Test sending a reconciliation summary"""
    # Test parameters
    date = "2025-05-15"
    total_runs = 24
    total_orders = 2400
    total_mismatches = 36
    avg_mismatch_rate = 0.015  # 1.5%
    alerts_triggered = 3
    user_ids = ["user1", "user2"]
    channels = [NotificationChannel.EMAIL]
    
    # Call the method
    await reconciliation_alert_manager.send_summary(
        date=date,
        total_runs=total_runs,
        total_orders=total_orders,
        total_mismatches=total_mismatches,
        avg_mismatch_rate=avg_mismatch_rate,
        alerts_triggered=alerts_triggered,
        user_ids=user_ids,
        channels=channels
    )
    
    # Verify AlertManager was called
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert date in call_args["title"]
    assert str(total_mismatches) in call_args["message"]
    assert call_args["level"] == "warning"  # Based on mismatch rate > 1%
    
    # Verify NotificationService was called for each user
    assert mock_notification_service.send_notification.call_count == len(user_ids)
    
    # Verify notification parameters for first user
    call_args = mock_notification_service.send_notification.call_args_list[0][1]
    assert call_args["user_id"] == user_ids[0]
    assert call_args["template_name"] == "reconciliation_summary"
    assert call_args["context"]["total_runs"] == total_runs
    assert call_args["context"]["total_orders"] == total_orders
    assert call_args["context"]["total_mismatches"] == total_mismatches
    assert "1.50%" in call_args["context"]["avg_mismatch_rate"]
    assert call_args["force_channel"] == channels[0]

@pytest.mark.asyncio
async def test_send_threshold_breach_alert(reconciliation_alert_manager, mock_alert_manager, mock_notification_service):
    """Test sending a threshold breach alert"""
    # Test parameters
    threshold_name = "max_mismatch_rate"
    threshold_value = 0.05  # 5%
    current_value = 0.08  # 8%
    user_ids = ["user1", "user2"]
    channels = [NotificationChannel.EMAIL, NotificationChannel.SMS]
    
    # Call the method
    await reconciliation_alert_manager.send_threshold_breach_alert(
        threshold_name=threshold_name,
        threshold_value=threshold_value,
        current_value=current_value,
        user_ids=user_ids,
        channels=channels
    )
    
    # Verify AlertManager was called
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert threshold_name in call_args["title"]
    assert str(threshold_value) in call_args["message"]
    assert str(current_value) in call_args["message"]
    assert call_args["level"] == "critical"
    
    # Verify NotificationService was called for each user
    assert mock_notification_service.send_notification.call_count == len(user_ids)
    
    # Verify notification parameters for first user
    call_args = mock_notification_service.send_notification.call_args_list[0][1]
    assert call_args["user_id"] == user_ids[0]
    assert call_args["template_name"] == "threshold_breach_alert"
    assert call_args["context"]["threshold_name"] == threshold_name
    assert call_args["context"]["threshold_value"] == threshold_value
    assert call_args["context"]["current_value"] == current_value
    assert call_args["force_channel"] == channels[0]

@pytest.mark.asyncio
async def test_send_alert(reconciliation_alert_manager, mock_alert_manager, mock_notification_service):
    """Test the new generic send_alert method"""
    # Test parameters
    level = "error"
    title = "Test Alert"
    message = "This is a test alert"
    details = {"key1": "value1", "key2": "value2"}
    recipients = ["user1", "user2"]
    channels = [NotificationChannel.EMAIL]
    
    # Call the method
    await reconciliation_alert_manager.send_alert(
        level=level,
        title=title,
        message=message,
        details=details,
        recipients=recipients,
        channels=channels
    )
    
    # Verify AlertManager was called
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify alert parameters
    call_args = mock_alert_manager.send_alert.call_args[1]
    assert call_args["title"] == title
    assert call_args["message"] == message
    assert call_args["level"] == level
    assert "key1" in call_args["data"]
    assert call_args["data"]["key1"] == "value1"
    
    # Verify NotificationService was called for each recipient
    assert mock_notification_service.send_notification.call_count == len(recipients)
    
    # Verify notification parameters for first recipient
    call_args = mock_notification_service.send_notification.call_args_list[0][1]
    assert call_args["user_id"] == recipients[0]
    assert call_args["template_name"] == "error_alert"  # Based on level
    assert call_args["context"]["title"] == title
    assert call_args["context"]["message"] == message
    assert call_args["context"]["level"] == level
    assert call_args["force_channel"] == channels[0]

@pytest.mark.asyncio
async def test_send_alert_with_notification_error(reconciliation_alert_manager, mock_alert_manager, mock_notification_service):
    """Test send_alert with notification service error"""
    # Make notification service raise an exception
    mock_notification_service.send_notification.side_effect = Exception("Service unavailable")
    
    # Test parameters
    level = "critical"
    title = "Critical Alert"
    message = "This is a critical alert"
    recipients = ["user1"]
    
    # Call the method - should not raise an exception
    await reconciliation_alert_manager.send_alert(
        level=level,
        title=title,
        message=message,
        recipients=recipients
    )
    
    # Verify AlertManager was still called
    mock_alert_manager.send_alert.assert_called_once()
    
    # Verify notification service was attempted
    mock_notification_service.send_notification.assert_called_once()

@pytest.mark.asyncio
async def test_send_alert_template_selection(reconciliation_alert_manager, mock_notification_service):
    """Test template selection in send_alert method"""
    # Test different alert levels
    levels = ["info", "warning", "error", "critical"]
    expected_templates = ["generic_alert", "generic_alert", "error_alert", "critical_alert"]
    
    for i, level in enumerate(levels):
        # Reset mock
        mock_notification_service.send_notification.reset_mock()
        
        # Call the method
        await reconciliation_alert_manager.send_alert(
            level=level,
            title=f"Test {level.capitalize()} Alert",
            message=f"This is a {level} alert",
            recipients=["user1"]
        )
        
        # Verify correct template was selected
        call_args = mock_notification_service.send_notification.call_args[1]
        assert call_args["template_name"] == expected_templates[i]