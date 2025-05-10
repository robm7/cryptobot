import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "Backtest Service"
    debug: bool = False
    max_concurrent_backtests: int = 5
    results_ttl_days: int = 7  # Days to keep backtest results
    
    # Database configuration
    database_url: str = "sqlite:///./backtest.db"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()