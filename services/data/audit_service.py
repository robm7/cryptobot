import logging
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import AuditLog
from database.db import get_db
import json

class AuditService:
    """Service for handling audit logging operations"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session if db_session else next(get_db())
        self.logger = logging.getLogger('audit')

    def log_event(self, 
                 event_type: str,
                 action_details: Dict[str, Any],
                 user_id: int = None,
                 ip_address: str = None,
                 status: str = "success",
                 resource_type: str = None,
                 resource_id: int = None) -> AuditLog:
        """Log an audit event to the database"""
        
        try:
            audit_log = AuditLog(
                event_type=event_type,
                user_id=user_id,
                action_details=json.dumps(action_details),
                ip_address=ip_address,
                status=status,
                resource_type=resource_type,
                resource_id=resource_id
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            self.logger.info(f"Audit log created: {event_type} by user {user_id}")
            return audit_log
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Failed to create audit log: {str(e)}")
            raise

    def get_logs(self, 
                event_type: str = None,
                user_id: int = None,
                start_date: datetime = None,
                end_date: datetime = None,
                status: str = None,
                resource_type: str = None,
                limit: int = 100) -> list[AuditLog]:
        """Query audit logs with filters"""
        
        query = self.db.query(AuditLog)
        
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if status:
            query = query.filter(AuditLog.status == status)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
            
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def search_logs(self, search_term: str, limit: int = 100) -> list[AuditLog]:
        """Search audit logs by content"""
        return self.db.query(AuditLog)\
            .filter(AuditLog.action_details.ilike(f"%{search_term}%"))\
            .order_by(AuditLog.timestamp.desc())\
            .limit(limit)\
            .all()