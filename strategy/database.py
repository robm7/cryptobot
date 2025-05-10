from typing import Generator
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get database URL from environment
def get_database_url():
    """Get database URL with proper fallback"""
    db_url = os.getenv("DATABASE_URL")
    
    # Default to SQLite if no URL provided
    if not db_url:
        db_path = os.path.abspath('database/cryptobot.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"
    
    return db_url

# Create engine and session
DATABASE_URL = get_database_url()
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a SQLAlchemy session.
    
    This dependency is compatible with FastAPI's Depends() function
    and handles proper session cleanup.
    
    Returns:
        Generator yielding a SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        logger.debug("Creating new database session")
        yield db
        db.commit()
        logger.debug("Session committed")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        logger.debug("Session rolled back")
        raise
    finally:
        logger.debug("Closing database session")
        db.close()