from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from typing import Callable, Awaitable
from datetime import datetime, timedelta
import time

from auth.redis_service import RateLimiter
from config import settings

class RateLimitRoute(APIRoute):
    """Custom route class that applies rate limiting"""
    
    def get_route_handler(self) -> Callable[[Request], Awaitable[JSONResponse]]:
        original_route_handler = super().get_route_handler()
        
        async def custom_route_handler(request: Request) -> JSONResponse:
            # Skip rate limiting for certain paths
            if request.url.path in settings.RATE_LIMIT_EXEMPT_PATHS:
                return await original_route_handler(request)
                
            # Apply rate limiting
            await RateLimiter.check_rate_limit(request)
            return await original_route_handler(request)
            
        return custom_route_handler

async def rate_limit_middleware(request: Request, call_next):
    """Middleware version of rate limiter"""
    try:
        # Skip rate limiting for certain paths
        if request.url.path in settings.RATE_LIMIT_EXEMPT_PATHS:
            return await call_next(request)
            
        # Apply rate limiting
        await RateLimiter.check_rate_limit(request)
        response = await call_next(request)
        
        # Add rate limit headers to response
        if hasattr(request.state, "rate_limit"):
            response.headers.update({
                "X-RateLimit-Limit": str(request.state.rate_limit["limit"]),
                "X-RateLimit-Remaining": str(request.state.rate_limit["remaining"]),
                "X-RateLimit-Reset": str(request.state.rate_limit["reset"])
            })
            
        return response
        
    except HTTPException as e:
        if e.status_code == 429:  # Rate limit exceeded
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(e.headers.get("Retry-After", 60)),
                    "X-RateLimit-Limit": str(e.headers.get("X-RateLimit-Limit", 60)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(e.headers.get("X-RateLimit-Reset", 60))
                }
            )
        raise