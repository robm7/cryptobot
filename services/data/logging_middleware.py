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

        db_session: Session = None
        audit_service_instance: AuditService
        try:
            if self.db_session_factory:
                db_session = self.db_session_factory()
                audit_service_instance = AuditService(db_session=db_session)
            else:
                # Fallback if no factory is provided, audit to log only
                audit_service_instance = AuditService(db_session=None)
            request.state.audit_service = audit_service_instance
            
            # Log request details (now uses request.state.audit_service)
            self.log_request(request, request_id)
            
            response = await call_next(request)
            
        except Exception as e:
            # Log errors (now uses request.state.audit_service if available, or a new instance)
            # Ensure audit_service is available on request.state even if initial setup failed partially
            if not hasattr(request.state, 'audit_service'):
                 request.state.audit_service = AuditService(db_session=None) # Fallback for error logging
            self.log_error(request, request_id, e)
            raise
        finally:
            if db_session: # Close session if it was opened by the factory
                try:
                    db_session.close()
                except Exception as e:
                    self.logger.error(f"Error closing DB session in audit middleware: {e}")

        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        self.log_response(request, request_id, response, process_time)
        
        return response

    def log_request(self, request: Request, request_id: str):
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
        if hasattr(request.state, 'audit_service'):
            request.state.audit_service.log_event(
                event_type="api_request_started", # Changed event type
                action_details=log_data,
                user_id=request.state.user.get("username") if hasattr(request.state, "user") and hasattr(request.state.user, "get") else None,
                ip_address=request.client.host if request.client else None,
                status="started"
            )
        else:
            # Fallback if audit_service was not set on request.state (should not happen with current dispatch logic)
            self.logger.warning("AuditService not found on request.state during log_request")


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

    def log_error(self, request: Request, request_id: str, error: Exception):
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
        if hasattr(request.state, 'audit_service'):
            request.state.audit_service.log_event(
                event_type="api_error",
                action_details=log_data,
                user_id=request.state.user.get("username") if hasattr(request.state, "user") and hasattr(request.state.user, "get") else None,
                ip_address=request.client.host if request.client else None,
                status="error"
            )
        else:
            # Fallback if audit_service was not set on request.state
            self.logger.warning("AuditService not found on request.state during log_error")