from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = None
    
    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_RATE_LIMIT: int = 60  # requests per minute
    DEFAULT_RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_EXEMPT_PATHS: List[str] = ["/health", "/docs", "/openapi.json"]
    
    # Security settings
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4
    
    # Application settings
    ALLOW_ORIGINS: List[str] = ["*"]
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()