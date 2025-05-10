from enum import Enum
from pydantic import BaseSettings
from .service import NotificationChannel

class NotificationSettings(BaseSettings):
    # Email provider config
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    email_from: str

    # SMS provider config
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str

    # Rate limiting
    rate_limit_per_hour: int = 100
    rate_limit_per_day: int = 1000

    class Config:
        env_prefix = "NOTIFICATION_"

def get_provider_configs(settings: NotificationSettings) -> dict:
    return {
        NotificationChannel.EMAIL: {
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "username": settings.smtp_username,
            "password": settings.smtp_password
        },
        NotificationChannel.SMS: {
            "account_sid": settings.twilio_account_sid,
            "auth_token": settings.twilio_auth_token,
            "from_number": settings.twilio_from_number
        }
    }