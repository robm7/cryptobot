import os
import pytest
from unittest.mock import patch
from utils.exchange_clients import KrakenClient

@pytest.mark.skipif(
    not os.getenv('KRAKEN_PAPER_API_KEY'),
    reason="Kraken paper trading credentials not configured"
)
class TestKrakenPaperTrading:
    """Tests for Kraken paper trading interface"""
    
    @pytest.fixture
    def client(self):
        return KrakenClient(
            api_key=os.getenv('KRAKEN_PAPER_API_KEY'),
            api_secret=os.getenv('KRAKEN_PAPER_API_SECRET'),
            paper_trading=True
        )

    def test_connectivity(self, client):
        """Test basic API connectivity"""
        assert client.ping() is True

    def test_market_data(self, client):
        """Test market data endpoints"""
        ticker = client.get_ticker('BTC/USD')
        assert 'ask' in ticker
        assert 'bid' in ticker
        assert isinstance(ticker['ask'], float)
        assert isinstance(ticker['bid'], float)

    def test_order_placement(self, client):
        """Test paper order placement"""
        order = client.create_order(
            symbol='BTC/USD',
            side='buy',
            amount=0.01,
            price=50000,
            order_type='limit'
        )
        assert 'id' in order
        assert order['status'] == 'open'

        # Verify order cancellation
        cancel_result = client.cancel_order(order['id'])
        assert cancel_result is True

    def test_balance_check(self, client):
        """Test paper balance retrieval"""
        balances = client.get_balances()
        assert isinstance(balances, dict)
        assert 'USD' in balances
        assert isinstance(balances['USD'], float)

@pytest.mark.skipif(
    os.getenv('KRAKEN_PAPER_API_KEY'),
    reason="Skipping mock tests when paper trading configured"
)
class TestKrakenMock:
    """Fallback mock tests when paper trading not configured"""
    
    @patch('utils.exchange_clients.KrakenClient')
    def test_mock_connectivity(self, mock_client):
        mock_client.return_value.ping.return_value = True
        client = KrakenClient('mock_key', 'mock_secret')
        assert client.ping() is True