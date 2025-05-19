import redis
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Any
from .auth_service import serve # Corrected import
import smtplib # Added for email notifications
from email.mime.text import MIMEText # Added for email notifications
import os # For environment variables

class KeyManager:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis: redis.Redis = redis_client
        self.current_version: str = "v1"
        self.notification_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
    def generate_key(self, user_id: str, permissions: List[str], expires_in: int = 30) -> str:
        """Generate new API key with versioning and expiration"""
        key_data = {
            'value': f"sk_{user_id}_{int(time.time())}",
            'version': self.current_version,
            'permissions': permissions,
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=expires_in)).isoformat(),
            'is_active': True,
            'rotation_status': 'active',
            'audit_log': [{
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'created',
                'details': f'Generated new key version {self.current_version}'
            }]
        }
        self.redis.set(f"keys:{key_data['value']}", json.dumps(key_data))
        self.redis.sadd(f"user:{user_id}:keys", key_data['value'])
        self._notify('key_created', {
            'user_id': user_id,
            'key': key_data['value'],
            'expires_at': key_data['expires_at']
        })
        return key_data['value']
        
    def rotate_key(self, old_key: str, grace_period_hours: int = 24) -> str:
        """Rotate existing key to new version with grace period"""
        key_data = json.loads(self.redis.get(f"keys:{old_key}"))
        if not key_data:
            raise ValueError("Key not found")
            
        user_id = key_data['value'].split('_')[1]
        new_key = self.generate_key(
            user_id=user_id,
            permissions=key_data['permissions'],
            expires_in=30
        )
        
        # Update old key with rotation info and grace period
        key_data['rotated_to'] = new_key
        key_data['rotation_status'] = 'grace_period'
        key_data['grace_period_end'] = (datetime.utcnow() +
            timedelta(hours=grace_period_hours)).isoformat()
        key_data['audit_log'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'rotated',
            'details': f'Rotated to {new_key} with {grace_period_hours}h grace period'
        })
        self.redis.set(f"keys:{old_key}", json.dumps(key_data))
        
        self._notify('key_rotated', {
            'user_id': user_id,
            'old_key': old_key,
            'new_key': new_key,
            'grace_period_end': key_data['grace_period_end']
        })
        
        return new_key

    def _notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger notification callbacks"""
        for callback in self.notification_callbacks:
            try:
                callback({
                    'event_type': event_type,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data
                })
            except Exception as e:
                print(f"Notification callback failed: {str(e)}")
    
    def revoke_key(self, key_value: str, reason: str = "Revoked by user action") -> bool:
        """Revoke an API key."""
        key_data_str = self.redis.get(f"keys:{key_value}")
        if not key_data_str:
            logger.warning(f"Attempted to revoke non-existent key: {key_value}")
            return False # Or raise error

        key_data = json.loads(key_data_str)
        if not key_data.get('is_active', False):
            logger.info(f"Key already inactive, no action taken for revoke: {key_value}")
            return True # Already inactive

        key_data['is_active'] = False
        key_data['rotation_status'] = 'revoked'
        key_data.setdefault('audit_log', []).append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'revoked',
            'details': reason
        })
        self.redis.set(f"keys:{key_value}", json.dumps(key_data))
        
        user_id_parts = key_value.split('_')
        user_id = user_id_parts[1] if len(user_id_parts) > 1 else None

        self._notify('key_revoked', {
            'key': key_value,
            'user_id': user_id,
            'reason': reason
        })
        logger.info(f"Revoked key: {key_value} for user: {user_id} due to: {reason}")
        return True

    def add_notification_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register notification callback"""
        self.notification_callbacks.append(callback)

def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )

def rotate_expiring_keys(key_manager: KeyManager) -> None:
    """Rotate keys expiring within 7 days"""
    keys = key_manager.redis.keys("keys:*")
    for key in keys:
        key_data = json.loads(key_manager.redis.get(key))
        if key_data['is_active']:
            expires_at = datetime.fromisoformat(key_data['expires_at'])
            remaining = expires_at - datetime.utcnow()
            
            if remaining < timedelta(days=7):
                # Rotate expiring keys
                key_manager.rotate_key(key_data['value'])
            elif remaining < timedelta(days=14):
                # Notify about upcoming expiration
                key_manager._notify('key_expiring', {
                    'key': key_data['value'],
                    'expires_at': key_data['expires_at'],
                    'days_remaining': remaining.days
                })

from flask import Flask, jsonify, request, send_from_directory, redirect, render_template, make_response
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics # Added

def create_app(redis_client: redis.Redis, key_manager: KeyManager) -> Flask:
    app = Flask(__name__, static_folder='static')
    
    # Instrument with Prometheus
    # This will expose /metrics endpoint by default
    # And automatically track request latencies and counts for Flask routes
    metrics = PrometheusMetrics(app)
    
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {"origins": "*"},
        r"/health": {"origins": "*"}
    })
    
    # Configure rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # Favicon route
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            app.static_folder,
            'favicon.ico',
            mimetype='image/vnd.microsoft.icon'
        )
    
    # Root endpoint with content negotiation
    @app.route('/')
    def root():
        if 'application/json' in request.headers.get('Accept', ''):
            return jsonify({
                'service': 'CryptoBot Auth Service',
                'version': '1.0.0',
                'status': 'operational',
                'endpoints': {
                    'health': '/health',
                    'documentation': '/docs',
                    'api': '/api/keys'
                }
            })
        return render_template('index.html')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        try:
            # Basic health check - verify Redis connection
            redis_client.ping()
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'dependencies': {
                    'redis': 'connected'
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    # Documentation redirect
    @app.route('/docs')
    def docs():
        return redirect('https://docs.cryptobot.example.com/auth-service')
    
    # Custom 404 handler
    @app.errorhandler(404)
    def not_found(error):
        # Always return JSON for 404 to avoid template issues for API calls
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested URL was not found on the server.', # Generic message
            'status_code': 404
        }), 404
    
    @app.route('/api/keys/current', methods=['GET'])
    def get_current_key():
        """Get current active key for user"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise Unauthorized('User ID required')
            
        keys = redis_client.smembers(f"user:{user_id}:keys")
        for key in keys:
            key_data = json.loads(redis_client.get(f"keys:{key}"))
            if key_data['is_active']:
                return jsonify(key_data)
        return jsonify({'error': 'No active key found'}), 404
    
    @app.route('/api/keys/rotate', methods=['POST'])
    def rotate_key():
        """Rotate current key to new version"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise Unauthorized('User ID required')
            
        keys = redis_client.smembers(f"user:{user_id}:keys")
        for key in keys:
            key_data = json.loads(redis_client.get(f"keys:{key}"))
            if key_data['is_active']:
                new_key = key_manager.rotate_key(key)
                return jsonify({'new_key': new_key})
        return jsonify({'error': 'No active key to rotate'}), 400
    
    @app.route('/api/keys/revoke-current', methods=['POST'])
    def revoke_current_key():
        """Revoke current active key"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise Unauthorized('User ID required')
            
        keys = redis_client.smembers(f"user:{user_id}:keys")
        for key in keys:
            key_data = json.loads(redis_client.get(f"keys:{key}"))
            if key_data['is_active']:
                key_manager.revoke_key(key)
                return jsonify({'status': 'revoked'})
        return jsonify({'error': 'No active key to revoke'}), 400
    
    @app.route('/api/keys/revoke-all', methods=['POST'])
    def revoke_all_keys():
        """Revoke all keys for user"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise Unauthorized('User ID required')
            
        count = key_manager.revoke_all_keys(user_id, emergency=True)
        return jsonify({'revoked_count': count})
    
    @app.route('/api/keys/settings', methods=['POST'])
    def save_settings():
        """Save key rotation settings"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise Unauthorized('User ID required')
            
        settings = request.get_json()
        redis_client.hset(f"user:{user_id}:settings", mapping=settings)
        return jsonify({'status': 'saved'})
    
    @app.route('/api/keys/history', methods=['GET'])
    def get_key_history():
        """Get full key history for user"""
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise Unauthorized('User ID required')
            
        keys = redis_client.smembers(f"user:{user_id}:keys")
        history = []
        for key in keys:
            key_data = json.loads(redis_client.get(f"keys:{key}"))
            history.append({
                'key': key_data['value'],
                'version': key_data['version'],
                'created_at': key_data['created_at'],
                'status': key_data.get('rotation_status', 'active'),
                'audit_log': key_data.get('audit_log', [])
            })
        return jsonify({'history': sorted(history,
            key=lambda x: x['created_at'], reverse=True)})
    
    @app.route('/api/keys/emergency-revoke', methods=['POST'])
    def emergency_revoke():
        """Emergency revoke all keys for a target user. Requires admin privileges."""
        # This is a conceptual check. A real implementation needs robust admin auth.
        admin_user_id = request.headers.get('X-Admin-User-ID') # Hypothetical header for admin making the call
        admin_api_key = request.headers.get('X-Admin-API-Key')   # Hypothetical header for admin auth

        # Placeholder for actual admin authentication & authorization
        # For example, verify admin_api_key or a JWT token for an admin user
        is_admin = (admin_user_id == "admin_user" and admin_api_key == os.getenv("ADMIN_SERVICE_API_KEY")) # Simplified check
        
        if not is_admin:
            logger.warning(f"Unauthorized attempt at emergency revoke by: {admin_user_id}")
            raise Unauthorized('Admin privileges required for emergency revocation.')

        target_user_id = request.headers.get('X-Target-User-ID') # User whose keys are to be revoked
        if not target_user_id:
            raise BadRequest('Target User ID (X-Target-User-ID) required for emergency revocation.')
            
        logger.info(f"Admin {admin_user_id} initiating emergency revoke for user {target_user_id}")
        keys = redis_client.smembers(f"user:{target_user_id}:keys")
        for key in keys:
            key_data = json.loads(redis_client.get(f"keys:{key}"))
            key_data['is_active'] = False
            key_data['rotation_status'] = 'emergency_revoked'
            key_data['audit_log'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'emergency_revoked',
                'details': 'Revoked via emergency endpoint'
            })
            redis_client.set(f"keys:{key}", json.dumps(key_data))
            
        key_manager._notify('emergency_revoked', { # Changed self._notify to key_manager._notify
            'user_id': target_user_id, # Ensure using target_user_id
            'revoked_keys': list(keys),
            'admin_user_id': admin_user_id # Pass admin_user_id if available in context
        })
        
        return jsonify({'revoked_count': len(keys), 'target_user_id': target_user_id})
    
    return app

if __name__ == '__main__':
    redis_client = get_redis_client()
    key_manager = KeyManager(redis_client)
    
    # Setup notification callback
    def notify_handler(event: Dict[str, Any]) -> None:
        event_type = event.get('event_type')
        data = event.get('data', {})
        print(f"Key event: {event_type}, Data: {data}")

        # Email Notification Logic
        SMTP_SERVER = os.getenv("SMTP_SERVER")
        SMTP_PORT = os.getenv("SMTP_PORT", 587)
        SMTP_USER = os.getenv("SMTP_USER")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        SENDER_EMAIL = os.getenv("SENDER_EMAIL")
        RECIPIENT_EMAIL = os.getenv("KEY_NOTIFICATION_RECIPIENT_EMAIL") # Target for key notifications

        if not all([SMTP_SERVER, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL, RECIPIENT_EMAIL]):
            logger.warning("SMTP configuration missing. Email notifications for key events are disabled.")
            return

        subject = ""
        body = ""

        if event_type == 'key_expiring':
            subject = f"API Key Expiring Soon: {data.get('key')}"
            body = (f"API Key {data.get('key')} for user_id associated with this key "
                    f"is expiring on {data.get('expires_at')}.\n"
                    f"Days remaining: {data.get('days_remaining')}.\n"
                    "Please rotate the key soon.")
        elif event_type == 'key_rotated':
            subject = f"API Key Rotated: {data.get('old_key')}"
            body = (f"API Key {data.get('old_key')} has been rotated.\n"
                    f"New key: {data.get('new_key')}\n"
                    f"The old key will remain active until {data.get('grace_period_end')}.")
        elif event_type == 'key_created':
             subject = f"New API Key Created"
             body = (f"A new API key {data.get('key')} was created for user {data.get('user_id')} "
                     f"and expires on {data.get('expires_at')}.")
        elif event_type == 'emergency_revoked':
            subject = f"Emergency Revocation of API Keys for User {data.get('user_id')}"
            body = (f"All API keys for user {data.get('user_id')} have been emergency revoked.\n"
                    f"Revoked keys: {', '.join(data.get('revoked_keys', []))}")
        else:
            logger.info(f"No email notification configured for event type: {event_type}")
            return

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL

        try:
            with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
                server.starttls() # Use TLS
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, [RECIPIENT_EMAIL], msg.as_string())
            logger.info(f"Sent key event notification email for {event_type} to {RECIPIENT_EMAIL}")
        except Exception as e:
            logger.error(f"Failed to send key event email for {event_type}: {str(e)}")
        
    key_manager.add_notification_callback(notify_handler)
    
    # Start scheduled rotation job
    import schedule
    import threading
    
    def run_scheduler() -> None:
        # Check expirations every hour
        schedule.every().hour.do(rotate_expiring_keys, key_manager)
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    import logging
    logger = logging.getLogger(__name__)
    
    # Start both gRPC and REST servers with error handling
    from concurrent.futures import ThreadPoolExecutor
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Start gRPC server with port fallback
            grpc_future = executor.submit(
                serve,
                redis_client,
                key_manager=key_manager,
                port=50051,
                max_retries=5
            )
            
            # Start REST API
            app = create_app(redis_client, key_manager)
            rest_future = executor.submit(
                app.run,
                port=5000,
                debug=False,  # Disable debug for production
                use_reloader=False
            )
            
            # Log server status
            logger.info("Servers started successfully")
            logger.info(f"gRPC server running on port {grpc_future.result().port}")
            logger.info(f"REST API running on port 5000")
            
            # Wait for servers to complete
            grpc_future.result()
            rest_future.result()
            
    except Exception as e:
        logger.error(f"Failed to start servers: {str(e)}")
        raise