import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime

from trade.engine import TradingEngine, Order, OrderStatus
from trade.utils.exchange import ExchangeInterface, BinanceExchange, CoinbaseProExchange
from trade.services.risk_manager import RiskManager
from trade.services.portfolio_manager import PortfolioManager
from trade.utils.metrics import MetricsCollector
from trade.utils.alerting import AlertManager
from services.mcp.risk_management.basic_rules import BasicRiskRules
# Assuming exchange_config is accessible for mocking
# from trade.config import exchange_config # This might need to be mocked differently if it's module-level

# Mock exchange_config directly if it's imported at module level in engine.py
@pytest.fixture(autouse=True)
def mock_exchange_config_module():
    mock_config = MagicMock()
    mock_config.api_key = "test_api_key"
    mock_config.api_secret = "test_api_secret"
    mock_config.get_coinbase_pro_credentials.return_value = {
        "api_key": "cb_api_key",
        "api_secret": "cb_api_secret",
        "passphrase": "cb_passphrase",
    }
    with patch('trade.engine.exchange_config', mock_config):
        yield mock_config

@pytest.fixture
def mock_binance_exchange():
    return AsyncMock(spec=BinanceExchange)

@pytest.fixture
def mock_coinbase_pro_exchange():
    return AsyncMock(spec=CoinbaseProExchange)

@pytest.fixture
def mock_binance_websocket():
    return AsyncMock()

@pytest.fixture
def mock_risk_manager():
    rm = AsyncMock(spec=RiskManager)
    rm.validate_order.return_value = (True, None)
    return rm

@pytest.fixture
def mock_portfolio_manager():
    pm = AsyncMock(spec=PortfolioManager)
    pm.get_account_equity.return_value = Decimal("100000")
    return pm

@pytest.fixture
def mock_metrics_collector():
    return AsyncMock(spec=MetricsCollector)

@pytest.fixture
def mock_alert_manager():
    return AsyncMock(spec=AlertManager)

@pytest.fixture
def mock_basic_risk_rules():
    brr = AsyncMock(spec=BasicRiskRules)
    brr.check_position_size.return_value = True
    brr.check_portfolio_risk.return_value = True
    return brr

@pytest.fixture
@patch('trade.engine.BinanceExchange', new_callable=AsyncMock)
@patch('trade.engine.CoinbaseProExchange', new_callable=AsyncMock)
@patch('trade.engine.BinanceWebSocket', new_callable=AsyncMock)
@patch('trade.engine.RiskManager', new_callable=AsyncMock)
@patch('trade.engine.PortfolioManager', new_callable=AsyncMock)
@patch('trade.engine.MetricsCollector', new_callable=AsyncMock)
@patch('trade.engine.AlertManager', new_callable=AsyncMock)
@patch('trade.engine.BasicRiskRules', new_callable=AsyncMock)
def trading_engine_binance(
    MockBasicRiskRules, MockAlertManager, MockMetricsCollector,
    MockPortfolioManager, MockRiskManager, MockBinanceWebSocket,
    MockCoinbaseProExchange, MockBinanceExchange,
    mock_exchange_config_module # Ensure this fixture is used
):
    # Configure mocks before TradingEngine instantiation
    mock_binance_exchange_instance = MockBinanceExchange.return_value
    mock_binance_websocket_instance = MockBinanceWebSocket.return_value
    mock_risk_manager_instance = MockRiskManager.return_value
    mock_portfolio_manager_instance = MockPortfolioManager.return_value
    mock_metrics_collector_instance = MockMetricsCollector.return_value
    mock_alert_manager_instance = MockAlertManager.return_value
    mock_basic_risk_rules_instance = MockBasicRiskRules.return_value

    mock_risk_manager_instance.validate_order.return_value = (True, None)
    mock_portfolio_manager_instance.get_account_equity.return_value = Decimal("100000")
    mock_basic_risk_rules_instance.check_position_size.return_value = True
    mock_basic_risk_rules_instance.check_portfolio_risk.return_value = True
    
    engine = TradingEngine(exchange_name="binance")
    engine.exchange = mock_binance_exchange_instance
    engine.websocket = mock_binance_websocket_instance
    engine.risk_manager = mock_risk_manager_instance
    engine.portfolio_manager = mock_portfolio_manager_instance
    engine.metrics_collector = mock_metrics_collector_instance
    engine.alert_manager = mock_alert_manager_instance
    engine.basic_risk_rules = mock_basic_risk_rules_instance
    return engine

@pytest.mark.asyncio
async def test_trading_engine_init_binance(mock_exchange_config_module):
    with patch('trade.engine.BinanceExchange') as MockedBinanceExchange, \
         patch('trade.engine.BinanceWebSocket') as MockedBinanceWebSocket:
        
        mock_binance_exchange_instance = AsyncMock(spec=BinanceExchange)
        MockedBinanceExchange.return_value = mock_binance_exchange_instance
        
        mock_binance_websocket_instance = AsyncMock()
        MockedBinanceWebSocket.return_value = mock_binance_websocket_instance

        engine = TradingEngine(exchange_name="binance")
        
        MockedBinanceExchange.assert_called_once_with(api_key="test_api_key", api_secret="test_api_secret")
        assert engine.exchange == mock_binance_exchange_instance
        MockedBinanceWebSocket.assert_called_once()
        assert engine.websocket == mock_binance_websocket_instance
        assert engine.exchange_name == "binance"
        assert isinstance(engine.risk_manager, RiskManager)
        assert isinstance(engine.portfolio_manager, PortfolioManager)
        assert isinstance(engine.metrics_collector, MetricsCollector)
        assert isinstance(engine.alert_manager, AlertManager)
        assert isinstance(engine.basic_risk_rules, BasicRiskRules)

@pytest.mark.asyncio
async def test_trading_engine_init_coinbase_pro(mock_exchange_config_module):
    with patch('trade.engine.CoinbaseProExchange') as MockedCoinbaseProExchange:
        mock_cb_exchange_instance = AsyncMock(spec=CoinbaseProExchange)
        MockedCoinbaseProExchange.return_value = mock_cb_exchange_instance

        engine = TradingEngine(exchange_name="coinbasepro")

        mock_exchange_config_module.get_coinbase_pro_credentials.assert_called_once()
        MockedCoinbaseProExchange.assert_called_once_with(
            api_key="cb_api_key",
            api_secret="cb_api_secret",
            passphrase="cb_passphrase"
        )
        assert engine.exchange == mock_cb_exchange_instance
        assert engine.websocket is None # As per current engine logic
        assert engine.exchange_name == "coinbasepro"

@pytest.mark.asyncio
async def test_trading_engine_init_unsupported_exchange():
    with pytest.raises(ValueError, match="Unsupported exchange: unsupportedex"):
        TradingEngine(exchange_name="unsupportedex")

@pytest.mark.asyncio
async def test_place_order_success(trading_engine_binance: TradingEngine):
    order_to_place = Order(
        id="test_order_001",
        symbol="BTCUSDT",
        side="buy",
        type="limit",
        amount=0.1,
        price=50000.0
    )

    trading_engine_binance.exchange.test_connection = AsyncMock()
    trading_engine_binance.exchange.create_order = AsyncMock(return_value={"orderId": "exchange_order_123"})
    
    # Mock the _update_order_status method directly if it's complex or to simplify
    # For now, let's assume its direct effects are what we test via order.status
    trading_engine_binance._update_order_status = AsyncMock()


    placed_order = await trading_engine_binance.place_order(order_to_place)

    trading_engine_binance.basic_risk_rules.check_position_size.assert_called_once_with(order_to_place.symbol, Decimal(str(order_to_place.amount)))
    trading_engine_binance.basic_risk_rules.check_portfolio_risk.assert_called_once_with(trading_engine_binance.portfolio_manager.positions)
    trading_engine_binance.risk_manager.validate_order.assert_called_once()
    # The actual order object passed to validate_order would be order_to_place, and account_equity
    
    trading_engine_binance.exchange.test_connection.assert_awaited_once_with(max_retries=3, delay=1)
    trading_engine_binance.exchange.create_order.assert_awaited_once_with(
        symbol=order_to_place.symbol,
        side=order_to_place.side,
        type=order_to_place.type,
        amount=Decimal(str(order_to_place.amount)),
        price=Decimal(str(order_to_place.price))
    )
    
    assert placed_order.id == "exchange_order_123" # ID updated from exchange
    # Check that _update_order_status was called to set status to OPEN
    # This can be checked by looking at the calls to the mock _update_order_status
    trading_engine_binance._update_order_status.assert_any_call("exchange_order_123", OrderStatus.OPEN)
    
    trading_engine_binance.metrics_collector.record_counter.assert_any_call("orders.placed", 1)


@pytest.mark.asyncio
async def test_place_order_rejection_basic_risk_rules_position_size(trading_engine_binance: TradingEngine):
    order_to_place = Order(
        id="test_order_002",
        symbol="ETHUSDT",
        side="buy",
        type="market",
        amount=100.0 # Large amount likely to be rejected
    )

    trading_engine_binance.basic_risk_rules.check_position_size.return_value = False
    
    with pytest.raises(ValueError, match="Order rejected by risk manager: Order exceeds maximum position size"):
        await trading_engine_binance.place_order(order_to_place)

    trading_engine_binance.basic_risk_rules.check_position_size.assert_called_once_with(order_to_place.symbol, Decimal(str(order_to_place.amount)))
    trading_engine_binance.alert_manager.send_alert.assert_called_once_with(
        "Order Rejected",
        "Order for ETHUSDT rejected: Order exceeds maximum position size",
        level="warning"
    )
    trading_engine_binance.metrics_collector.record_counter.assert_called_once_with("orders.rejected", 1)
    trading_engine_binance.risk_manager.validate_order.assert_not_called()
    trading_engine_binance.exchange.create_order.assert_not_called()
    assert order_to_place.status == OrderStatus.REJECTED


@pytest.mark.asyncio
async def test_place_order_rejection_basic_risk_rules_portfolio_risk(trading_engine_binance: TradingEngine):
    order_to_place = Order(
        id="test_order_003",
        symbol="ADAUSDT",
        side="sell",
        type="limit",
        amount=500.0,
        price=1.0
    )

    # basic_risk_rules.check_position_size will pass (default mock is True)
    trading_engine_binance.basic_risk_rules.check_portfolio_risk.return_value = False
    
    with pytest.raises(ValueError, match="Order rejected by risk manager: Order exceeds maximum portfolio risk"):
        await trading_engine_binance.place_order(order_to_place)

    trading_engine_binance.basic_risk_rules.check_position_size.assert_called_once_with(order_to_place.symbol, Decimal(str(order_to_place.amount)))
    trading_engine_binance.basic_risk_rules.check_portfolio_risk.assert_called_once_with(trading_engine_binance.portfolio_manager.positions)
    trading_engine_binance.alert_manager.send_alert.assert_called_once_with(
        "Order Rejected",
        "Order for ADAUSDT rejected: Order exceeds maximum portfolio risk",
        level="warning"
    )
    trading_engine_binance.metrics_collector.record_counter.assert_called_once_with("orders.rejected", 1)
    trading_engine_binance.risk_manager.validate_order.assert_not_called()
    trading_engine_binance.exchange.create_order.assert_not_called()
    assert order_to_place.status == OrderStatus.REJECTED


@pytest.mark.asyncio
async def test_place_order_rejection_risk_manager_validate_order(trading_engine_binance: TradingEngine):
    order_to_place = Order(
        id="test_order_004",
        symbol="DOTUSDT",
        side="buy",
        type="market",
        amount=10.0
    )

    # basic_risk_rules checks will pass
    trading_engine_binance.risk_manager.validate_order.return_value = (False, "Insufficient account balance")
    
    with pytest.raises(ValueError, match="Order rejected by risk manager: Insufficient account balance"):
        await trading_engine_binance.place_order(order_to_place)

    trading_engine_binance.basic_risk_rules.check_position_size.assert_called_once()
    trading_engine_binance.basic_risk_rules.check_portfolio_risk.assert_called_once()
    trading_engine_binance.risk_manager.validate_order.assert_called_once()
    # The actual arguments for validate_order would be (order_to_place, account_equity_value)
    
    trading_engine_binance.alert_manager.send_alert.assert_called_once_with(
        "Order Rejected",
        "Order for DOTUSDT rejected: Insufficient account balance",
        level="warning"
    )
    trading_engine_binance.metrics_collector.record_counter.assert_called_once_with("orders.rejected", 1)
    trading_engine_binance.exchange.create_order.assert_not_called()
    assert order_to_place.status == OrderStatus.REJECTED


@pytest.mark.asyncio
async def test_place_order_failure_exchange_connection_error(trading_engine_binance: TradingEngine):
    order_to_place = Order(
        id="test_order_005",
        symbol="SOLUSDT",
        side="buy",
        type="limit",
        amount=5.0,
        price=100.0
    )

    # Risk checks pass
    trading_engine_binance.exchange.test_connection.side_effect = Exception("Connection timeout")
    trading_engine_binance._update_order_status = AsyncMock() # Mock to check status update

    with pytest.raises(Exception, match="Exchange connection is not available: Connection timeout"):
        await trading_engine_binance.place_order(order_to_place)

    trading_engine_binance.exchange.test_connection.assert_awaited_once()
    trading_engine_binance.alert_manager.send_alert.assert_called_once_with(
        "Exchange Connectivity Issue",
        "Could not place order for SOLUSDT due to exchange connectivity issues: Connection timeout",
        level="critical",
        data={"order_id": order_to_place.id, "symbol": order_to_place.symbol, "side": order_to_place.side, "type": order_to_place.type, "amount": order_to_place.amount, "price": order_to_place.price}
    )
    trading_engine_binance.exchange.create_order.assert_not_called()
    # Status should be REJECTED after failure
    # We need to ensure _update_order_status was called correctly for rejection
    # This depends on how the original order_id is handled if it's not yet updated by exchange
    # Assuming the original id is used for status update on pre-exchange failure
    trading_engine_binance._update_order_status.assert_any_call(order_to_place.id, OrderStatus.REJECTED)
    # trading_engine_binance.metrics_collector.record_counter.assert_called_once_with("orders.failed", 1) # This is not recorded in this path


@pytest.mark.asyncio
async def test_place_order_failure_exchange_create_order_error(trading_engine_binance: TradingEngine):
    order_to_place = Order(
        id="test_order_006",
        symbol="AVAXUSDT",
        side="sell",
        type="market",
        amount=20.0
    )

    # Risk checks pass, connection test passes
    trading_engine_binance.exchange.test_connection = AsyncMock()
    trading_engine_binance.exchange.create_order.side_effect = Exception("Exchange API error: Insufficient funds")
    trading_engine_binance._update_order_status = AsyncMock()

    with pytest.raises(Exception, match="Exchange API error: Insufficient funds"):
        await trading_engine_binance.place_order(order_to_place)

    trading_engine_binance.exchange.create_order.assert_awaited_once()
    trading_engine_binance.alert_manager.send_alert.assert_called_once_with(
        "Order Placement Failed",
        f"Order for {order_to_place.symbol} failed to be placed: Exchange API error: Insufficient funds",
        level="error",
        data={"order_id": order_to_place.id, "symbol": order_to_place.symbol, "side": order_to_place.side, "type": order_to_place.type, "amount": order_to_place.amount, "price": order_to_place.price}
    )
    trading_engine_binance._update_order_status.assert_any_call(order_to_place.id, OrderStatus.REJECTED)
    trading_engine_binance.metrics_collector.record_counter.assert_any_call("orders.failed", 1)
    # Ensure "orders.placed" was not called
    call_args_list = trading_engine_binance.metrics_collector.record_counter.call_args_list
    assert not any(call[0][0] == "orders.placed" for call in call_args_list)


@pytest.mark.asyncio
async def test_start_engine_binance_full_flow(trading_engine_binance: TradingEngine):
    # Mock methods called by start()
    trading_engine_binance.websocket.connect = AsyncMock()
    trading_engine_binance.websocket.subscribe_user_data = AsyncMock()
    trading_engine_binance.exchange.get_listen_key = AsyncMock(return_value="listen_key_123")
    trading_engine_binance._setup_market_data = AsyncMock() # Mock this helper
    trading_engine_binance.risk_manager.start_monitoring = AsyncMock()
    trading_engine_binance.metrics_collector.start_exporting = AsyncMock()

    await trading_engine_binance.start()

    trading_engine_binance.websocket.connect.assert_awaited_once()
    trading_engine_binance._setup_market_data.assert_awaited_once()
    trading_engine_binance.exchange.get_listen_key.assert_awaited_once()
    trading_engine_binance.websocket.subscribe_user_data.assert_awaited_once_with("listen_key_123")
    trading_engine_binance.risk_manager.start_monitoring.assert_awaited_once()
    trading_engine_binance.metrics_collector.start_exporting.assert_awaited_once()
    # Check if execution handler is registered (simplified check)
    assert 'execution' in trading_engine_binance.websocket._callbacks


@pytest.mark.asyncio
async def test_start_engine_coinbase_pro_no_websocket(mock_exchange_config_module):
    # For Coinbase Pro, websocket is None, so some calls should be skipped
    with patch('trade.engine.CoinbaseProExchange') as MockedCoinbaseProExchange, \
         patch('trade.engine.RiskManager') as MockRiskManager, \
         patch('trade.engine.PortfolioManager') as MockPortfolioManager, \
         patch('trade.engine.MetricsCollector') as MockMetricsCollector, \
         patch('trade.engine.AlertManager'), \
         patch('trade.engine.BasicRiskRules'):

        mock_cb_exchange_instance = AsyncMock(spec=CoinbaseProExchange)
        MockedCoinbaseProExchange.return_value = mock_cb_exchange_instance
        
        mock_risk_manager_instance = MockRiskManager.return_value
        mock_metrics_collector_instance = MockMetricsCollector.return_value

        engine = TradingEngine(exchange_name="coinbasepro")
        engine.risk_manager.start_monitoring = AsyncMock() # Mock the method on the instance
        engine.metrics_collector.start_exporting = AsyncMock() # Mock the method on the instance
        engine._setup_market_data = AsyncMock() # Mock this helper

        await engine.start()

        engine._setup_market_data.assert_not_called() # Because websocket is None
        assert not hasattr(engine.exchange, 'get_listen_key') # Coinbase mock doesn't have this
        engine.risk_manager.start_monitoring.assert_awaited_once()
        engine.metrics_collector.start_exporting.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_engine(trading_engine_binance: TradingEngine):
    trading_engine_binance.risk_manager.stop_monitoring = AsyncMock()
    trading_engine_binance.metrics_collector.stop_exporting = AsyncMock()
    trading_engine_binance.websocket.close = AsyncMock()

    await trading_engine_binance.stop()

    trading_engine_binance.risk_manager.stop_monitoring.assert_awaited_once()
    trading_engine_binance.metrics_collector.stop_exporting.assert_awaited_once()
    trading_engine_binance.websocket.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_market_data_with_websocket(trading_engine_binance: TradingEngine):
    trading_engine_binance.websocket.subscribe = AsyncMock()
    trading_engine_binance.websocket.subscribe_depth = AsyncMock()
    trading_engine_binance.risk_manager.register_circuit_breaker = MagicMock() # Sync mock for now

    await trading_engine_binance._setup_market_data()

    trading_engine_binance.websocket.subscribe.assert_any_call("!ticker@arr", trading_engine_binance._handle_ticker)
    # Check if subscribe_depth was called, e.g. for BTCUSDT as in engine
    # This depends on the exact implementation detail if it's always BTCUSDT or configurable
    trading_engine_binance.websocket.subscribe_depth.assert_any_call("BTCUSDT")
    
    # Check circuit breaker registration for major symbols
    major_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    for symbol in major_symbols:
        trading_engine_binance.risk_manager.register_circuit_breaker.assert_any_call(symbol)

@pytest.mark.asyncio
async def test_setup_market_data_no_websocket():
    # Create an engine instance where websocket would be None (e.g., CoinbasePro)
    with patch('trade.engine.CoinbaseProExchange'), \
         patch('trade.engine.RiskManager') as MockRiskManager, \
         patch('trade.engine.PortfolioManager'), \
         patch('trade.engine.MetricsCollector'), \
         patch('trade.engine.AlertManager'), \
         patch('trade.engine.BasicRiskRules'):
        
        engine = TradingEngine(exchange_name="coinbasepro")
        engine.risk_manager.register_circuit_breaker = MagicMock() # Sync mock

        # Manually set websocket to None if not already by init logic for test clarity
        engine.websocket = None
        
        await engine._setup_market_data()

        # Assert that websocket dependent calls were not made
        # No direct way to check engine.websocket.subscribe if websocket is None and not mocked
        # The logger warning is a good indicator if we could capture logs.
        # For now, we primarily check that circuit breakers are still registered.
        major_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        for symbol in major_symbols:
            engine.risk_manager.register_circuit_breaker.assert_any_call(symbol)


@pytest.mark.asyncio
async def test_cancel_order_success(trading_engine_binance: TradingEngine):
    order_id = "order_to_cancel_123"
    # Simulate the order exists
    trading_engine_binance.orders[order_id] = Order(id=order_id, symbol="BTCUSDT", side="buy", type="limit", amount=0.1, price=50000.0)
    trading_engine_binance._update_order_status = AsyncMock()

    result = await trading_engine_binance.cancel_order(order_id)

    assert result is True
    trading_engine_binance._update_order_status.assert_awaited_once_with(order_id, OrderStatus.CANCELLED)

@pytest.mark.asyncio
async def test_cancel_order_not_found(trading_engine_binance: TradingEngine):
    order_id = "non_existent_order_456"
    trading_engine_binance._update_order_status = AsyncMock()

    result = await trading_engine_binance.cancel_order(order_id)

    assert result is False
    trading_engine_binance._update_order_status.assert_not_awaited()