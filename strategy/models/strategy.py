from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.mutable import MutableDict
from database.db import Base
import logging

logger = logging.getLogger(__name__)

class Strategy(Base):
    """SQLAlchemy model for trading strategies"""
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    parameters = Column(MutableDict.as_mutable(JSON), default={})
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Strategy {self.name} v{self.version}>"

class StrategyVersion(Base):
    """Version history for strategies"""
    __tablename__ = "strategy_versions"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, index=True)
    version = Column(Integer, nullable=False)
    parameters = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)