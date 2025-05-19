"""
Alerting Utility

This module provides alerting functionality for the trading system.
It supports different alert levels and delivery methods.
"""
from typing import Dict, List, Optional, Any, Callable
import logging
import json
import os
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class AlertManager:
    """
    Alert manager for trading systems.
    
    Handles sending alerts through various channels based on severity.
    """
    
    # Alert levels and their numeric values (higher = more severe)
    LEVELS = {
        "debug": 0,
        "info": 1,
        "warning": 2,
        "error": 3,
        "critical": 4
    }
    
    def __init__(self, min_level: str = "warning"):
        """
        Initialize the alert manager.
        
        Args:
            min_level: Minimum alert level to send (default: warning)
        """
        self.min_level = min_level
        self.min_level_value = self.LEVELS.get(min_level, 2)  # Default to warning if invalid
        
        # Alert handlers for different delivery methods
        self.handlers: Dict[str, Callable] = {
            "log": self._log_alert,
            "file": self._file_alert,
            "slack": self._slack_alert,
            # Additional handlers can be added here (email, SMS, webhook, etc.)
        }
        
        # Slack webhook URL (optional)
        self.slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        
        # Active delivery methods
        self.active_methods = ["log"]
        
        # Enable slack if webhook url is available
        if self.slack_webhook_url:
            self.active_methods.append("slack")
        
        # Add file alerting if directory exists
        alerts_dir = os.path.join(os.getcwd(), "alerts")
        if os.path.exists(alerts_dir) and os.path.isdir(alerts_dir):
            self.active_methods.append("file")
            self.alerts_dir = alerts_dir
        else:
            self.alerts_dir = None
        
        logger.info(f"Alert manager initialized with min level: {min_level}")
    
    def send_alert(self, title: str, message: str, level: str = "warning", 
                 data: Optional[Dict[str, Any]] = None, methods: Optional[List[str]] = None):
        """
        Send an alert through configured channels.
        
        Args:
            title: Alert title
            message: Alert message
            level: Alert level (debug, info, warning, error, critical)
            data: Optional additional data to include with the alert
            methods: Optional list of delivery methods to use (overrides defaults)
        """
        # Check if alert level meets minimum threshold
        level_value = self.LEVELS.get(level, 0)
        if level_value < self.min_level_value:
            return
        
        # Prepare alert data
        alert = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "data": data or {}
        }
        
        # Determine which methods to use
        delivery_methods = methods if methods is not None else self.active_methods
        
        # Send through each method
        for method in delivery_methods:
            if method in self.handlers:
                try:
                    self.handlers[method](alert)
                except Exception as e:
                    logger.error(f"Error sending alert via {method}: {e}")
    
    def _log_alert(self, alert: Dict[str, Any]):
        """Log the alert using the logging system"""
        level = alert["level"]
        title = alert["title"]
        message = alert["message"]
        
        log_message = f"ALERT: {title} - {message}"
        
        if level == "debug":
            logger.debug(log_message)
        elif level == "info":
            logger.info(log_message)
        elif level == "warning":
            logger.warning(log_message)
        elif level == "error":
            logger.error(log_message)
        elif level == "critical":
            logger.critical(log_message)
    
    def _file_alert(self, alert: Dict[str, Any]):
        """Write the alert to a file"""
        if not self.alerts_dir:
            return
        
        # Create filename based on date and alert level
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"{date_str}_{alert['level']}.log"
        filepath = os.path.join(self.alerts_dir, filename)
        
        # Write alert to file
        try:
            with open(filepath, "a") as f:
                f.write(json.dumps(alert) + "\n")
        except Exception as e:
            logger.error(f"Error writing alert to file: {e}")

    def _slack_alert(self, alert: Dict[str, Any]):
        """Send the alert to a Slack channel"""
        if not self.slack_webhook_url:
            return
        
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        
        client = WebClient()
        
        try:
            client.chat_postMessage(
                channel="#alerts",  # Replace with your channel name
                text=f"*{alert['level'].upper()}*: {alert['title']} - {alert['message']}",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{alert['level'].upper()}*: {alert['title']}\n{alert['message']}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Level:*\n{alert['level']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Timestamp:*\n{alert['timestamp']}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Data:*\n```{json.dumps(alert['data'], indent=2)}```"
                        }
                    }
                ]
            )
        except SlackApiError as e:
            logger.error(f"Error sending alert to Slack: {e}")

    def set_min_level(self, level: str):
        """
        Set the minimum alert level.
        
        Args:
            level: New minimum alert level
        """
        if level in self.LEVELS:
            self.min_level = level
            self.min_level_value = self.LEVELS[level]
            logger.info(f"Alert minimum level set to: {level}")
        else:
            logger.warning(f"Invalid alert level: {level}")
    
    def add_delivery_method(self, method: str, handler: Callable):
        """
        Add a new alert delivery method.
        
        Args:
            method: Method name
            handler: Function to handle the alert delivery
        """
        self.handlers[method] = handler
        self.active_methods.append(method)
        logger.info(f"Added alert delivery method: {method}")
    
    def remove_delivery_method(self, method: str):
        """
        Remove an alert delivery method.
        
        Args:
            method: Method name to remove
        """
        if method in self.active_methods:
            self.active_methods.remove(method)
            logger.info(f"Removed alert delivery method: {method}")