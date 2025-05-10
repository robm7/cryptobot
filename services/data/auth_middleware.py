from functools import wraps
from flask import request, jsonify
import jwt
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RBACMiddleware:
    def __init__(self, app=None, secret_key=None, redis_client=None):
        self.app = app
        self.secret_key = secret_key
        self.redis_client = redis_client
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.secret_key = app.config.get('SECRET_KEY')
        self.redis_client = app.config.get('REDIS_CLIENT')

    @staticmethod
    def required_roles(*roles):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Get token from header
                token = request.headers.get('Authorization')
                if not token:
                    logger.warning("Unauthorized: No token provided")
                    return jsonify({"error": "Unauthorized"}), 401

                try:
                    # Verify and decode token
                    token = token.split(' ')[1]  # Remove Bearer prefix
                    payload = jwt.decode(token, RBACMiddleware.secret_key, algorithms=['HS256'])
                    
                    # Check if user has required role
                    user_role = payload.get('role')
                    if user_role not in roles:
                        logger.warning(f"Forbidden: User role {user_role} not in required roles {roles}")
                        return jsonify({"error": "Forbidden"}), 403

                    # Add user info to request context
                    request.user = payload
                    return f(*args, **kwargs)

                except jwt.ExpiredSignatureError:
                    logger.warning("Unauthorized: Token expired")
                    return jsonify({"error": "Token expired"}), 401
                except jwt.InvalidTokenError:
                    logger.warning("Unauthorized: Invalid token")
                    return jsonify({"error": "Invalid token"}), 401
                except Exception as e:
                    logger.error(f"Authorization error: {str(e)}")
                    return jsonify({"error": "Authorization failed"}), 500

            return wrapped
        return decorator

    @staticmethod
    def required_permissions(*permissions):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Get token from header
                token = request.headers.get('Authorization')
                if not token:
                    return jsonify({"error": "Unauthorized"}), 401

                try:
                    # Verify and decode token
                    token = token.split(' ')[1]
                    payload = jwt.decode(token, RBACMiddleware.secret_key, algorithms=['HS256'])
                    
                    # Check if user has required permissions
                    user_permissions = payload.get('permissions', [])
                    if not all(perm in user_permissions for perm in permissions):
                        logger.warning(f"Forbidden: Missing required permissions {permissions}")
                        return jsonify({"error": "Forbidden"}), 403

                    # Add user info to request context
                    request.user = payload
                    return f(*args, **kwargs)

                except Exception as e:
                    logger.error(f"Permission check failed: {str(e)}")
                    return jsonify({"error": "Authorization failed"}), 500

            return wrapped
        return decorator

    def log_activity(self, action):
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                try:
                    # Get user info if available
                    user_id = None
                    if hasattr(request, 'user'):
                        user_id = request.user.get('sub')
                    
                    # Call the original function
                    response = f(*args, **kwargs)
                    
                    # Log the activity
                    if user_id:
                        log_entry = {
                            'timestamp': datetime.utcnow().isoformat(),
                            'user_id': user_id,
                            'action': action,
                            'endpoint': request.path,
                            'method': request.method,
                            'status_code': response.status_code
                        }
                        self.redis_client.lpush('activity_logs', str(log_entry))
                    
                    return response

                except Exception as e:
                    logger.error(f"Activity logging failed: {str(e)}")
                    return f(*args, **kwargs)

            return wrapped
        return decorator