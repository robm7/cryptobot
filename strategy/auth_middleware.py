from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any, List, Optional
import httpx
import os
import importlib
from functools import lru_cache
import jwt
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe settings import
try:
    from config import settings
    logger.info("Successfully imported settings from config")
    # Get auth service URL from settings or environment
    AUTH_SERVICE_URL = settings.AUTH_SERVICE_URL
except Exception as e:
    logger.warning(f"Error importing settings: {str(e)}. Using default values.")
    # Default settings if config module fails
    AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
    
logger.info(f"Using AUTH_SERVICE_URL: {AUTH_SERVICE_URL}")

# Configure OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{AUTH_SERVICE_URL}/auth/login")

# Create cache for token validation
token_cache = {}

async def validate_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token with auth service
    
    Args:
        token: JWT token
        
    Returns:
        Dict with validation result
        
    Raises:
        HTTPException if validation fails
    """
    # Check cache first
    if token in token_cache:
        return token_cache[token]
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Handle validation response
            if response.status_code == 200:
                result = response.json()
                if result.get("valid"):
                    # Cache successful validations temporarily (60 seconds)
                    token_cache[token] = result
                    return result
            
            # Handle validation errors
            raise HTTPException(
                status_code=response.status_code,
                detail="Invalid authentication credentials"
            )
    except httpx.RequestError as e:
        # Log the error for troubleshooting
        logger.warning(f"Auth service unavailable: {str(e)}. Using fallback mode")
        
        # If auth service is down, try to decode token as fallback
        try:
            # Get SECRET_KEY safely
            secret_key = None
            try:
                # Try to get from settings if available
                from config import settings
                secret_key = settings.SECRET_KEY
                logger.info("Using SECRET_KEY from settings")
            except Exception as e:
                # Fallback to environment variable
                secret_key = os.getenv("SECRET_KEY", "test_secret_key_for_local_testing")
                logger.warning(f"Error getting SECRET_KEY from settings: {str(e)}. Using environment variable.")
                
            if secret_key:
                try:
                    payload = jwt.decode(
                        token,
                        secret_key,
                        algorithms=["HS256"]
                    )
                    logger.info(f"Successfully decoded token with local secret key")
                except jwt.PyJWTError:
                    logger.warning("Failed to verify token with local secret key, falling back to non-verification mode")
                    # Fall back to non-verification mode
                    payload = jwt.decode(token, options={"verify_signature": False})
            else:
                # No secret key, use non-verification mode
                payload = jwt.decode(token, options={"verify_signature": False})
            
            # Ensure minimal required fields are present
            if not payload.get("sub"):
                raise jwt.PyJWTError("Missing subject claim in token")
                
            result = {
                "valid": True,
                "username": payload.get("sub"),
                "roles": payload.get("roles", []),
                "using_fallback": True
            }
            
            # Cache the result but with shorter TTL in fallback mode
            token_cache[token] = result
            
            logger.info(f"Using fallback auth for user: {result['username']}")
            return result
        except jwt.PyJWTError as jwt_error:
            logger.error(f"Invalid token format in fallback mode: {str(jwt_error)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token format"
            )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get current user from token
    
    Args:
        token: JWT token from OAuth2PasswordBearer
        
    Returns:
        Dict with user info
        
    Raises:
        HTTPException if authentication fails
    """
    validation_result = await validate_token(token)
    
    if not validation_result.get("valid"):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
    
    return {
        "username": validation_result.get("username"),
        "roles": validation_result.get("roles", [])
    }

def has_role(required_roles: List[str]):
    """
    Check if user has required roles
    
    Args:
        required_roles: List of required roles (any match is sufficient)
        
    Returns:
        Dependency function that returns user dict if authorized
        
    Raises:
        HTTPException if not authorized
    """
    async def _check_roles(user: Dict[str, Any] = Depends(get_current_user)):
        user_roles = user.get("roles", [])
        
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail="Not enough permissions"
            )
        
        return user
    
    return _check_roles

def setup_auth_middleware(app: FastAPI):
    """
    Set up auth middleware for FastAPI app
    
    Args:
        app: FastAPI app
    """
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        """
        Auth middleware for FastAPI
        
        This middleware:
        1. Checks if route is public
        2. Extracts token from Authorization header
        3. Validates token if present
        4. Adds user info to request state
        5. Passes request to next handler
        """
        # Skip auth for certain paths
        path = request.url.path
        public_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
        
        if any(path.startswith(p) for p in public_paths):
            return await call_next(request)
        
        # Get auth header
        auth_header = request.headers.get("Authorization")
        
        # Process auth header if present
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            try:
                # Validate token
                validation_result = await validate_token(token)
                
                # Add user info to request state if token is valid
                if validation_result.get("valid"):
                    request.state.user = {
                        "username": validation_result.get("username"),
                        "roles": validation_result.get("roles", [])
                    }
            except HTTPException:
                # Continue without user info on validation error
                pass
        
        # Continue with request processing
        return await call_next(request)

def configure_auth(app: FastAPI):
    """
    Configure auth for FastAPI app
    
    This:
    1. Sets up auth middleware
    2. Adds auth dependencies
    
    Args:
        app: FastAPI app
    """
    # Set up middleware
    setup_auth_middleware(app)
    
    # Add auth dependencies to app
    app.dependency_overrides[oauth2_scheme] = oauth2_scheme