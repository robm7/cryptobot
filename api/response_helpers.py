"""Standardized response helpers for API endpoints.

Provides consistent success/error response formats and error handling decorators.
"""

from typing import Any, Dict, Union, Callable, TypeVar, cast
from flask import jsonify, Response
from functools import wraps
import json

T = TypeVar('T', bound=Callable[..., Any])

def success_response(
    data: Any = None,
    count: int = None,
    status_code: int = 200,
    **kwargs: Any
) -> tuple[Response, int]:
    """Return a standardized success response.
    
    Args:
        data: The primary response data
        count: Optional count of items (for pagination)
        status_code: HTTP status code
        **kwargs: Additional response fields
        
    Returns:
        Tuple of (json response, status code)
    """
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if count is not None:
        response['count'] = count
    response.update(kwargs)
    return jsonify(response), status_code


def error_response(
    error_data: Union[str, Dict[str, Any]],
    code: int = 400,
    **kwargs: Any
) -> tuple[Response, int]:
    """Return a standardized error response.
    
    Args:
        error_data: Either error message string or error details dict
        code: HTTP status code
        **kwargs: Additional response fields
        
    Returns:
        Tuple of (json response, status code)
    """
    if isinstance(error_data, str):
        error_data = {'message': error_data}
    elif not isinstance(error_data, dict):
        error_data = {'message': str(error_data)}
    
    # Ensure required error fields
    if 'message' not in error_data:
        error_data['message'] = 'Error occurred'
    
    response = {
        'success': False,
        'error': {
            **error_data,
            'code': code
        }
    }
    response.update(kwargs)
    return jsonify(response), code


def handle_errors(f: T) -> T:
    """Decorator to standardize error handling for route handlers.
    
    Catches exceptions and returns formatted error responses:
    - ValueError -> 400 Bad Request
    - Other exceptions -> 500 Internal Server Error
    
    Args:
        f: The route handler function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return error_response({'message': str(e)}, 400)
        except Exception as e:
            return error_response({'message': str(e)}, 500)
    return cast(T, wrapper)