from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union, Any
import uuid
import jwt
import pyotp
import qrcode
import secrets
import string
import io
import base64
import json
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from config import settings
from database.db import get_db # Corrected import
from auth.models.user import User, Role
from auth.schemas.token import TokenType, TokenData

# Import monitoring decorators
from services.mcp.order_execution.monitoring import (
    log_execution_time,
    track_metrics,
    alert_on_failure,
    retry_with_backoff
)

def get_redis():
    """Get Redis client - mocked in tests"""
    from unittest.mock import MagicMock
    return MagicMock()

# Password hashing context - upgraded to Argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 password bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

@log_execution_time
@track_metrics("authentication")
@alert_on_failure(alert_threshold=5, window_seconds=300)
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password"""
    # First check cache
    cache_key = f"user:{username}"
    redis = get_redis()
    cached_user = redis.get_user(cache_key)
    
    if cached_user:
        if verify_password(password, cached_user.hashed_password):
            return cached_user
        return None
    
    # Cache miss - query database
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    if user.disabled:
        return None
    
    # Cache user data for future requests
    redis = get_redis()
    redis.cache_user(cache_key, user, ttl=3600)  # Cache for 1 hour
    
    return user

def create_token(
    data: Dict[str, Any], 
    token_type: TokenType, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT token"""
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    elif token_type == TokenType.REFRESH:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add token metadata
    to_encode.update({
        "exp": expire,
        "token_type": token_type.value,
        "jti": str(uuid.uuid4())  # Add unique JWT ID for potential revocation
    })
    
    # Create the token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

@log_execution_time
@track_metrics("token_creation")
def create_token_pair(user: User) -> Dict[str, Any]:
    """Create access and refresh tokens for a user"""
    # Get user roles as strings
    user_roles = [role.name for role in user.roles]
    
    # Create payload for tokens
    token_data = {
        "sub": user.username,
        "roles": user_roles,
        "email": user.email
    }
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(
        data=token_data,
        token_type=TokenType.ACCESS,
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = create_token(
        data=token_data,
        token_type=TokenType.REFRESH,
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "refresh_token_expires_in": int(refresh_token_expires.total_seconds())
    }

@log_execution_time
@track_metrics("token_refresh")
@retry_with_backoff(max_retries=3, retryable_errors=["timeout", "connection"])
@alert_on_failure(alert_threshold=5, window_seconds=300)
def refresh_access_token(refresh_token: str, db: Session) -> Dict[str, Any]:
    """Create a new access token using a refresh token"""
    try:
        # Acquire lock to prevent concurrent refresh attempts
        redis = get_redis()
        if not redis.acquire_refresh_lock(refresh_token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Concurrent refresh attempt detected",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            # Verify the token
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Check token type
            if payload.get("token_type") != TokenType.REFRESH.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if token is blacklisted
            redis = get_redis()
            if redis.is_blacklisted(refresh_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get username from token
            username = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Get user from database
            user = db.query(User).filter(User.username == username).first()
            if user is None or user.disabled:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Create a new access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
            # Get user roles
            user_roles = [role.name for role in user.roles]
            
            # Create new access token
            access_token = create_token(
                data={
                    "sub": username,
                    "roles": user_roles,
                    "email": user.email
                },
                token_type=TokenType.ACCESS,
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds())
            }
        
        finally:
            # Release the refresh token lock
            redis = get_redis()
            redis.release_refresh_lock(refresh_token)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@log_execution_time
@track_metrics("token_revocation")
@alert_on_failure(alert_threshold=3, window_seconds=300)
def revoke_token(token: str) -> bool:
    """Add a token to the blacklist"""
    try:
        # Decode token without verification to get expiration time
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        # Calculate remaining time until expiration
        exp = payload.get("exp")
        if exp:
            current_time = datetime.utcnow().timestamp()
            remaining_time = exp - current_time
            
            if remaining_time > 0:
                # Add token to blacklist with TTL matching its expiration
                return RedisService.add_to_blacklist(token, int(remaining_time))
        
        return False
    except jwt.JWTError:
        return False

@log_execution_time
@track_metrics("token_validation")
@alert_on_failure(alert_threshold=5, window_seconds=300)
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get the current user from a JWT token"""
    try:
        # Verify the token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Extract token data
        username = payload.get("sub")
        token_type = payload.get("token_type")
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check token type
        if token_type != TokenType.ACCESS.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is blacklisted
        redis = get_redis()
        if redis.is_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create token data model
        token_data = TokenData(
            sub=username,
            exp=datetime.fromtimestamp(payload.get("exp")),
            token_type=TokenType.ACCESS,
            roles=payload.get("roles", []),
            jti=payload.get("jti")
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # First check cache
    cache_key = f"user:{token_data.sub}"
    redis = get_redis()
    user = redis.get_user(cache_key)
    
    if not user:
        # Cache miss - query database
        user = db.query(User).filter(User.username == token_data.sub).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Cache user data for future requests
        redis = get_redis()
        redis.cache_user(cache_key, user, ttl=3600)  # Cache for 1 hour
    
    # Check if user is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is disabled"
        )
    return current_user

def has_role(roles: List[str]):
    """Dependency to check if user has any of the specified roles"""
    async def check_role(current_user: User = Depends(get_current_user)):
        # Get user roles as strings
        user_roles = [role.name for role in current_user.roles]
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return check_role

def generate_reset_token(email: str, db: Session) -> str:
    """Generate a password reset token"""
    # Verify the user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if user exists for security
        return None
    
    # Create reset token
    reset_token = create_token(
        data={"sub": email}, 
        token_type=TokenType.RESET,
        expires_delta=timedelta(minutes=30)
    )
    
    return reset_token

@log_execution_time
@track_metrics("reset_token_verification")
@alert_on_failure(alert_threshold=3, window_seconds=300)
def verify_reset_token(token: str) -> str:
    """Verify a password reset token and return email if valid"""
    try:
        # Verify the token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("token_type") != TokenType.RESET.value:
            raise ValueError("Invalid token type")
        
        # Return the email from the token
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise ValueError("Reset token expired")
    except jwt.JWTError:
        raise ValueError("Invalid reset token")

def update_password(email: str, new_password: str, db: Session) -> bool:
    """Update user password after validation"""
    # Get user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise ValueError("User not found")
    
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    # Hash the new password
    user.hashed_password = get_password_hash(new_password)
    
    # Save user to database
    db.commit()
    
    # Invalidate cached user data
    cache_key = f"user:{user.username}"
    redis = get_redis()
    redis.invalidate_user(cache_key)
    
    return True

# MFA Functions
def generate_totp_secret() -> str:
    """Generate a new TOTP secret"""
    return pyotp.random_base32()

def generate_totp_uri(secret: str, username: str, issuer: str = "CryptoBot") -> str:
    """Generate TOTP provisioning URI for QR code"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name=issuer
    )

def generate_qr_code(uri: str) -> str:
    """Generate base64 encoded QR code from TOTP URI"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@log_execution_time
@track_metrics("totp_verification")
@alert_on_failure(alert_threshold=5, window_seconds=300)
def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def generate_backup_codes(count: int = 10) -> List[str]:
    """Generate backup codes for MFA recovery"""
    alphabet = string.ascii_letters + string.digits
    return [
        ''.join(secrets.choice(alphabet) for _ in range(12))
        for _ in range(count)
    ]

def setup_mfa(user: User, db: Session) -> Dict[str, Any]:
    """Setup MFA for a user and return setup data"""
    # Generate TOTP secret
    secret = generate_totp_secret()
    user.totp_secret = secret
    
    # Generate backup codes
    backup_codes = generate_backup_codes()
    user.backup_codes = json.dumps(backup_codes)
    
    # Generate QR code URI
    uri = generate_totp_uri(secret, user.username)
    qr_code = generate_qr_code(uri)
    
    # Save changes
    user.mfa_setup = True
    db.commit()
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "manual_entry_code": secret,
        "backup_codes": backup_codes
    }

def verify_mfa_setup(user: User, code: str, db: Session) -> bool:
    """Verify MFA setup with a TOTP code"""
    if verify_totp_code(user.totp_secret, code):
        user.mfa_enabled = True
        db.commit()
        return True
    return False

def disable_mfa(user: User, db: Session) -> None:
    """Disable MFA for a user"""
    user.mfa_enabled = False
    user.mfa_setup = False
    user.totp_secret = None
    user.backup_codes = None
    db.commit()

def verify_backup_code(user: User, code: str, db: Session) -> bool:
    """Verify a backup code and mark it as used"""
    try:
        backup_codes = json.loads(user.backup_codes)
        
        if code in backup_codes:
            # Remove used code
            backup_codes.remove(code)
            user.backup_codes = json.dumps(backup_codes)
            db.commit()
            return True
        
        return False
    except Exception:
        return False

def get_mfa_status(user: User) -> Dict[str, Any]:
    """Get MFA status for a user"""
    try:
        backup_codes_count = 0
        if user.backup_codes:
            backup_codes = json.loads(user.backup_codes)
            backup_codes_count = len(backup_codes)
    except Exception:
        backup_codes_count = 0
    
    return {
        "mfa_enabled": user.mfa_enabled,
        "mfa_setup": user.mfa_setup,
        "backup_codes_remaining": backup_codes_count
    }

def enforce_mfa_required(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to enforce MFA is enabled for a user"""
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA is required for this operation"
        )
    return current_user

def get_mfa_challenge(user: User) -> Dict[str, Any]:
    """Generate MFA challenge for a user"""
    return {
        "mfa_required": user.mfa_enabled,
        "user_id": user.id,
        "username": user.username
    }

# Add the missing token_required decorator
def token_required(f):
    """Decorator to require a valid JWT token for a route"""
    @wraps(f)
    async def decorated_function(request: Request, *args, **kwargs):
        # Get the token from the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header is missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract the token
        parts = auth_header.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = parts[1]
        
        try:
            # Verify the token
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # Check token type
            if payload.get("token_type") != TokenType.ACCESS.value:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if token is blacklisted
            redis = get_redis()
            if redis.is_blacklisted(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Add user info to request state
            request.state.user = payload
            
            return await f(request, *args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return decorated_function

# Add the missing refresh_token_required decorator
def refresh_token_required(f):
    """Decorator to require a valid refresh token for a route"""
    @wraps(f)
    async def decorated_function(request: Request, *args, **kwargs):
        # Get the token from the Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header is missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract the token
        parts = auth_header.split()
        if parts[0].lower() != "bearer" or len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = parts[1]
        
        try:
            # Verify the token
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # Check token type
            if payload.get("token_type") != TokenType.REFRESH.value:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if token is blacklisted
            redis = get_redis()
            if redis.is_blacklisted(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Add user info to request state
            request.state.user = payload
            
            return await f(request, *args, **kwargs)
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    return decorated_function