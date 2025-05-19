import logging
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, Callable, Awaitable
from contextvars import ContextVar
import json
from sqlalchemy.orm import Session # Added
from .audit_service import AuditService

request_id_var: ContextVar[str] = ContextVar("request_id")

class RequestLoggingMiddleware(BaseHTTPMiddleware): # Inherit from BaseHTTPMiddleware
    """Middleware for enhanced request logging"""

    def __init__(self, app: Any, logger_name: str = "api", db_session_factory: Callable[[], Session] = None): # Modified
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.db_session_factory = db_session_factory # Added

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        start_time = time.time()
        request.state.start_time = start_time # Store start time for processing time calculation

        response: Response
        # audit_service_instance will be set within the try or if/else block
        # request.state.audit_service will be the primary way to access it

        try:
            if self.db_session_factory:
                async with self.db_session_factory() as db_session: # Use async with for session management
                    # Create and assign AuditService instance within the session's context
                    audit_service_instance = AuditService(db_session=db_session)
                    request.state.audit_service = audit_service_instance
                    
                    await self.log_request(request, request_id) # Now async
                    response = await call_next(request)
            else:
                # Fallback if no factory is provided, audit to log only
                audit_service_instance = AuditService(db_session=None)
                request.state.audit_service = audit_service_instance

                await self.log_request(request, request_id) # Now async
                response = await call_next(request)
            
        except Exception as e:
            # Ensure audit_service is available for error logging, potentially without a session
            if not hasattr(request.state, 'audit_service') or not request.state.audit_service:
                # This case might happen if db_session_factory() itself fails before audit_service_instance is set,
                # or if we are in the 'else' block and something went wrong before audit_service_instance was set.
                self.logger.warning("AuditService not available on request.state during exception handling, creating fallback.")
                request.state.audit_service = AuditService(db_session=None) # Fallback for error logging
            
            await self.log_error(request, request_id, e) # Now async
            raise
        # 'finally' block for db_session.close() is no longer needed due to 'async with'

        # If an exception was raised and not caught locally (i.e. re-raised),
        # 'response' might not be set. However, the original code structure implies
        # that if we reach here, 'response' from call_next is available.
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        # log_response does not use audit_service and remains synchronous
        self.log_response(request, request_id, response, process_time)
        
        return response

    async def log_request(self, request: Request, request_id: str): # Changed to async
        """Log incoming request details"""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "timestamp": time.time(),
            "type": "request"
        }
        self.logger.info(json.dumps(log_data))
        # Use audit_service from request.state
        if hasattr(request.state, 'audit_service') and request.state.audit_service: # Added check for truthiness
            await request.state.audit_service.log_event( # Added await
                event_type="api_request_started",
                action_details=log_data,
                user_id=request.state.user.get("username") if hasattr(request.state, "user") and hasattr(request.state.user, "get") else None,
                ip_address=request.client.host if request.client else None,
                status="started"
            )
        else:
            self.logger.warning("AuditService not found or not initialized on request.state during log_request")


    def log_response(self, request: Request, request_id: str, response, process_time: float):
        """Log response details"""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": process_time,
            "timestamp": time.time(),
            "type": "response"
        }
        self.logger.info(json.dumps(log_data))

    async def log_error(self, request: Request, request_id: str, error: Exception): # Changed to async
        """Log error details"""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time(),
            "type": "error"
        }
        self.logger.error(json.dumps(log_data))
        # Use audit_service from request.state
        if hasattr(request.state, 'audit_service') and request.state.audit_service: # Added check for truthiness
            await request.state.audit_service.log_event( # Added await
                event_type="api_error",
                action_details=log_data,
                user_id=request.state.user.get("username") if hasattr(request.state, "user") and hasattr(request.state.user, "get") else None,
                ip_address=request.client.host if request.client else None,
                status="error"
            )
        else:
            self.logger.warning("AuditService not found or not initialized on request.state during log_error")