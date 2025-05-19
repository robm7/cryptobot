import uuid
import json
from datetime import datetime, timedelta
from fastapi import Request, Response
from fastapi.middleware import Middleware
from fastapi.encoders import jsonable_encoder
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
import jwt
import geoip2.database
import user_agents
from typing import Optional, Dict, Any

from ..config import settings # Corrected import
from database.db import get_db # Corrected import
from ..models.session import Session, SuspiciousActivity # Corrected import
from ..models.user import User # Corrected import

import sys
import os
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# from utils.ip_utils import get_client_ip # Commented out as file doesn't exist
# from utils.logger import logger # Commented out as file might not exist or to simplify
def get_client_ip(request: Request) -> Optional[str]: # Placeholder
    if request.client:
        return request.client.host
    return "0.0.0.0" # Fallback placeholder

# Basic placeholder logger if utils.logger is also an issue
class PrintLogger:
    def error(self, msg):
        print(f"ERROR: {msg}")
    def info(self, msg):
        print(f"INFO: {msg}")
    # Add other methods as needed (warning, debug, etc.)
logger = PrintLogger()

del sys, os, _PROJECT_ROOT # Clean up

class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware for managing user sessions and detecting suspicious activity"""
    
    def __init__(self, app):
        super().__init__(app)
        # self.geoip_reader = geoip2.database.Reader('GeoLite2-City.mmdb') # Temporarily commented out
        self.geoip_reader = None # Ensure attribute exists
        
    async def dispatch(self, request: Request, call_next):
        # Skip session handling for certain paths
        if request.url.path in ['/health', '/docs', '/openapi.json']:
            return await call_next(request)
            
        db = next(get_db())
        session_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
        current_user = None
        session = None
        
        try:
            # Validate existing session or create new one
            if session_token:
                session = self._validate_session(db, session_token)
                if session:
                    current_user = db.query(User).filter(User.id == session.user_id).first()
                    
                    # Check for suspicious activity
                    self._check_suspicious_activity(request, session, current_user)
                    
                    # Update last activity
                    session.last_activity = datetime.utcnow()
                    db.commit()
            
            # Attach session and user to request state
            request.state.session = session
            request.state.user = current_user
            
            # Process request
            response = await call_next(request)
            
            # Create new session if authenticated but no session exists
            if not session and hasattr(request.state, 'user') and request.state.user:
                session = self._create_session(db, request, request.state.user)
                response = self._set_session_cookie(response, session)
            
            return response
            
        except Exception as e:
            print(f"ERROR: Session middleware error: {str(e)}") # Replaced logger
            raise
        finally:
            db.close()
    
    def _validate_session(self, db, session_token: str) -> Optional[Session]:
        """Validate and return active session"""
        try:
            # Verify JWT signature
            payload = jwt.decode(
                session_token,
                settings.SESSION_SECRET_KEY,
                algorithms=["HS256"]
            )
            
            session = db.query(Session).filter(
                Session.session_token == session_token,
                Session.is_active == True
            ).first()
            
            # Check expiration
            if datetime.utcnow() - session.last_activity > timedelta(minutes=settings.SESSION_INACTIVITY_TIMEOUT):
                session.is_active = False
                db.commit()
                return None
                
            return session
            
        except (jwt.PyJWTError, AttributeError):
            return None
    
    def _create_session(self, db, request: Request, user: User) -> Session:
        """Create new session for authenticated user"""
        device_info = self._parse_device_info(request)
        location = self._get_location_info(request)
        
        session_token = jwt.encode(
            {
                "sub": str(user.id),
                "jti": str(uuid.uuid4()),
                "iat": datetime.utcnow().timestamp(),
                "exp": (datetime.utcnow() + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES)).timestamp()
            },
            settings.SESSION_SECRET_KEY,
            algorithm="HS256"
        )
        
        session = Session(
            session_token=session_token,
            user_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            device_info=device_info,
            location=location,
            is_active=True
        )
        
        db.add(session)
        db.commit()
        return session
    
    def _set_session_cookie(self, response: Response, session: Session) -> Response:
        """Set session cookie on response"""
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session.session_token,
            max_age=settings.SESSION_EXPIRE_MINUTES * 60,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        return response
    
    def _parse_device_info(self, request: Request) -> Dict[str, Any]:
        """Parse device info from user agent"""
        ua = user_agents.parse(request.headers.get("user-agent", ""))
        return {
            "device": ua.device.family,
            "os": f"{ua.os.family} {ua.os.version_string}",
            "browser": f"{ua.browser.family} {ua.browser.version_string}",
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_pc": ua.is_pc,
            "is_bot": ua.is_bot
        }
    
    def _get_location_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get location info from IP address"""
        ip = get_client_ip(request)
        if not ip or ip == "127.0.0.1":
            return None
            
        # Temporarily disable GeoIP lookup
        if not self.geoip_reader:
            logger.warning("GeoIP lookup disabled as geoip_reader is not initialized.")
            return None

        try:
            response = self.geoip_reader.city(ip)
            return {
                "city": response.city.name,
                "country": response.country.name,
                "country_code": response.country.iso_code,
                "latitude": response.location.latitude,
                "longitude": response.location.longitude,
                "timezone": response.location.time_zone
            }
        except Exception:
            return None
    
    def _check_suspicious_activity(self, request: Request, session: Session, user: User):
        """Check for and log suspicious activity"""
        suspicious = False
        activity_type = None
        details = {}
        
        # Check IP change
        current_ip = get_client_ip(request)
        if current_ip != session.ip_address:
            activity_type = "ip_change"
            details = {
                "old_ip": session.ip_address,
                "new_ip": current_ip
            }
            suspicious = True
        
        # Check location change
        current_location = self._get_location_info(request)
        if current_location and session.location:
            # Calculate distance between locations (simplified)
            lat_diff = abs(current_location["latitude"] - session.location["latitude"])
            lon_diff = abs(current_location["longitude"] - session.location["longitude"])
            if lat_diff > 0.5 or lon_diff > 0.5:  # Roughly 50km threshold
                activity_type = "location_change"
                details = {
                    "old_location": session.location,
                    "new_location": current_location,
                    "distance_approx_km": max(lat_diff * 111, lon_diff * 111)  # 1 degree ≈ 111km
                }
                suspicious = True
        
        if suspicious:
            self._log_suspicious_activity(session, activity_type, details)
    
    def _log_suspicious_activity(self, session: Session, activity_type: str, details: Dict[str, Any]):
        """Log suspicious activity to database"""
        db = next(get_db())
        try:
            activity = SuspiciousActivity(
                session_id=session.id,
                activity_type=activity_type,
                details=details,
                severity="medium"  # Default severity
            )
            db.add(activity)
            db.commit()
            
            # Mark session as suspicious if multiple activities
            count = db.query(SuspiciousActivity).filter(
                SuspiciousActivity.session_id == session.id,
                SuspiciousActivity.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            
            if count >= settings.SUSPICIOUS_ACTIVITY_THRESHOLDS.get(activity_type, {}).get("count", 3):
                session.is_suspicious = True
                db.commit()
                
        except Exception as e:
            print(f"ERROR: Failed to log suspicious activity: {str(e)}") # Replaced logger
        finally:
            db.close()