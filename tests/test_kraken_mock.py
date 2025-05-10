import pytest
from unittest.mock import MagicMock, patch
from utils.exchange_clients import KrakenClient

@pytest.fixture
def mock_client():
    """Fixture providing a mocked Kraken client"""
    with patch('utils.exchange_clients.KrakenClient') as mock:
        client = mock.return_value
        client.ping.return_value = True
        client.get_ticker.return_value = {
            'ask': 50123.45,
            'bid': 50100.00,
            'last': 50110.50
        }
        client.get_balances.return_value = {
            'USD': 10000.00,
            'BTC': 0.5
        }
        client.create_order.return_value = {
            'id': 'MOCK123',
            'status': 'open',
            'symbol': 'BTC/USD',
            'side': 'buy',
            'amount': 0.01,
            'price': 50000.00
        }
        client.cancel_order.return_value = True
        yield client

class TestKrakenMock:
    """Tests for mocked Kraken exchange interface"""

    def test_connectivity(self, mock_client):
        """Test mock API connectivity"""
        assert mock_client.ping() is True
        mock_client.ping.assert_called_once()

    def test_market_data(self, mock_client):
        """Test mock market data endpoints"""
        ticker = mock_client.get_ticker('BTC/USD')
        assert 'ask' in ticker
        assert 'bid' in ticker
        assert ticker['ask'] == 50123.45
        mock_client.get_ticker.assert_called_with('BTC/USD')

    def test_order_flow(self, mock_client):
        """Test mock order placement and cancellation"""
        order = mock_client.create_order(
            symbol='BTC/USD',
            side='buy',
            amount=0.01,
            price=50000,
            order_type='limit'
        )
        assert order['id'] == 'MOCK123'
        
        cancel_result = mock_client.cancel_order('MOCK123')
        assert cancel_result is True
        mock_client.cancel_order.assert_called_with('MOCK123')

    def test_balance_check(self, mock_client):
        """Test mock balance retrieval"""
        balances = mock_client.get_balances()
        assert balances['USD'] == 10000.00
        assert balances['BTC'] == 0.5
        mock_client.get_balances.assert_called_once()