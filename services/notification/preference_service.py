"""
Notification Preference Service

This module provides a service for managing user notification preferences.
"""

import json
import os
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime

from services.notification.models import UserNotificationPreferences, NotificationChannel, AlertSeverity

logger = logging.getLogger(__name__)

class NotificationPreferenceService:
    """
    Service for managing user notification preferences.
    
    This service handles the storage and retrieval of user notification preferences.
    In a production environment, this would use a database, but for simplicity,
    this implementation uses a JSON file.
    """
    
    def __init__(self, storage_path: str = "data/notification_preferences"):
        """
        Initialize the notification preference service.
        
        Args:
            storage_path: Path to the storage directory
        """
        self.storage_path = storage_path
        self.preferences_file = os.path.join(storage_path, "preferences.json")
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self):
        """Ensure the storage directory and files exist"""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            
            if not os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'w') as f:
                    json.dump({}, f)
        except Exception as e:
            logger.error(f"Failed to ensure storage exists: {str(e)}")
            raise
    
    async def get_user_preferences(self, user_id: str) -> Optional[UserNotificationPreferences]:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            UserNotificationPreferences object or None if not found
        """
        try:
            # Load all preferences
            with open(self.preferences_file, 'r') as f:
                all_preferences = json.load(f)
            
            # Get preferences for the specified user
            user_prefs_dict = all_preferences.get(user_id)
            if not user_prefs_dict:
                return None
            
            # Convert to UserNotificationPreferences object
            return UserNotificationPreferences(**user_prefs_dict)
        except Exception as e:
            logger.error(f"Failed to get user preferences: {str(e)}")
            raise
    
    async def save_user_preferences(self, preferences: UserNotificationPreferences) -> UserNotificationPreferences:
        """
        Save notification preferences for a user.
        
        Args:
            preferences: UserNotificationPreferences object
            
        Returns:
            Updated UserNotificationPreferences object
        """
        try:
            # Load all preferences
            with open(self.preferences_file, 'r') as f:
                all_preferences = json.load(f)
            
            # Update preferences for the specified user
            all_preferences[preferences.user_id] = preferences.dict()
            
            # Save all preferences
            with open(self.preferences_file, 'w') as f:
                json.dump(all_preferences, f, indent=2)
            
            return preferences
        except Exception as e:
            logger.error(f"Failed to save user preferences: {str(e)}")
            raise
    
    async def delete_user_preferences(self, user_id: str) -> bool:
        """
        Delete notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if preferences were deleted, False if not found
        """
        try:
            # Load all preferences
            with open(self.preferences_file, 'r') as f:
                all_preferences = json.load(f)
            
            # Check if preferences exist for the specified user
            if user_id not in all_preferences:
                return False
            
            # Delete preferences for the specified user
            del all_preferences[user_id]
            
            # Save all preferences
            with open(self.preferences_file, 'w') as f:
                json.dump(all_preferences, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to delete user preferences: {str(e)}")
            raise
    
    async def get_all_user_preferences(self) -> List[UserNotificationPreferences]:
        """
        Get notification preferences for all users.
        
        Returns:
            List of UserNotificationPreferences objects
        """
        try:
            # Load all preferences
            with open(self.preferences_file, 'r') as f:
                all_preferences = json.load(f)
            
            # Convert to UserNotificationPreferences objects
            return [UserNotificationPreferences(**prefs) for prefs in all_preferences.values()]
        except Exception as e:
            logger.error(f"Failed to get all user preferences: {str(e)}")
            raise
    
    async def should_notify_user(
        self, 
        user_id: str, 
        alert_type: str, 
        severity: AlertSeverity,
        channel: NotificationChannel
    ) -> bool:
        """
        Check if a user should be notified for a specific alert.
        
        Args:
            user_id: User ID
            alert_type: Type of alert (e.g., "reconciliation", "system", "performance")
            severity: Alert severity
            channel: Notification channel
            
        Returns:
            True if the user should be notified, False otherwise
        """
        try:
            # Get user preferences
            preferences = await self.get_user_preferences(user_id)
            if not preferences:
                # Default to notifying if no preferences are set
                return True
            
            # Check if the alert type is enabled
            if alert_type == "reconciliation" and not preferences.reconciliation_alerts:
                return False
            elif alert_type == "system" and not preferences.system_alerts:
                return False
            elif alert_type == "performance" and not preferences.performance_alerts:
                return False
            
            # Check if the channel is enabled and the severity meets the minimum
            channel_config = preferences.channels.get(channel)
            if not channel_config or not channel_config.enabled:
                return False
            
            # Convert severity to numeric value for comparison
            severity_values = {
                AlertSeverity.INFO: 0,
                AlertSeverity.WARNING: 1,
                AlertSeverity.ERROR: 2,
                AlertSeverity.CRITICAL: 3
            }
            
            if severity_values[severity] < severity_values[channel_config.min_severity]:
                return False
            
            # Check quiet hours
            if preferences.quiet_hours_start is not None and preferences.quiet_hours_end is not None:
                current_hour = datetime.now().hour
                in_quiet_hours = False
                
                if preferences.quiet_hours_start < preferences.quiet_hours_end:
                    # Simple case: quiet hours within the same day
                    in_quiet_hours = preferences.quiet_hours_start <= current_hour < preferences.quiet_hours_end
                else:
                    # Complex case: quiet hours span midnight
                    in_quiet_hours = current_hour >= preferences.quiet_hours_start or current_hour < preferences.quiet_hours_end
                
                if in_quiet_hours:
                    # Check if critical alerts override quiet hours
                    if severity != AlertSeverity.CRITICAL or not preferences.quiet_hours_override_critical:
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to check if user should be notified: {str(e)}")
            # Default to notifying in case of error
            return True