from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from typing import List, Optional, Callable, Dict, Any
import os

from auth.auth_service_client import create_auth_client

class AuthServiceIntegration:
    """Integration helper for FastAPI services"""
    
    def __init__(self, app: FastAPI, auth_service_url: Optional[str] = None):
        """
        Initialize auth service integration
        
        Args:
            app: FastAPI application
            auth_service_url: URL of the auth service (default: from environment)
        """
        # Get auth service URL from environment if not provided
        if not auth_service_url:
            auth_service_url = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
        
        # Create auth client
        self.auth_client = create_auth_client(auth_service_url)
        
        # Add auth middleware
        @app.middleware("http")
        async def auth_middleware(request: Request, call_next: Callable):
            """Middleware to handle authentication"""
            # Skip auth for OPTIONS requests (CORS)
            if request.method == "OPTIONS":
                return await call_next(request)
            
            # Get authorization header
            auth_header = request.headers.get("Authorization")
            
            # Skip auth for public endpoints
            path = request.url.path
            
            # Define public paths (customize as needed)
            public_paths = [
                "/docs",
                "/redoc",
                "/openapi.json",
                "/health",
                "/metrics",
            ]
            
            # Skip auth for public paths
            if any(path.startswith(p) for p in public_paths) or not auth_header:
                return await call_next(request)
            
            # Extract token
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    # Validate token
                    validation_result = await self.auth_client.validate_token(token)
                    
                    # Add user info to request state
                    if validation_result.get("valid", False):
                        request.state.user = {
                            "username": validation_result.get("username"),
                            "roles": validation_result.get("roles", [])
                        }
                except HTTPException as e:
                    # Return auth error
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"detail": e.detail}
                    )
            
            # Continue to next middleware or endpoint
            response = await call_next(request)
            return response
        
        # Add exception handler for auth errors
        @app.exception_handler(HTTPException)
        async def auth_exception_handler(request: Request, exc: HTTPException):
            """Handle auth exceptions"""
            if exc.status_code == 401:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": exc.detail},
                    headers={"WWW-Authenticate": "Bearer"}
                )
            elif exc.status_code == 403:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": exc.detail}
                )
            else:
                # Let FastAPI handle other exceptions
                raise exc
        
        # Store app reference
        self.app = app
        
        # Create OAuth2 scheme for dependency injection
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{auth_service_url}/auth/login")
    
    async def get_current_user(self, request: Request) -> Dict[str, Any]:
        """
        Get current user from request state
        
        Args:
            request: FastAPI request
            
        Returns:
            Dict with username and roles
            
        Raises:
            HTTPException if not authenticated
        """
        if not hasattr(request.state, "user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return request.state.user
    
    def has_role(self, roles: List[str]):
        """
        Dependency to check if user has specified roles
        
        Args:
            roles: List of required roles (any match is sufficient)
            
        Returns:
            Dependency function that returns user dict if authorized
            
        Raises:
            HTTPException if not authorized
        """
        async def _has_role(request: Request):
            # Get current user
            user = await self.get_current_user(request)
            
            # Check roles
            user_roles = user.get("roles", [])
            if not any(role in user_roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                )
            
            return user
        
        return _has_role
    
    def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract token from request
        
        Args:
            request: FastAPI request
            
        Returns:
            JWT token or None
        """
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ")[1]
        return None
    
    def login_required(self):
        """
        Dependency for login requirement
        
        Returns:
            Dependency function that returns user dict if authenticated
            
        Example:
            @app.get("/protected")
            async def protected(user = Depends(auth.login_required())):
                return {"message": f"Hello {user['username']}"}
        """
        async def _login_required(request: Request):
            return await self.get_current_user(request)
        
        return _login_required


def setup_auth_integration(app: FastAPI, auth_service_url: Optional[str] = None) -> AuthServiceIntegration:
    """
    Set up auth service integration with a FastAPI app
    
    Args:
        app: FastAPI application
        auth_service_url: URL of the auth service (default: from environment)
        
    Returns:
        AuthServiceIntegration instance
    """
    return AuthServiceIntegration(app, auth_service_url)