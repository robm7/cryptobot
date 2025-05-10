from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = True
    WORKERS: int = 1
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Data source configuration
    DATA_CACHE_TTL: int = 300  # 5 minutes
    EXCHANGES: List[str] = ["binance", "kraken", "coinbase"]
    
    # Redis configuration for caching
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()