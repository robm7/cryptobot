import logging
import time
import uuid
from fastapi import Request
from typing import Dict, Any
from contextvars import ContextVar
import json
from .audit_service import AuditService

request_id_var: ContextVar[str] = ContextVar("request_id")

class RequestLoggingMiddleware:
    """Middleware for enhanced request logging"""

    def __init__(self, logger_name: str = "api"):
        self.logger = logging.getLogger(logger_name)
        self.audit_service = AuditService()

    async def __call__(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Log request start
        start_time = time.time()
        request.state.start_time = start_time
        
        # Log request details
        self.log_request(request, request_id)
        
        try:
            response = await call_next(request)
        except Exception as e:
            # Log errors
            self.log_error(request, request_id, e)
            raise
        
        # Calculate response time
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        # Log response
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
        self.audit_service.log_event(
            event_type="api_response",
            action_details=log_data,
            user_id=request.user.state.get("user_id") if hasattr(request.state, "user_id") else None,
            ip_address=request.client.host if request.client else None,
            status="success" if response.status_code < 400 else "failure"
        )
        self.audit_service.log_event(
            event_type="api_request",
            action_details=log_data,
            user_id=request.user.state.get("user_id") if hasattr(request.state, "user_id") else None,
            ip_address=request.client.host if request.client else None,
            status="started"
        )

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
        self.audit_service.log_event(
            event_type="api_error",
            action_details=log_data,
            user_id=request.user.state.get("user_id") if hasattr(request.state, "user_id") else None,
            ip_address=request.client.host if request.client else None,
            status="error"
        )