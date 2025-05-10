import os
from typing import Dict, Any
from .errors import ExchangeError

class ExchangeConfig:
    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load exchange configurations from environment"""
        self.binance_config = {
            'api_key': os.getenv('BINANCE_API_KEY'),
            'api_secret': os.getenv('BINANCE_API_SECRET'),
            'timeout': int(os.getenv('BINANCE_TIMEOUT', '5000')),
            'rate_limit': os.getenv('BINANCE_RATE_LIMIT', '10req/s')
        }
        
        self.kraken_config = {
            'api_key': os.getenv('KRAKEN_API_KEY'),
            'api_secret': os.getenv('KRAKEN_API_SECRET'),
            'timeout': int(os.getenv('KRAKEN_TIMEOUT', '3000')),
            'rate_limit': os.getenv('KRAKEN_RATE_LIMIT', '15req/s')
        }

    def get_exchange_client(self, exchange: str):
        """Initialize and return exchange client"""
        if exchange not in self._clients:
            if exchange == 'binance':
                from services.data.exchanges.binance import BinanceClient
                self._clients[exchange] = BinanceClient(**self.binance_config)
            elif exchange == 'kraken':
                from services.data.exchanges.kraken import KrakenClient
                self._clients[exchange] = KrakenClient(**self.kraken_config)
            else:
                raise ExchangeError(f"Unsupported exchange: {exchange}")
        
        return self._clients[exchange]

# Singleton configuration instance
exchange_config = ExchangeConfig()

def get_exchange_client(exchange: str):
    """Public interface to get exchange client"""
    return exchange_config.get_exchange_client(exchange)