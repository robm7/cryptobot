from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from contextlib import contextmanager

from config import settings

# Get database URL from environment or use SQLite by default
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./auth_service.db"
)

# Create engine with appropriate parameters
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db():
    """Get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def initialize_db():
    """Create all tables in the database"""
    # Import models to ensure they are registered with Base.metadata
    from models.user import User, Role, APIKey
    
    Base.metadata.create_all(bind=engine)
    
    # Create default roles if they don't exist
    with get_db_session() as db:
        from models.user import Role
        
        # Define default roles
        default_roles = ["admin", "user", "trader", "read_only"]
        
        # Create roles if they don't exist
        for role_name in default_roles:
            existing_role = db.query(Role).filter(Role.name == role_name).first()
            if not existing_role:
                new_role = Role(name=role_name)
                db.add(new_role)
        
        # Create default admin user if no users exist
        from models.user import User
        if db.query(User).count() == 0:
            admin_password = os.getenv("ADMIN_PASSWORD", "admin")
            admin_user = User(
                username="admin",
                email="admin@cryptobot.com",
                full_name="Admin User",
                hashed_password=User.get_password_hash(admin_password)
            )
            
            # Add admin role to user
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            admin_user.roles.append(admin_role)
            
            db.add(admin_user)
        
        db.commit()