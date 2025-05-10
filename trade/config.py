import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class ExchangeConfig:
    def __init__(self):
        self.api_key = os.getenv("EXCHANGE_API_KEY")
        self.api_secret = os.getenv("EXCHANGE_API_SECRET")
        self.passphrase = os.getenv("EXCHANGE_PASSPHRASE", "")
        self.sandbox = os.getenv("EXCHANGE_SANDBOX", "false").lower() == "true"

        # Rate limits (requests per minute)
        self.rate_limits = {
            "binance": 1200,
            "coinbase": 300,
            "kraken": 360,
            "ftx": 30
        }

    def get_exchange_config(self, exchange: str) -> Dict[str, Any]:
        """Get configuration for a specific exchange"""
        return {
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "password": self.passphrase,
            "enableRateLimit": True,
            "rateLimit": self._get_rate_limit_ms(exchange),
            "verbose": False,
            "options": {
                "sandboxMode": self.sandbox
            }
        }

    def _get_rate_limit_ms(self, exchange: str) -> int:
        """Convert requests per minute to milliseconds delay between requests"""
        rpm = self.rate_limits.get(exchange.lower(), 300)
        return int(60000 / rpm)  # 60,000ms (1 minute) / requests per minute

# Singleton configuration instance
exchange_config = ExchangeConfig()