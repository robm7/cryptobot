import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class ExchangeConfig:
    def __init__(self):
        self.api_key = os.getenv("EXCHANGE_API_KEY") # Generic, might be for a default exchange
        self.api_secret = os.getenv("EXCHANGE_API_SECRET")
        self.passphrase = os.getenv("EXCHANGE_PASSPHRASE", "") # Generic
        
        # Coinbase Pro specific keys
        self.coinbase_api_key = os.getenv("COINBASE_API_KEY")
        self.coinbase_api_secret = os.getenv("COINBASE_API_SECRET")
        self.coinbase_passphrase = os.getenv("COINBASE_PASSPHRASE")

        self.sandbox = os.getenv("EXCHANGE_SANDBOX", "false").lower() == "true"

        # Rate limits (requests per minute)
        self.rate_limits = {
            "binance": 1200,
            "coinbase": 300, # This might be for coinbase.com, not pro
            "coinbasepro": 600, # Coinbase Pro: 10 requests/sec for private, 15 for public (bursts)
                               # Let's set a general 600/min (10/sec) as a safe default.
            "kraken": 360,
            "ftx": 30
        }

    def get_coinbase_pro_credentials(self) -> Dict[str, Optional[str]]:
        """Returns Coinbase Pro specific API credentials."""
        if not all([self.coinbase_api_key, self.coinbase_api_secret, self.coinbase_passphrase]):
            # Or raise an error, or return None to indicate missing config
            print("Warning: Coinbase Pro API credentials are not fully configured in environment variables.") # TODO: Use proper logging
        return {
            "api_key": self.coinbase_api_key,
            "api_secret": self.coinbase_api_secret,
            "passphrase": self.coinbase_passphrase
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