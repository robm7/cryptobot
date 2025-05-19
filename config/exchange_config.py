import os
from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class ExchangeConfig:
    """Configuration for a cryptocurrency exchange."""
    api_key: str
    api_secret: str
    testnet: bool = False
    additional_params: Dict[str, Any] = None

class ExchangeConfigManager:
    """Manages configurations for multiple exchanges."""
    
    @staticmethod
    def get_binance_config(testnet: bool = False) -> ExchangeConfig:
        """Get Binance exchange configuration.
        
        Args:
            testnet: Whether to use Binance testnet
            
        Returns:
            ExchangeConfig: Configuration for Binance
        """
        params = {
            'options': {
                'adjustForTimeDifference': True,  # Helps with timestamp synchronization
                'recvWindow': 60000,  # 60 second recvWindow
                'defaultType': 'spot',  # Default to spot trading
            }
        }
        
        if testnet:
            params.update({
                'testnet': True,
                'urls': {
                    'api': 'https://testnet.binance.vision'
                }
            })
            
        return ExchangeConfig(
            api_key=os.getenv('BINANCE_API_KEY'),
            api_secret=os.getenv('BINANCE_SECRET_KEY'),
            testnet=testnet,
            additional_params=params
        )

    @staticmethod
    def get_kraken_config(testnet: bool = False) -> ExchangeConfig:
        """Get Kraken exchange configuration.
        
        Args:
            testnet: Whether to use Kraken sandbox
            
        Returns:
            ExchangeConfig: Configuration for Kraken
        """
        params = {
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000
            }
        }
        
        if testnet:
            params.update({
                'urls': {
                    'api': 'https://api-sandbox.kraken.com'
                }
            })
            
        return ExchangeConfig(
            api_key=os.getenv('KRAKEN_API_KEY', 'KRAKEN_API_KEY_PLACEHOLDER'),
            api_secret=os.getenv('KRAKEN_API_SECRET', 'KRAKEN_API_SECRET_PLACEHOLDER'),
            testnet=testnet,
            additional_params=params
        )

    @staticmethod
    def get_exchange_config(exchange_name: str, testnet: bool = False) -> ExchangeConfig:
        """Get configuration for a specific exchange.
        
        Args:
            exchange_name: Name of the exchange ('binance' or 'kraken')
            testnet: Whether to use testnet (only applicable for Binance)
            
        Returns:
            ExchangeConfig: Configuration for the specified exchange
            
        Raises:
            ValueError: If exchange_name is not supported
        """
        if exchange_name.lower() == 'binance':
            return ExchangeConfigManager.get_binance_config(testnet)
        elif exchange_name.lower() == 'kraken':
            return ExchangeConfigManager.get_kraken_config(testnet)
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")