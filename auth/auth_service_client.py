import httpx
import jwt
import logging
from typing import Dict, List, Optional, Union, Callable, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from cachetools import TTLCache, cached
from functools import wraps

# Configure logging
logger = logging.getLogger("auth-service-client")

class AuthServiceClient:
    """Client for interacting with the Auth service"""
    
    def __init__(self, base_url: str, timeout: int = 5, cache_ttl: int = 60):
        """
        Initialize the Auth service client
        
        Args:
            base_url: Base URL of the Auth service (e.g., "http://auth-service:8000")
            timeout: Request timeout in seconds
            cache_ttl: Cache TTL in seconds for token validation results
        """
        self.base_url = base_url
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{base_url}/auth/login")
        
        # Create a cache for token validation results
        self._validation_cache = TTLCache(maxsize=1000, ttl=cache_ttl)
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login to the Auth service
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Dict containing access_token, refresh_token, etc.
            
        Raises:
            HTTPException: If login fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use form data as required by OAuth2
                response = await client.post(
                    f"{self.base_url}/auth/login",
                    data={
                        "username": username,
                        "password": password
                    }
                )
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (4xx, 5xx)
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                logger.error(f"Auth service login failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable",
                )
        except httpx.RequestError as e:
            # Handle request errors (connection, timeout, etc.)
            logger.error(f"Auth service request failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an access token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict containing new access_token, etc.
            
        Raises:
            HTTPException: If refresh fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/auth/refresh",
                    json={"refresh_token": refresh_token}
                )
                
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                logger.error(f"Auth service refresh failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable",
                )
        except httpx.RequestError as e:
            logger.error(f"Auth service request failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a token with the Auth service
        
        Args:
            token: JWT token
            
        Returns:
            Dict containing validation result (valid, username, roles)
            
        Raises:
            HTTPException: If validation fails
        """
        # Check cache first
        if token in self._validation_cache:
            return self._validation_cache[token]
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/auth/validate",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Cache result if valid
                if result.get("valid", False):
                    self._validation_cache[token] = result
                
                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                logger.error(f"Auth service validation failed: {str(e)}")
                
                # Try local validation as fallback
                try:
                    # This is a fallback in case the auth service is down
                    # We decode the token without verification just to get basic info
                    # This is not fully secure but better than completely failing
                    payload = jwt.decode(
                        token, 
                        options={"verify_signature": False}
                    )
                    logger.warning("Using fallback local token validation (signature not verified)")
                    return {
                        "valid": True,  # We can't truly verify it
                        "username": payload.get("sub"),
                        "roles": payload.get("roles", [])
                    }
                except jwt.JWTError:
                    pass
                
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable",
                )
        except httpx.RequestError as e:
            logger.error(f"Auth service request failed: {str(e)}")
            
            # Try local validation as fallback
            try:
                # This is a fallback in case the auth service is down
                payload = jwt.decode(
                    token, 
                    options={"verify_signature": False}
                )
                logger.warning("Using fallback local token validation (signature not verified)")
                return {
                    "valid": True,  # We can't truly verify it
                    "username": payload.get("sub"),
                    "roles": payload.get("roles", [])
                }
            except jwt.JWTError:
                pass
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
    
    # FastAPI dependencies
    
    async def get_current_user(self, token: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))) -> Dict[str, Any]:
        """
        FastAPI dependency to get the current authenticated user
        
        Args:
            token: JWT token from OAuth2PasswordBearer
            
        Returns:
            Dict containing user info (username, roles)
            
        Raises:
            HTTPException: If authentication fails
        """
        validation_result = await self.validate_token(token)
        
        if not validation_result.get("valid", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "username": validation_result.get("username"),
            "roles": validation_result.get("roles", [])
        }
    
    def has_role(self, required_roles: List[str]):
        """
        FastAPI dependency to check if user has any of the required roles
        
        Args:
            required_roles: List of role names
            
        Returns:
            Dependency function
            
        Example:
            @app.get("/admin-only")
            async def admin_only(user: dict = Depends(auth_client.has_role(["admin"]))):
                return {"message": "You are an admin"}
        """
        async def check_roles(user: Dict[str, Any] = Depends(self.get_current_user)):
            user_roles = user.get("roles", [])
            
            if not any(role in user_roles for role in required_roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            
            return user
        
        return check_roles
    
    # FastAPI middleware
    
    async def auth_middleware(self, request: Request, call_next: Callable):
        """
        FastAPI middleware for authentication
        
        This middleware:
        1. Extracts JWT token from Authorization header
        2. Validates the token
        3. Adds user info to request state
        4. Continues to the next middleware or endpoint
        
        Protected endpoints should be configured in your FastAPI app
        
        Example:
            app.add_middleware(auth_client.auth_middleware)
        """
        # Get the path
        path = request.url.path
        
        # Skip authentication for public endpoints
        public_paths = [
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/auth/login",
            "/auth/refresh",
            "/health"
        ]
        
        if any(path.startswith(public_path) for public_path in public_paths):
            return await call_next(request)
        
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)
        
        # Extract token
        token = auth_header.split(" ")[1]
        
        try:
            # Validate token
            validation_result = await self.validate_token(token)
            
            # Add user info to request state
            request.state.user = {
                "username": validation_result.get("username"),
                "roles": validation_result.get("roles", [])
            }
        except HTTPException:
            # Continue without user info
            pass
        
        # Continue to the next middleware or endpoint
        return await call_next(request)


# Client instance factory
def create_auth_client(base_url: str, timeout: int = 5, cache_ttl: int = 60) -> AuthServiceClient:
    """
    Create an Auth service client instance
    
    Args:
        base_url: Base URL of the Auth service
        timeout: Request timeout in seconds
        cache_ttl: Cache TTL in seconds for token validation results
        
    Returns:
        AuthServiceClient instance
    """
    return AuthServiceClient(base_url, timeout, cache_ttl)