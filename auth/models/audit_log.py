from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from database.db import Base # Corrected import
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List, Optional

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(50), index=True)  # e.g. "api_key_create", "api_key_rotate"
    resource_type = Column(String(50), index=True)  # e.g. "api_key", "user"
    resource_id = Column(String(255), index=True)  # ID of affected resource
    details = Column(Text)  # JSON details of changes
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(String(45))  # Store IPv4 or IPv6
    user_agent = Column(String(255), nullable=True)  # User agent string
    severity = Column(String(20), default="normal", index=True)  # normal, high, critical
    status = Column(String(20), default="success")  # success, failure, warning
    is_sensitive = Column(Boolean, default=False, index=True)  # Flag for sensitive operations
    masked_details = Column(Text, nullable=True)  # Masked version of details for sensitive logs
    
    # Create indexes for common queries
    __table_args__ = (
        Index('ix_audit_logs_user_timestamp', 'user_id', 'timestamp'),
        Index('ix_audit_logs_action_timestamp', 'action', 'timestamp'),
        Index('ix_audit_logs_resource_timestamp', 'resource_type', 'resource_id', 'timestamp'),
    )
    
    @classmethod
    def create_from_request(cls,
                           db_session,
                           user_id: Optional[int],
                           action: str,
                           resource_type: str,
                           resource_id: str,
                           details: Dict[str, Any],
                           request=None,
                           severity: str = "normal",
                           status: str = "success") -> "AuditLog":
        """Create an audit log entry from a request"""
        # Determine if this is a sensitive action
        from ..config import settings # Corrected import
        is_sensitive = action in settings.AUDIT_LOG_SENSITIVE_ACTIONS
        
        # Create masked details for sensitive actions
        masked_details = None
        if is_sensitive:
            masked_details = cls.mask_sensitive_data(details)
        
        # Create log entry
        log_entry = cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details),
            masked_details=json.dumps(masked_details) if masked_details else None,
            severity=severity,
            status=status,
            is_sensitive=is_sensitive
        )
        
        # Add request information if available
        if request:
            log_entry.ip_address = request.client.host
            log_entry.user_agent = request.headers.get("user-agent")
        
        # Save to database
        db_session.add(log_entry)
        db_session.commit()
        
        return log_entry
    
    @staticmethod
    def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in audit logs"""
        masked_data = data.copy()
        
        # Define sensitive fields to mask
        sensitive_fields = ["key", "password", "token", "secret", "api_key"]
        
        # Recursively mask sensitive fields
        def mask_dict(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    mask_dict(v)
                elif isinstance(v, str) and any(field in k.lower() for field in sensitive_fields):
                    if len(v) > 8:
                        d[k] = v[:4] + "*" * (len(v) - 8) + v[-4:]
                    else:
                        d[k] = "*" * len(v)
        
        mask_dict(masked_data)
        return masked_data
    
    @classmethod
    def get_logs_for_user(cls, db_session, user_id: int, limit: int = 100) -> List["AuditLog"]:
        """Get audit logs for a specific user"""
        return db_session.query(cls).filter(cls.user_id == user_id).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_for_resource(cls, db_session, resource_type: str, resource_id: str, limit: int = 100) -> List["AuditLog"]:
        """Get audit logs for a specific resource"""
        return db_session.query(cls).filter(
            cls.resource_type == resource_type,
            cls.resource_id == resource_id
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_logs_by_action(cls, db_session, action: str, limit: int = 100) -> List["AuditLog"]:
        """Get audit logs for a specific action"""
        return db_session.query(cls).filter(cls.action == action).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_high_severity_logs(cls, db_session, days: int = 7, limit: int = 100) -> List["AuditLog"]:
        """Get high severity audit logs"""
        since = datetime.utcnow() - timedelta(days=days)
        return db_session.query(cls).filter(
            cls.severity.in_(["high", "critical"]),
            cls.timestamp >= since
        ).order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def cleanup_old_logs(cls, db_session, retention_days: int = 365) -> int:
        """Delete audit logs older than retention_days"""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        result = db_session.query(cls).filter(cls.timestamp < cutoff_date).delete()
        db_session.commit()
        return result