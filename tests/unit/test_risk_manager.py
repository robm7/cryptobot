import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from trade.services.risk_manager import RiskManager
from trade.services.portfolio_manager import PortfolioManager # For type hinting, will be mocked
from trade.utils.metrics import MetricsCollector
from trade.utils.alerting import AlertManager
from trade.utils.circuit_breaker import CircuitBreaker
from trade.config import risk_config # For default values
from trade.schemas.trade import LimitOrder # For order validation tests

@pytest.fixture
def mock_portfolio_service():
    service = AsyncMock(spec=PortfolioManager) # Use PortfolioManager spec
    service.get_account_equity.return_value = Decimal("100000")
    service.calculate_portfolio_risk.return_value = {
        "total_exposure": Decimal("50000"),
        "current_drawdown": Decimal("0.05"),
        "max_drawdown_metric": Decimal("0.10"),
        "position_count": 2,
        # Add other fields as expected by RiskManager
    }
    service.get_drawdown_metrics.return_value = {
        "current_drawdown": Decimal("0.05"),
        "max_drawdown": Decimal("0.10")
    }
    service.get_symbol_exposure.return_value = Decimal("10000")
    service.get_portfolio_value.return_value = Decimal("95000") # Account equity - unrealized PnL
    service.get_total_exposure.return_value = Decimal("50000")
    service.get_position_risk.return_value = { # For validate_order correlation check
        "correlation_risk": Decimal("0.3")
    }
    return service

@pytest.fixture
def mock_metrics_collector():
    return AsyncMock(spec=MetricsCollector)

@pytest.fixture
def mock_alert_manager():
    return AsyncMock(spec=AlertManager)

@pytest.fixture
@patch('trade.services.risk_manager.AlertManager', new_callable=AsyncMock)
def risk_manager(mock_alert_manager_class, mock_portfolio_service, mock_metrics_collector):
    # Ensure AlertManager() inside RiskManager uses the mock
    mock_alert_manager_instance = mock_alert_manager_class.return_value
    
    manager = RiskManager(portfolio_service=mock_portfolio_service, metrics_collector=mock_metrics_collector)
    # Replace the instance if it was already created with a real one
    manager.alert_manager = mock_alert_manager_instance 
    return manager

def test_risk_manager_init(risk_manager: RiskManager, mock_portfolio_service, mock_metrics_collector):
    assert risk_manager.portfolio_service == mock_portfolio_service
    assert risk_manager.metrics_collector == mock_metrics_collector
    assert isinstance(risk_manager.alert_manager, AsyncMock) # Check it's the mocked instance
    assert not risk_manager.trading_halted
    assert risk_manager.risk_limits == risk_config.get_risk_limits()

@pytest.mark.asyncio
async def test_start_stop_monitoring(risk_manager: RiskManager):
    assert risk_manager.monitoring_task is None
    assert not risk_manager.monitoring_active

    # Mock the loop to prevent it from actually running indefinitely
    with patch.object(risk_manager, '_risk_monitoring_loop', new_callable=AsyncMock) as mock_loop:
        await risk_manager.start_monitoring()
        assert risk_manager.monitoring_task is not None
        assert risk_manager.monitoring_active
        await asyncio.sleep(0.01) # Give event loop time to start task
        mock_loop.assert_awaited_once()

        await risk_manager.stop_monitoring()
        assert risk_manager.monitoring_task is None
        assert not risk_manager.monitoring_active
        # Check if cancel was called on the task if it was running
        # This is tricky as the task is replaced by None.
        # We rely on the loop mock not being called again after stop.

@pytest.mark.asyncio
async def test_reset_time_based_counters_daily(risk_manager: RiskManager):
    risk_manager.daily_trades_count = {"BTCUSDT": 5}
    risk_manager.daily_pnl = {"BTCUSDT": Decimal("100")}
    risk_manager.last_daily_reset = datetime.now() - timedelta(days=1)
    
    await risk_manager._reset_time_based_counters()
    
    assert risk_manager.daily_trades_count == {}
    assert risk_manager.daily_pnl == {}
    assert risk_manager.last_daily_reset.date() == datetime.now().date()

@pytest.mark.asyncio
async def test_reset_time_based_counters_weekly(risk_manager: RiskManager):
    risk_manager.weekly_pnl = {"BTCUSDT": Decimal("500")}
    risk_manager.last_weekly_reset = datetime.now() - timedelta(weeks=1)

    await risk_manager._reset_time_based_counters()

    assert risk_manager.weekly_pnl == {}
    assert risk_manager.last_weekly_reset.date() == datetime.now().date()

@pytest.mark.asyncio
async def test_reset_time_based_counters_no_reset_needed(risk_manager: RiskManager):
    risk_manager.daily_trades_count = {"BTCUSDT": 1}
    risk_manager.daily_pnl = {"BTCUSDT": Decimal("10")}
    risk_manager.weekly_pnl = {"BTCUSDT": Decimal("50")}
    
    # Set last resets to earlier today
    now = datetime.now()
    risk_manager.last_daily_reset = now - timedelta(hours=1)
    risk_manager.last_weekly_reset = now - timedelta(days=1) # Assuming it's not a week boundary

    original_daily_counts = risk_manager.daily_trades_count.copy()
    original_daily_pnl = risk_manager.daily_pnl.copy()
    original_weekly_pnl = risk_manager.weekly_pnl.copy()

    await risk_manager._reset_time_based_counters()

    assert risk_manager.daily_trades_count == original_daily_counts
    assert risk_manager.daily_pnl == original_daily_pnl
    assert risk_manager.weekly_pnl == original_weekly_pnl


@pytest.mark.asyncio
async def test_halt_and_resume_trading(risk_manager: RiskManager):
    reason_halt = "Test halt"
    await risk_manager._halt_trading(reason_halt)
    assert risk_manager.trading_halted is True
    assert risk_manager.trading_halt_reason == reason_halt
    risk_manager.alert_manager.send_alert.assert_awaited_with(
        "TRADING HALTED", f"Reason: {reason_halt}", level="critical"
    )

    reason_resume = "Test resume"
    risk_manager._resume_trading(reason_resume) # This is a sync method
    assert risk_manager.trading_halted is False
    assert risk_manager.trading_halt_reason == ""
    risk_manager.alert_manager.send_alert.assert_awaited_with(
        "Trading resumed", f"Reason: {reason_resume}", level="info"
    )

@pytest.mark.asyncio
async def test_check_risk_metrics_critical_drawdown_halt(risk_manager: RiskManager, mock_portfolio_service):
    mock_portfolio_service.calculate_portfolio_risk.return_value["current_drawdown"] = risk_config.CRITICAL_DRAWDOWN_THRESHOLD + Decimal("0.01")
    
    with patch.object(risk_manager, '_halt_trading', new_callable=AsyncMock) as mock_halt:
        await risk_manager._check_risk_metrics()
        mock_halt.assert_awaited_once()
        assert "Critical drawdown threshold exceeded" in mock_halt.call_args[0][0]

@pytest.mark.asyncio
async def test_check_risk_metrics_excessive_exposure_alert(risk_manager: RiskManager, mock_portfolio_service):
    # Ensure CRITICAL_DRAWDOWN_THRESHOLD is not met
    mock_portfolio_service.calculate_portfolio_risk.return_value["current_drawdown"] = risk_config.CRITICAL_DRAWDOWN_THRESHOLD - Decimal("0.05")
    
    # Set exposure to exceed limit
    limit_exposure = risk_manager.risk_limits["max_portfolio_exposure"]
    mock_portfolio_service.calculate_portfolio_risk.return_value["total_exposure"] = limit_exposure + Decimal("1000")

    with patch.object(risk_manager, '_halt_trading', new_callable=AsyncMock) as mock_halt:
        await risk_manager._check_risk_metrics()
        mock_halt.assert_not_awaited() # Should not halt for exposure alone
        risk_manager.alert_manager.send_alert.assert_awaited_with(
            "Portfolio exposure exceeds limit",
            f"Current exposure: {float(limit_exposure + Decimal('1000'))}, Limit: {float(limit_exposure)}"
        )

@pytest.mark.asyncio
async def test_check_risk_metrics_daily_drawdown_halt(risk_manager: RiskManager, mock_portfolio_service):
    # Ensure CRITICAL_DRAWDOWN_THRESHOLD is not met
    mock_portfolio_service.calculate_portfolio_risk.return_value["current_drawdown"] = Decimal("0.01")
    mock_portfolio_service.get_account_equity.return_value = Decimal("100000")
    
    # Simulate daily PnL leading to drawdown > limit
    limit_daily_dd = risk_manager.risk_limits["max_daily_drawdown"] # e.g., 0.02
    loss_amount = -(limit_daily_dd + Decimal("0.01")) * Decimal("100000") # Loss > 2% of 100k
    risk_manager.daily_pnl = {"ANY_SYMBOL": loss_amount}

    with patch.object(risk_manager, '_halt_trading', new_callable=AsyncMock) as mock_halt:
        await risk_manager._check_risk_metrics()
        mock_halt.assert_awaited_once()
        assert "Daily drawdown limit exceeded" in mock_halt.call_args[0][0]

@pytest.mark.asyncio
async def test_check_risk_metrics_weekly_drawdown_halt(risk_manager: RiskManager, mock_portfolio_service):
    mock_portfolio_service.calculate_portfolio_risk.return_value["current_drawdown"] = Decimal("0.01")
    mock_portfolio_service.get_account_equity.return_value = Decimal("100000")
    risk_manager.daily_pnl = {} # No daily issue

    limit_weekly_dd = risk_manager.risk_limits["max_weekly_drawdown"] # e.g., 0.05
    loss_amount = -(limit_weekly_dd + Decimal("0.01")) * Decimal("100000")
    risk_manager.weekly_pnl = {"ANY_SYMBOL": loss_amount}

    with patch.object(risk_manager, '_halt_trading', new_callable=AsyncMock) as mock_halt:
        await risk_manager._check_risk_metrics()
        mock_halt.assert_awaited_once()
        assert "Weekly drawdown limit exceeded" in mock_halt.call_args[0][0]

@pytest.mark.asyncio
async def test_check_risk_metrics_resume_trading(risk_manager: RiskManager, mock_portfolio_service):
    # First, halt trading
    await risk_manager._halt_trading("Initial halt due to critical drawdown")
    risk_manager.alert_manager.reset_mock() # Reset mock after halt alert

    # Now, simulate improved conditions
    improved_drawdown = risk_config.CRITICAL_DRAWDOWN_THRESHOLD * Decimal("0.7") # Below 0.8 threshold
    mock_portfolio_service.calculate_portfolio_risk.return_value["current_drawdown"] = improved_drawdown
    mock_portfolio_service.calculate_portfolio_risk.return_value["total_exposure"] = risk_manager.risk_limits["max_portfolio_exposure"] - Decimal("1000")
    risk_manager.daily_pnl = {}
    risk_manager.weekly_pnl = {}
    
    with patch.object(risk_manager, '_resume_trading') as mock_resume: # _resume_trading is sync
        await risk_manager._check_risk_metrics()
        mock_resume.assert_called_once_with("Risk conditions have improved")
        assert risk_manager.trading_halted is False # Check side effect of _resume_trading

def test_register_circuit_breaker(risk_manager: RiskManager):
    symbol = "BTCUSDT"
    threshold = Decimal("0.05")
    cooldown = 10 # minutes

    risk_manager.register_circuit_breaker(symbol, threshold, cooldown)
    
    assert symbol in risk_manager.circuit_breakers
    breaker = risk_manager.circuit_breakers[symbol]
    assert isinstance(breaker, CircuitBreaker)
    assert breaker.symbol == symbol
    assert breaker.threshold == threshold
    assert breaker.cooldown_seconds == cooldown * 60

def test_register_circuit_breaker_defaults(risk_manager: RiskManager):
    symbol = "ETHUSDT"
    risk_manager.register_circuit_breaker(symbol)
    assert symbol in risk_manager.circuit_breakers
    breaker = risk_manager.circuit_breakers[symbol]
    assert breaker.threshold == risk_config.CIRCUIT_BREAKER_THRESHOLD
    assert breaker.cooldown_seconds == risk_config.CIRCUIT_BREAKER_COOLDOWN_MINUTES * 60

@pytest.mark.asyncio
async def test_update_trade_metrics(risk_manager: RiskManager, mock_metrics_collector):
    symbol = "BTCUSDT"
    pnl1 = Decimal("50")
    pnl2 = Decimal("-20")

    await risk_manager.update_trade_metrics(symbol, pnl1)
    assert risk_manager.daily_trades_count[symbol] == 1
    assert risk_manager.daily_pnl[symbol] == pnl1
    assert risk_manager.weekly_pnl[symbol] == pnl1
    mock_metrics_collector.record_counter.assert_any_call(f"trades.count.{symbol}", 1)
    mock_metrics_collector.record_gauge.assert_any_call(f"trades.pnl.daily.{symbol}", float(pnl1))

    await risk_manager.update_trade_metrics(symbol, pnl2)
    assert risk_manager.daily_trades_count[symbol] == 2
    assert risk_manager.daily_pnl[symbol] == pnl1 + pnl2
    assert risk_manager.weekly_pnl[symbol] == pnl1 + pnl2
    mock_metrics_collector.record_counter.assert_any_call(f"trades.count.{symbol}", 1) # Called again
    mock_metrics_collector.record_gauge.assert_any_call(f"trades.pnl.daily.{symbol}", float(pnl1 + pnl2))

# Placeholder for order schema for validation tests
mock_order_data_limit = {
    "symbol": "BTCUSDT",
    "side": "buy",
    "amount": Decimal("0.1"),
    "price": Decimal("50000"),
    "type": "limit"
}
mock_order_limit = LimitOrder(**mock_order_data_limit)

@pytest.mark.asyncio
async def test_validate_order_trading_halted(risk_manager: RiskManager):
    await risk_manager._halt_trading("Maintenance")
    is_valid, reason = await risk_manager.validate_order(mock_order_limit)
    assert not is_valid
    assert "Trading is currently halted: Maintenance" in reason

@pytest.mark.asyncio
async def test_validate_order_circuit_breaker_triggered(risk_manager: RiskManager):
    symbol = "BTCUSDT"
    risk_manager.register_circuit_breaker(symbol)
    # Manually trigger breaker for test
    risk_manager.circuit_breakers[symbol].trigger_event(Decimal("100"), datetime.now()) 
    
    order_btc = LimitOrder(symbol=symbol, side="buy", amount=Decimal("0.1"), price=Decimal("60000"), type="limit")
    is_valid, reason = await risk_manager.validate_order(order_btc)
    assert not is_valid
    assert f"Circuit breaker triggered for {symbol}" in reason

@pytest.mark.asyncio
async def test_validate_order_max_order_size_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    order_value = risk_manager.risk_limits["max_order_size"] + Decimal("1")
    # Mock _calculate_order_value to control the exact value being checked
    with patch.object(risk_manager, '_calculate_order_value', return_value=order_value):
        is_valid, reason = await risk_manager.validate_order(mock_order_limit)
        assert not is_valid
        assert f"Order size ({float(order_value)}) exceeds maximum allowed" in reason

@pytest.mark.asyncio
async def test_validate_order_risk_per_trade_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    account_equity = await mock_portfolio_service.get_account_equity()
    max_allowed_risk_abs = account_equity * risk_manager.risk_limits["risk_per_trade"]
    order_risk = max_allowed_risk_abs + Decimal("1")

    with patch.object(risk_manager, '_calculate_order_risk', return_value=order_risk):
        is_valid, reason = await risk_manager.validate_order(mock_order_limit, account_equity=account_equity)
        assert not is_valid
        assert f"Order risk ({float(order_risk)}) exceeds maximum allowed ({float(max_allowed_risk_abs)})" in reason

@pytest.mark.asyncio
async def test_validate_order_symbol_exposure_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    order_value = Decimal("5000") # Value of the incoming order
    current_exposure = risk_manager.risk_limits["max_symbol_exposure"] - order_value + Decimal("1") # Current exposure is such that new order will exceed
    
    mock_portfolio_service.get_symbol_exposure.return_value = current_exposure
    
    with patch.object(risk_manager, '_calculate_order_value', return_value=order_value):
        is_valid, reason = await risk_manager.validate_order(mock_order_limit) # Assuming mock_order_limit is a 'buy'
        new_exposure_val = current_exposure + order_value
        assert not is_valid
        assert f"Symbol exposure ({float(new_exposure_val)}) would exceed maximum allowed" in reason

@pytest.mark.asyncio
async def test_validate_order_symbol_concentration_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    order_value = Decimal("20000") # e.g. 20k
    portfolio_value = Decimal("100000") # e.g. 100k
    # Max concentration e.g. 0.25. New concentration = 20k / 100k = 0.2
    # Let's set max_symbol_concentration to 0.1 to make this fail
    risk_manager.risk_limits["max_symbol_concentration"] = Decimal("0.1")
    
    mock_portfolio_service.get_symbol_exposure.return_value = Decimal("0") # No prior exposure for simplicity
    mock_portfolio_service.get_portfolio_value.return_value = portfolio_value - order_value # Portfolio value *before* this order's value is added for concentration calc

    with patch.object(risk_manager, '_calculate_order_value', return_value=order_value):
        is_valid, reason = await risk_manager.validate_order(mock_order_limit)
        # new_exposure is order_value. new_concentration = order_value / portfolio_value
        new_concentration_val = order_value / portfolio_value
        assert not is_valid
        assert f"Symbol concentration ({float(new_concentration_val):.2%}) would exceed maximum allowed" in reason
    risk_manager.risk_limits["max_symbol_concentration"] = risk_config.DEFAULT_MAX_SYMBOL_CONCENTRATION # Reset

@pytest.mark.asyncio
async def test_validate_order_portfolio_exposure_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    order_value = Decimal("10000")
    current_total_exposure = risk_manager.risk_limits["max_portfolio_exposure"] - order_value + Decimal("1")
    mock_portfolio_service.get_total_exposure.return_value = current_total_exposure

    with patch.object(risk_manager, '_calculate_order_value', return_value=order_value):
        is_valid, reason = await risk_manager.validate_order(mock_order_limit) # Assuming 'buy'
        new_total_exposure_val = current_total_exposure + order_value
        assert not is_valid
        assert f"Portfolio exposure ({float(new_total_exposure_val)}) would exceed maximum allowed" in reason

@pytest.mark.asyncio
async def test_validate_order_leverage_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    account_equity = Decimal("10000")
    risk_manager.risk_limits["max_leverage"] = Decimal("2.0") # Max 2x leverage
    
    # Current exposure is 15k (1.5x leverage). New order of 6k would make it 21k (2.1x leverage)
    current_total_exposure = Decimal("15000")
    order_value = Decimal("6000")
    
    mock_portfolio_service.get_account_equity.return_value = account_equity
    mock_portfolio_service.get_total_exposure.return_value = current_total_exposure

    with patch.object(risk_manager, '_calculate_order_value', return_value=order_value):
        is_valid, reason = await risk_manager.validate_order(mock_order_limit) # Assuming 'buy'
        new_total_exposure_val = current_total_exposure + order_value
        new_leverage_val = new_total_exposure_val / account_equity
        assert not is_valid
        assert f"Leverage ({float(new_leverage_val):.2f}x) would exceed maximum allowed" in reason
    risk_manager.risk_limits["max_leverage"] = risk_config.DEFAULT_MAX_LEVERAGE # Reset

@pytest.mark.asyncio
async def test_validate_order_correlation_risk_exceeded(risk_manager: RiskManager, mock_portfolio_service):
    risk_manager.risk_limits["max_correlation"] = Decimal("0.4")
    # Mock portfolio_service.get_position_risk to return high correlation
    mock_portfolio_service.get_position_risk.return_value = {"correlation_risk": Decimal("0.5")}

    is_valid, reason = await risk_manager.validate_order(mock_order_limit)
    assert not is_valid
    assert f"Correlation risk (0.50) exceeds maximum allowed (0.40)" in reason
    risk_manager.risk_limits["max_correlation"] = risk_config.DEFAULT_MAX_CORRELATION # Reset

@pytest.mark.asyncio
async def test_validate_order_daily_trade_count_exceeded(risk_manager: RiskManager):
    symbol = mock_order_limit.symbol
    risk_manager.risk_limits["max_trades_per_day"] = 5
    risk_manager.daily_trades_count[symbol] = 5 # Already at limit

    is_valid, reason = await risk_manager.validate_order(mock_order_limit)
    assert not is_valid
    assert f"Daily trade count (5) for {symbol} would exceed maximum allowed (5)" in reason
    risk_manager.risk_limits["max_trades_per_day"] = risk_config.DEFAULT_MAX_TRADES_PER_DAY # Reset

@pytest.mark.asyncio
async def test_validate_order_critical_drawdown_active_halt(risk_manager: RiskManager, mock_portfolio_service):
    # Simulate that a critical drawdown is active (e.g. > CRITICAL_DRAWDOWN_THRESHOLD)
    # This is slightly different from trading_halted flag, this checks the live drawdown value
    mock_portfolio_service.get_drawdown_metrics.return_value["current_drawdown"] = risk_config.CRITICAL_DRAWDOWN_THRESHOLD + Decimal("0.01")
    
    is_valid, reason = await risk_manager.validate_order(mock_order_limit)
    assert not is_valid
    assert "Trading halted - drawdown" in reason
    assert f"exceeds critical threshold ({float(risk_config.CRITICAL_DRAWDOWN_THRESHOLD):.2%})" in reason

@pytest.mark.asyncio
async def test_validate_order_success(risk_manager: RiskManager, mock_portfolio_service):
    # Ensure all conditions are met for success
    risk_manager.trading_halted = False
    if mock_order_limit.symbol in risk_manager.circuit_breakers:
        risk_manager.circuit_breakers[mock_order_limit.symbol]._triggered = False # Ensure not triggered
    
    mock_portfolio_service.get_drawdown_metrics.return_value["current_drawdown"] = Decimal("0.01") # Low drawdown
    risk_manager.daily_trades_count[mock_order_limit.symbol] = 1 # Not at limit
    
    # Mock portfolio service calls to return values within limits
    mock_portfolio_service.get_symbol_exposure.return_value = Decimal("1000")
    mock_portfolio_service.get_portfolio_value.return_value = Decimal("100000")
    mock_portfolio_service.get_total_exposure.return_value = Decimal("20000")
    mock_portfolio_service.get_account_equity.return_value = Decimal("80000") # e.g. unrealized loss
    mock_portfolio_service.get_position_risk.return_value = {"correlation_risk": Decimal("0.1")}

    # Mock calculation helpers
    with patch.object(risk_manager, '_calculate_order_value', return_value=Decimal("5000")), \
         patch.object(risk_manager, '_calculate_order_risk', return_value=Decimal("50")): # 50 is < (80000 * risk_per_trade)
        
        is_valid, reason = await risk_manager.validate_order(mock_order_limit)
        assert is_valid is True
        assert reason is None

@pytest.mark.asyncio
@patch('trade.config.risk_config.VOLATILITY_SCALING_ENABLED', True)
@patch('trade.config.risk_config.DRAWDOWN_CONTROL_ENABLED', True)
async def test_calculate_position_size_all_factors(risk_manager: RiskManager, mock_portfolio_service):
    symbol = "XYZUSDT"
    account_equity = Decimal("100000")
    risk_percentage = Decimal("0.01") # Risk 1% of equity = 1000
    stop_loss_pct = Decimal("0.05") # Stop loss at 5%
    
    # Base size before SL: 100000 * 0.01 = 1000
    # Base size after SL: 1000 / 0.05 = 20000

    # Mock portfolio service calls for this specific test
    # Volatility significantly above baseline
    mock_portfolio_service.get_position_risk.side_effect = [
        {"volatility": risk_config.VOLATILITY_BASELINE * Decimal("2"), "correlation_risk": Decimal("0.2")}, # First call for volatility
        {"volatility": risk_config.VOLATILITY_BASELINE * Decimal("2"), "correlation_risk": Decimal("0.6")}  # Second call for correlation
    ]
    # Current drawdown is moderate
    mock_portfolio_service.get_drawdown_metrics.return_value = {"current_drawdown": Decimal("0.10")} # 10% drawdown

    # Expected calculations:
    # 1. Initial size: 20000
    # 2. Volatility adjustment:
    #    excess_vol_ratio = (2*VB / VB) - 1 = 1
    #    sqrt_excess_vol_ratio = 1
    #    adj_factor = 1 - (VOLATILITY_MAX_ADJUSTMENT * 1) = 1 - 0.5 = 0.5 (assuming MAX_ADJUSTMENT is 0.5)
    #    size_after_vol = 20000 * 0.5 = 10000
    # 3. Drawdown adjustment (10% DD):
    #    severity = (0.10 - 0.05) / (MAX_DRAWDOWN_THRESHOLD - 0.05)
    #    Assuming MAX_DRAWDOWN_THRESHOLD = 0.20, severity = 0.05 / 0.15 = 1/3
    #    reduction_factor = 1 - ( (1/3) * 0.5 * DRAWDOWN_SCALING_FACTOR )
    #    Assuming DRAWDOWN_SCALING_FACTOR = 1, reduction = 1 - (1/6) = 5/6
    #    size_after_dd = 10000 * (5/6) = 8333.33
    # 4. Correlation adjustment (corr_risk = 0.6):
    #    correlation_factor = 1.0 - (0.6 - 0.5) = 0.9
    #    size_after_corr = 8333.33 * 0.9 = 7500
    # 5. Max order size limit (e.g. 50000, so 7500 is fine)

    calculated_size = await risk_manager.calculate_position_size(
        symbol, account_equity, risk_percentage, stop_loss_pct,
        volatility_factor=True, # Explicitly true for clarity
        current_drawdown=Decimal("0.10") # Passed directly
    )
    
    # Due to complex interactions, we'll check if it's less than initial and greater than some minimal
    assert calculated_size < Decimal("20000")
    assert calculated_size > Decimal("1000") # Should not be excessively small

    # More precise checks if we fix intermediate mock values for VOLATILITY_MAX_ADJUSTMENT etc.
    # For now, this confirms factors are being applied.
    # Example: If VOLATILITY_MAX_ADJUSTMENT = 0.5, DRAWDOWN_SCALING_FACTOR = 1, MAX_DRAWDOWN_THRESHOLD = 0.20
    # Expected size around 7500.
    # Let's use pytest.approx for floating point comparisons if needed.
    # For this example, let's assume the above manual calculation is roughly correct.
    # A more robust test would mock config values or calculate expected precisely.
    
    # Check that get_position_risk was called twice (once for vol, once for corr)
    assert mock_portfolio_service.get_position_risk.call_count == 2
    mock_portfolio_service.get_drawdown_metrics.assert_not_called() # Drawdown was passed in

@pytest.mark.asyncio
async def test_calculate_position_size_no_stop_loss_no_vol_scaling(risk_manager: RiskManager, mock_portfolio_service):
    # Disable scaling for this test via patching config directly for this test's scope
    with patch('trade.config.risk_config.VOLATILITY_SCALING_ENABLED', False), \
         patch('trade.config.risk_config.DRAWDOWN_CONTROL_ENABLED', False):
        
        symbol = "ABCUSDT"
        account_equity = Decimal("50000")
        risk_percentage = Decimal("0.02") # Risk 2% = 1000
        
        # No stop loss, no volatility scaling, no drawdown passed (will use default from mock)
        # mock_portfolio_service.get_drawdown_metrics.return_value = {"current_drawdown": Decimal("0.05")}
        # mock_portfolio_service.get_position_risk.return_value = {"correlation_risk": Decimal("0.1")} # Low correlation

        # Expected size = account_equity * risk_percentage = 50000 * 0.02 = 1000
        # Correlation adjustment: (1.0 - (0.1 - 0.5)) = 1.0 (no reduction if corr_risk < 0.5)
        # So, expected size should be 1000, unless max_order_size is smaller.
        risk_manager.risk_limits["max_order_size"] = Decimal("5000") # Ensure it's not limiting here

        calculated_size = await risk_manager.calculate_position_size(
            symbol, account_equity, risk_percentage,
            stop_loss_pct=None, volatility_factor=False
        )
        
        assert calculated_size == Decimal("1000")
        mock_portfolio_service.get_position_risk.assert_called_once() # Called for correlation
        mock_portfolio_service.get_drawdown_metrics.assert_called_once() # Called as drawdown not passed

@pytest.mark.asyncio
async def test_get_risk_report_structure(risk_manager: RiskManager, mock_portfolio_service):
    # Simulate some state
    risk_manager.trading_halted = True
    risk_manager.trading_halt_reason = "Market volatility"
    risk_manager.daily_pnl = {"BTCUSDT": Decimal("-200")}
    risk_manager.weekly_pnl = {"BTCUSDT": Decimal("-500")}
    risk_manager.register_circuit_breaker("ETHUSDT")

    # Mock portfolio service calls made by get_risk_report
    mock_portfolio_service.calculate_portfolio_risk.return_value = {
        "total_exposure": Decimal("30000"), "current_drawdown": Decimal("0.08"),
        "max_drawdown_metric": Decimal("0.12"), "position_count": 1,
        "portfolio_volatility": Decimal("0.025"), "var_95": Decimal("1500"), "cvar_95": Decimal("2000"),
        "diversification_score": Decimal("0.7")
    }
    mock_portfolio_service.get_account_equity.return_value = Decimal("90000")

    report = await risk_manager.get_risk_report()

    assert "timestamp" in report
    assert report["trading_status"]["halted"] is True
    assert report["trading_status"]["halt_reason"] == "Market volatility"
    
    assert "account" in report
    assert report["account"]["equity"] == 90000.0
    assert report["account"]["total_exposure"] == 30000.0
    
    assert "drawdown" in report
    assert report["drawdown"]["current_portfolio_drawdown"] == 0.08
    assert report["drawdown"]["max_portfolio_drawdown"] == 0.12
    assert "daily_pnl_sum" in report["drawdown"]
    assert "weekly_pnl_sum" in report["drawdown"]

    assert "limits" in report
    assert report["limits"]["max_order_size"] == float(risk_manager.risk_limits["max_order_size"])

    assert "circuit_breakers" in report
    assert "ETHUSDT" in report["circuit_breakers"]
    assert "triggered" in report["circuit_breakers"]["ETHUSDT"]

    assert "portfolio_metrics" in report
    assert report["portfolio_metrics"]["volatility"] == 0.025
    assert report["portfolio_metrics"]["var_95"] == 1500

    # Check that portfolio service methods were called
    mock_portfolio_service.calculate_portfolio_risk.assert_awaited_once()
    mock_portfolio_service.get_account_equity.assert_awaited_once()