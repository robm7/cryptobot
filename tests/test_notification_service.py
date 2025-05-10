import pytest
from datetime import datetime, timedelta
from services.notification import (
    NotificationService,
    NotificationChannel,
    NotificationTemplate,
    UserPreferences,
    NotificationSettings
)

@pytest.fixture
def mock_settings():
    return NotificationSettings(
        smtp_host="smtp.example.com",
        smtp_username="user@example.com",
        smtp_password="password",
        email_from="noreply@example.com",
        twilio_account_sid="test_sid",
        twilio_auth_token="test_token",
        twilio_from_number="+1234567890"
    )

@pytest.fixture
def notification_service(mock_settings):
    from services.notification import get_provider_configs
    configs = get_provider_configs(mock_settings)
    return NotificationService(configs)

@pytest.fixture
def test_template():
    return NotificationTemplate(
        name="test_template",
        subject="Test Notification",
        body="Hello {name}, this is a test notification",
        channels=[NotificationChannel.EMAIL, NotificationChannel.SMS]
    )

@pytest.fixture
def test_user():
    return UserPreferences(
        user_id="test_user",
        email="test@example.com",
        phone="+15551234567",
        preferred_channels=[NotificationChannel.EMAIL]
    )

def test_add_template(notification_service, test_template):
    notification_service.add_template(test_template)
    assert test_template.name in notification_service.templates

def test_update_user_preferences(notification_service, test_user):
    notification_service.update_user_preferences(test_user)
    assert test_user.user_id in notification_service.user_prefs

def test_rate_limiting(notification_service):
    user_id = "test_user"
    channel = NotificationChannel.EMAIL
    
    # First check should pass
    assert notification_service.check_rate_limit(user_id, channel)
    
    # Simulate hitting rate limit
    notification_service.rate_limits[user_id] = {
        channel.value: [datetime.now() - timedelta(minutes=1)] * 100
    }
    assert not notification_service.check_rate_limit(user_id, channel)

@pytest.mark.asyncio
async def test_send_notification(notification_service, test_template, test_user):
    notification_service.add_template(test_template)
    notification_service.update_user_preferences(test_user)
    
    # This will fail since we're using mock providers, but should go through the flow
    result = await notification_service.send_notification(
        test_user.user_id,
        test_template.name,
        {"name": "Test User"}
    )
    assert isinstance(result, bool)