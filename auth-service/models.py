from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict

class KeyStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"

class KeyPermission(BaseModel):
    name: str
    description: str

class APIKey(BaseModel):
    id: str
    key: Optional[str]  # Only returned on creation
    version: int
    created_at: datetime
    expires_at: datetime
    is_active: bool
    is_revoked: bool
    status: KeyStatus
    permissions: List[str]
    last_used_at: Optional[datetime]
    last_used_ip: Optional[str]
    last_used_agent: Optional[str]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class KeyRotationRequest(BaseModel):
    expire_in_days: int = 30  # Default 30 day expiration
    notify_before_days: int = 7  # Notify 7 days before expiration

class KeyRevocationRequest(BaseModel):
    reason: str

class PermissionUpdateRequest(BaseModel):
    permissions: List[str]

class KeyHistoryResponse(BaseModel):
    keys: List[APIKey]
    current_version: int

class ExpirationAlert(BaseModel):
    key_id: str
    expires_in_days: int
    expires_at: datetime

# User Management Models
class Role(BaseModel):
    name: str
    permissions: List[str]
    created_at: datetime
    description: Optional[str] = None

class User(BaseModel):
    id: str
    username: str
    email: str
    password: str  # Note: Should be hashed in production
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]
    roles: List[Role] = []
    metadata: Dict[str, str] = {}

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ActivityLog(BaseModel):
    user_id: str
    action: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    metadata: Dict[str, str] = {}

class AuditLog(BaseModel):
    admin_id: str
    action: str
    target_type: str
    target_id: str
    timestamp: datetime
    ip_address: str
    metadata: Dict[str, str] = {}