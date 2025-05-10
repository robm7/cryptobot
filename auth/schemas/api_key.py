"""
API Key schemas for the API Key Rotation System
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

class KeyStatus(str, Enum):
    """API Key status enum"""
    ACTIVE = "active"           # Current active key
    ROTATING = "rotating"       # New key during rotation (grace period)
    EXPIRED = "expired"         # Key that has been rotated out
    REVOKED = "revoked"         # Key that was manually revoked
    COMPROMISED = "compromised" # Key that was marked as compromised

class APIKeyCreate(BaseModel):
    """Request to create a new API key"""
    description: str = Field(..., description="Description of the key's purpose")
    exchange: str = Field(..., description="Exchange this key is for")
    is_test: bool = Field(False, description="Whether this is a test key")
    expiry_days: Optional[int] = Field(90, description="Days until key expires")

class APIKeyRotate(BaseModel):
    """Request to rotate an API key"""
    key_id: str = Field(..., description="ID of the key to rotate")
    grace_period_hours: Optional[int] = Field(24, description="Hours to keep old key valid")

class APIKeyRevoke(BaseModel):
    """Request to revoke an API key"""
    key_id: str = Field(..., description="ID of the key to revoke")
    reason: str = Field("Manual revocation", description="Reason for revocation")

class APIKeyCompromise(BaseModel):
    """Request to mark an API key as compromised"""
    key_id: str = Field(..., description="ID of the key to mark as compromised")
    details: str = Field(..., description="Details about the compromise")

class APIKeyResponse(BaseModel):
    """Response containing API key details"""
    id: str = Field(..., description="Unique identifier for the key")
    key: str = Field(..., description="The API key value")
    description: str = Field(..., description="Description of the key's purpose")
    exchange: str = Field(..., description="Exchange this key is for")
    is_test: bool = Field(..., description="Whether this is a test key")
    status: KeyStatus = Field(..., description="Current status of the key")
    version: int = Field(..., description="Version number of the key")
    created_at: datetime = Field(..., description="When the key was created")
    expires_at: datetime = Field(..., description="When the key expires")
    last_used: Optional[datetime] = Field(None, description="When the key was last used")
    permissions: List[str] = Field(..., description="Permissions granted to this key")
    
    # Optional fields for rotating keys
    rotated_at: Optional[datetime] = Field(None, description="When the key was rotated")
    grace_period_ends: Optional[datetime] = Field(None, description="When the grace period ends")
    next_key_id: Optional[str] = Field(None, description="ID of the next key version")
    previous_key_id: Optional[str] = Field(None, description="ID of the previous key version")
    
    # Optional fields for revoked keys
    revoked_at: Optional[datetime] = Field(None, description="When the key was revoked")
    revocation_reason: Optional[str] = Field(None, description="Reason for revocation")
    
    # Optional fields for compromised keys
    compromised_at: Optional[datetime] = Field(None, description="When the key was marked compromised")
    compromise_details: Optional[str] = Field(None, description="Details about the compromise")
    
    class Config:
        """Pydantic config"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class APIKeyListResponse(BaseModel):
    """Response containing a list of API keys"""
    keys: List[APIKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")
    active: int = Field(..., description="Number of active keys")
    rotating: int = Field(..., description="Number of keys in rotation")
    expiring_soon: int = Field(..., description="Number of keys expiring within 7 days")

class APIKeyHistoryResponse(BaseModel):
    """Response containing API key version history"""
    exchange: str = Field(..., description="Exchange name")
    versions: List[APIKeyResponse] = Field(..., description="List of key versions")
    current_version: int = Field(..., description="Current active version")

class APIKeyExpiringResponse(BaseModel):
    """Response containing keys that are expiring soon"""
    keys: List[APIKeyResponse] = Field(..., description="List of expiring keys")
    days_threshold: int = Field(..., description="Days threshold used")

class APIKeyValidationResponse(BaseModel):
    """Response for API key validation"""
    valid: bool = Field(..., description="Whether the key is valid")
    key: Optional[APIKeyResponse] = Field(None, description="Key details if valid")
    message: Optional[str] = Field(None, description="Error message if invalid")