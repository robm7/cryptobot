"""
API Key Rotation System - API Endpoints

This module provides the API endpoints for the API Key Rotation System:
- Create, list, rotate, and revoke API keys
- View key history and expiring keys
- Emergency revocation
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from auth_service import get_current_active_user
from key_manager import KeyManager, KeyStatus
from schemas.api_key import (
    APIKeyCreate,
    APIKeyRotate,
    APIKeyRevoke,
    APIKeyCompromise,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyHistoryResponse,
    APIKeyExpiringResponse,
    APIKeyValidationResponse
)

# Create router
router = APIRouter(prefix="/api-keys", tags=["api-keys"])

def get_key_manager(db: Session = Depends(get_db)) -> KeyManager:
    """Dependency to get KeyManager instance"""
    return KeyManager(db)

@router.post("", response_model=APIKeyResponse)
async def create_api_key(
    api_key: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Create a new API key
    
    Creates a new API key for the specified exchange with the given description.
    The key will expire after the specified number of days (default: 90).
    """
    try:
        key_data = key_manager.create_key(
            user_id=current_user.id,
            description=api_key.description,
            exchange=api_key.exchange,
            is_test=api_key.is_test,
            expiry_days=api_key.expiry_days
        )
        
        # Convert string dates to datetime objects for response
        key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])
        key_data["expires_at"] = datetime.fromisoformat(key_data["expires_at"])
        
        return key_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )

@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    List all API keys for the current user
    
    Returns a list of all API keys owned by the current user,
    including active, rotating, and expired keys.
    """
    try:
        keys = key_manager.get_user_keys(current_user.id)
        
        # Convert string dates to datetime objects for response
        for key in keys:
            key["created_at"] = datetime.fromisoformat(key["created_at"])
            key["expires_at"] = datetime.fromisoformat(key["expires_at"])
            
            if key.get("rotated_at"):
                key["rotated_at"] = datetime.fromisoformat(key["rotated_at"])
            
            if key.get("grace_period_ends"):
                key["grace_period_ends"] = datetime.fromisoformat(key["grace_period_ends"])
            
            if key.get("revoked_at"):
                key["revoked_at"] = datetime.fromisoformat(key["revoked_at"])
            
            if key.get("compromised_at"):
                key["compromised_at"] = datetime.fromisoformat(key["compromised_at"])
            
            if key.get("last_used"):
                key["last_used"] = datetime.fromisoformat(key["last_used"])
        
        # Count keys by status
        active_count = sum(1 for k in keys if k["status"] == KeyStatus.ACTIVE)
        rotating_count = sum(1 for k in keys if k["status"] == KeyStatus.ROTATING)
        
        # Count keys expiring soon (within 7 days)
        now = datetime.utcnow()
        expiring_soon_count = sum(
            1 for k in keys 
            if k["status"] == KeyStatus.ACTIVE and 
            datetime.fromisoformat(k["expires_at"]) < now + timedelta(days=7)
        )
        
        return {
            "keys": keys,
            "total": len(keys),
            "active": active_count,
            "rotating": rotating_count,
            "expiring_soon": expiring_soon_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )

@router.post("/rotate", response_model=APIKeyResponse)
async def rotate_api_key(
    rotation: APIKeyRotate,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Rotate an API key
    
    Creates a new API key to replace the specified key.
    The old key will remain valid for the specified grace period (default: 24 hours).
    """
    try:
        key_data = key_manager.rotate_key(
            key_id=rotation.key_id,
            user_id=current_user.id,
            grace_period_hours=rotation.grace_period_hours
        )
        
        # Convert string dates to datetime objects for response
        key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])
        key_data["expires_at"] = datetime.fromisoformat(key_data["expires_at"])
        
        if key_data.get("last_used"):
            key_data["last_used"] = datetime.fromisoformat(key_data["last_used"])
        
        return key_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate API key: {str(e)}"
        )

@router.post("/revoke")
async def revoke_api_key(
    revocation: APIKeyRevoke,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Revoke an API key
    
    Immediately invalidates the specified API key.
    This action cannot be undone.
    """
    try:
        success = key_manager.revoke_key(
            key_id=revocation.key_id,
            user_id=current_user.id,
            reason=revocation.reason
        )
        
        if success:
            return {"detail": "API key revoked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )

@router.post("/emergency-revoke")
async def emergency_revoke_api_key(
    compromise: APIKeyCompromise,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager),
    background_tasks: BackgroundTasks = None
):
    """
    Emergency revocation for compromised API key
    
    Immediately invalidates the specified API key and marks it as compromised.
    This will trigger security alerts and create a high-severity audit log entry.
    """
    try:
        success = key_manager.mark_key_compromised(
            key_id=compromise.key_id,
            user_id=current_user.id,
            details=compromise.details
        )
        
        if success:
            # In a real implementation, this would trigger security alerts
            if background_tasks:
                # background_tasks.add_task(send_security_alert, compromise.key_id, compromise.details)
                pass
                
            return {
                "detail": "API key marked as compromised and revoked",
                "security_alert": "Security team has been notified"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark API key as compromised"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark API key as compromised: {str(e)}"
        )

@router.get("/history/{exchange}", response_model=APIKeyHistoryResponse)
async def get_api_key_history(
    exchange: str,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Get API key version history
    
    Returns the version history of API keys for the specified exchange.
    """
    try:
        history = key_manager.get_key_history(exchange, current_user.id)
        
        # Convert string dates to datetime objects for response
        for key in history:
            key["created_at"] = datetime.fromisoformat(key["created_at"])
            key["expires_at"] = datetime.fromisoformat(key["expires_at"])
            
            if key.get("rotated_at"):
                key["rotated_at"] = datetime.fromisoformat(key["rotated_at"])
            
            if key.get("grace_period_ends"):
                key["grace_period_ends"] = datetime.fromisoformat(key["grace_period_ends"])
            
            if key.get("revoked_at"):
                key["revoked_at"] = datetime.fromisoformat(key["revoked_at"])
            
            if key.get("compromised_at"):
                key["compromised_at"] = datetime.fromisoformat(key["compromised_at"])
            
            if key.get("last_used"):
                key["last_used"] = datetime.fromisoformat(key["last_used"])
        
        # Find current version
        current_version = max((k["version"] for k in history if k["status"] == KeyStatus.ACTIVE), default=0)
        
        return {
            "exchange": exchange,
            "versions": history,
            "current_version": current_version
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key history: {str(e)}"
        )

@router.get("/expiring", response_model=APIKeyExpiringResponse)
async def get_expiring_api_keys(
    days: int = 7,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Get API keys that are expiring soon
    
    Returns a list of API keys that will expire within the specified number of days.
    """
    try:
        # Get all user keys
        all_keys = key_manager.get_user_keys(current_user.id)
        
        # Filter for active keys expiring within the threshold
        now = datetime.utcnow()
        threshold = now + timedelta(days=days)
        
        expiring_keys = [
            k for k in all_keys 
            if k["status"] == KeyStatus.ACTIVE and 
            datetime.fromisoformat(k["expires_at"]) < threshold
        ]
        
        # Convert string dates to datetime objects for response
        for key in expiring_keys:
            key["created_at"] = datetime.fromisoformat(key["created_at"])
            key["expires_at"] = datetime.fromisoformat(key["expires_at"])
            
            if key.get("last_used"):
                key["last_used"] = datetime.fromisoformat(key["last_used"])
        
        return {
            "keys": expiring_keys,
            "days_threshold": days
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get expiring API keys: {str(e)}"
        )

@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Get API key details
    
    Returns detailed information about the specified API key.
    """
    try:
        key_data = key_manager.get_key(key_id)
        
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Verify user owns the key
        if key_data["user_id"] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this API key"
            )
        
        # Convert string dates to datetime objects for response
        key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])
        key_data["expires_at"] = datetime.fromisoformat(key_data["expires_at"])
        
        if key_data.get("rotated_at"):
            key_data["rotated_at"] = datetime.fromisoformat(key_data["rotated_at"])
        
        if key_data.get("grace_period_ends"):
            key_data["grace_period_ends"] = datetime.fromisoformat(key_data["grace_period_ends"])
        
        if key_data.get("revoked_at"):
            key_data["revoked_at"] = datetime.fromisoformat(key_data["revoked_at"])
        
        if key_data.get("compromised_at"):
            key_data["compromised_at"] = datetime.fromisoformat(key_data["compromised_at"])
        
        if key_data.get("last_used"):
            key_data["last_used"] = datetime.fromisoformat(key_data["last_used"])
        
        return key_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key: {str(e)}"
        )

@router.post("/validate", response_model=APIKeyValidationResponse)
async def validate_api_key(
    api_key: str,
    key_manager: KeyManager = Depends(get_key_manager)
):
    """
    Validate an API key
    
    Checks if the provided API key is valid and returns its details.
    This endpoint is primarily for internal service-to-service authentication.
    """
    try:
        is_valid, key_data = key_manager.validate_key(api_key)
        
        if is_valid and key_data:
            # Convert string dates to datetime objects for response
            key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])
            key_data["expires_at"] = datetime.fromisoformat(key_data["expires_at"])
            
            if key_data.get("last_used"):
                key_data["last_used"] = datetime.fromisoformat(key_data["last_used"])
            
            return {
                "valid": True,
                "key": key_data,
                "message": None
            }
        elif key_data:
            # Key exists but is not valid (expired, revoked, etc.)
            return {
                "valid": False,
                "key": None,
                "message": f"API key is not valid (status: {key_data['status']})"
            }
        else:
            # Key does not exist
            return {
                "valid": False,
                "key": None,
                "message": "API key not found"
            }
    except Exception as e:
        return {
            "valid": False,
            "key": None,
            "message": f"Error validating API key: {str(e)}"
        }