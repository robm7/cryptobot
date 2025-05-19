"""
Notification Preferences API Router

This module provides API endpoints for managing user notification preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Dict, Optional

from services.notification.models import UserNotificationPreferences, NotificationChannel, AlertSeverity, ChannelConfig
from services.notification.preference_service import NotificationPreferenceService
from auth_service import get_current_active_user

router = APIRouter(prefix="/notification-preferences", tags=["notification-preferences"])

# Dependency to get the notification preference service
def get_preference_service():
    """
    Get the notification preference service.
    
    Returns:
        NotificationPreferenceService instance
    """
    # In a real implementation, this would get the service from a dependency injection system
    # For now, we'll create a new instance
    return NotificationPreferenceService()

@router.get("/me", response_model=UserNotificationPreferences)
async def get_my_preferences(
    current_user = Depends(get_current_active_user),
    preference_service = Depends(get_preference_service)
):
    """
    Get the current user's notification preferences.
    
    Returns:
        UserNotificationPreferences object
    """
    try:
        # Get preferences for the current user
        preferences = await preference_service.get_user_preferences(current_user["id"])
        
        if not preferences:
            # Create default preferences if none exist
            preferences = UserNotificationPreferences(
                user_id=current_user["id"],
                email=current_user.get("email"),
                channels={
                    NotificationChannel.EMAIL: ChannelConfig(
                        enabled=True,
                        address=current_user.get("email"),
                        min_severity=AlertSeverity.WARNING
                    ),
                    NotificationChannel.IN_APP: ChannelConfig(
                        enabled=True,
                        min_severity=AlertSeverity.INFO
                    )
                }
            )
            # Save default preferences
            await preference_service.save_user_preferences(preferences)
        
        return preferences
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification preferences: {str(e)}"
        )

@router.put("/me", response_model=UserNotificationPreferences)
async def update_my_preferences(
    preferences: UserNotificationPreferences = Body(...),
    current_user = Depends(get_current_active_user),
    preference_service = Depends(get_preference_service)
):
    """
    Update the current user's notification preferences.
    
    Args:
        preferences: Updated UserNotificationPreferences object
        
    Returns:
        Updated UserNotificationPreferences object
    """
    try:
        # Ensure the user_id matches the current user
        if preferences.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID in preferences does not match authenticated user"
            )
        
        # Validate channel configurations
        for channel, config in preferences.channels.items():
            if channel == NotificationChannel.EMAIL and config.enabled:
                if not config.address or "@" not in config.address:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid email address for {channel} channel"
                    )
            elif channel == NotificationChannel.SMS and config.enabled:
                if not config.address or not config.address.startswith("+"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid phone number for {channel} channel"
                    )
            elif channel == NotificationChannel.WEBHOOK and config.enabled:
                if not config.address or not config.address.startswith("http"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid webhook URL for {channel} channel"
                    )
        
        # Save updated preferences
        updated_preferences = await preference_service.save_user_preferences(preferences)
        
        return updated_preferences
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification preferences: {str(e)}"
        )

@router.get("/channels", response_model=List[Dict])
async def get_available_channels(
    current_user = Depends(get_current_active_user)
):
    """
    Get available notification channels and their capabilities.
    
    Returns:
        List of available notification channels
    """
    # Return the list of available channels and their capabilities
    return [
        {
            "id": NotificationChannel.EMAIL,
            "name": "Email",
            "description": "Receive notifications via email",
            "requires_address": True,
            "address_type": "email"
        },
        {
            "id": NotificationChannel.SMS,
            "name": "SMS",
            "description": "Receive notifications via SMS text messages",
            "requires_address": True,
            "address_type": "phone"
        },
        {
            "id": NotificationChannel.SLACK,
            "name": "Slack",
            "description": "Receive notifications in Slack",
            "requires_address": True,
            "address_type": "slack_id"
        },
        {
            "id": NotificationChannel.IN_APP,
            "name": "In-App",
            "description": "Receive notifications within the application",
            "requires_address": False
        },
        {
            "id": NotificationChannel.WEBHOOK,
            "name": "Webhook",
            "description": "Send notifications to a webhook URL",
            "requires_address": True,
            "address_type": "url"
        }
    ]

@router.get("/severities", response_model=List[Dict])
async def get_severity_levels(
    current_user = Depends(get_current_active_user)
):
    """
    Get available alert severity levels.
    
    Returns:
        List of available severity levels
    """
    # Return the list of severity levels
    return [
        {
            "id": AlertSeverity.INFO,
            "name": "Info",
            "description": "Informational alerts that don't require immediate attention"
        },
        {
            "id": AlertSeverity.WARNING,
            "name": "Warning",
            "description": "Warnings that may require attention"
        },
        {
            "id": AlertSeverity.ERROR,
            "name": "Error",
            "description": "Errors that require attention"
        },
        {
            "id": AlertSeverity.CRITICAL,
            "name": "Critical",
            "description": "Critical issues that require immediate attention"
        }
    ]