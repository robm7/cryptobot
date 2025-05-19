from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from database.db import Base # Corrected import

class Session(Base):
    """Database model for user sessions"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(512), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String(45))  # IPv6 max length
    user_agent = Column(String(512))
    device_info = Column(JSON)
    location = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_suspicious = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    suspicious_activities = relationship("SuspiciousActivity", back_populates="session")

class SuspiciousActivity(Base):
    """Database model for tracking suspicious session activities"""
    __tablename__ = "suspicious_activities"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    activity_type = Column(String(128))
    details = Column(JSON)
    severity = Column(String(32))  # low, medium, high
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="suspicious_activities")