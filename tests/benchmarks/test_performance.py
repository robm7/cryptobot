"""
Performance benchmarks for critical system components.
Measures:
- Trade execution latency
- Data processing throughput 
- Strategy evaluation performance
"""

import pytest
from strategies.base_strategy import BaseStrategy
from trade.services.execution import TradeExecutionService
from services.data.realtime import DataService
from utils.exchange_interface import ExchangeInterface
from database.models import Trade, Strategy
from datetime import datetime

@pytest.fixture
def mock_exchange():
    """Mock exchange interface for benchmarks"""
    with patch('utils.exchange_interface.ExchangeInterface') as mock:
        mock.get_ticker.return_value = {'last': 50000.0}
        mock.place_order.return_value = {'id': 'order123', 'status': 'filled'}
        yield mock

@pytest.fixture
def mock_risk():
    """Mock risk service for benchmarks"""
    with patch('trade.services.risk.RiskService') as mock:
        mock.calculate_position_size.return_value = 0.1
        mock.validate_order.return_value = True
        yield mock

@pytest.fixture 
def mock_db():
    """Mock database for benchmarks"""
    with patch('database.session') as mock:
        mock.query.return_value.filter.return_value.first.return_value = Strategy(
            id=1,
            name="Benchmark Strategy",
            parameters={}
        )
        yield mock

def test_trade_execution_latency(benchmark, mock_exchange, mock_risk, mock_db):
    """Benchmark trade execution latency"""
    trade_service = TradeExecutionService()
    signal = {
        'symbol': 'BTCUSDT',
        'side': 'buy',
        'price': 50000.0,
        'amount': 0.1,
        'strategy_id': 1
    }
    
    benchmark(trade_service.execute_trade, signal)

def test_data_processing_throughput(benchmark):
    """Benchmark data processing throughput"""
    data_service = DataService()
    ticker_data = {'last': 50000.0, 'volume': 1000.0, 'timestamp': datetime.now()}
    
    def process_data():
        data_service.process_ticker_update('BTCUSDT', ticker_data)
    
    benchmark(process_data)

def test_strategy_evaluation(benchmark, mock_exchange):
    """Benchmark strategy evaluation performance"""
    strategy = BaseStrategy(exchange_interface=mock_exchange)
    
    def evaluate_strategy():
        strategy.evaluate('BTCUSDT', {'last': 50000.0})
    
    benchmark(evaluate_strategy)

def test_stress_trade_execution(benchmark, mock_exchange, mock_risk, mock_db):
    """Stress test trade execution under load"""
    trade_service = TradeExecutionService()
    signals = [{
        'symbol': f'BTCUSDT_{i}',
        'side': 'buy',
        'price': 50000.0 + i,
        'amount': 0.1,
        'strategy_id': 1
    } for i in range(1000)]
    
    def execute_bulk_trades():
        for signal in signals:
            trade_service.execute_trade(signal)
    
    benchmark(execute_bulk_trades)