import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import importlib
binance_client = importlib.import_module('services.mcp.exchange-gateway.binance_client')
BinanceClient = binance_client.BinanceClient

class TestBinanceClient(unittest.TestCase):
    @patch('requests.Session')
    def setUp(self, mock_session):
        self.mock_session = mock_session.return_value
        self.client = BinanceClient(api_key="test_key", api_secret="test_secret")
        
    def test_get_balances(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'balances': [
                {'asset': 'BTC', 'free': '1.5'},
                {'asset': 'ETH', 'free': '10.0'}
            ]
        }
        self.mock_session.get.return_value = mock_response
        
        balances = self.client.get_balances()
        self.assertEqual(balances['BTC'], Decimal('1.5'))
        self.assertEqual(balances['ETH'], Decimal('10.0'))
        
    @patch.object(BinanceClient, '_generate_signature')
    def test_create_order(self, mock_signature):
        mock_signature.return_value = 'test_signature'
        mock_response = MagicMock()
        mock_response.json.return_value = {'orderId': '12345'}
        self.mock_session.post.return_value = mock_response
        
        order_id = self.client.create_order(
            symbol='BTCUSDT',
            side='BUY',
            quantity=Decimal('0.1'),
            price=Decimal('50000')
        )
        self.assertEqual(order_id, '12345')
        
    def test_get_ticker(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'symbol': 'BTCUSDT',
            'price': '50000.00'
        }
        self.mock_session.get.return_value = mock_response
        
        ticker = self.client.get_ticker('BTCUSDT')
        self.assertEqual(ticker['price'], '50000.00')

if __name__ == '__main__':
    unittest.main()