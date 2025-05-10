import os
import pytest
from unittest.mock import patch, MagicMock
from utils.exchange_interface import get_exchange_interface, KrakenExchangeInterface

@pytest.fixture
def kraken_interface():
    """Fixture providing a Kraken exchange interface"""
    # Use mock credentials for testing
    return KrakenExchangeInterface('test_key', 'test_secret')

def test_kraken_interface_initialization():
    """Test Kraken interface can be initialized"""
    interface = KrakenExchangeInterface('test_key', 'test_secret')
    assert isinstance(interface, KrakenExchangeInterface)
    assert interface.exchange is not None

@patch('ccxt.kraken')
def test_kraken_mock(mock_kraken):
    """Test with fully mocked Kraken API"""
    mock_exchange = MagicMock()
    mock_exchange.fetch_ticker.return_value = {'bid': 50000, 'ask': 50010}
    mock_kraken.return_value = mock_exchange
    
    interface = KrakenExchangeInterface('test_key', 'test_secret')
    ticker = interface.get_ticker('BTC/USD')
    
    assert ticker['bid'] == 50000
    assert ticker['ask'] == 50010
    mock_exchange.fetch_ticker.assert_called_once_with('BTC/USD')

def test_kraken_factory():
    """Test exchange factory creates correct Kraken interface"""
    interface = get_exchange_interface('kraken', 'test_key', 'test_secret')
    assert isinstance(interface, KrakenExchangeInterface)