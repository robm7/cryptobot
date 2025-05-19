"""
Risk Management Integration Tests

This module contains tests for the risk management integration with the trading engine.
"""
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock

from trade.services.risk_manager import RiskManager
from trade.services.portfolio_manager import PortfolioManager
from trade.utils.metrics import MetricsCollector
from trade.utils.circuit_breaker import CircuitBreaker
from trade.engine import TradingEngine, Order, OrderStatus
from trade.config.risk_config import risk_config

@pytest.fixture
def portfolio_manager():
    """Create a portfolio manager for testing"""
    pm = PortfolioManager(initial_equity=Decimal("100000"))
    return pm

@pytest.fixture
def metrics_collector():
    """Create a metrics collector for testing"""
    mc = MetricsCollector()
    return mc

@pytest.fixture
def risk_manager(portfolio_manager, metrics_collector):
    """Create a risk manager for testing"""
    rm = RiskManager(portfolio_manager, metrics_collector)
    return rm

@pytest.fixture
def mock_exchange():
    """Create a mock exchange interface"""
    exchange = AsyncMock()
    exchange.create_order = AsyncMock(return_value={"orderId": "test123"})
    exchange.get_listen_key = AsyncMock(return_value="test_listen_key")
    return exchange

@pytest.fixture
def trading_engine(mock_exchange):
    """Create a trading engine with mocked components"""
    # Create a mock exchange class that returns our mock exchange instance
    mock_exchange_class = MagicMock()
    mock_exchange_class.return_value = mock_exchange
    
    # Create engine with mock exchange
    engine = TradingEngine(mock_exchange_class, "test_api_key", "test_api_secret")
    
    # Mock websocket
    engine.websocket = AsyncMock()
    engine.websocket.connect = AsyncMock()
    engine.websocket.subscribe = AsyncMock()
    engine.websocket.subscribe_user_data = AsyncMock()
    engine.websocket.subscribe_depth = AsyncMock()
    
    # Replace risk manager with a mock
    engine.risk_manager = AsyncMock()
    engine.risk_manager.validate_order = AsyncMock(return_value=(True, None))
    
    # Replace portfolio manager with a mock
    engine.portfolio_manager = AsyncMock()
    engine.portfolio_manager.get_account_equity = AsyncMock(return_value=Decimal("100000"))
    
    return engine

@pytest.mark.asyncio
async def test_risk_manager_initialization(risk_manager):
    """Test risk manager initialization"""
    assert risk_manager is not None
    assert risk_manager.portfolio_service is not None
    assert risk_manager.metrics_collector is not None
    assert risk_manager.alert_manager is not None
    assert risk_manager.circuit_breakers == {}
    assert risk_manager.trading_halted is False

@pytest.mark.asyncio
async def test_risk_manager_validate_order_success(risk_manager, portfolio_manager):
    """Test successful order validation"""
    # Create a test order
    order = MagicMock()
    order.symbol = "BTC/USDT"
    order.side = "buy"
    order.amount = Decimal("0.1")  # Small order that should pass validation
    
    # Mock portfolio service methods
    portfolio_manager.get_symbol_exposure = AsyncMock(return_value=Decimal("0"))
    portfolio_manager.get_total_exposure = AsyncMock(return_value=Decimal("0"))
    portfolio_manager.get_portfolio_value = AsyncMock(return_value=Decimal("100000"))
    portfolio_manager.get_position_risk = AsyncMock(return_value={
        "volatility": 0.5,
        "correlation_risk": 0.2,
        "concentration": 0.05
    })
    
    # Validate order
    is_valid, reason = await risk_manager.validate_order(order, Decimal("100000"))
    
    # Order should be valid
    assert is_valid is True
    assert reason is None

@pytest.mark.asyncio
async def test_risk_manager_validate_order_failure_size(risk_manager, portfolio_manager):
    """Test order validation failure due to size"""
    # Create a test order with excessive size
    order = MagicMock()
    order.symbol = "BTC/USDT"
    order.side = "buy"
    order.amount = Decimal("20000")  # Large order that should exceed max order size
    
    # Mock portfolio service methods
    portfolio_manager.get_symbol_exposure = AsyncMock(return_value=Decimal("0"))
    portfolio_manager.get_total_exposure = AsyncMock(return_value=Decimal("0"))
    portfolio_manager.get_portfolio_value = AsyncMock(return_value=Decimal("100000"))
    portfolio_manager.get_position_risk = AsyncMock(return_value={
        "volatility": 0.5,
        "correlation_risk": 0.2,
        "concentration": 0.05
    })
    
    # Validate order
    is_valid, reason = await risk_manager.validate_order(order, Decimal("100000"))
    
    # Order should be invalid
    assert is_valid is False
    assert "size" in reason.lower()

@pytest.mark.asyncio
async def test_risk_manager_validate_order_failure_correlation(risk_manager, portfolio_manager):
    """Test order validation failure due to correlation"""
    # Create a test order
    order = MagicMock()
    order.symbol = "BTC/USDT"
    order.side = "buy"
    order.amount = Decimal("1000")  # Reasonable size
    
    # Mock portfolio service methods
    portfolio_manager.get_symbol_exposure = AsyncMock(return_value=Decimal("0"))
    portfolio_manager.get_total_exposure = AsyncMock(return_value=Decimal("0"))
    portfolio_manager.get_portfolio_value = AsyncMock(return_value=Decimal("100000"))
    portfolio_manager.get_position_risk = AsyncMock(return_value={
        "volatility": 0.5,
        "correlation_risk": 0.95,  # High correlation that should fail
        "concentration": 0.05
    })
    
    # Validate order
    is_valid, reason = await risk_manager.validate_order(order, Decimal("100000"))
    
    # Order should be invalid
    assert is_valid is False
    assert "correlation" in reason.lower()

@pytest.mark.asyncio
async def test_risk_manager_calculate_position_size(risk_manager, portfolio_manager):
    """Test position size calculation"""
    # Mock portfolio service methods
    portfolio_manager.get_position_risk = AsyncMock(return_value={
        "volatility": 0.5,
        "correlation_risk": 0.2,
        "concentration": 0.05
    })
    portfolio_manager.get_drawdown_metrics = MagicMock(return_value={
        "current_drawdown": Decimal("0.05"),
        "max_drawdown": Decimal("0.1")
    })
    
    # Calculate position size
    size = await risk_manager.calculate_position_size(
        "BTC/USDT",
        Decimal("100000"),
        risk_percentage=Decimal("0.01"),
        stop_loss_pct=Decimal("0.05")
    )
    
    # Size should be reasonable
    assert size > Decimal("0")
    assert size <= Decimal("10000")  # Should not exceed max order size

@pytest.mark.asyncio
async def test_risk_manager_calculate_position_size_with_drawdown(risk_manager: RiskManager, portfolio_manager: PortfolioManager):
    """Test position size calculation with drawdown adjustment and specific thresholds."""
    # Mock portfolio service methods
    portfolio_manager.get_position_risk = AsyncMock(return_value={
        "volatility": 0.5, # Assuming baseline volatility for simplicity here
        "correlation_risk": 0.2
    })
    
    original_dd_control_enabled = risk_config.DRAWDOWN_CONTROL_ENABLED
    original_max_dd_thresh = risk_config.MAX_DRAWDOWN_THRESHOLD
    original_crit_dd_thresh = risk_config.CRITICAL_DRAWDOWN_THRESHOLD
    original_dd_scaling_factor = risk_config.DRAWDOWN_SCALING_FACTOR

    risk_config.DRAWDOWN_CONTROL_ENABLED = True
    # Use default config values for thresholds for this test
    # MAX_DRAWDOWN_THRESHOLD = Decimal("0.15")
    # CRITICAL_DRAWDOWN_THRESHOLD = Decimal("0.25")
    # DRAWDOWN_SCALING_FACTOR = Decimal("2.0")

    equity = Decimal("100000")
    risk_pct = Decimal("0.01")
    sl_pct = Decimal("0.05")
    
    # Base size without drawdown control (capped by MAX_ORDER_SIZE)
    # (100000 * 0.01) / 0.05 = 20000. Capped by MAX_ORDER_SIZE (default 10000)
    unscaled_size_no_dd = min( (equity * risk_pct) / sl_pct, risk_config.MAX_ORDER_SIZE)

    test_scenarios = [
        # (drawdown_level, expected_scaling_factor_approx)
        (Decimal("0.04"), Decimal("1.0")), # Below 5% threshold
        (Decimal("0.05"), Decimal("1.0")), # At 5% threshold (linear scaling starts just above)
        # For 0.10 DD: severity = (0.10 - 0.05) / (0.15 - 0.05) = 0.05 / 0.10 = 0.5
        # reduction_factor = 1.0 - (0.5 * 0.5 * 2.0) = 1.0 - 0.5 = 0.5
        (Decimal("0.10"), Decimal("0.5")), # Linear scaling range
        # For 0.14 DD: severity = (0.14 - 0.05) / (0.15 - 0.05) = 0.09 / 0.10 = 0.9
        # reduction_factor = 1.0 - (0.9 * 0.5 * 2.0) = 1.0 - 0.9 = 0.1
        (Decimal("0.14"), Decimal("0.1")), # Near MAX_DRAWDOWN_THRESHOLD
        (Decimal("0.15"), Decimal("0.25")), # At MAX_DRAWDOWN_THRESHOLD (jumps to 25%)
        (Decimal("0.20"), Decimal("0.25")), # Between MAX and CRITICAL
        (Decimal("0.24"), Decimal("0.25")), # Just below CRITICAL
        (Decimal("0.25"), Decimal("0.10")), # At CRITICAL_DRAWDOWN_THRESHOLD (jumps to 10%)
        (Decimal("0.30"), Decimal("0.10")), # Above CRITICAL
    ]

    for dd_level, expected_factor in test_scenarios:
        portfolio_manager.get_drawdown_metrics = MagicMock(return_value={"current_drawdown": dd_level})
        
        # Temporarily disable volatility scaling for this specific drawdown test focus
        original_vol_scaling = risk_config.VOLATILITY_SCALING_ENABLED
        risk_config.VOLATILITY_SCALING_ENABLED = False

        calculated_size = await risk_manager.calculate_position_size(
            "BTC/USDT", equity, risk_percentage=risk_pct, stop_loss_pct=sl_pct, current_drawdown=dd_level
        )
        risk_config.VOLATILITY_SCALING_ENABLED = original_vol_scaling # Restore

        expected_size = unscaled_size_no_dd * expected_factor
        assert calculated_size == pytest.approx(expected_size, rel=Decimal("0.01")), \
            f"Mismatch for DD {dd_level*100}%. Expected size ~{expected_size:.2f}, got {calculated_size:.2f}"

    # Restore original settings
    risk_config.DRAWDOWN_CONTROL_ENABLED = original_dd_control_enabled
    risk_config.MAX_DRAWDOWN_THRESHOLD = original_max_dd_thresh
    risk_config.CRITICAL_DRAWDOWN_THRESHOLD = original_crit_dd_thresh
    risk_config.DRAWDOWN_SCALING_FACTOR = original_dd_scaling_factor

@pytest.mark.asyncio
async def test_risk_manager_calculate_position_size_with_volatility_scaling(risk_manager: RiskManager, portfolio_manager: PortfolioManager):
    """Test position size calculation with volatility scaling adjustment"""
    # Mock portfolio service methods to control volatility
    # Scenario 1: Low volatility (below baseline) - no scaling or minimal scaling expected
    portfolio_manager.get_position_risk = AsyncMock(return_value={"volatility": 0.3, "correlation_risk": 0.2}) # VOLATILITY_BASELINE is 0.5
    portfolio_manager.get_drawdown_metrics = MagicMock(return_value={"current_drawdown": Decimal("0.0")})
    
    original_vol_scaling_enabled = risk_config.VOLATILITY_SCALING_ENABLED
    risk_config.VOLATILITY_SCALING_ENABLED = True

    size_low_vol = await risk_manager.calculate_position_size(
        "BTC/USDT", Decimal("100000"), risk_percentage=Decimal("0.01"), stop_loss_pct=Decimal("0.05")
    )

    # Scenario 2: High volatility (above baseline) - scaling should reduce size
    portfolio_manager.get_position_risk = AsyncMock(return_value={"volatility": 0.8, "correlation_risk": 0.2}) # Above VOLATILITY_BASELINE
    size_high_vol = await risk_manager.calculate_position_size(
        "BTC/USDT", Decimal("100000"), risk_percentage=Decimal("0.01"), stop_loss_pct=Decimal("0.05")
    )
    
    # Scenario 3: Volatility scaling disabled
    risk_config.VOLATILITY_SCALING_ENABLED = False
    size_vol_disabled = await risk_manager.calculate_position_size(
        "BTC/USDT", Decimal("100000"), risk_percentage=Decimal("0.01"), stop_loss_pct=Decimal("0.05")
    )
    risk_config.VOLATILITY_SCALING_ENABLED = original_vol_scaling_enabled # Restore

    assert size_high_vol < size_low_vol, "Position size should be smaller with higher volatility when scaling is enabled."
    # When vol scaling is disabled, high vol should not lead to smaller size than low vol (assuming other factors constant)
    # For this specific test, size_vol_disabled (with high vol but scaling off) should be similar to size_low_vol (with low vol and scaling on but not really kicking in)
    # A more precise assertion would be that size_vol_disabled is what size_high_vol would be if scaling factor was 1.
    # Given the current logic, if volatility is below baseline, adjustment_factor is not applied or is 1.
    # So size_low_vol should be close to the unscaled size.
    # size_vol_disabled (with high vol but scaling off) should also be the unscaled size.
    assert size_vol_disabled == size_low_vol, "Position size should not be scaled if VOLATILITY_SCALING_ENABLED is False."
    
    # Test that very high volatility doesn't reduce size below 25% of the unscaled size
    # Unscaled size for 100k equity, 1% risk, 5% SL = 100000 * 0.01 / 0.05 = 20000
    # Max order size is 10000, so unscaled is capped at 10000.
    # Min expected size = 10000 * 0.25 = 2500
    portfolio_manager.get_position_risk = AsyncMock(return_value={"volatility": 2.0, "correlation_risk": 0.2}) # Very high volatility
    risk_config.VOLATILITY_SCALING_ENABLED = True
    size_very_high_vol = await risk_manager.calculate_position_size(
        "BTC/USDT", Decimal("100000"), risk_percentage=Decimal("0.01"), stop_loss_pct=Decimal("0.05")
    )
    risk_config.VOLATILITY_SCALING_ENABLED = original_vol_scaling_enabled # Restore
    
    unscaled_size_capped = min( (Decimal("100000") * Decimal("0.01")) / Decimal("0.05") , risk_config.MAX_ORDER_SIZE)
    min_expected_size_due_to_vol = unscaled_size_capped * Decimal("0.25")

    assert size_very_high_vol >= min_expected_size_due_to_vol, "Position size should not go below 25% due to extreme volatility."


@pytest.mark.asyncio
async def test_circuit_breaker_functionality():
    """Test circuit breaker functionality"""
    # Create a circuit breaker
    cb = CircuitBreaker("BTC/USDT", Decimal("0.05"), 60)
    
    # Initial state
    assert cb.is_triggered() is False
    
    # Small price movements shouldn't trigger
    cb.update_price(Decimal("50000"))
    cb.update_price(Decimal("50100"))  # 0.2% increase
    assert cb.is_triggered() is False
    
    # Large price movement should trigger
    cb.update_price(Decimal("52600"))  # 5.2% increase from 50000
    assert cb.is_triggered() is True
    
    # Should remain triggered during cooldown
    cb.update_price(Decimal("52000"))
    assert cb.is_triggered() is True
    
    # Force reset for testing
    cb.force_reset()
    assert cb.is_triggered() is False

@pytest.mark.asyncio
async def test_trading_engine_risk_integration(trading_engine):
    """Test trading engine integration with risk management"""
    # Start the engine
    await trading_engine.start()
    
    # Create a test order
    order = Order(
        id="test_order",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=0.1,
        price=50000
    )
    
    # Place the order
    result = await trading_engine.place_order(order)
    
    # Verify risk validation was called
    trading_engine.risk_manager.validate_order.assert_called_once()
    
    # Verify order was placed
    trading_engine.exchange.create_order.assert_called_once()
    
    # Verify order status
    assert result.status == OrderStatus.OPEN

@pytest.mark.asyncio
async def test_trading_engine_risk_rejection(trading_engine):
    """Test trading engine rejection of risky orders"""
    # Configure risk manager to reject orders
    trading_engine.risk_manager.validate_order = AsyncMock(return_value=(False, "Order exceeds risk limits"))
    
    # Create a test order
    order = Order(
        id="test_order",
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=0.1,
        price=50000
    )
    
    # Place the order - should raise ValueError
    with pytest.raises(ValueError, match="Order rejected by risk manager"):
        await trading_engine.place_order(order)
    
    # Verify risk validation was called
    trading_engine.risk_manager.validate_order.assert_called_once()
    
    # Verify order was not placed
    trading_engine.exchange.create_order.assert_not_called()

@pytest.mark.asyncio
async def test_portfolio_manager_position_tracking(portfolio_manager):
    """Test portfolio manager position tracking"""
    # Add a position
    position = await portfolio_manager.add_position(
        "BTC/USDT",
        Decimal("0.5"),
        Decimal("50000")
    )
    
    # Verify position was added
    assert "BTC/USDT" in portfolio_manager.positions
    assert portfolio_manager.positions["BTC/USDT"]["quantity"] == Decimal("0.5")
    assert portfolio_manager.positions["BTC/USDT"]["value"] == Decimal("25000")
    
    # Update position price
    updated = await portfolio_manager.update_position_price(
        "BTC/USDT",
        Decimal("52000")
    )
    
    # Verify position was updated
    assert updated["value"] == Decimal("26000")  # 0.5 * 52000
    assert updated["pnl"] == Decimal("1000")  # (52000 - 50000) * 0.5
    
    # Close position
    closed = await portfolio_manager.close_position(
        "BTC/USDT",
        Decimal("53000")
    )
    
    # Verify position was closed
    assert "BTC/USDT" not in portfolio_manager.positions
    assert closed["pnl"] == Decimal("1500")  # (53000 - 50000) * 0.5
    assert closed["pnl_pct"] == Decimal("0.06")  # 1500 / 25000

@pytest.mark.asyncio
async def test_risk_report_generation(risk_manager):
    """Test risk report generation"""
    # Generate risk report
    report = await risk_manager.get_risk_report()
    
    # Verify report structure
    assert "timestamp" in report
    assert "trading_status" in report
    assert "account" in report
    assert "drawdown" in report
    assert "risk_metrics" in report
    assert "limits" in report
    assert "circuit_breakers" in report

@pytest.mark.asyncio
async def test_basic_risk_rules_position_size(trading_engine):
   """Test basic risk rules for position size"""
   # Create a test order
   order = Order(
       id="test_order",
       symbol="BTC/USDT",
       side="buy",
       type="limit",
       amount=100000,  # Exceeds max position size of 0.1 * 100000 = 10000
       price=50000
   )

   # Place the order - should raise ValueError
   with pytest.raises(ValueError, match="Order exceeds maximum position size"):
       await trading_engine.place_order(order)

@pytest.mark.asyncio
async def test_basic_risk_rules_portfolio_risk(trading_engine, portfolio_manager):
   """Test basic risk rules for portfolio risk"""
   # Set up initial position
   await portfolio_manager.add_position("ETH/USDT", Decimal("0.2"), Decimal("3000"))

   # Create a test order that exceeds portfolio risk
   order = Order(
       id="test_order",
       symbol="BTC/USDT",
       side="buy",
       type="limit",
       amount=50000,  # Exceeds max portfolio risk of 0.3 * 100000 = 30000
       price=50000
   )

   # Place the order - should raise ValueError
   with pytest.raises(ValueError, match="Order exceeds maximum portfolio risk"):
       await trading_engine.place_order(order)

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])