from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any

class ExchangeError(Exception):
    """Base exception for exchange-related errors"""
    def __init__(self, message: str, exchange: str = None, retryable: bool = False):
        self.message = message
        self.exchange = exchange
        self.retryable = retryable
        super().__init__(message)

def format_error_response(
    error_type: str,
    message: str,
    exchange: str = None,
    retryable: bool = False
) -> Dict[str, Any]:
    """Format consistent error responses"""
    return {
        "error": error_type,
        "message": message,
        "exchange": exchange,
        "retryable": retryable
    }

async def handle_exchange_errors(request: Request, exc: Exception):
    """Global exception handler for exchange operations"""
    if isinstance(exc, ExchangeError):
        return JSONResponse(
            status_code=400,
            content=format_error_response(
                error_type="EXCHANGE_ERROR",
                message=exc.message,
                exchange=exc.exchange,
                retryable=exc.retryable
            )
        )
    elif isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(
                error_type="HTTP_ERROR",
                message=str(exc.detail)
            )
        )
    else:
        return JSONResponse(
            status_code=500,
            content=format_error_response(
                error_type="INTERNAL_ERROR",
                message="Internal server error"
            )
        )

# Common exchange errors
class RateLimitError(ExchangeError):
    def __init__(self, exchange: str):
        super().__init__(
            message="Rate limit exceeded",
            exchange=exchange,
            retryable=True
        )

class InvalidOrderError(ExchangeError):
    def __init__(self, exchange: str, message: str):
        super().__init__(
            message=f"Invalid order: {message}",
            exchange=exchange,
            retryable=False
        )

class ConnectionError(ExchangeError):
    def __init__(self, exchange: str):
        super().__init__(
            message="Connection failed",
            exchange=exchange,
            retryable=True
        )