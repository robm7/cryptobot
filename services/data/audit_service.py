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
        self.db = db_session # If no session passed, db will be None. Methods using it will fail.
        self.logger = logging.getLogger('audit')
        if not db_session:
            self.logger.warning("AuditService initialized without a DB session. Audit logging will be disabled.")

    async def log_event(self,
                        event_type: str,
                        action_details: Dict[str, Any],
                        user_id: int = None,
                        ip_address: str = None,
                        status: str = "success",
                        resource_type: str = None,
                        resource_id: int = None) -> AuditLog:
        """Log an audit event to the database"""
        
        if not self.db:
            self.logger.warning(f"Audit event '{event_type}' not logged to DB: AuditService has no DB session.")
            return None # Or some other appropriate non-DB action

        async with self.db as session:
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
                
                session.add(audit_log)
                await session.commit()
                await session.refresh(audit_log)
                
                self.logger.info(f"Audit log created: {event_type} by user {user_id}")
                return audit_log
            except Exception as e:
                self.logger.error(f"Failed to create audit log: {str(e)}")
                await session.rollback()
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