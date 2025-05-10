"""
Integration tests for service interactions in the trading system.
Tests workflows across service boundaries including:
- Data service to trade execution
- Strategy to trade execution
- Error handling across services
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from services.data.realtime import DataService
from trade.services.execution import TradeExecutionService
from strategies.base_strategy import BaseStrategy
from utils.exchange_interface import ExchangeInterface
from database.models import Trade, Strategy
from datetime import datetime

@pytest.fixture
def mock_exchange():
    """Mock exchange interface for testing"""
    with patch('utils.exchange_interface.ExchangeInterface') as mock:
        yield mock

@pytest.fixture
def mock_risk():
    """Mock risk service for testing"""
    with patch('trade.services.risk.RiskService') as mock:
        yield mock

@pytest.fixture
def mock_db():
    """Mock database session for testing"""
    with patch('database.session') as mock:
        yield mock

@pytest.mark.integration
async def test_data_to_trade_workflow(mock_exchange, mock_risk, mock_db):
    """Test full workflow from data service to trade execution"""
    # Setup mock exchange
    mock_exchange.get_ticker.return_value = {'last': 50000.0}
    mock_exchange.place_order.return_value = {'id': 'order123', 'status': 'filled'}
    
    # Setup mock risk service
    mock_risk.calculate_position_size.return_value = 0.1
    mock_risk.validate_order.return_value = True
    
    # Setup mock DB
    mock_db.query.return_value.filter.return_value.first.return_value = Strategy(
        id=1,
        name="Test Strategy",
        parameters={}
    )
    
    # Initialize services
    data_service = DataService()
    trade_service = TradeExecutionService()
    
    # Simulate data event
    await data_service.handle_ticker_update('BTCUSDT', {'last': 50000.0})
    
    # Verify trade execution
    trades = mock_db.query(Trade).all()
    assert len(trades) == 1
    assert trades[0].exchange_order_id == 'order123'

@pytest.mark.integration
async def test_strategy_to_trade_workflow(mock_exchange, mock_risk, mock_db):
    """Test strategy signal generation to trade execution"""
    # Setup strategy
    strategy = BaseStrategy(exchange_interface=mock_exchange)
    
    # Setup mock exchange
    mock_exchange.get_ticker.return_value = {'last': 50000.0}
    mock_exchange.place_order.return_value = {'id': 'order456', 'status': 'filled'}
    
    # Setup mock risk service
    mock_risk.calculate_position_size.return_value = 0.1
    mock_risk.validate_order.return_value = True
    
    # Generate signal
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'buy',
        'price': 50000.0,
        'amount': 0.1,
        'strategy_id': 1
    }
    
    # Execute trade
    trade_service = TradeExecutionService()
    await trade_service.execute_trade(signal)
    
    # Verify trade execution
    trades = mock_db.query(Trade).all()
    assert len(trades) == 1
    assert trades[0].exchange_order_id == 'order456'

@pytest.mark.integration
async def test_error_handling_integration(mock_exchange, mock_risk):
    """Test error handling across service boundaries"""
    # Setup failing exchange
    mock_exchange.place_order.side_effect = Exception("API error")
    
    # Setup strategy
    strategy = BaseStrategy(exchange_interface=mock_exchange)
    
    # Generate signal
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'buy',
        'price': 50000.0,
        'amount': 0.1,
        'strategy_id': 1
    }
    
    # Execute trade with error handling
    trade_service = TradeExecutionService()
    with pytest.raises(Exception, match="API error"):
        await trade_service.execute_trade(signal)