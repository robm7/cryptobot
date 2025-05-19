"""
Slack Notification Provider

This module provides a Slack notification provider for the notification service.
"""

import logging
import json
import aiohttp
from typing import Optional
from ..service import NotificationTemplate

class SlackProvider:
    """
    Slack notification provider.
    
    Sends notifications to Slack channels using webhooks.
    """
    
    def __init__(self, webhook_url: str):
        """
        Initialize the Slack provider.
        
        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)
    
    async def send(
        self, 
        channel: str, 
        template: NotificationTemplate, 
        context: Optional[dict] = None
    ) -> bool:
        """
        Send a notification to a Slack channel.
        
        Args:
            channel: Slack channel name (e.g., "#alerts")
            template: Notification template
            context: Template context
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Render template with context
            subject = template.subject.format(**(context or {}))
            body = template.body.format(**(context or {}))
            
            # Determine color based on context
            color = "#36a64f"  # Default to green
            if context and "level" in context:
                if context["level"] == "warning":
                    color = "#ffcc00"  # Yellow
                elif context["level"] in ["error", "critical"]:
                    color = "#ff0000"  # Red
            
            # Create Slack message payload
            payload = {
                "channel": channel,
                "attachments": [
                    {
                        "fallback": subject,
                        "color": color,
                        "title": subject,
                        "text": body,
                        "fields": []
                    }
                ]
            }
            
            # Add fields from context data if available
            if context and "data" in context and isinstance(context["data"], dict):
                for key, value in context["data"].items():
                    if key != "level":  # Skip level as it's used for color
                        payload["attachments"][0]["fields"].append({
                            "title": key.replace("_", " ").title(),
                            "value": str(value),
                            "short": True
                        })
            
            # Send to Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Slack API error: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")
            return False