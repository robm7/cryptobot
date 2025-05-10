import os
from pydantic import BaseSettings
from typing import Dict, Any

class Settings(BaseSettings):
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Redis Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Email Settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.example.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@cryptobot.com")
    
    # CORS Settings
    ALLOW_ORIGINS: list = ["*"]
    
    # Session settings
    SESSION_SECRET_KEY: str = "your-secret-key-here"  # Should be set via env var in production
    SESSION_EXPIRE_MINUTES: int = 43200  # 30 days
    SESSION_INACTIVITY_TIMEOUT: int = 1440  # 24 hours
    SESSION_COOKIE_NAME: str = "session_token"
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    
    # Suspicious activity detection
    SUSPICIOUS_ACTIVITY_THRESHOLDS: Dict[str, Any] = {
        "ip_change": {"count": 3, "window": 3600},  # 3 IP changes in 1 hour
        "location_change": {"distance": 500, "window": 3600},  # 500km in 1 hour
        "failed_actions": {"count": 5, "window": 300}  # 5 failed actions in 5 minutes
    }
    
    class Config:
        env_file = ".env"

settings = Settings()