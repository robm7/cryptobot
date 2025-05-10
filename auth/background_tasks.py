"""
Background Tasks for API Key Rotation System

This module provides background tasks for:
- Scheduled key rotation
- Expiration checks
- Notification generation
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks, Depends

from database import get_db
from key_manager import KeyManager
from email_service import EmailService
from models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeyRotationTasks:
    """Background tasks for API key rotation"""
    
    def __init__(self, db: Session):
        """Initialize with database session"""
        self.db = db
        self.key_manager = KeyManager(db)
        self.email_service = EmailService()
        self.running = False
    
    async def start_scheduled_tasks(self):
        """Start all scheduled tasks"""
        if self.running:
            logger.warning("Scheduled tasks already running")
            return
        
        self.running = True
        
        # Start tasks
        asyncio.create_task(self.run_expiration_check())
        asyncio.create_task(self.run_notification_check())
        
        logger.info("Started scheduled API key rotation tasks")
    
    async def stop_scheduled_tasks(self):
        """Stop all scheduled tasks"""
        self.running = False
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
                
                # Get keys expiring in the next 7 days
                expiring_keys = self.key_manager.get_expiring_keys(days_threshold=7)
                
                # Group by user
                user_keys = {}
                for key in expiring_keys:
                    user_id = key["user_id"]
                    if user_id not in user_keys:
                        user_keys[user_id] = []
                    user_keys[user_id].append(key)
                
                # Send notifications
                for user_id, keys in user_keys.items():
                    await self.send_expiration_notification(user_id, keys)
                
                logger.info(f"Sent notifications for {len(expiring_keys)} expiring keys")
            except Exception as e:
                logger.error(f"Error in notification check: {str(e)}")
            
            # Wait for next interval
            await asyncio.sleep(interval_seconds)
    
    async def send_expiration_notification(self, user_id: int, keys: List[Dict[str, Any]]):
        """
        Send expiration notification to user
        
        Args:
            user_id: User ID
            keys: List of expiring keys
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
                "keys": []
            }
            
            for key in keys:
                # Calculate days until expiration
                expires_at = datetime.fromisoformat(key["expires_at"])
                days_left = (expires_at - datetime.utcnow()).days
                
                notification_data["keys"].append({
                    "id": key["id"],
                    "description": key["description"],
                    "exchange": key["exchange"],
                    "expires_at": key["expires_at"],
                    "days_left": days_left
                })
            
            # Send email notification
            # In a real implementation, this would send an actual email
            logger.info(f"Sending expiration notification to {user.email}")
            logger.info(f"Notification data: {notification_data}")
            
            # Uncomment in real implementation
            # await self.email_service.send_key_expiration_email(
            #     email=user.email,
            #     username=user.username,
            #     keys=notification_data["keys"]
            # )
        except Exception as e:
            logger.error(f"Error sending expiration notification: {str(e)}")
    
    async def rotate_expiring_keys(self, days_threshold: int = 7):
        """
        Automatically rotate keys that are about to expire
        
        Args:
            days_threshold: Days threshold for auto-rotation
        """
        try:
            logger.info(f"Auto-rotating keys expiring within {days_threshold} days")
            
            # Get keys expiring soon
            expiring_keys = self.key_manager.get_expiring_keys(days_threshold=days_threshold)
            
            # Rotate each key
            rotated_count = 0
            for key in expiring_keys:
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
            return rotated_count
        except Exception as e:
            logger.error(f"Error in auto-rotation: {str(e)}")
            return 0
    
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
                    "key": new_key["key"],
                    "description": new_key["description"],
                    "exchange": new_key["exchange"],
                    "expires_at": new_key["expires_at"]
                }
            }
            
            # Send email notification
            # In a real implementation, this would send an actual email
            logger.info(f"Sending rotation notification to {user.email}")
            logger.info(f"Notification data: {notification_data}")
            
            # Uncomment in real implementation
            # await self.email_service.send_key_rotation_email(
            #     email=user.email,
            #     username=user.username,
            #     old_key=notification_data["old_key"],
            #     new_key=notification_data["new_key"]
            # )
        except Exception as e:
            logger.error(f"Error sending rotation notification: {str(e)}")

# Global instance for background tasks
_rotation_tasks = None

def get_rotation_tasks(db: Session = Depends(get_db)) -> KeyRotationTasks:
    """Get or create KeyRotationTasks instance"""
    global _rotation_tasks
    if _rotation_tasks is None:
        _rotation_tasks = KeyRotationTasks(db)
    return _rotation_tasks

async def start_background_tasks(db: Session):
    """Start background tasks on application startup"""
    tasks = get_rotation_tasks(db)
    await tasks.start_scheduled_tasks()

async def stop_background_tasks():
    """Stop background tasks on application shutdown"""
    global _rotation_tasks
    if _rotation_tasks:
        await _rotation_tasks.stop_scheduled_tasks()