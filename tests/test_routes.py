import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import threading
import time
from multiprocessing import Lock

from database.models import Strategy, BacktestResult, Trade
from utils.backtest import Backtester # Assuming Backtester might be mocked

def test_get_trades(client, auth_headers):
    with patch('database.models.Trade') as mock_trade, \
         patch('api.routes.db.session') as mock_session:
        mock_trade.query.order_by.return_value.limit.return_value.all.return_value = []
        
        response = client.get('/api/trades', headers=auth_headers)
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'data' in response_data
        assert len(response_data['data']) == 0
        assert response_data['count'] == 0

def test_get_trades_with_filters(client, auth_headers):
    with patch('database.models.Trade') as mock_trade:
        # Mock trade data
        trades = [
            MagicMock(to_dict=lambda: {
                'symbol': 'BTC/USDT',
                'trade_type': 'buy',
                'amount': 1.0,
                'price': 50000,
                'timestamp': '2025-01-01T00:00:00'
            }),
            MagicMock(to_dict=lambda: {
                'symbol': 'ETH/USDT',
                'trade_type': 'sell',
                'amount': 2.0,
                'price': 3000,
                'timestamp': '2025-01-02T00:00:00'
            }),
            MagicMock(to_dict=lambda: {
                'symbol': 'BTC/USDT',
                'trade_type': 'sell',
                'amount': 0.5,
                'price': 51000,
                'timestamp': '2025-01-03T00:00:00'
            })
        ]

        # Setup mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # Test cases
        test_cases = [
            ('symbol=BTC/USDT', [trades[0], trades[2]]),
            ('trade_type=sell', [trades[1], trades[2]]),
            ('symbol=BTC/USDT&trade_type=buy', [trades[0]]),
            ('limit=1', [trades[0]]),
            ('is_backtest=true', [trades[0], trades[1], trades[2]])
        ]

        for query, expected_trades in test_cases:
            mock_query.all.return_value = expected_trades
            response = client.get(f'/api/trades?{query}', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json
            assert 'data' in data
            assert len(data['data']) == len(expected_trades)
            assert data['count'] == len(expected_trades)
            
            # Verify filters were applied correctly
            if 'symbol=' in query:
                assert all(t['symbol'] == 'BTC/USDT' for t in data['data'])
            if 'trade_type=' in query:
                assert all(t['trade_type'] == 'sell' for t in data['data'])
            if 'limit=' in query:
                assert len(data['data']) == 1

def test_create_trade(client, auth_headers):
    """Test successful trade creation"""
    with patch('api.routes.db.session') as mock_session:
        with client.application.app_context():
            test_data = {
            'symbol': 'BTC/USDT',
            'quantity': '1.0',
            'side': 'buy'
        }
        
            response = client.post(
                '/api/trades',
                json=test_data,
                headers=auth_headers
            )
            assert response.status_code == 201
            assert response.json['success'] == True
            assert 'data' in response.json

def test_create_trade_validation(client, auth_headers):
    """Test trade validation scenarios"""
    test_cases = [
        # Symbol validation
        ({'symbol': 'BTCUSDT', 'quantity': '1.0', 'side': 'buy'}, "Invalid symbol format"),
        ({'symbol': '', 'quantity': '1.0', 'side': 'buy'}, "Invalid symbol format"),
        ({'symbol': 'BTC/', 'quantity': '1.0', 'side': 'buy'}, "Invalid symbol format"),
        
        # Quantity validation
        ({'symbol': 'BTC/USDT', 'quantity': '0', 'side': 'buy'}, "Quantity must be positive"),
        ({'symbol': 'BTC/USDT', 'quantity': '-1', 'side': 'buy'}, "Quantity must be positive"),
        ({'symbol': 'BTC/USDT', 'quantity': 'invalid', 'side': 'buy'}, "Invalid quantity"),
        
        # Side validation
        ({'symbol': 'BTC/USDT', 'quantity': '1.0', 'side': 'invalid'}, "Invalid side"),
        ({'symbol': 'BTC/USDT', 'quantity': '1.0', 'side': ''}, "Invalid side"),
        
        # Missing fields
        ({'quantity': '1.0', 'side': 'buy'}, "Missing required fields"),
        ({'symbol': 'BTC/USDT', 'side': 'buy'}, "Missing required fields"),
        ({'symbol': 'BTC/USDT', 'quantity': '1.0'}, "Missing required fields"),
        
        # Edge cases
        ({'symbol': 'BTC/USDT', 'quantity': '1e-8', 'side': 'buy'}, None),  # Very small quantity
        ({'symbol': 'BTC/USDT', 'quantity': '1000000', 'side': 'sell'}, None)  # Large quantity
    ]
    
    for data, expected_error in test_cases:
        response = client.post(
            '/api/trades',
            json=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        error_data = response.json['error']
        assert isinstance(error_data, dict)
        assert 'message' in error_data
        assert expected_error.lower() in str(error_data['message']).lower()

def test_get_strategies(client, auth_headers):
    """Test GET /api/strategies endpoint"""
    with patch('database.models.Strategy') as mock_strategy:
        # Setup mock strategy data
        strategy1 = MagicMock()
        strategy1.id = 1
        strategy1.name = "Breakout and Reset"
        strategy1.description = "Breakout strategy"
        strategy1.parameters = '{"lookback": 14, "threshold": 0.02}'
        strategy1.created_at = datetime(2025, 1, 1)
        strategy1.updated_at = datetime(2025, 1, 2)
        strategy1.user_id = 1  # Match the mocked JWT identity
        strategy1.to_dict.return_value = {
            'id': 1,
            'name': "Breakout and Reset",
            'description': "Breakout strategy",
            'parameters': {"lookback": 14, "threshold": 0.02},
            'created_at': "2025-01-01T00:00:00",
            'updated_at': "2025-01-02T00:00:00",
            'user_id': 1
        }
        
        strategy2 = MagicMock()
        strategy2.id = 2
        strategy2.name = "Mean Reversion"
        strategy2.description = "Mean reversion strategy"
        strategy2.parameters = '{"period": 20, "deviation": 2.0}'
        strategy2.created_at = datetime(2025, 1, 3)
        strategy2.updated_at = datetime(2025, 1, 4)
        strategy2.user_id = 1  # Match the mocked JWT identity
        strategy2.to_dict.return_value = {
            'id': 2,
            'name': "Mean Reversion",
            'description': "Mean reversion strategy",
            'parameters': {"period": 20, "deviation": 2.0},
            'created_at': "2025-01-03T00:00:00",
            'updated_at': "2025-01-04T00:00:00",
            'user_id': 1
        }
        
        # Mock query to return our test strategies
        mock_strategy.query.filter_by.return_value.all.return_value = [strategy1, strategy2]
        print(f"Mock strategies: {mock_strategy.query.filter_by.return_value.all.return_value}")  # Debug mock data

        # Mock current_user from JWT and test the first route implementation
        with patch('api.routes.get_jwt_identity', return_value=1), \
             patch('api.routes.Strategy', mock_strategy):
            response = client.get('/api/strategies', headers=auth_headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        print(f"Response data: {data}")  # Debug output

        # Verify response structure and data
        assert 'data' in data, "Response should contain 'data' field"
        strategies = data['data']
        assert len(strategies) == 2, f"Expected 2 strategies, got {len(strategies)}"
        assert strategies[0]['id'] == 1, f"First strategy should have id=1, got {strategies[0]['id'] if strategies else 'empty'}"
        assert strategies[0]['name'] == "Breakout and Reset"
        assert strategies[0]['description'] == "Breakout strategy"
        assert strategies[0]['parameters'] == {"lookback": 14, "threshold": 0.02}
        assert strategies[0]['created_at'] == "2025-01-01T00:00:00"
        assert strategies[0]['updated_at'] == "2025-01-02T00:00:00"
        
        assert strategies[1]['id'] == 2
        assert strategies[1]['name'] == "Mean Reversion"
        assert strategies[1]['description'] == "Mean reversion strategy"
        assert strategies[1]['parameters'] == {"period": 20, "deviation": 2.0}
        assert strategies[1]['created_at'] == "2025-01-03T00:00:00"
        assert strategies[1]['updated_at'] == "2025-01-04T00:00:00"

def test_get_strategies_unauthorized(client):
    """Test GET /api/strategies without auth"""
    response = client.get('/api/strategies')
    assert response.status_code == 401
    assert isinstance(response.json, dict)
    assert 'error' in response.json
    assert response.json['error']['message'] == 'Authorization required'

def test_get_strategy(client, auth_headers):
    """Test GET /api/strategies/<id> endpoint"""
    with patch('database.models.Strategy') as mock_strategy, \
         patch('auth.auth_service.verify_token') as mock_verify:
        # Setup mock strategy
        strategy = MagicMock()
        strategy.id = 1
        strategy.name = "Test Strategy"
        strategy.description = "Test description"
        strategy.parameters = '{"param1": "value1"}'
        strategy.created_at = datetime(2025, 1, 1)
        strategy.updated_at = datetime(2025, 1, 2)
        strategy.to_dict.return_value = {
            'id': 1,
            'name': "Test Strategy",
            'description': "Test description",
            'parameters': {'param1': 'value1'},
            'created_at': '2025-01-01T00:00:00',
            'updated_at': '2025-01-02T00:00:00'
        }

        # Mock auth verification
        mock_verify.return_value = {'user_id': 1}

        # Mock query to return our test strategy
        mock_strategy.query.get.return_value = strategy

        response = client.get('/api/strategies/1', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'data' in data
        assert data['data']['name'] == "Test Strategy"
        assert data['description'] == "Test description"
        assert data['parameters'] == {"param1": "value1"}
        assert data['created_at'] == "2025-01-01T00:00:00"
        assert data['updated_at'] == "2025-01-02T00:00:00"

def test_get_strategy_not_found(client, auth_headers):
    """Test GET /api/strategies/<id> with invalid ID"""
    with patch('database.models.Strategy') as mock_strategy:
        mock_strategy.query.get.return_value = None

        response = client.get('/api/strategies/999', headers=auth_headers)
        assert response.status_code == 404
        assert 'error' in response.json
        assert 'not found' in response.json['error']['message'].lower()

def test_get_strategy_unauthorized(client):
    """Test GET /api/strategies/<id> without auth"""
    response = client.get('/api/strategies/1')
    assert response.status_code == 401
    assert isinstance(response.json, dict)
    assert 'error' in response.json
    assert 'Authorization required' in response.json['error']['message']

def test_create_strategy(client, auth_headers):
    """Test successful strategy creation"""
    with patch('api.routes.db.session') as mock_session, \
         patch('database.models.Strategy') as mock_strategy:
        # Setup test data
        test_data = {
            'name': 'New Strategy',
            'parameters': {
                'param1': 'value1',
                'param2': 42
            }
        }

        # Mock strategy creation
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.id = 1
        mock_strategy_instance.to_dict.return_value = {
            'id': 1,
            'name': test_data['name'],
            'parameters': test_data['parameters']
        }
        mock_strategy.return_value = mock_strategy_instance

        # Make request
        response = client.post(
            '/api/strategies',
            json=test_data,
            headers=auth_headers
        )

        # Verify response
        assert response.status_code == 201
        assert 'data' in response.json
        assert response.json['data']['name'] == test_data['name']
        assert 'data' in response.json
        assert response.json['success'] == True
        
        # Verify strategy was created with correct params
        mock_strategy.assert_called_once_with(
            name='New Strategy',
            parameters='{"param1": "value1", "param2": 42}',
            user_id=1  # From mocked auth headers
        )
        assert mock_session.add.called
        assert mock_session.commit.called

def test_create_strategy_validation(client, auth_headers):
    """Test strategy validation scenarios"""
    test_cases = [
        # Missing required fields
        ({'description': 'Test', 'parameters': {}}, "Missing required fields"),
        ({'name': 'Test', 'description': 'Test'}, "Missing required fields"),
        
        # Name validation
        ({'name': '', 'parameters': {}}, "Strategy name must be 1-100 characters"),
        ({'name': 'A'*101, 'parameters': {}}, "Strategy name must be 1-100 characters"),
        
        # Parameters validation
        ({'name': 'Test', 'parameters': 'invalid'}, "Parameters must be a JSON object"),
        ({'name': 'Test', 'parameters': []}, "Parameters must be a JSON object"),
        ({'name': 'Test', 'parameters': {}}, "Parameters cannot be empty"),
        
        # Edge cases
        ({'name': 'Test', 'parameters': None}, "Invalid parameters format"),
        ({'name': 'Test', 'parameters': 123}, "Parameters must be a JSON object")
    ]
    
    for data, expected_error in test_cases:
        response = client.post(
            '/api/strategies',
            json=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        error_data = response.json
        assert isinstance(error_data, dict)
        assert 'error' in error_data
        assert expected_error.lower() in str(error_data['error']['message']).lower()

def test_create_strategy_unauthorized(client):
    """Test POST /api/strategies without auth"""
    response = client.post('/api/strategies', json={'name': 'Test'})
    assert response.status_code == 401
    assert isinstance(response.json, dict)
    assert 'error' in response.json
    assert 'Authorization required' in response.json['error']
def test_get_strategy_backtests(client, auth_headers):
    """Test GET /api/strategies/<id>/backtests"""
    with patch('database.models.BacktestResult') as mock_backtest:
        with client.application.app_context():
            # Mock backtest data
            backtests = [
            MagicMock(to_dict=lambda: {
                'id': 1,
                'strategy_id': 1,
                'results': {'profit': 100},
                'created_at': '2025-01-01T00:00:00'
            }),
            MagicMock(to_dict=lambda: {
                'id': 2,
                'strategy_id': 1,
                'results': {'profit': -50},
                'created_at': '2025-01-02T00:00:00'
            })
        ]

        # Setup mock query
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.all.return_value = backtests
        mock_backtest.query = mock_query

        # Test successful case
        response = client.get('/api/strategies/1/backtests', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'data' in data
        assert len(data['data']) == 2
        assert all(isinstance(b, dict) for b in data['data'])

        # Test empty results
        mock_query.all.return_value = []
        response = client.get('/api/strategies/999/backtests', headers=auth_headers)
        assert response.status_code == 200
        assert response.json == {'data': [], 'success': True}

        # Test error handling
        with patch('api.routes.BacktestResult.query') as mock_query_error:
            mock_query_error.filter_by.side_effect = Exception('DB error')
            response = client.get('/api/strategies/1/backtests', headers=auth_headers)
            assert response.status_code == 500
            assert 'error' in response.json
            assert 'DB error' in response.json['error']['message']
def test_strategy_factory(client, auth_headers):
    """Test POST /api/strategies/factory"""
    with patch('database.models.Strategy') as mock_strategy:
        # Mock strategy data with proper serialization
        mock_strategy_instance = MagicMock(
            id=1,
            name="Test Strategy",
            parameters='{"param1": "value1"}',
            to_dict=lambda: {
                'id': 1,
                'name': "Test Strategy",
                'parameters': {'param1': 'value1'}
            }
        )

        # Mock query response
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = mock_strategy_instance
        mock_strategy.query = mock_query

        # Test successful case
        response = client.post(
            '/api/strategies/factory',
            json={'strategy_id': 1},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert 'data' in response.json
        assert 'instance' in response.json['data']
        assert 'parameters' in response.json['data']
        assert response.json['success'] == True
        
        # Test missing strategy_id
        response = client.post(
            '/api/strategies/factory',
            json={},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert response.json == {'message': 'Missing strategy_id'}
        
        # Test invalid strategy_id
        mock_query.first.return_value = None
        response = client.post(
            '/api/strategies/factory',
            json={'strategy_id': 999},
            headers=auth_headers
        )
        assert response.status_code == 404
        assert response.json == {'message': 'Strategy not found'}
        
        # Test error handling
        with patch('api.routes.Strategy.query') as mock_query_error:
            mock_query_error.filter_by.side_effect = Exception('DB error')
            response = client.post(
                '/api/strategies/factory',
                json={'strategy_id': 1},
                headers=auth_headers
            )
            assert response.status_code == 500
            assert response.json == {'message': 'Failed to create strategy instance'}

def test_strategy_factory_edge_cases(client, auth_headers):
    """Test edge cases for strategy factory parameters"""
    test_cases = [
        # Invalid parameter types
        ({'strategy_id': 'invalid'}, "Invalid strategy_id format"),
        ({'strategy_id': -1}, "Invalid strategy_id format"),
        ({'strategy_id': 0}, "Invalid strategy_id format"),
        
        # Missing required fields
        ({}, "Missing strategy_id"),
        
        # Invalid JSON payload
        ('invalid', "Invalid JSON payload"),
    ]

    for data, expected_error in test_cases:
        response = client.post(
            '/api/strategies/factory',
            json=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert expected_error.lower() in str(response.json.get('message', '')).lower()

def test_strategy_factory_parameter_validation(client, auth_headers):
    """Test parameter validation for different strategy types"""
    with patch('database.models.Strategy') as mock_strategy:
        # Test Breakout and Reset strategy validation
        mock_breakout = MagicMock(
            id=1,
            name="Breakout and Reset",
            parameters=json.dumps({
                'period': 14,
                'threshold': 0.02,
                'risk_management': {
                    'stop_loss_pct': 2.0,
                    'take_profit_pct': 3.0
                }
            })
        )
        
        # Test Mean Reversion strategy validation
        mock_mean_reversion = MagicMock(
            id=2,
            name="Mean Reversion",
            parameters=json.dumps({
                'lookback': 20,
                'entry_z': 2.0,
                'risk_management': {
                    'position_sizing_method': 'percent_risk',
                    'risk_per_trade_pct': 1.0
                }
            })
        )
        
        # Test invalid strategy type
        mock_invalid = MagicMock(
            id=3,
            name="Invalid Strategy",
            parameters=json.dumps({'param': 'value'})
        )
        
        test_cases = [
            (mock_breakout, {'strategy_id': 1}, None),
            (mock_mean_reversion, {'strategy_id': 2}, None),
            (mock_invalid, {'strategy_id': 3}, "Unsupported strategy type"),
            
            # Test boundary values
            (MagicMock(
                id=4,
                name="Breakout and Reset",
                parameters=json.dumps({'period': 9, 'threshold': 0.09})  # Below min period
            ), {'strategy_id': 4}, "Period must be between 10-50"),
            
            (MagicMock(
                id=5,
                name="Mean Reversion",
                parameters=json.dumps({'lookback': 4, 'entry_z': 0.4})  # Below min values
            ), {'strategy_id': 5}, "Lookback must be between 5-100"),
        ]
        
        for mock_strat, data, expected_error in test_cases:
            mock_strategy.query.filter_by.return_value.first.return_value = mock_strat
            
            response = client.post(
                '/api/strategies/factory',
                json=data,
                headers=auth_headers
            )
            
            if expected_error:
                assert response.status_code == 400
                assert expected_error.lower() in str(response.json.get('message', '')).lower()
            else:
                assert response.status_code == 200
                assert 'data' in response.json

def test_concurrent_strategy_creation(client, auth_headers):
    """Test concurrent strategy creation scenarios"""
    with patch('database.models.Strategy') as mock_strategy:
        # Setup mock strategy that will be accessed concurrently
        mock_strategy_instance = MagicMock(
            id=1,
            name="Test Strategy",
            parameters='{"param1": "value1"}'
        )
        
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance
        
        # Simulate concurrent requests
        def make_request():
            return client.post(
                '/api/strategies/factory',
                json={'strategy_id': 1},
                headers=auth_headers
            )
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
            
            # Verify all requests completed successfully
            for result in results:
                assert result.status_code == 200
                assert 'data' in result.json

def test_strategy_factory_error_scenarios(client, auth_headers):
    """Test comprehensive error scenarios for strategy factory"""
    with patch('database.models.Strategy') as mock_strategy:
        # Test database connection error
        with patch('api.routes.Strategy.query') as mock_query:
            mock_query.filter_by.side_effect = Exception('Database connection error')
            response = client.post(
                '/api/strategies/factory',
                json={'strategy_id': 1},
                headers=auth_headers
            )
            assert response.status_code == 500
            assert 'Database connection error' in str(response.json)
        
        # Test invalid parameters JSON
        mock_strategy_instance = MagicMock(
            id=1,
            name="Test Strategy",
            parameters='invalid json'
        )
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance
        
        response = client.post(
            '/api/strategies/factory',
            json={'strategy_id': 1},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert 'Invalid parameters format' in str(response.json)
        
        # Test unauthorized access
        mock_strategy_instance = MagicMock(
            id=1,
            name="Test Strategy",
            parameters='{"param1": "value1"}',
            user_id=2  # Different from current user
        )
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance
        
        response = client.post(
            '/api/strategies/factory',
            json={'strategy_id': 1},
            headers=auth_headers
        )
        assert response.status_code == 403
        assert 'Forbidden' in str(response.json)

def test_backtest_run_success(client, auth_headers):
    """Test successful backtest run with optional parameters"""
    with patch('api.routes.Strategy') as mock_strategy, \
         patch('api.routes.StrategyFactory.create_strategy') as mock_create_strategy, \
         patch('api.routes.Backtester') as mock_backtester_cls:
        
        # Mock Strategy DB record
        mock_strategy_instance_db = MagicMock()
        mock_strategy_instance_db.id = 1
        mock_strategy_instance_db.user_id = 1 # Matches JWT identity
        mock_strategy_instance_db.name = 'TestStrategy'
        mock_strategy_instance_db.parameters = {'param': 'value'}
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance_db

        # Mock Strategy object creation
        mock_strategy_obj = MagicMock()
        mock_create_strategy.return_value = mock_strategy_obj

        # Mock Backtester instance and its result
        mock_backtester_instance = MagicMock()
        mock_backtester_instance.run_backtest.return_value = {
            'total_return': 0.15, # 15%
            'sharpe': 1.5,
            'max_drawdown': 0.05, # 5%
            'win_rate': 0.60, # 60%
            'total_trades': 25,
            'portfolio': pd.DataFrame({'timestamp': pd.to_datetime(['2025-01-01', '2025-01-31']), 'value': [10000, 11500]}),
            'trades': pd.DataFrame({'type': ['buy'], 'price': [50000]})
        }
        mock_backtester_cls.return_value = mock_backtester_instance
        
        # Test data including optional risk params
        test_data = {
            'strategy_id': 1,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000,
            'risk_per_trade_pct': 0.01, # Optional: 1%
            'max_drawdown_pct': 0.15,  # Optional: 15%
            'position_size_pct': 0.8    # Optional: 80%
        }
        
        response = client.post(
            '/api/backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json['success'] == True
        assert 'data' in response.json
        # Check if backtester was called with correct params
        mock_backtester_cls.assert_called_once_with(
            strategy=mock_strategy_obj,
            symbol='BTC/USDT',
            timeframe='1h',
            start_date='2025-01-01',
            end_date='2025-01-31',
            initial_capital=10000.0,
            risk_per_trade_pct=0.01,
            max_drawdown_pct=0.15,
            position_size_pct=0.8
        )
        mock_backtester_instance.run_backtest.assert_called_once()
        # Check response data structure
        assert 'total_return' in response.json['data']
        assert 'sharpe_ratio' in response.json['data']
        assert 'max_drawdown' in response.json['data']
        assert 'equity_curve' in response.json['data']
        assert response.json['data']['total_return'] == 0.15

def test_backtest_run_missing_fields(client, auth_headers):
    """Test backtest with missing required fields"""
    required_fields = ['strategy_id', 'symbol', 'timeframe', 'start_date', 'end_date', 'initial_capital']
    
    # Test each missing field individually
    for field in required_fields:
        test_data = {
            'strategy_id': 1,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000
        }
        del test_data[field]
        
        response = client.post(
            '/api/backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert 'Missing required fields' in response.json['error']['message']

def test_backtest_run_invalid_strategy(client, auth_headers):
    """Test backtest with invalid strategy ID"""
    with patch('api.routes.Strategy') as mock_strategy:
        mock_strategy.query.filter_by.return_value.first.return_value = None
        
        test_data = {
            'strategy_id': 999,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000
        }
        
        response = client.post(
            '/api/backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert 'Strategy not found' in response.json['error']['message']

def test_backtest_run_unauthorized(client):
    """Test backtest without authentication"""
    test_data = {
        'strategy_id': 1,
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'start_date': '2025-01-01',
        'end_date': '2025-01-31',
        'initial_capital': 10000
    }
    
    response = client.post('/api/backtest', json=test_data)
    assert response.status_code == 401
    assert 'Authorization required' in response.json['error']['message']

def test_backtest_run_wrong_owner(client, auth_headers):
    """Test backtest with strategy belonging to another user"""
    with patch('api.routes.Strategy') as mock_strategy:
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.id = 1
        mock_strategy_instance.user_id = 2  # Different from mocked JWT identity (1)
        
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance
        
        test_data = {
            'strategy_id': 1,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000
        }
        
        response = client.post(
            '/api/backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403
        assert 'strategy belongs to another user' in response.json['error']['message']

def test_backtest_run_invalid_dates(client, auth_headers):
    """Test backtest with invalid date ranges"""
    test_cases = [
        {'start_date': 'invalid-date', 'end_date': '2025-01-31'},
        {'start_date': '2025-01-01', 'end_date': 'invalid-date'},
        {'start_date': '2025-01-31', 'end_date': '2025-01-01'},  # End before start
        {'start_date': '2025-01-01', 'end_date': '2025-01-01'}   # Same date
    ]
    
    for date_case in test_cases:
        test_data = {
            'strategy_id': 1,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': date_case['start_date'],
            'end_date': date_case['end_date'],
            'initial_capital': 10000
        }
        
        response = client.post(
            '/api/backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert 'Invalid date' in response.json['error']['message']

def test_backtest_run_server_error(client, auth_headers):
    """Test backtest with server error"""
    with patch('api.routes.Strategy') as mock_strategy:
        mock_strategy.query.filter_by.side_effect = Exception('DB error')
        
        test_data = {
            'strategy_id': 1,
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000
        }
        
        response = client.post(
            '/api/backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 500
        assert 'Failed to run backtest' in response.json['error']['message']
def test_save_backtest_success(client, auth_headers):
    """Test successful backtest save"""
    with patch('api.routes.db.session') as mock_session, \
         patch('api.routes.Strategy') as mock_strategy, \
         patch('api.routes.BacktestResult') as mock_backtest:
        
        # Setup test data
        test_data = {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000,
            'final_capital': 12000,
            'return_pct': 20,
            'total_trades': 10,
            'win_rate': 60,
            'strategy_parameters': {'param1': 'value1'},
            'trades': [
                {
                    'trade_type': 'buy',
                    'amount': 1.0,
                    'price': 50000,
                    'timestamp': '2025-01-01 12:00:00',
                    'profit_loss': 1000
                }
            ]
        }

        # Mock strategy query
        mock_strategy.query.filter_by.return_value.scalar_one_or_none.return_value = MagicMock(id=1)

        # Mock backtest result
        mock_backtest.return_value = MagicMock(id=1)

        response = client.post(
            '/api/save-backtest',
            json=test_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        assert 'data' in response.json
        assert response.json['data']['backtest_id'] == 1
        assert mock_session.add.call_count == 2  # Backtest + Trade
        assert mock_session.commit.called

def test_save_backtest_missing_fields(client, auth_headers):
    """Test backtest save with missing required fields"""
    required_fields = [
        'symbol', 'timeframe', 'start_date', 'end_date',
        'initial_capital', 'final_capital', 'return_pct',
        'total_trades', 'win_rate', 'strategy_parameters', 'trades'
    ]
    
    # Test each missing field
    for field in required_fields:
        test_data = {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000,
            'final_capital': 12000,
            'return_pct': 20,
            'total_trades': 10,
            'win_rate': 60,
            'strategy_parameters': {'param1': 'value1'},
            'trades': [
                {
                    'trade_type': 'buy',
                    'amount': 1.0,
                    'price': 50000,
                    'timestamp': '2025-01-01 12:00:00',
                    'profit_loss': 1000
                }
            ]
        }
        del test_data[field]
        
        response = client.post(
            '/api/save-backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert 'Missing required fields' in response.json['error']['message']

def test_save_backtest_invalid_trades(client, auth_headers):
    """Test backtest save with invalid trade data"""
    test_cases = [
        # Missing trade_type
        ([{'amount': 1.0, 'price': 50000}], "Missing required trade fields"),
        # Invalid trade_type
        ([{'trade_type': 'invalid', 'amount': 1.0, 'price': 50000}], "Invalid trade_type"),
        # Negative amount
        ([{'trade_type': 'buy', 'amount': -1.0, 'price': 50000}], "Invalid amount"),
        # Zero price
        ([{'trade_type': 'buy', 'amount': 1.0, 'price': 0}], "Invalid price"),
        # Missing timestamp
        ([{'trade_type': 'buy', 'amount': 1.0, 'price': 50000}], "Missing timestamp"),
        # Invalid timestamp format
        ([{'trade_type': 'buy', 'amount': 1.0, 'price': 50000, 'timestamp': 'invalid'}], "Invalid timestamp format")
    ]
    
    for trades, expected_error in test_cases:
        test_data = {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000,
            'final_capital': 12000,
            'return_pct': 20,
            'total_trades': 10,
            'win_rate': 60,
            'strategy_parameters': {'param1': 'value1'},
            'trades': trades
        }
        
        response = client.post(
            '/api/save-backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert expected_error.lower() in str(response.json['error']['message']).lower()

def test_save_backtest_db_error(client, auth_headers):
    """Test backtest save with database error"""
    with patch('api.routes.db.session.commit', side_effect=Exception('DB error')):
        test_data = {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'start_date': '2025-01-01',
            'end_date': '2025-01-31',
            'initial_capital': 10000,
            'final_capital': 12000,
            'return_pct': 20,
            'total_trades': 10,
            'win_rate': 60,
            'strategy_parameters': {'param1': 'value1'},
            'trades': [
                {
                    'trade_type': 'buy',
                    'amount': 1.0,
                    'price': 50000,
                    'timestamp': '2025-01-01 12:00:00',
                    'profit_loss': 1000
                }
            ]
        }
        
        response = client.post(
            '/api/save-backtest',
            json=test_data,
            headers=auth_headers
        )
        
        assert response.status_code == 500
        assert 'Failed to save backtest' in response.json['error']['message']

def test_save_backtest_unauthorized(client):
    """Test backtest save without authentication"""
    response = client.post('/api/save-backtest', json={})
    assert response.status_code == 401
    assert 'Authorization required' in response.json['error']['message']
def test_auth_login_success(client):
    """Test successful authentication"""
    with patch('api.routes.create_access_token') as mock_access, \
         patch('api.routes.create_refresh_token') as mock_refresh:
        
        mock_access.return_value = 'test_access_token'
        mock_refresh.return_value = 'test_refresh_token'
        
        test_data = {'username': 'testuser', 'password': 'testpass'}
        response = client.post('/api/auth/login', json=test_data)
        
        assert response.status_code == 200
        assert 'data' in response.json
        assert response.json['data']['access_token'] == 'test_access_token'
        assert response.json['data']['refresh_token'] == 'test_refresh_token'

def test_auth_login_missing_fields():
    """Test auth login with missing fields"""
    test_cases = [
        ({}, "Missing username or password"),
        ({'username': 'testuser'}, "Missing username or password"),
        ({'password': 'testpass'}, "Missing username or password")
    ]
    
    for data, expected_error in test_cases:
        response = client.post('/api/auth/login', json=data)
        assert response.status_code == 400
        assert expected_error in response.json['error']['message']

def test_auth_login_invalid_credentials():
    """Test auth login with invalid credentials"""
    with patch('auth.auth_service.authenticate_user', return_value=None):
        test_data = {'username': 'invalid', 'password': 'invalid'}
        response = client.post('/api/auth/login', json=test_data)
        
        assert response.status_code == 401
        assert 'Invalid credentials' in response.json['error']['message']

def test_auth_login_server_error():
    """Test auth login with server error"""
    with patch('auth.auth_service.authenticate_user', side_effect=Exception('DB error')):
        test_data = {'username': 'testuser', 'password': 'testpass'}
        response = client.post('/api/auth/login', json=test_data)
        
        assert response.status_code == 500
        assert 'Login failed' in response.json['error']['message']
def test_strategy_parameters_edge_cases(client, auth_headers):
    """Test edge cases for strategy parameter validation"""
    test_cases = [
        # Breakout and Reset strategy
        ({
            'name': 'Breakout and Reset',
            'parameters': {'period': 9, 'threshold': 0.09}  # Minimum valid values
        }, None),
        ({
            'name': 'Breakout and Reset', 
            'parameters': {'period': 51, 'threshold': 1.01}  # Above max values
        }, "Invalid parameters"),
        ({
            'name': 'Breakout and Reset',
            'parameters': {'period': 14}  # Missing threshold
        }, "Missing required parameters"),
        
        # Mean Reversion strategy
        ({
            'name': 'Mean Reversion',
            'parameters': {'lookback': 4, 'entry_z': 0.49}  # Below min values
        }, "Invalid parameters"),
        ({
            'name': 'Mean Reversion',
            'parameters': {'lookback': 101, 'entry_z': 3.01}  # Above max values
        }, "Invalid parameters"),
        ({
            'name': 'Mean Reversion',
            'parameters': {'entry_z': 1.5}  # Missing lookback
        }, "Missing required parameters"),
        
        # Extreme values
        ({
            'name': 'Breakout and Reset',
            'parameters': {'period': 1000, 'threshold': 1000}
        }, "Invalid parameters"),
        ({
            'name': 'Mean Reversion',
            'parameters': {'lookback': -10, 'entry_z': -5}
        }, "Invalid parameters"),
        
        # Invalid parameter types
        ({
            'name': 'Breakout and Reset',
            'parameters': {'period': 'invalid', 'threshold': 'invalid'}
        }, "Invalid parameters"),
        ({
            'name': 'Mean Reversion',
            'parameters': {'lookback': None, 'entry_z': None}
        }, "Invalid parameters")
    ]
    
    for data, expected_error in test_cases:
        response = client.post(
            '/api/strategies',
            json=data,
            headers=auth_headers
        )
        
        if expected_error:
            assert response.status_code == 400
            assert expected_error.lower() in str(response.json['error']['message']).lower()
        else:
            assert response.status_code == 201

def test_trade_execution_edge_cases(client, auth_headers):
    """Test edge cases for trade execution"""
    test_cases = [
        # Very small quantities
        ({'symbol': 'BTC/USDT', 'quantity': '0.00000001', 'side': 'buy'}, None),
        # Very large quantities
        ({'symbol': 'BTC/USDT', 'quantity': '1000000000', 'side': 'sell'}, None),
        # Extremely large quantity
        ({'symbol': 'BTC/USDT', 'quantity': '1000000000000', 'side': 'sell'}, None),
        # Different symbol formats
        ({'symbol': 'BTC-USD', 'quantity': '1', 'side': 'buy'}, None),
        ({'symbol': 'BTC_USDT', 'quantity': '1', 'side': 'buy'}, None),
        # Exotic symbols
        ({'symbol': 'XRP/BTC', 'quantity': '100', 'side': 'buy'}, None),
        ({'symbol': 'SHIB/USDT', 'quantity': '1000000', 'side': 'buy'}, None),
        ({'symbol': 'BTC/DAI', 'quantity': '1', 'side': 'sell'}, None),
        # Mixed case side
        ({'symbol': 'BTC/USDT', 'quantity': '1', 'side': 'BuY'}, None),
        ({'symbol': 'BTC/USDT', 'quantity': '1', 'side': 'SeLl'}, None),
        # Symbols with different quote currencies
        ({'symbol': 'ETH/BTC', 'quantity': '0.1', 'side': 'buy'}, None),
        ({'symbol': 'SOL/ETH', 'quantity': '10', 'side': 'sell'}, None)
    ]
    
    with patch('api.routes.db.session'):
        for data, expected_error in test_cases:
            response = client.post(
                '/api/trades',
                json=data,
                headers=auth_headers
            )
            
            if expected_error:
                assert response.status_code == 400
                assert isinstance(response.json, dict)
                assert 'error' in response.json
            else:
                assert response.status_code == 201
                assert response.json['success'] == True

def test_concurrent_trade_execution(client, auth_headers):
    """Test concurrent trade execution scenarios"""
    test_data = {'symbol': 'BTC/USDT', 'quantity': '1', 'side': 'buy'}
    
    def make_request():
        with patch('api.routes.db.session'):
            response = client.post(
                '/api/trades',
                json=test_data,
                headers=auth_headers
            )
            return response.status_code
    
    # Simulate concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request) for _ in range(10)]
        results = [f.result() for f in futures]
    
    # Should all succeed with proper locking
    assert all(code == 201 for code in results)
    assert len(set(results)) == 1  # All same status

def test_trade_execution_unauthorized(client):
    """Test trade execution with invalid/missing authentication"""
    test_data = {'symbol': 'BTC/USDT', 'quantity': '1', 'side': 'buy'}
    
    # No auth headers
    response = client.post('/api/trades', json=test_data)
    assert response.status_code == 401
    assert 'Authorization required' in response.json['error']['message']
    
    # Invalid token
    response = client.post(
        '/api/trades',
        json=test_data,
        headers={'Authorization': 'Bearer invalid'}
    )
    assert response.status_code == 401
    assert 'Invalid token' in response.json['error']['message']
    
    # Expired token
    response = client.post(
        '/api/trades',
        json=test_data,
        headers={'Authorization': 'Bearer expired'}
    )
    assert response.status_code == 401
    assert 'Token expired' in response.json['error']['message']

def test_backtest_date_validation(client, auth_headers):
    """Test backtest date validation edge cases"""
    test_cases = [
        # Start date after end date
        ({'start_date': '2025-02-01', 'end_date': '2025-01-01'}, "Invalid date range"),
        # Same start and end date
        ({'start_date': '2025-01-01', 'end_date': '2025-01-01'}, None),
        # Far future dates
        ({'start_date': '2030-01-01', 'end_date': '2030-12-31'}, None),
        # Invalid date formats
        ({'start_date': 'invalid', 'end_date': 'invalid'}, "Invalid date format"),
        ({'start_date': '01-01-2025', 'end_date': '31-01-2025'}, "Invalid date format"),
        # Missing timezone info
        ({'start_date': '2025-01-01T00:00:00', 'end_date': '2025-01-31T00:00:00'}, None)
    ]
    
    base_data = {
        'strategy_id': 1,
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'initial_capital': 10000
    }
    
    with patch('api.routes.Strategy'):
        for date_data, expected_error in test_cases:
            test_data = {**base_data, **date_data}
            response = client.post(
                '/api/backtest',
                json=test_data,
                headers=auth_headers
            )
            
            if expected_error:
                assert response.status_code == 400
                assert expected_error.lower() in str(response.json['error']['message']).lower()
            else:
                assert response.status_code == 200

def test_backtest_invalid_parameters(client, auth_headers):
    """Test backtest with invalid strategy parameters"""
    test_cases = [
        # Invalid symbol
        ({'symbol': 'INVALID'}, "Invalid symbol format"),
        ({'symbol': ''}, "Invalid symbol format"),
        # Invalid timeframe
        ({'timeframe': 'invalid'}, "Invalid timeframe"),
        ({'timeframe': ''}, "Invalid timeframe"),
        # Missing required fields
        ({}, "Missing required field: strategy_id"),
        ({'strategy_id': 1}, "Missing required field: symbol"),
        ({'strategy_id': 1, 'symbol': 'BTC/USDT'}, "Missing required field: timeframe"),
        # Invalid strategy parameters
        ({'parameters': 'invalid'}, "Invalid parameters format"),
        ({'parameters': []}, "Invalid parameters format"),
        # Edge cases
        ({'strategy_id': 0}, "Invalid strategy ID"),
        ({'strategy_id': -1}, "Invalid strategy ID"),
        ({'strategy_id': 'invalid'}, "Invalid strategy ID")
    ]

    base_data = {
        'strategy_id': 1,
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'start_date': '2025-01-01',
        'end_date': '2025-01-02',
        'initial_capital': 10000
    }

    with patch('api.routes.Strategy'):
        for param_data, expected_error in test_cases:
            test_data = {**base_data, **param_data}
            response = client.post(
                '/api/backtest',
                json=test_data,
                headers=auth_headers
            )
            assert response.status_code == 400
            assert expected_error.lower() in str(response.json['error']['message']).lower()

def test_backtest_performance(client, auth_headers):
    """Test performance of large backtest runs"""
    with patch('api.routes.Strategy') as mock_strategy, \
         patch('api.routes.StrategyFactory.create_strategy') as mock_create_strategy, \
         patch('api.routes.Backtester') as mock_backtester_cls:
        
        # Mock Strategy DB record
        mock_strategy_instance_db = MagicMock()
        mock_strategy_instance_db.id = 1
        mock_strategy_instance_db.user_id = 1
        mock_strategy_instance_db.name = 'TestStrategy'
        mock_strategy_instance_db.parameters = {'param': 'value'}
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance_db

        # Mock Strategy object creation
        mock_strategy_obj = MagicMock()
        mock_create_strategy.return_value = mock_strategy_obj

        # Mock Backtester instance
        mock_backtester_instance = MagicMock()
        mock_backtester_cls.return_value = mock_backtester_instance

        # Test cases for different timeframes and date ranges
        test_cases = [
            # Large date range with small timeframe
            {
                'start_date': '2020-01-01',
                'end_date': '2025-01-01',
                'timeframe': '1m',
                'expected_calls': 5*365*24*60  # 5 years of 1-minute data
            },
            # Medium date range with medium timeframe
            {
                'start_date': '2024-01-01',
                'end_date': '2025-01-01',
                'timeframe': '1h',
                'expected_calls': 365*24  # 1 year of hourly data
            },
            # Small date range with large timeframe
            {
                'start_date': '2025-01-01',
                'end_date': '2025-01-31',
                'timeframe': '1d',
                'expected_calls': 31  # 31 days
            }
        ]

        for test_case in test_cases:
            test_data = {
                'strategy_id': 1,
                'symbol': 'BTC/USDT',
                'start_date': test_case['start_date'],
                'end_date': test_case['end_date'],
                'timeframe': test_case['timeframe'],
                'initial_capital': 10000
            }

            # Time the request
            start_time = time.time()
            response = client.post(
                '/api/backtest',
                json=test_data,
                headers=auth_headers
            )
            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            assert elapsed_time < 10  # Should complete within 10 seconds

def test_backtest_error_scenarios(client, auth_headers):
    """Test comprehensive error scenarios for backtests"""
    test_cases = [
        # Database errors
        ({'strategy_id': 1}, "Database error", 500, lambda: patch('api.routes.Strategy.query.filter_by', side_effect=Exception("DB error"))),
        # Exchange client errors
        ({'symbol': 'UNKNOWN/PAIR'}, "Symbol not supported", 400, None),
        # Strategy execution errors
        ({'parameters': {'invalid': 'param'}}, "Strategy execution failed", 500,
         lambda: patch('api.routes.StrategyFactory.create_strategy', side_effect=Exception("Strategy error"))),
        # Backtester errors
        ({'timeframe': 'error'}, "Backtest failed", 500,
         lambda: patch('api.routes.Backtester.run_backtest', side_effect=Exception("Backtest error")))
    ]

    base_data = {
        'strategy_id': 1,
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'start_date': '2025-01-01',
        'end_date': '2025-01-02',
        'initial_capital': 10000
    }

    for param_data, expected_error, expected_code, mock_setup in test_cases:
        test_data = {**base_data, **param_data}
        
        if mock_setup:
            with mock_setup():
                response = client.post(
                    '/api/backtest',
                    json=test_data,
                    headers=auth_headers
                )
        else:
            response = client.post(
                '/api/backtest',
                json=test_data,
                headers=auth_headers
            )

        assert response.status_code == expected_code
        assert expected_error.lower() in str(response.json['error']['message']).lower()
def test_database_strategy_creation(client, auth_headers):
    """Test database integration for strategy creation"""
    test_data = {
        'name': 'Integration Test Strategy',
        'parameters': {'param1': 'value1'}
    }

    with patch('api.routes.verify_jwt_in_request') as mock_verify:
        mock_verify.return_value = {'user_id': 1}
        
        # Verify initial count
        with client.application.app_context():
            initial_count = Strategy.query.count()

        response = client.post(
            '/api/strategies',
            json=test_data,
            headers=auth_headers
        )

        assert response.status_code == 201
        with client.application.app_context():
            assert Strategy.query.count() == initial_count + 1
            # Verify data was saved correctly
            strategy = Strategy.query.order_by(Strategy.id.desc()).first()
        assert strategy.name == test_data['name']
        assert json.loads(strategy.parameters) == test_data['parameters']

def test_database_transaction_rollback(client, auth_headers):
    """Test transaction rollback on error"""
    with client.application.app_context():
        initial_count = Strategy.query.count()
    
    # This will fail due to missing required fields
    response = client.post(
        '/api/strategies',
        json={'invalid': 'data'},
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert Strategy.query.count() == initial_count  # Verify no record was created

def test_database_constraint_violations(client, auth_headers):
    """Test database constraint violations"""
    # Create duplicate strategy
    test_data = {
        'name': 'Duplicate Strategy',
        'parameters': {'param1': 'value1'}
    }
    
    # First creation should succeed
    response1 = client.post(
        '/api/strategies',
        json=test_data,
        headers=auth_headers
    )
    assert response1.status_code == 201
    
    # Second creation should fail due to unique constraint
    response2 = client.post(
        '/api/strategies',
        json=test_data,
        headers=auth_headers
    )
    assert response2.status_code == 400
    assert 'already exists' in response2.json['error']['message']

def test_database_relationships(client, auth_headers):
    """Test database relationships between models"""
    # Create strategy
    strategy_data = {
        'name': 'Relationship Test Strategy',
        'parameters': {'param1': 'value1'}
    }
    strategy_resp = client.post(
        '/api/strategies',
        json=strategy_data,
        headers=auth_headers
    )
    strategy_id = strategy_resp.json['data']['id']
    
    # Create backtest
    backtest_data = {
        'strategy_id': strategy_id,
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'start_date': '2025-01-01',
        'end_date': '2025-01-31',
        'initial_capital': 10000,
        'final_capital': 12000,
        'return_pct': 20,
        'total_trades': 10,
        'win_rate': 60,
        'strategy_parameters': {'param1': 'value1'},
        'trades': [
            {
                'trade_type': 'buy',
                'amount': 1.0,
                'price': 50000,
                'timestamp': '2025-01-01 12:00:00',
                'profit_loss': 1000
            }
        ]
    }
    backtest_resp = client.post(
        '/api/backtests',
        json=backtest_data,
        headers=auth_headers
    )

def test_thread_safety_in_strategy_factory(client, auth_headers):
    """Verify thread safety in strategy factory endpoint"""
    with patch('database.models.Strategy') as mock_strategy:
        mock_strategy_instance = MagicMock(
            id=1,
            name="Test Strategy",
            parameters='{"param1": "value1"}'
        )
        mock_strategy.query.filter_by.return_value.first.return_value = mock_strategy_instance
        
        # Track factory instances to detect race conditions
        instances = []
        instance_lock = Lock()
        
        def make_request():
            response = client.post(
                '/api/strategies/factory',
                json={'strategy_id': 1},
                headers=auth_headers
            )
            with instance_lock:
                instances.append(response.json['data'])
            return response.status_code

        # High concurrency test
        with ThreadPoolExecutor(max_workers=30) as executor:
            results = list(executor.map(make_request, range(30)))
            
        assert all(code == 200 for code in results)
        assert len(instances) == 30, "Missing factory instances"
        assert all(i['parameters'] == {'param1': 'value1'} for i in instances), "Parameter corruption detected"

def test_race_condition_in_backtest_save(client, auth_headers):
    """Simulate and detect race conditions in backtest saving"""
    with patch('database.models.BacktestResult') as mock_backtest:
        # Shared counter to detect race conditions
        save_counter = 0
        counter_lock = Lock()
        
        def make_request():
            nonlocal save_counter
            response = client.post(
                '/api/backtests',
                json={
                    'strategy_id': 1,
                    'results': {'profit': 100},
                    'trades': [{'symbol': 'BTC/USDT', 'side': 'buy', 'price': 50000}]
                },
                headers=auth_headers
            )
            with counter_lock:
                save_counter += 1
            return response.status_code

        # Concurrent save attempts
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(make_request, range(20)))
            
        assert all(code == 201 for code in results)
        assert save_counter == 20, "Backtest saves were lost"

def test_performance_benchmark(client, auth_headers):
    """Benchmark performance of critical endpoints under load"""


# Auth Service Tests
def test_auth_login_success(client):
    """Test successful login"""
    with patch('auth.routers.auth.authenticate_user') as mock_auth:
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.roles = ["user"]
        mock_auth.return_value = mock_user
        
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()


def test_auth_login_failure(client):
    """Test failed login"""
    with patch('auth.routers.auth.authenticate_user', return_value=None):
        response = client.post(
            "/auth/login",
            data={"username": "baduser", "password": "badpass"}
        )
        assert response.status_code == 401


def test_auth_logout(client):
    """Test logout functionality"""
    with patch('auth.routers.auth.revoke_token') as mock_revoke:
        # First login to get token
        with patch('auth.routers.auth.authenticate_user') as mock_auth:
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_auth.return_value = mock_user
            
            login_response = client.post(
                "/auth/login",
                data={"username": "testuser", "password": "password"}
            )
            token = login_response.json()["access_token"]
        
        # Then logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        mock_revoke.assert_called_once()


def test_refresh_token(client):
    """Test token refresh"""
    with patch('auth.routers.auth.refresh_access_token') as mock_refresh:
        mock_refresh.return_value = {"access_token": "new_token"}
        
        response = client.post(
            "/auth/refresh-token",
            json={"refresh_token": "valid_refresh_token"}
        )
        assert response.status_code == 200
        assert response.json()["access_token"] == "new_token"


def test_refresh_token_invalid(client):
    """Test invalid refresh token"""
    with patch('auth.routers.auth.refresh_access_token',
              side_effect=ValueError("Invalid token")):
        response = client.post(
            "/auth/refresh-token",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401


def test_role_based_access(client):
    """Test role-based access control"""
    # Test admin route with admin user
    with patch('auth.routers.auth.get_current_user') as mock_user:
        mock_user.return_value = MagicMock(roles=["admin"])
        response = client.get(
            "/admin/route",
            headers={"Authorization": "Bearer admin_token"}
        )
        assert response.status_code == 200

    # Test admin route with regular user
    with patch('auth.routers.auth.get_current_user') as mock_user:
        mock_user.return_value = MagicMock(roles=["user"])
        response = client.get(
            "/admin/route",
            headers={"Authorization": "Bearer user_token"}
        )
        assert response.status_code == 403

# Auth Service Tests
def test_auth_login_success(client):
    """Test successful login"""
    with patch('auth.routers.auth.authenticate_user') as mock_auth:
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.roles = ["user"]
        mock_auth.return_value = mock_user
        
        response = client.post(
            "/auth/login",
            data={"username": "testuser", "password": "password"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()

def test_auth_login_failure(client):
    """Test failed login"""
    with patch('auth.routers.auth.authenticate_user', return_value=None):
        response = client.post(
            "/auth/login",
            data={"username": "baduser", "password": "badpass"}
        )
        assert response.status_code == 401

def test_auth_logout(client):
    """Test logout functionality"""
    with patch('auth.routers.auth.revoke_token') as mock_revoke:
        # First login to get token
        with patch('auth.routers.auth.authenticate_user') as mock_auth:
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_auth.return_value = mock_user
            
            login_response = client.post(
                "/auth/login",
                data={"username": "testuser", "password": "password"}
            )
            token = login_response.json()["access_token"]
        
        # Then logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        mock_revoke.assert_called_once()

def test_refresh_token(client):
    """Test token refresh"""
    with patch('auth.routers.auth.refresh_access_token') as mock_refresh:
        mock_refresh.return_value = {"access_token": "new_token"}
        
        response = client.post(
            "/auth/refresh-token",
            json={"refresh_token": "valid_refresh_token"}
        )
        assert response.status_code == 200
        assert response.json()["access_token"] == "new_token"

def test_refresh_token_invalid(client):
    """Test invalid refresh token"""
    with patch('auth.routers.auth.refresh_access_token',
              side_effect=ValueError("Invalid token")):
        response = client.post(
            "/auth/refresh-token",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401

def test_role_based_access(client):
    """Test role-based access control"""
    # Test admin route with admin user
    with patch('auth.routers.auth.get_current_user') as mock_user:
        mock_user.return_value = MagicMock(roles=["admin"])
        response = client.get(
            "/admin/route",
            headers={"Authorization": "Bearer admin_token"}
        )
        assert response.status_code == 200

    # Test admin route with regular user
    with patch('auth.routers.auth.get_current_user') as mock_user:
        mock_user.return_value = MagicMock(roles=["user"])
        response = client.get(
            "/admin/route",
            headers={"Authorization": "Bearer user_token"}
        )
        assert response.status_code == 403
    """Benchmark performance of critical endpoints under load"""
    test_cases = [
        ('/api/strategies', 'GET', None),
        ('/api/trades', 'GET', None),
        ('/api/strategies/factory', 'POST', {'strategy_id': 1}),
        ('/api/trades', 'POST', {'symbol': 'BTC/USDT', 'quantity': '1.0', 'side': 'buy'})
    ]
    
    results = {}
    for endpoint, method, data in test_cases:
        start_time = time.time()
        
        # Run 100 sequential requests
        for _ in range(100):
            if method == 'GET':
                client.get(endpoint, headers=auth_headers)
            else:
                client.post(endpoint, json=data, headers=auth_headers)
                
        avg_time = (time.time() - start_time) / 100
        results[endpoint] = {
            'method': method,
            'average_time_ms': avg_time * 1000,
            'requests_per_second': 1 / avg_time
        }
    
    # Verify no endpoint exceeds 500ms average
    assert all(v['average_time_ms'] < 500 for v in results.values()), \
        f"Performance issues detected: {results}"
    # Verify relationships
    strategy = Strategy.query.get(strategy_id)
    assert len(strategy.backtests) == 1
    backtest = strategy.backtests[0]
    assert len(backtest.trades) == 1
    assert backtest.trades[0].trade_type == 'buy'