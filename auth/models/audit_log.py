from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50))  # e.g. "user_create", "setting_update"
    entity_type = Column(String(50))  # e.g. "user", "setting"
    entity_id = Column(String(255))  # ID of affected entity
    details = Column(Text)  # JSON details of changes
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))  # Store IPv4 or IPv6