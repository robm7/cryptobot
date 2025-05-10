import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from database.models import Trade
from api.routes import api_blueprint

@pytest.fixture
def sample_trades():
    return [
        Trade(
            id=1,
            symbol='BTC/USDT',
            quantity=0.1,
            price=50000,
            side='buy',
            timestamp=datetime.utcnow() - timedelta(days=1),
            is_backtest=False
        ),
        Trade(
            id=2,
            symbol='ETH/USDT', 
            quantity=1,
            price=3000,
            side='sell',
            timestamp=datetime.utcnow(),
            is_backtest=True
        )
    ]

class TestTradeEndpoints:
    def test_get_trades_no_filter(self, client, auth_headers, sample_trades):
        """Test GET /trades with no filters"""
        with patch('api.routes.Trade.query') as mock_query:
            mock_query.order_by.return_value.limit.return_value.all.return_value = sample_trades
            
            response = client.get('/api/trades', headers=auth_headers)
            
            assert response.status_code == 200
            assert len(response.json['data']) == 2
            assert response.json['count'] == 2

    def test_get_trades_with_filters(self, client, auth_headers, sample_trades):
        """Test GET /trades with symbol filter"""
        with patch('api.routes.Trade.query') as mock_query:
            mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_trades[0]]
            
            response = client.get('/api/trades?symbol=BTC/USDT', headers=auth_headers)
            
            assert response.status_code == 200
            assert len(response.json['data']) == 1
            assert response.json['data'][0]['symbol'] == 'BTC/USDT'

    def test_post_trade_valid(self, client, auth_headers):
        """Test POST /trades with valid data"""
        trade_data = {
            'symbol': 'BTC/USDT',
            'quantity': 0.1,
            'side': 'buy',
            'price': 50000
        }
        
        with patch('api.routes.execute_trade') as mock_execute:
            mock_execute.return_value = {'id': 1, 'status': 'filled'}
            
            response = client.post('/api/trades', 
                                json=trade_data,
                                headers=auth_headers)
            
            assert response.status_code == 200
            assert response.json['data']['id'] == 1

    def test_post_trade_missing_fields(self, client, auth_headers):
        """Test POST /trades with missing required fields"""
        response = client.post('/api/trades',
                            json={'symbol': 'BTC/USDT'},
                            headers=auth_headers)
        
        assert response.status_code == 400
        assert 'Missing required fields' in response.json['error']['message']