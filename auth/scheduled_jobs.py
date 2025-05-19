"""
Scheduled Jobs for API Key Rotation System

This module provides scheduled jobs for:
- Automatic key rotation
- Expiration checks
- Notification generation
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks, Depends
from sqlalchemy.orm import Session

from database import get_db
from key_manager import KeyManager
from models.user import User
from config import settings
from email_service import EmailService
from redis_service import RedisService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeyRotationScheduler:
    """Scheduler for API key rotation jobs"""
    
    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
        self.key_manager = KeyManager(db)
        self.email_service = EmailService()
        self.redis_service = RedisService()
        self.running = False
        self.tasks = []
    
    async def start_scheduled_tasks(self):
        """Start all scheduled tasks"""
        if self.running:
            logger.warning("Scheduled tasks already running")
            return
        
        self.running = True
        
        # Start tasks
        self.tasks = [
            asyncio.create_task(self.run_expiration_check()),
            asyncio.create_task(self.run_notification_check()),
            asyncio.create_task(self.run_auto_rotation())
        ]
        
        logger.info("Started scheduled API key rotation tasks")
    
    async def stop_scheduled_tasks(self):
        """Stop all scheduled tasks"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks = []
        logger.info("Stopped scheduled API key rotation tasks")
    
    async def run_expiration_check(self, interval_seconds: int = 3600):
        """
        Run periodic expiration check
        
        Args:
            interval_seconds: Seconds between checks (default: 1 hour)
        """
        while self.running:
            try:
                logger.info("Running API key expiration check")
                processed_count = self.key_manager.process_expired_keys()
                logger.info(f"Processed {processed_count} expired keys")
            except Exception as e:
                logger.error(f"Error in expiration check: {str(e)}")
            
            # Wait for next interval
            await asyncio.sleep(interval_seconds)
    
    async def run_notification_check(self, interval_seconds: int = 86400):
        """
        Run periodic notification check for expiring keys
        
        Args:
            interval_seconds: Seconds between checks (default: 1 day)
        """
        while self.running:
            try:
                logger.info("Running API key expiration notification check")
                
                # Get keys expiring in the next 30 days
                expiring_keys = self.key_manager.get_expiring_keys(days_threshold=30)
                
                # Group by user and days until expiration
                user_notifications = {}
                
                for key in expiring_keys:
                    user_id = key["user_id"]
                    days_left = key.get("days_until_expiration", 0)
                    
                    # Only send notifications at specific thresholds
                    if days_left not in settings.API_KEY_EXPIRY_NOTIFICATION_DAYS:
                        continue
                    
                    if user_id not in user_notifications:
                        user_notifications[user_id] = {}
                    
                    if days_left not in user_notifications[user_id]:
                        user_notifications[user_id][days_left] = []
                    
                    user_notifications[user_id][days_left].append(key)
                
                # Send notifications
                notification_count = 0
                for user_id, days_data in user_notifications.items():
                    for days_left, keys in days_data.items():
                        await self.send_expiration_notification(user_id, keys, days_left)
                        notification_count += len(keys)
                
                logger.info(f"Sent notifications for {notification_count} expiring keys")
            except Exception as e:
                logger.error(f"Error in notification check: {str(e)}")
            
            # Wait for next interval
            await asyncio.sleep(interval_seconds)
    
    async def run_auto_rotation(self, interval_seconds: int = 86400):
        """
        Run periodic automatic key rotation
        
        Args:
            interval_seconds: Seconds between checks (default: 1 day)
        """
        while self.running:
            try:
                # Only run if auto-rotation is enabled
                if settings.API_KEY_AUTO_ROTATION_ENABLED:
                    logger.info("Running automatic API key rotation")
                    
                    # Get keys scheduled for rotation
                    rotation_keys = await self.get_keys_for_rotation()
                    
                    # Rotate each key
                    rotated_count = 0
                    for key in rotation_keys:
                        try:
                            # Rotate key with default grace period
                            new_key = self.key_manager.rotate_key(
                                key_id=key["id"],
                                user_id=key["user_id"]
                            )
                            
                            rotated_count += 1
                            
                            # Send notification about rotation
                            await self.send_rotation_notification(key["user_id"], key, new_key)
                        except Exception as e:
                            logger.error(f"Error rotating key {key['id']}: {str(e)}")
                    
                    logger.info(f"Auto-rotated {rotated_count} keys")
            except Exception as e:
                logger.error(f"Error in auto-rotation: {str(e)}")
            
            # Wait for next interval
            await asyncio.sleep(interval_seconds)
    
    async def get_keys_for_rotation(self) -> List[Dict[str, Any]]:
        """
        Get keys that should be automatically rotated
        
        Returns:
            List of keys to rotate
        """
        keys_to_rotate = []
        
        # Get keys expiring soon
        threshold_days = settings.API_KEY_AUTO_ROTATION_THRESHOLD_DAYS
        expiring_keys = self.key_manager.get_expiring_keys(days_threshold=threshold_days)
        
        # Filter keys based on rotation schedule
        for key in expiring_keys:
            # Check if key has a rotation schedule
            rotation_schedule = key.get("rotation_schedule")
            if rotation_schedule:
                # Check if scheduled rotation time has passed
                next_rotation = rotation_schedule.get("next_rotation")
                if next_rotation and datetime.fromisoformat(next_rotation) <= datetime.utcnow():
                    keys_to_rotate.append(key)
            else:
                # If no schedule, use default threshold
                days_left = key.get("days_until_expiration", 0)
                if days_left <= threshold_days:
                    keys_to_rotate.append(key)
        
        return keys_to_rotate
    
    async def send_expiration_notification(self, user_id: int, keys: List[Dict[str, Any]], days_left: int):
        """
        Send expiration notification to user
        
        Args:
            user_id: User ID
            keys: List of expiring keys
            days_left: Days until expiration
        """
        try:
            # Get user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for expiration notification")
                return
            
            # Prepare notification data
            notification_data = {
                "user": {
                    "username": user.username,
                    "email": user.email
                },
                "keys": [],
                "days_left": days_left
            }
            
            for key in keys:
                notification_data["keys"].append({
                    "id": key["id"],
                    "description": key["description"],
                    "exchange": key["exchange"],
                    "expires_at": key["expires_at"]
                })
            
            # Send email notification
            logger.info(f"Sending expiration notification to {user.email} for keys expiring in {days_left} days")
            
            await self.email_service.send_key_expiration_email(
                email=user.email,
                username=user.username,
                keys=notification_data["keys"],
                days_left=days_left
            )
        except Exception as e:
            logger.error(f"Error sending expiration notification: {str(e)}")
    
    async def send_rotation_notification(self, 
                                       user_id: int, 
                                       old_key: Dict[str, Any], 
                                       new_key: Dict[str, Any]):
        """
        Send notification about key rotation
        
        Args:
            user_id: User ID
            old_key: Old key data
            new_key: New key data
        """
        try:
            # Get user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for rotation notification")
                return
            
            # Calculate grace period end
            grace_period_ends = datetime.fromisoformat(old_key["grace_period_ends"])
            
            # Prepare notification data
            notification_data = {
                "user": {
                    "username": user.username,
                    "email": user.email
                },
                "old_key": {
                    "id": old_key["id"],
                    "description": old_key["description"],
                    "exchange": old_key["exchange"],
                    "grace_period_ends": old_key["grace_period_ends"]
                },
                "new_key": {
                    "id": new_key["id"],
                    "key": new_key["key"],  # This will be sent securely via email
                    "description": new_key["description"],
                    "exchange": new_key["exchange"],
                    "expires_at": new_key["expires_at"]
                }
            }
            
            # Send email notification
            logger.info(f"Sending rotation notification to {user.email}")
            
            await self.email_service.send_key_rotation_email(
                email=user.email,
                username=user.username,
                old_key=notification_data["old_key"],
                new_key=notification_data["new_key"]
            )
        except Exception as e:
            logger.error(f"Error sending rotation notification: {str(e)}")

# Global instance for scheduled jobs
_rotation_scheduler = None

def get_rotation_scheduler(db: Session = Depends(get_db)) -> KeyRotationScheduler:
    """Get or create KeyRotationScheduler instance"""
    global _rotation_scheduler
    if _rotation_scheduler is None:
        _rotation_scheduler = KeyRotationScheduler(db)
    return _rotation_scheduler

async def start_scheduled_jobs(db: Session):
    """Start scheduled jobs on application startup"""
    scheduler = get_rotation_scheduler(db)
    await scheduler.start_scheduled_tasks()

async def stop_scheduled_jobs():
    """Stop scheduled jobs on application shutdown"""
    global _rotation_scheduler
    if _rotation_scheduler:
        await _rotation_scheduler.stop_scheduled_tasks()