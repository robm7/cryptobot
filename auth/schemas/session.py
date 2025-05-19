from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class SessionOut(BaseModel):
    id: int
    session_token: str
    user_id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool
    is_suspicious: bool
    created_at: datetime
    last_activity: datetime
    # Add other fields from the Session model as needed for output

    class Config:
        from_attributes = True

class SessionTerminate(BaseModel):
    session_id: int
    message: str = "Session terminated"

class SuspiciousActivityOut(BaseModel): # Assuming this might also be needed if SessionOut is
    id: int
    session_id: int
    activity_type: str
    details: Optional[Any] = None # Using Any for JSON, be more specific if possible
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True
class SuspiciousActivityCreate(BaseModel):
    session_id: int
    activity_type: str
    details: Optional[Any] = None # Using Any for JSON, be more specific if possible
    severity: str