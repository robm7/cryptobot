"""
Reconciliation Alert Manager

This module provides an enhanced alert manager for reconciliation alerts,
integrating both the AlertManager and NotificationService.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from trade.utils.alerting import AlertManager
from services.notification.service import NotificationService, NotificationChannel
from services.notification.templates import RECONCILIATION_TEMPLATES
from services.notification.preference_service import NotificationPreferenceService
from services.notification.models import AlertSeverity

logger = logging.getLogger(__name__)

class ReconciliationAlertManager:
    """
    Enhanced alert manager for reconciliation alerts.
    
    Integrates the AlertManager for logging and file-based alerts with
    the NotificationService for email, SMS, and Slack notifications.
    """
    
    def __init__(
        self,
        notification_service: Optional[NotificationService] = None,
        preference_service: Optional[NotificationPreferenceService] = None,
        min_level: str = "warning",
        dashboard_url: str = "http://localhost:3000/reconciliation"
    ):
        """
        Initialize the reconciliation alert manager.
        
        Args:
            notification_service: Optional NotificationService instance
            preference_service: Optional NotificationPreferenceService instance
            min_level: Minimum alert level to send (default: warning)
            dashboard_url: URL to the reconciliation dashboard
        """
        self.alert_manager = AlertManager(min_level=min_level)
        self.notification_service = notification_service
        self.preference_service = preference_service or NotificationPreferenceService()
        self.dashboard_url = dashboard_url
        
        # Register templates with notification service if available
        if self.notification_service:
            for template in RECONCILIATION_TEMPLATES.values():
                self.notification_service.add_template(template)
        
        logger.info("ReconciliationAlertManager initialized")
    
    async def send_mismatch_alert(
        self,
        time_period: str,
        total_orders: int,
        mismatched_orders: int,
        missing_orders: int,
        extra_orders: int,
        user_ids: Optional[List[str]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        Send an alert for reconciliation mismatches.
        
        Args:
            time_period: Time period of the reconciliation (e.g., "daily")
            total_orders: Total number of orders processed
            mismatched_orders: Number of mismatched orders
            missing_orders: Number of missing orders
            extra_orders: Number of extra orders
            user_ids: Optional list of user IDs to notify
            channels: Optional list of notification channels to use
        """
        # Calculate mismatch rate
        mismatch_rate = f"{(mismatched_orders / total_orders * 100):.2f}%" if total_orders > 0 else "0.00%"
        
        # Prepare alert data
        alert_data = {
            "time_period": time_period,
            "total_orders": total_orders,
            "mismatched_orders": mismatched_orders,
            "mismatch_rate": mismatch_rate,
            "missing_orders": missing_orders,
            "extra_orders": extra_orders,
            "dashboard_url": self.dashboard_url,
            "timestamp": datetime.now().isoformat()
        }
        
        # Determine alert level based on mismatch rate
        level = "info"
        if mismatched_orders > 0:
            mismatch_percentage = mismatched_orders / total_orders if total_orders > 0 else 0
            if mismatch_percentage >= 0.05:  # 5% or more
                level = "critical"
            elif mismatch_percentage >= 0.01:  # 1% or more
                level = "warning"
        
        # Send alert through AlertManager
        self.alert_manager.send_alert(
            title="Reconciliation Mismatch Alert",
            message=f"Detected {mismatched_orders} mismatched orders ({mismatch_rate}) in {time_period} reconciliation",
            level=level,
            data=alert_data
        )
        
        # Send notification if notification service is available
        if self.notification_service and user_ids:
            template_name = "reconciliation_mismatch_alert"
            for user_id in user_ids:
                await self.notification_service.send_notification(
                    user_id=user_id,
                    template_name=template_name,
                    context=alert_data,
                    force_channel=channels[0] if channels else None
                )
    
    async def send_failure_alert(
        self,
        error_message: str,
        user_ids: Optional[List[str]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        Send an alert for reconciliation process failures.
        
        Args:
            error_message: Error message describing the failure
            user_ids: Optional list of user IDs to notify
            channels: Optional list of notification channels to use
        """
        # Prepare alert data
        alert_data = {
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send alert through AlertManager
        self.alert_manager.send_alert(
            title="Reconciliation Process Failed",
            message=f"Reconciliation process failed: {error_message}",
            level="error",
            data=alert_data
        )
        
        # Send notification if notification service is available
        if self.notification_service and user_ids:
            template_name = "reconciliation_failure_alert"
            for user_id in user_ids:
                await self.notification_service.send_notification(
                    user_id=user_id,
                    template_name=template_name,
                    context=alert_data,
                    force_channel=channels[0] if channels else None
                )
    
    async def send_summary(
        self,
        date: str,
        total_runs: int,
        total_orders: int,
        total_mismatches: int,
        avg_mismatch_rate: float,
        alerts_triggered: int,
        user_ids: Optional[List[str]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        Send a reconciliation summary.
        
        Args:
            date: Date of the summary
            total_runs: Total number of reconciliation runs
            total_orders: Total number of orders processed
            total_mismatches: Total number of mismatched orders
            avg_mismatch_rate: Average mismatch rate
            alerts_triggered: Number of alerts triggered
            user_ids: Optional list of user IDs to notify
            channels: Optional list of notification channels to use
        """
        # Format average mismatch rate as percentage
        avg_mismatch_rate_str = f"{avg_mismatch_rate * 100:.2f}%"
        
        # Prepare alert data
        alert_data = {
            "date": date,
            "total_runs": total_runs,
            "total_orders": total_orders,
            "total_mismatches": total_mismatches,
            "avg_mismatch_rate": avg_mismatch_rate_str,
            "alerts_triggered": alerts_triggered,
            "dashboard_url": self.dashboard_url
        }
        
        # Determine level based on mismatch rate and alerts
        level = "info"
        if alerts_triggered > 0 or avg_mismatch_rate >= 0.01:
            level = "warning"
        
        # Send alert through AlertManager
        self.alert_manager.send_alert(
            title=f"Reconciliation Summary: {date}",
            message=f"Daily summary: {total_mismatches} mismatches in {total_orders} orders ({avg_mismatch_rate_str})",
            level=level,
            data=alert_data
        )
        
        # Send notification if notification service is available
        if self.notification_service and user_ids:
            template_name = "reconciliation_summary"
            for user_id in user_ids:
                await self.notification_service.send_notification(
                    user_id=user_id,
                    template_name=template_name,
                    context=alert_data,
                    force_channel=channels[0] if channels else None
                )
    
    async def send_threshold_breach_alert(
        self,
        threshold_name: str,
        threshold_value: Any,
        current_value: Any,
        user_ids: Optional[List[str]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        Send an alert for threshold breaches.
        
        Args:
            threshold_name: Name of the threshold that was breached
            threshold_value: Value of the threshold
            current_value: Current value that breached the threshold
            user_ids: Optional list of user IDs to notify
            channels: Optional list of notification channels to use
        """
        # Prepare alert data
        alert_data = {
            "threshold_name": threshold_name,
            "threshold_value": threshold_value,
            "current_value": current_value,
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": self.dashboard_url
        }
        
        # Send alert through AlertManager
        self.alert_manager.send_alert(
            title=f"Reconciliation Threshold Breach: {threshold_name}",
            message=f"Threshold breach: {threshold_name} = {threshold_value}, current value: {current_value}",
            level="critical",
            data=alert_data
        )
        
        # Send notification if notification service is available
        if self.notification_service and user_ids:
            template_name = "threshold_breach_alert"
            for user_id in user_ids:
                await self.notification_service.send_notification(
                    user_id=user_id,
                    template_name=template_name,
                    context=alert_data,
                    force_channel=channels[0] if channels else None
                )
    
    async def send_alert(
        self,
        level: str,
        title: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recipients: Optional[List[str]] = None,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        Send a generic alert with the specified level, title, and message.
        
        This is a general-purpose method that can be used for any type of alert.
        
        Args:
            level: Alert level (info, warning, error, critical)
            title: Alert title
            message: Alert message
            details: Optional dictionary with additional alert details
            recipients: Optional list of user IDs to notify
            channels: Optional list of notification channels to use
        """
        # Prepare alert data
        alert_data = details or {}
        alert_data.update({
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "dashboard_url": self.dashboard_url
        })
        
        # Send alert through AlertManager
        self.alert_manager.send_alert(
            title=title,
            message=message,
            level=level,
            data=alert_data
        )
        
        # Send notification if notification service is available
        if self.notification_service and recipients:
            template_name = "generic_alert"
            
            # Fall back to a specific template based on the alert level if available
            if level == "critical":
                template_name = "critical_alert"
            elif level == "error":
                template_name = "error_alert"
            
            # Convert level string to AlertSeverity enum
            severity = AlertSeverity.INFO
            if level.lower() == "warning":
                severity = AlertSeverity.WARNING
            elif level.lower() == "error":
                severity = AlertSeverity.ERROR
            elif level.lower() == "critical":
                severity = AlertSeverity.CRITICAL
            
            # Determine alert type from details or default to reconciliation
            alert_type = "reconciliation"
            if details and "alert_type" in details:
                alert_type = details["alert_type"]
            
            # Get available channels if none specified
            if not channels:
                channels = [
                    NotificationChannel.EMAIL,
                    NotificationChannel.SMS,
                    NotificationChannel.SLACK,
                    NotificationChannel.IN_APP
                ]
            
            for user_id in recipients:
                try:
                    # Check user preferences for each channel
                    for channel in channels:
                        # Check if user should be notified on this channel
                        should_notify = await self.preference_service.should_notify_user(
                            user_id=user_id,
                            alert_type=alert_type,
                            severity=severity,
                            channel=channel
                        )
                        
                        if should_notify:
                            # Get user preferences to get the correct address
                            user_prefs = await self.preference_service.get_user_preferences(user_id)
                            
                            # Skip if user has no preferences
                            if not user_prefs:
                                continue
                            
                            # Get channel config
                            channel_config = user_prefs.channels.get(channel)
                            if not channel_config or not channel_config.enabled:
                                continue
                            
                            # Send notification on this channel
                            await self.notification_service.send_notification(
                                user_id=user_id,
                                template_name=template_name,
                                context=alert_data,
                                force_channel=channel
                            )
                            
                            logger.info(f"Sent {level} alert to user {user_id} via {channel}")
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user_id}: {str(e)}")