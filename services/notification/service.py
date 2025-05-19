import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from enum import Enum
from .providers import NotificationProviderFactory

class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    SLACK = "slack"

class NotificationTemplate(BaseModel):
    name: str
    subject: str
    body: str
    channels: List[NotificationChannel]

class UserPreferences(BaseModel):
    user_id: str
    email: Optional[EmailStr]
    phone: Optional[str]
    preferred_channels: List[NotificationChannel]
    opt_out: bool = False

class DeliveryStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"

class NotificationDelivery(BaseModel):
    notification_id: str
    channel: NotificationChannel
    status: DeliveryStatus
    timestamp: datetime
    error: Optional[str]

class NotificationService:
    def __init__(self, provider_configs: Dict[NotificationChannel, dict]):
        self.templates: Dict[str, NotificationTemplate] = {}
        self.user_prefs: Dict[str, UserPreferences] = {}
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.delivery_log: Dict[str, NotificationDelivery] = {}
        self.providers = {
            channel: NotificationProviderFactory.create_provider(channel, config)
            for channel, config in provider_configs.items()
        }
        self.logger = logging.getLogger(__name__)

    def add_template(self, template: NotificationTemplate):
        self.templates[template.name] = template

    def update_user_preferences(self, prefs: UserPreferences):
        self.user_prefs[prefs.user_id] = prefs

    def check_rate_limit(self, user_id: str, channel: NotificationChannel) -> bool:
        now = datetime.now()
        window_start = now - timedelta(hours=1)
        
        user_limits = self.rate_limits.get(user_id, {})
        channel_limits = user_limits.get(channel.value, [])
        
        # Filter events within the time window
        recent_events = [t for t in channel_limits if t >= window_start]
        
        # Update the rate limit tracker
        self.rate_limits.setdefault(user_id, {})
        self.rate_limits[user_id][channel.value] = recent_events + [now]
        
        # Check against limit (100/hour default)
        return len(recent_events) < 100

    async def send_notification(
        self,
        user_id: str,
        template_name: str,
        context: Dict = None,
        force_channel: Optional[NotificationChannel] = None
    ) -> bool:
        # Get user preferences
        prefs = self.user_prefs.get(user_id)
        if not prefs or prefs.opt_out:
            self.logger.info(f"User {user_id} has opted out of notifications")
            return False

        # Get template
        template = self.templates.get(template_name)
        if not template:
            self.logger.error(f"Template {template_name} not found")
            return False

        # Determine channel
        channel = force_channel or prefs.preferred_channels[0]
        if channel not in template.channels:
            self.logger.error(f"Channel {channel} not supported for template {template_name}")
            return False

        # Check rate limit
        if not self.check_rate_limit(user_id, channel):
            self.logger.warning(f"Rate limit exceeded for user {user_id} on channel {channel}")
            return False

        # Send notification (implementation varies by channel)
        success = await self._send_via_channel(user_id, channel, template, context)
        
        # Log delivery
        delivery = NotificationDelivery(
            notification_id=str(uuid.uuid4()),
            channel=channel,
            status=DeliveryStatus.SENT if success else DeliveryStatus.FAILED,
            timestamp=datetime.now(),
            error=None if success else "Failed to send notification"
        )
        self.delivery_log[delivery.notification_id] = delivery
        
        return success

    async def _send_via_channel(
        self,
        user_id: str,
        channel: NotificationChannel,
        template: NotificationTemplate,
        context: Dict
    ) -> bool:
        provider = self.providers.get(channel)
        if not provider:
            self.logger.error(f"No provider configured for channel {channel}")
            return False

        prefs = self.user_prefs.get(user_id)
        if not prefs:
            self.logger.error(f"No preferences found for user {user_id}")
            return False

        if channel == NotificationChannel.EMAIL and prefs.email:
            return await provider.send(prefs.email, template, context)
        elif channel == NotificationChannel.SMS and prefs.phone:
            return await provider.send(prefs.phone, template, context)
        elif channel == NotificationChannel.SLACK:
            # For Slack, we use a default channel from preferences or context
            slack_channel = context.get("slack_channel", "#alerts")
            return await provider.send(slack_channel, template, context)
        
        self.logger.error(f"Missing required contact info for channel {channel}")
        return False

    def get_delivery_status(self, notification_id: str) -> Optional[NotificationDelivery]:
        return self.delivery_log.get(notification_id)