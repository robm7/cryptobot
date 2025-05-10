from typing import Dict, List, Optional
import asyncio
import aiohttp
from decimal import Decimal
from .exceptions import ExchangeError

class ExchangeInterface:
    """Unified interface for cryptocurrency exchanges"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = aiohttp.ClientSession()
        
    async def get_balances(self) -> Dict[str, Decimal]:
        """Get current account balances"""
        raise NotImplementedError
        
    async def get_ticker(self, symbol: str) -> Dict:
        """Get current market price for symbol"""
        raise NotImplementedError
        
    async def create_order(self, symbol: str, side: str, type: str, 
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        """Create new trading order"""
        raise NotImplementedError
        
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel existing order"""
        raise NotImplementedError
        
    async def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """Get list of open orders"""
        raise NotImplementedError
        
    async def close(self):
        """Clean up resources"""
        await self.session.close()

class BinanceExchange(ExchangeInterface):
    """Binance exchange implementation"""
    
    BASE_URL = "https://api.binance.com"
    
    async def get_balances(self) -> Dict[str, Decimal]:
        endpoint = "/api/v3/account"
        data = await self._signed_request("GET", endpoint)
        return {
            asset['asset']: Decimal(asset['free'])
            for asset in data['balances']
            if Decimal(asset['free']) > 0
        }

    async def get_ticker(self, symbol: str) -> Dict:
        endpoint = "/api/v3/ticker/24hr"
        params = {'symbol': symbol}
        return await self._signed_request("GET", endpoint, **params)

    async def create_order(self, symbol: str, side: str, type: str,
                         amount: Decimal, price: Optional[Decimal] = None) -> Dict:
        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': type.upper(),
            'quantity': str(amount),
        }
        if price:
            params['price'] = str(price)
            params['timeInForce'] = 'GTC'
        
        return await self._signed_request("POST", endpoint, **params)

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        endpoint = "/api/v3/order"
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        try:
            await self._signed_request("DELETE", endpoint, **params)
            return True
        except ExchangeError:
            return False
        
    async def _signed_request(self, method: str, endpoint: str, **params):
        """Make authenticated API request with signature"""
        import hmac
        import hashlib
        import urllib.parse
        import time
        
        timestamp = int(time.time() * 1000)
        params['timestamp'] = timestamp
        
        # Create query string
        query_string = urllib.parse.urlencode(params)
        
        # Generate signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        if method == "GET":
            url = f"{url}?{query_string}&signature={signature}"
            async with self.session.get(url, headers=headers) as response:
                return await self._handle_response(response)
        else:
            async with self.session.post(url, headers=headers, data=params) as response:
                return await self._handle_response(response)
                
    async def _handle_response(self, response):
        """Handle API response and errors"""
        data = await response.json()
        if response.status != 200:
            raise ExchangeError(
                f"API request failed: {data.get('msg', 'Unknown error')}",
                code=data.get('code', -1)
            )
        return data