import pytest
from unittest.mock import MagicMock

class TestKrakenMock:
    @pytest.fixture
    def mock_kraken(self):
        mock = MagicMock()
        mock.fetch_ticker.return_value = {
            'bid': 50000.0,
            'ask': 50001.0
        }
        mock.create_order.return_value = {
            'id': '12345',
            'symbol': 'BTC/USD',
            'status': 'open',
            'amount': 0.0001,
            'price': 45000.0
        }
        return mock

    def test_mock_order_placement(self, mock_kraken):
        # Test market data
        ticker = mock_kraken.fetch_ticker('BTC/USD')
        assert ticker['bid'] == 50000.0
        assert ticker['ask'] == 50001.0

        # Test order placement
        order = mock_kraken.create_order(
            symbol='BTC/USD',
            order_type='limit',
            side='buy',
            amount=0.0001,
            price=45000.0
        )
        assert order['id'] == '12345'
        assert order['status'] == 'open'
        assert float(order['amount']) == 0.0001