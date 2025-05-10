from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from typing import List
from datetime import datetime, timedelta
import logging
from .key_manager import KeyManager
from .models import APIKey, KeyPermission

router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-Key")

def get_key_manager() -> KeyManager:
    return KeyManager()

@router.get("/keys/current", response_model=APIKey)
async def get_current_key(
    key_manager: KeyManager = Depends(get_key_manager),
    current_key: str = Depends(api_key_header)
):
    """Get the current active API key"""
    key = key_manager.get_key(current_key)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key

@router.get("/keys/history", response_model=List[APIKey])
async def get_key_history(
    key_manager: KeyManager = Depends(get_key_manager)
):
    """Get history of all keys for the current user"""
    return key_manager.get_key_history()

@router.get("/keys/expirations", response_model=List[APIKey])
async def get_upcoming_expirations(
    key_manager: KeyManager = Depends(get_key_manager)
):
    """Get keys that will expire soon"""
    return key_manager.get_expiring_keys(days=7)  # Keys expiring in next 7 days

@router.get("/keys/permissions", response_model=List[KeyPermission])
async def get_permissions(
    key_manager: KeyManager = Depends(get_key_manager),
    current_key: str = Depends(api_key_header)
):
    """Get permissions for current key"""
    return key_manager.get_permissions(current_key)

@router.post("/keys/permissions")
async def update_permissions(
    permissions: List[str],
    key_manager: KeyManager = Depends(get_key_manager),
    current_key: str = Depends(api_key_header)
):
    """Update permissions for current key"""
    if not key_manager.update_key_permissions(current_key, permissions):
        raise HTTPException(status_code=400, detail="Failed to update permissions")
    return {"status": "success"}

@router.post("/keys/rotate", response_model=APIKey)
async def rotate_key(
    key_manager: KeyManager = Depends(get_key_manager),
    current_key: str = Depends(api_key_header)
):
    """Rotate the current API key (creates new version)"""
    new_key = key_manager.rotate_key(current_key)
    if not new_key:
        raise HTTPException(status_code=400, detail="Failed to rotate key")
    return new_key

@router.post("/keys/revoke")
async def revoke_key(
    key_manager: KeyManager = Depends(get_key_manager),
    current_key: str = Depends(api_key_header)
):
    """Revoke the current API key"""
    if not key_manager.revoke_key(current_key):
        raise HTTPException(status_code=400, detail="Failed to revoke key")
    return {"status": "success"}