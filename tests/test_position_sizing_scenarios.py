import pytest
import asyncio
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from trade.services.risk import RiskService

@pytest.fixture
def mock_volatility():
    """Mock the get_historical_volatility function"""
    with patch('trade.services.risk.get_historical_volatility') as mock_vol:
        yield mock_vol

@pytest.mark.asyncio
async def test_position_sizing_volatility_scaling():
    """Test position sizing with different volatility levels"""
    # Enable volatility scaling
    original_setting = RiskService.VOLATILITY_SCALING_ENABLED
    RiskService.VOLATILITY_SCALING_ENABLED = True
    
    try:
        # Test with different volatility levels
        volatility_levels = [0.3, 0.5, 0.7, 0.9, 1.2]
        position_sizes = []
        
        for vol in volatility_levels:
            with patch('trade.services.risk.get_historical_volatility', return_value=vol):
                size = await RiskService.calculate_position_size(
                    "BTC/USDT",
                    Decimal("100000"),
                    volatility_factor=True
                )
                position_sizes.append(float(size))
        
        # Verify that position sizes decrease as volatility increases
        for i in range(1, len(position_sizes)):
            assert position_sizes[i] < position_sizes[i-1], f"Position size should decrease with higher volatility: {position_sizes}"
        
        # Verify that even with very high volatility, position size doesn't go below 25% of baseline
        baseline_size = 1000  # 1% of 100,000
        min_expected_size = baseline_size * 0.25
        assert position_sizes[-1] >= min_expected_size
        
    finally:
        # Restore original setting
        RiskService.VOLATILITY_SCALING_ENABLED = original_setting

@pytest.mark.asyncio
async def test_position_sizing_with_stop_loss_and_volatility():
    """Test position sizing with both stop loss and volatility adjustment"""
    # Enable volatility scaling
    original_setting = RiskService.VOLATILITY_SCALING_ENABLED
    RiskService.VOLATILITY_SCALING_ENABLED = True
    
    try:
        # Test with different stop loss levels and volatility
        stop_loss_levels = [Decimal("0.02"), Decimal("0.05"), Decimal("0.10")]
        volatility_levels = [0.4, 0.8]
        
        results = {}
        
        for vol in volatility_levels:
            vol_results = []
            with patch('trade.services.risk.get_historical_volatility', return_value=vol):
                for stop_loss in stop_loss_levels:
                    size = await RiskService.calculate_position_size(
                        "BTC/USDT",
                        Decimal("100000"),
                        stop_loss_pct=stop_loss,
                        volatility_factor=True
                    )
                    vol_results.append(float(size))
            results[vol] = vol_results
        
        # Verify that for each volatility level, position size increases with wider stop loss
        for vol, sizes in results.items():
            for i in range(1, len(sizes)):
                assert sizes[i] < sizes[i-1], f"Position size should decrease with wider stop loss: {sizes}"
        
        # Verify that for each stop loss level, position size decreases with higher volatility
        for i in range(len(stop_loss_levels)):
            assert results[0.8][i] < results[0.4][i], "Position size should decrease with higher volatility"
        
    finally:
        # Restore original setting
        RiskService.VOLATILITY_SCALING_ENABLED = original_setting

@pytest.mark.asyncio
async def test_position_sizing_with_drawdown_control():
    """Test position sizing with drawdown control"""
    # Enable drawdown control
    original_setting = RiskService.DRAWDOWN_CONTROL_ENABLED
    RiskService.DRAWDOWN_CONTROL_ENABLED = True
    
    try:
        # Test with different drawdown levels
        drawdown_levels = [
            None,  # No drawdown
            Decimal("0.05"),  # 5% drawdown
            Decimal("0.10"),  # 10% drawdown
            Decimal("0.15"),  # 15% drawdown (MAX_DRAWDOWN_THRESHOLD)
            Decimal("0.20"),  # 20% drawdown (between MAX and CRITICAL)
            Decimal("0.25"),  # 25% drawdown (CRITICAL_DRAWDOWN_THRESHOLD)
            Decimal("0.30"),  # 30% drawdown (beyond CRITICAL)
        ]
        
        position_sizes = []
        
        for drawdown in drawdown_levels:
            size = await RiskService.calculate_position_size(
                "BTC/USDT",
                Decimal("100000"),
                volatility_factor=False,
                current_drawdown=drawdown
            )
            position_sizes.append(float(size))
        
        # Verify that position sizes decrease as drawdown increases
        for i in range(1, len(position_sizes)):
            assert position_sizes[i] <= position_sizes[i-1], f"Position size should decrease with higher drawdown: {position_sizes}"
        
        # Verify specific thresholds
        baseline_size = position_sizes[0]  # No drawdown
        
        # At 5% drawdown, should be full size
        assert position_sizes[1] == baseline_size
        
        # At 10% drawdown, should be reduced
        assert position_sizes[2] < baseline_size
        
        # At critical drawdown (25%), should be 10% of normal size
        critical_index = drawdown_levels.index(Decimal("0.25"))
        assert position_sizes[critical_index] == pytest.approx(baseline_size * 0.1)
        
        # Beyond critical drawdown, should remain at 10% of normal size
        assert position_sizes[-1] == pytest.approx(baseline_size * 0.1)
        
    finally:
        # Restore original setting
        RiskService.DRAWDOWN_CONTROL_ENABLED = original_setting

@pytest.mark.asyncio
async def test_position_sizing_with_custom_risk_tolerance():
    """Test position sizing with custom risk tolerance levels"""
    # Test with different risk tolerance levels
    risk_levels = [
        Decimal("0.005"),  # 0.5% risk (conservative)
        Decimal("0.01"),   # 1% risk (default)
        Decimal("0.02"),   # 2% risk (aggressive)
        Decimal("0.05"),   # 5% risk (very aggressive)
    ]
    
    position_sizes = []
    
    for risk in risk_levels:
        size = await RiskService.calculate_position_size(
            "BTC/USDT",
            Decimal("100000"),
            volatility_factor=False,
            risk_tolerance=risk
        )
        position_sizes.append(float(size))
    
    # Verify that position sizes increase linearly with risk tolerance
    for i in range(1, len(position_sizes)):
        expected_ratio = float(risk_levels[i] / risk_levels[i-1])
        actual_ratio = position_sizes[i] / position_sizes[i-1]
        assert actual_ratio == pytest.approx(expected_ratio, abs=1e-2)

@pytest.mark.asyncio
async def test_position_sizing_interaction_all_factors():
    """Test position sizing with all factors interacting"""
    # Enable all controls
    original_vol_setting = RiskService.VOLATILITY_SCALING_ENABLED
    original_dd_setting = RiskService.DRAWDOWN_CONTROL_ENABLED
    RiskService.VOLATILITY_SCALING_ENABLED = True
    RiskService.DRAWDOWN_CONTROL_ENABLED = True
    
    try:
        # Define test scenarios
        scenarios = [
            # (volatility, drawdown, stop_loss, risk_tolerance)
            (0.5, None, None, None),  # Baseline
            (0.8, None, None, None),  # High volatility only
            (0.5, Decimal("0.15"), None, None),  # Drawdown only
            (0.5, None, Decimal("0.05"), None),  # Stop loss only
            (0.5, None, None, Decimal("0.02")),  # Risk tolerance only
            (0.8, Decimal("0.15"), Decimal("0.05"), Decimal("0.02")),  # All factors
        ]
        
        results = []
        
        for vol, drawdown, stop_loss, risk in scenarios:
            with patch('trade.services.risk.get_historical_volatility', return_value=vol):
                size = await RiskService.calculate_position_size(
                    "BTC/USDT",
                    Decimal("100000"),
                    stop_loss_pct=stop_loss,
                    volatility_factor=True,
                    current_drawdown=drawdown,
                    risk_tolerance=risk
                )
                results.append(float(size))
        
        # Baseline
        baseline = results[0]
        
        # High volatility should reduce position size
        assert results[1] < baseline
        
        # Drawdown should reduce position size
        assert results[2] < baseline
        
        # Stop loss should increase position size
        assert results[3] > baseline
        
        # Higher risk tolerance should increase position size
        assert results[4] > baseline
        
        # Combined factors - the effect depends on the specific values
        # In this case, high volatility and drawdown should reduce size,
        # while stop loss and higher risk tolerance increase it
        # The net effect depends on the magnitude of each factor
        
    finally:
        # Restore original settings
        RiskService.VOLATILITY_SCALING_ENABLED = original_vol_setting
        RiskService.DRAWDOWN_CONTROL_ENABLED = original_dd_setting

@pytest.mark.asyncio
async def test_maximum_drawdown_controls():
    """Test that position sizing respects maximum drawdown controls"""
    # Enable drawdown control
    original_setting = RiskService.DRAWDOWN_CONTROL_ENABLED
    RiskService.DRAWDOWN_CONTROL_ENABLED = True
    
    # Save original thresholds
    original_max = RiskService.MAX_DRAWDOWN_THRESHOLD
    original_critical = RiskService.CRITICAL_DRAWDOWN_THRESHOLD
    
    try:
        # Modify thresholds for testing
        RiskService.MAX_DRAWDOWN_THRESHOLD = Decimal("0.10")  # 10%
        RiskService.CRITICAL_DRAWDOWN_THRESHOLD = Decimal("0.20")  # 20%
        
        # Test with drawdown just below, at, and above thresholds
        drawdown_levels = [
            Decimal("0.09"),  # Just below MAX
            Decimal("0.10"),  # At MAX
            Decimal("0.11"),  # Just above MAX
            Decimal("0.19"),  # Just below CRITICAL
            Decimal("0.20"),  # At CRITICAL
            Decimal("0.21"),  # Just above CRITICAL
        ]
        
        position_sizes = []
        
        for drawdown in drawdown_levels:
            size = await RiskService.calculate_position_size(
                "BTC/USDT",
                Decimal("100000"),
                volatility_factor=False,
                current_drawdown=drawdown
            )
            position_sizes.append(float(size))
        
        # Verify threshold behavior
        # Below MAX should have minimal reduction
        assert position_sizes[0] > 900  # Some reduction but not severe
        
        # At MAX should have moderate reduction
        assert position_sizes[1] < position_sizes[0]
        
        # Above MAX but below CRITICAL should have significant reduction
        assert position_sizes[2] < position_sizes[1]
        assert position_sizes[3] < position_sizes[2]
        
        # At CRITICAL should be 25% of normal
        assert position_sizes[4] == pytest.approx(250, abs=1)
        
        # Above CRITICAL should be 10% of normal
        assert position_sizes[5] == pytest.approx(100, abs=1)
        
    finally:
        # Restore original settings
        RiskService.DRAWDOWN_CONTROL_ENABLED = original_setting
        RiskService.MAX_DRAWDOWN_THRESHOLD = original_max
        RiskService.CRITICAL_DRAWDOWN_THRESHOLD = original_critical

@pytest.mark.asyncio
async def test_order_validation_with_position_sizing():
    """Test order validation with position sizing"""
    from trade.schemas.trade import MarketOrder, RiskParameters
    
    # Create orders with different sizes
    orders = [
        # Within recommended size
        MarketOrder(
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            amount=Decimal("900"),  # 90% of recommended
            type="market"
        ),
        # Slightly over recommended size
        MarketOrder(
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            amount=Decimal("1100"),  # 110% of recommended
            type="market"
        ),
        # Significantly over recommended size
        MarketOrder(
            exchange="binance",
            symbol="BTC/USDT",
            side="buy",
            amount=Decimal("1600"),  # 160% of recommended
            type="market"
        ),
    ]
    
    # Mock calculate_position_size to return a fixed value
    with patch.object(RiskService, 'calculate_position_size', return_value=Decimal("1000")):
        # Within recommended size should pass
        await RiskService.validate_order(orders[0], Decimal("100000"))
        
        # Slightly over should pass with warning (would be logged)
        await RiskService.validate_order(orders[1], Decimal("100000"))
        
        # Significantly over should fail
        with pytest.raises(ValueError, match="significantly exceeds"):
            await RiskService.validate_order(orders[2], Decimal("100000"))