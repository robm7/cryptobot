"""
Notification Models

This module defines the data models for notification preferences and settings.
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Notification channel types"""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    IN_APP = "in_app"
    WEBHOOK = "webhook"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ChannelConfig(BaseModel):
    """Configuration for a notification channel"""
    enabled: bool = True
    address: Optional[str] = None  # Email address, phone number, webhook URL, etc.
    min_severity: AlertSeverity = AlertSeverity.WARNING  # Minimum severity level to notify on this channel


class UserNotificationPreferences(BaseModel):
    """User notification preferences model"""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    slack_user_id: Optional[str] = None
    webhook_url: Optional[str] = None
    
    # Channel-specific configurations
    channels: Dict[NotificationChannel, ChannelConfig] = Field(default_factory=dict)
    
    # Alert type preferences
    reconciliation_alerts: bool = True
    system_alerts: bool = True
    performance_alerts: bool = True
    
    # Time preferences
    quiet_hours_start: Optional[int] = None  # Hour of day (0-23)
    quiet_hours_end: Optional[int] = None  # Hour of day (0-23)
    quiet_hours_override_critical: bool = True  # Override quiet hours for critical alerts
    
    # Grouping preferences
    group_similar_alerts: bool = True
    max_alerts_per_hour: int = 10
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user123",
                "email": "user@example.com",
                "phone": "+15551234567",
                "channels": {
                    "email": {
                        "enabled": True,
                        "address": "user@example.com",
                        "min_severity": "warning"
                    },
                    "sms": {
                        "enabled": True,
                        "address": "+15551234567",
                        "min_severity": "error"
                    }
                },
                "reconciliation_alerts": True,
                "quiet_hours_start": 22,
                "quiet_hours_end": 7,
                "quiet_hours_override_critical": True
            }
        }


class NotificationDeliveryStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"  # Due to rate limiting, quiet hours, etc.


class NotificationRecord(BaseModel):
    """Record of a sent notification"""
    id: str
    user_id: str
    timestamp: str  # ISO format
    alert_id: Optional[str] = None
    alert_type: str
    severity: AlertSeverity
    channel: NotificationChannel
    status: NotificationDeliveryStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None  # Error message if delivery failed