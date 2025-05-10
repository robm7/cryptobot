import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from utils.exchange_interface import (
    BaseExchangeInterface,
    BinanceExchangeInterface,
    KrakenExchangeInterface,
    MockExchangeInterface
)

@pytest.mark.asyncio
async def test_base_interface_abstract_methods():
    """Test BaseExchangeInterface raises NotImplementedError for abstract methods"""
    interface = BaseExchangeInterface()
    
    with pytest.raises(NotImplementedError):
        await interface.get_ticker("BTC/USDT")
    
    with pytest.raises(NotImplementedError):
        await interface.place_order("BTC/USDT", "limit", "buy", 0.1, 50000)
    
    with pytest.raises(NotImplementedError):
        await interface.cancel_order("12345")
    
    with pytest.raises(NotImplementedError):
        await interface.get_order_status("12345")
    
    with pytest.raises(NotImplementedError):
        await interface.get_balance()
    
    with pytest.raises(NotImplementedError):
        await interface.get_open_orders()

@pytest.mark.asyncio
async def test_binance_interface_methods():
    """Test BinanceExchangeInterface methods"""
    with patch('ccxt.binance', new_callable=AsyncMock) as mock_binance:
        interface = BinanceExchangeInterface("test_key", "test_secret")
        interface.exchange = mock_binance
        
        # Test get_ticker
        mock_binance.fetch_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid': 50000,
            'ask': 50001,
            'last': 50000.5
        }
        ticker = await interface.get_ticker("BTC/USDT")
        assert ticker['symbol'] == 'BTC/USDT'
        mock_binance.fetch_ticker.assert_called_once_with("BTC/USDT")
        
        # Test place_order
        mock_binance.create_order.return_value = {
            'id': '12345',
            'status': 'open'
        }
        order = await interface.place_order(
            "BTC/USDT", "limit", "buy", 0.1, 50000
        )
        assert order['id'] == '12345'
        mock_binance.create_order.assert_called_once_with(
            symbol="BTC/USDT",
            type="limit",
            side="buy",
            amount=0.1,
            price=50000,
            params={}
        )
        
        # Test other methods similarly...

@pytest.mark.asyncio
async def test_kraken_interface_methods():
    """Test KrakenExchangeInterface methods"""
    with patch('ccxt.kraken', new_callable=AsyncMock) as mock_kraken:
        interface = KrakenExchangeInterface("test_key", "test_secret")
        interface.exchange = mock_kraken
        
        # Test get_ticker
        mock_kraken.fetch_ticker.return_value = {
            'symbol': 'BTC/USDT',
            'bid': 50000,
            'ask': 50001,
            'last': 50000.5
        }
        ticker = await interface.get_ticker("BTC/USDT")
        assert ticker['symbol'] == 'BTC/USDT'
        mock_kraken.fetch_ticker.assert_called_once_with("BTC/USDT")
        
        # Test place_order
        mock_kraken.create_order.return_value = {
            'id': '12345',
            'status': 'open'
        }
        order = await interface.place_order(
            "BTC/USDT", "limit", "buy", 0.1, 50000
        )
        assert order['id'] == '12345'
        mock_kraken.create_order.assert_called_once_with(
            symbol="BTC/USDT",
            type="limit",
            side="buy",
            amount=0.1,
            price=50000,
            params={}
        )
        
        # Test other methods similarly...

@pytest.mark.asyncio
async def test_mock_interface_methods():
    """Test MockExchangeInterface methods"""
    interface = MockExchangeInterface()
    
    # Test initial state
    assert len(interface._orders) == 0
    
    # Test place_order
    order = await interface.place_order(
        "BTC/USDT", "limit", "buy", 0.1, 50000
    )
    assert order['id'].startswith("mock_order_")
    assert order['status'] == 'open'
    assert len(interface._orders) == 1
    
    # Test get_order_status
    status = await interface.get_order_status(order['id'])
    assert status['status'] == 'open'
    
    # Test cancel_order
    await interface.cancel_order(order['id'])
    status = await interface.get_order_status(order['id'])
    assert status['status'] == 'canceled'
    
    # Test get_balance
    balance = await interface.get_balance('BTC')
    assert balance['free'] == 1.0
    
    # Test get_open_orders
    open_orders = await interface.get_open_orders()
    assert len(open_orders) == 0  # Since we canceled our only order
    
    # Place another order and verify open orders
    await interface.place_order("BTC/USDT", "limit", "buy", 0.1)
    open_orders = await interface.get_open_orders()
    assert len(open_orders) == 1

@pytest.mark.asyncio
async def test_interface_error_handling():
    """Test error handling in exchange interfaces"""
    with patch('ccxt.binance', new_callable=AsyncMock) as mock_binance:
        interface = BinanceExchangeInterface("test_key", "test_secret")
        interface.exchange = mock_binance
        
        # Test network error
        mock_binance.fetch_ticker.side_effect = Exception("Network error")
        with pytest.raises(Exception, match="Network error"):
            await interface.get_ticker("BTC/USDT")
        
        # Test exchange error
        mock_binance.create_order.side_effect = Exception("Invalid order")
        with pytest.raises(Exception, match="Invalid order"):
            await interface.place_order("BTC/USDT", "limit", "buy", 0.1)