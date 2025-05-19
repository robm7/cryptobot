from pydantic_settings import BaseSettings # Corrected import for Pydantic v2
from pydantic import PostgresDsn, validator
from typing import Optional, Union, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: Optional[str] = None # Changed from PostgresDsn to str to allow SQLite URLs from .env
    DEBUG: bool = False
    
    # Auth settings
    AUTH_SERVICE_URL: str = "http://auth-service:8000"
    SECRET_KEY: str = "test_secret_key_for_local_testing"  # Default for testing
    TOKEN_CACHE_TTL: int = 60  # Cache successful token validations for 60 seconds
    
    # Role-based access control
    ADMIN_ROLE: str = "admin"
    TRADER_ROLE: str = "trader"
    VIEWER_ROLE: str = "viewer"
    
    # Environment
    TESTING: bool = False

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        # If testing mode, no database URL is needed
        if values.get("TESTING", False):
            logger.info("Running in testing mode, database URL not required")
            return v
            
        # In development mode, create a default SQLite URL if none provided
        if not v:
            if os.getenv("ENVIRONMENT") == "development" or os.getenv("DEBUG") == "1":
                logger.warning("No DATABASE_URL provided, using SQLite for development")
                return "sqlite:///./test.db"
                
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow and ignore extra fields from .env

# Try to load settings, with fallback for testing
try:
    settings = Settings()
except Exception as e:
    logger.warning(f"Error loading settings: {str(e)}. Using testing defaults.")
    # Create testing defaults
    settings = Settings(TESTING=True)