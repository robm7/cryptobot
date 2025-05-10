from datetime import datetime
from typing import Optional, List, Union
from enum import Enum
from pydantic import BaseModel, Field, validator

class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: int = Field(..., description="Token expiration in seconds")

class TokenData(BaseModel):
    sub: str
    exp: datetime
    token_type: TokenType
    roles: List[str] = []
    jti: Optional[str] = None  # JWT ID for token revocation
    mfa_verified: bool = False  # Whether MFA was completed for this session

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPairResponse(TokenResponse):
    refresh_token: str
    refresh_token_expires_in: int

class TokenValidationResponse(BaseModel):
    valid: bool
    username: Optional[str] = None
    roles: List[str] = []
    message: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class APIKeyResponse(BaseModel):
    api_key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    permissions: List[str] = []


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @validator('new_password')
    def validate_password_complexity(cls, v):
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?`~' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
class MFASetupResponse(BaseModel):
    """Response for TOTP setup containing QR code and secret"""
    secret: str = Field(..., description="TOTP secret key for manual entry")
    qr_code: str = Field(..., description="Base64 encoded QR code image")
    manual_entry_code: str = Field(..., description="TOTP secret for manual entry")

class MFAVerifyRequest(BaseModel):
    """Request to verify a TOTP code"""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")

class MFABackupCodesResponse(BaseModel):
    """Response containing new backup codes"""
    codes: List[str] = Field(..., description="Newly generated backup codes")

class MFAStatusResponse(BaseModel):
    """Response showing MFA status for user"""
    enabled: bool = Field(..., description="Whether MFA is enabled")
    setup_complete: bool = Field(..., description="Whether MFA setup is complete")
    backup_codes_remaining: int = Field(..., description="Number of unused backup codes")

class MFAEnableRequest(BaseModel):
    """Request to enable/disable MFA"""
    enable: bool = Field(..., description="True to enable MFA, False to disable")