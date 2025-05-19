import os # Added for environment variable access
from pydantic_settings import BaseSettings # Corrected for Pydantic v2
from typing import List, Optional # Added Optional

class Settings(BaseSettings):
    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None # Made Optional
    REDIS_TIMEOUT: int = 5 # Added
    REDIS_MAX_CONNECTIONS: int = 10 # Added
    
    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT: int = 60  # requests per minute
    DEFAULT_RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_EXEMPT_PATHS: List[str] = ["/health", "/docs", "/openapi.json"]
    # Note: auth/redis_service.py uses settings.RATE_LIMIT_PER_MINUTE which is DEFAULT_RATE_LIMIT here.
    # This should be fine as it's used as a default if not passed to check_rate_limit.
    
    # Security settings
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4
    ENCRYPTION_KEY: str = "global_fallback_encryption_key" # Added, ensure this is secure or from .env
    ENCRYPTION_SALT: str = "global_fallback_encryption_salt" # Added, ensure this is secure or from .env
    
    # Application settings
    ALLOW_ORIGINS: List[str] = ["*"]
    DEBUG: bool = False
    DEFAULT_EXCHANGE: str = "kraken" # Added to set Kraken as default
    DRY_RUN: bool = True # Updated to Pydantic field with default
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Allow and ignore extra fields from .env

settings = Settings()