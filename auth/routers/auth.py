from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import secrets
import string
import pyotp
import qrcode
import base64
from io import BytesIO

from database import get_db
from models.user import User, APIKey, UserCreate, UserOut, UserUpdate, APIKeyCreate, APIKeyOut
from schemas.token import (
    Token,
    TokenResponse,
    TokenPairResponse,
    RefreshTokenRequest,
    TokenValidationResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    APIKeyResponse,
    ChangePasswordRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MFABackupCodesResponse,
    MFAStatusResponse,
    MFAEnableRequest,
    TokenType
)
from auth_service import (
    authenticate_user,
    create_token_pair,
    refresh_access_token,
    revoke_token,
    get_current_user,
    get_current_active_user,
    has_role,
    generate_reset_token,
    verify_reset_token,
    update_password,
    get_password_hash,
    generate_totp_secret,
    generate_totp_uri,
    verify_totp_code,
    generate_backup_codes,
    verify_backup_code,
    get_mfa_status,
    enforce_mfa_required
)
from redis_service import RateLimiter
from config import settings

# Create router
router = APIRouter()

# Rate limiting middleware
@router.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for token validation endpoint
    if not request.url.path.endswith("/validate"):
        await RateLimiter.check_rate_limit(request)
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers if available
    if hasattr(request.state, "rate_limit"):
        rate_limit = request.state.rate_limit
        response.headers["X-RateLimit-Limit"] = str(rate_limit["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit["reset"])
    
    return response

@router.post("/login", response_model=Union[TokenPairResponse, Dict[str, Any]])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username and password to get access and refresh tokens"""
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if MFA is required (enabled or admin enforcement)
    if user.mfa_enabled or (enforce_mfa_required(user) and not user.mfa_setup):
        return {
            "mfa_required": True,
            "mfa_token": create_token(
                {"sub": user.username},
                TokenType.MFA_CHALLENGE,
                timedelta(minutes=5)
            ),
            "mfa_setup_required": enforce_mfa_required(user) and not user.mfa_setup
        }
    
    # Create tokens
    tokens = create_token_pair(user)
    
    return tokens

@router.post("/mfa/verify-login", response_model=TokenPairResponse)
async def verify_mfa_login(
    verify_request: MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify MFA code during login"""
    try:
        # Verify MFA challenge token
        payload = jwt.decode(
            verify_request.mfa_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("token_type") != TokenType.MFA_CHALLENGE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
            
        # Get user
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Verify TOTP code
        if not verify_totp_code(user.totp_secret, verify_request.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
            
        # Create tokens
        return create_token_pair(user)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA challenge expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge"
        )

@router.post("/mfa/verify-backup", response_model=TokenPairResponse)
async def verify_backup_login(
    verify_request: MFAVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify backup code during login"""
    try:
        # Verify MFA challenge token
        payload = jwt.decode(
            verify_request.mfa_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("token_type") != TokenType.MFA_CHALLENGE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
            
        # Get user
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        # Verify backup code
        if not verify_backup_code(user, verify_request.code, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid backup code"
            )
            
        # Create tokens
        return create_token_pair(user)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA challenge expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using a refresh token"""
    try:
        tokens = refresh_access_token(refresh_request.refresh_token, db)
        return tokens
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/logout")
async def logout(
    refresh_token: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Logout by revoking tokens"""
    # Revoke access token (currently in use)
    access_token = None
    try:
        # Extract token from authorization header
        from fastapi import Request
        request = Request.scope.get("request", None)
        if request:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                access_token = auth_header.split(" ", 1)[1]
    except:
        pass
    
    # Revoke tokens
    if access_token:
        revoke_token(access_token)
    
    if refresh_token:
        revoke_token(refresh_token)
    
    return {"detail": "Successfully logged out"}

@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate a token and return user info (for service-to-service auth)"""
    # Get user roles
    roles = [role.name for role in current_user.roles]
    
    return {
        "valid": True,
        "username": current_user.username,
        "roles": roles
    }

@router.post("/request-reset")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset by email"""
    reset_token = generate_reset_token(reset_request.email, db)
    
    # Use background task to send email
    if reset_token:
        # For now, just print the token to the console
        # TODO: Implement proper email sending
        print(f"Password reset token for {reset_request.email}: {reset_token}")
        
        # background_tasks.add_task(send_reset_email, reset_request.email, reset_token)
    
    # Don't reveal if user exists for security
    return {"detail": "If an account exists with this email, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Reset password using valid token"""
    try:
        # Verify reset token
        email = verify_reset_token(reset_confirm.token)
        
        # Update password
        update_password(email, reset_confirm.new_password, db)
        
        return {"detail": "Password updated successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change password for current user"""
    # Verify current password
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"detail": "Password updated successfully"}


# API Key Management
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for exchanges"""
    # Generate random API key
    alphabet = string.ascii_letters + string.digits
    api_key_value = ''.join(secrets.choice(alphabet) for _ in range(40))
    
    # Create API key in database
    new_key = APIKey(
        key=api_key_value,
        description=api_key.description,
        exchange=api_key.exchange,
        is_test=api_key.is_test,
        user_id=current_user.id
    )
    
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    # Return the key
    return {
        "api_key": api_key_value,
        "created_at": datetime.utcnow(),
        "expires_at": None,
        "permissions": ["read", "trade"] if not api_key.is_test else ["read", "trade", "test"]
    }

@router.get("/api-keys", response_model=List[APIKeyOut])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List API keys for current user"""
    # Get API keys for current user
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    return keys

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    # Get API key
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Delete API key
    db.delete(key)
    db.commit()
    
    return {"detail": "API key deleted"}

# MFA Endpoints
@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Initiate MFA setup by generating TOTP secret and QR code"""
    # Generate new TOTP secret
    secret = generate_totp_secret()
    current_user.totp_secret = secret
    db.commit()

    # Generate provisioning URI
    uri = generate_totp_uri(secret, current_user.username)

    # Generate QR code image
    img = qrcode.make(uri)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return {
        "secret": secret,
        "qr_code": f"data:image/png;base64,{qr_code}",
        "manual_entry_code": uri.split("secret=")[1].split("&")[0]
    }

@router.post("/mfa/verify")
async def verify_mfa(
    verify_request: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify TOTP code to complete MFA setup"""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not set up"
        )

    # Verify code
    if not verify_totp_code(current_user.totp_secret, verify_request.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Mark MFA as enabled
    current_user.mfa_enabled = True
    current_user.mfa_setup = True
    db.commit()

    return {"detail": "MFA verification successful"}

@router.get("/mfa/backup-codes", response_model=MFABackupCodesResponse)
async def get_backup_codes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate new backup codes for MFA recovery"""
    codes = generate_backup_codes()
    current_user.backup_codes = codes
    db.commit()

    return {"codes": codes}

@router.get("/mfa/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get current MFA status"""
    return get_mfa_status(current_user)

@router.post("/mfa/enable")
async def enable_mfa(
    enable_request: MFAEnableRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enable or disable MFA"""
    if enable_request.enable:
        if not current_user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA not set up"
            )
        current_user.mfa_enabled = True
    else:
        current_user.mfa_enabled = False
    
    db.commit()
    return {"detail": "MFA status updated"}

# User Management (Admin only)
@router.post("/users", response_model=UserOut)
async def create_user(
    user_create: UserCreate,
    current_user: User = Depends(has_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Create a new user (admin only)"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_create.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_create.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create user
    user = User(
        username=user_create.username,
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=get_password_hash(user_create.password),
        disabled=user_create.disabled
    )
    
    # Add roles
    for role_name in user_create.roles:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            user.roles.append(role)
    
    # Save user
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Map user to UserOut model
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=[role.name for role in user.roles]
    )

@router.get("/users", response_model=List[UserOut])
async def list_users(
    current_user: User = Depends(has_role(["admin"])),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).all()
    
    # Map users to UserOut models
    return [
        UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            roles=[role.name for role in user.roles]
        )
        for user in users
    ]

@router.get("/users/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        disabled=current_user.disabled,
        roles=[role.name for role in current_user.roles]
    )

@router.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: User = Depends(has_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=[role.name for role in user.roles]
    )

@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(has_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user fields if provided
    if user_update.email is not None:
        user.email = user_update.email
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
    
    if user_update.disabled is not None:
        user.disabled = user_update.disabled
    
    if user_update.roles is not None:
        # Clear existing roles
        user.roles = []
        
        # Add new roles
        for role_name in user_update.roles:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                user.roles.append(role)
    
    # Save user
    db.commit()
    db.refresh(user)
    
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=[role.name for role in user.roles]
    )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(has_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting self
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return {"detail": "User deleted"}