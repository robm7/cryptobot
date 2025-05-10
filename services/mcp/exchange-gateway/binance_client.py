import os
import hmac
import hashlib
import time
import requests
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime
from .interfaces import ExchangeInterface

class BinanceClient(ExchangeInterface):
    """Binance exchange implementation"""
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.base_url = "https://api.binance.com"
        self.api_key = api_key or os.getenv('BINANCE_API_KEY')
        self.api_secret = api_secret or os.getenv('BINANCE_API_SECRET')
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })
        
    def _generate_signature(self, data: Dict) -> str:
        """Generate HMAC SHA256 signature"""
        query_string = '&'.join([f"{k}={v}" for k, v in data.items()])
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
    def get_balances(self) -> Dict[str, Decimal]:
        """Get current account balances"""
        data = {
            'timestamp': int(time.time() * 1000),
            'recvWindow': 5000
        }
        data['signature'] = self._generate_signature(data)
        
        response = self.session.get(
            f"{self.base_url}/api/v3/account",
            params=data
        )
        response.raise_for_status()
        
        return {
            asset['asset']: Decimal(asset['free'])
            for asset in response.json()['balances']
        }
        
    def get_ticker(self, symbol: str) -> Dict:
        """Get current market price for symbol"""
        response = self.session.get(
            f"{self.base_url}/api/v3/ticker/price",
            params={'symbol': symbol}
        )
        response.raise_for_status()
        return response.json()
        
    def create_order(self, symbol: str, side: str, 
                   quantity: Decimal, price: Optional[Decimal] = None) -> str:
        """Create new order and return order ID"""
        data = {
            'symbol': symbol,
            'side': side.upper(),
            'type': 'LIMIT' if price else 'MARKET',
            'quantity': str(quantity),
            'timestamp': int(time.time() * 1000),
            'recvWindow': 5000
        }
        
        if price:
            data['price'] = str(price)
            data['timeInForce'] = 'GTC'
            
        data['signature'] = self._generate_signature(data)
        
        response = self.session.post(
            f"{self.base_url}/api/v3/order",
            data=data
        )
        response.raise_for_status()
        return response.json()['orderId']
        
    # Implement remaining interface methods...
    def cancel_order(self, order_id: str) -> bool:
        pass
        
    def get_order_status(self, order_id: str) -> Dict:
        pass
        
    def get_ohlcv(self, symbol: str, interval: str, 
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None) -> List[Dict]:
        pass