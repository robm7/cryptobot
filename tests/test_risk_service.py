import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from trade.services.risk import RiskService
from trade.schemas.trade import MarketOrder, LimitOrder, RiskParameters

@pytest.fixture
def market_order():
    return MarketOrder(
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        amount=Decimal("0.1"),
        type="market"
    )

@pytest.fixture
def limit_order():
    return LimitOrder(
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        amount=Decimal("0.1"),
        price=Decimal("50000"),
        type="limit"
    )

@pytest.mark.asyncio
async def test_calculate_position_size_basic():
    """Test basic position size calculation"""
    size = await RiskService.calculate_position_size(
        "BTC/USDT",
        Decimal("100000"),
        volatility_factor=False
    )
    assert size == Decimal("1000")  # 1% of 100,000

@pytest.mark.asyncio
async def test_calculate_position_size_with_stop_loss():
    """Test position size with stop loss"""
    size = await RiskService.calculate_position_size(
        "BTC/USDT",
        Decimal("100000"),
        stop_loss_pct=Decimal("0.05")  # 5% stop
    )
    assert size == Decimal("20000")  # 1000 / 0.05

@pytest.mark.asyncio
async def test_calculate_position_size_with_volatility():
    """Test volatility-adjusted position sizing"""
    with patch('trade.services.risk.get_historical_volatility') as mock_vol:
        mock_vol.return_value = 0.8  # 80% volatility (high)
        
        # Enable volatility scaling
        original_setting = RiskService.VOLATILITY_SCALING_ENABLED
        RiskService.VOLATILITY_SCALING_ENABLED = True
        
        try:
            size = await RiskService.calculate_position_size(
                "BTC/USDT",
                Decimal("100000"),
                volatility_factor=True
            )
            
            # With 80% volatility (vs 50% baseline), position should be reduced
            # The exact value depends on the scaling algorithm, but should be less than 1000
            assert size < Decimal("1000")
            assert size > Decimal("400")  # Should not reduce too drastically
        finally:
            # Restore original setting
            RiskService.VOLATILITY_SCALING_ENABLED = original_setting

@pytest.mark.asyncio
async def test_validate_order_max_size(market_order):
    """Test max order size validation"""
    market_order.amount = Decimal("20000")  # Exceeds max
    with pytest.raises(ValueError, match="exceeds maximum"):
        await RiskService.validate_order(market_order)

@pytest.mark.asyncio
async def test_validate_order_recommended_size(market_order):
    """Test recommended size validation"""
    with patch.object(RiskService, 'calculate_position_size') as mock_calc:
        mock_calc.return_value = Decimal("500")
        # Order is 20% over recommended
        market_order.amount = Decimal("600")
        await RiskService.validate_order(market_order, Decimal("50000"))
        # Should log warning but not raise

@pytest.mark.asyncio
async def test_validate_limit_order_price(limit_order):
    """Test limit order price validation"""
    limit_order.price = Decimal("-100")
    with pytest.raises(ValueError, match="must be positive"):
        await RiskService.validate_order(limit_order)

@pytest.mark.asyncio
async def test_validate_order_portfolio_checks(market_order):
    """Test portfolio correlation checks"""
    market_order.portfolio_service = AsyncMock()
    market_order.portfolio_service.get_position_risk.return_value = {
        'correlation_risk': 0.8,
        'concentration': 0.4
    }
    await RiskService.validate_order(market_order)
    # Should log warnings for high correlation/concentration

@pytest.mark.asyncio
async def test_performance_boundary_large_account():
    """Test position sizing with very large account"""
    size = await RiskService.calculate_position_size(
        "BTC/USDT",
        Decimal("10000000")  # 10M account
    )
    assert size == RiskService.MAX_ORDER_SIZE  # Capped at max

@pytest.mark.asyncio
async def test_performance_boundary_small_order():
    """Test very small order validation"""
    order = MarketOrder(
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        amount=Decimal("0.000001"),
        type="market"
    )
    await RiskService.validate_order(order)  # Should pass

@pytest.mark.asyncio
async def test_drawdown_control():
    """Test drawdown control on position sizing"""
    # Enable drawdown control
    original_setting = RiskService.DRAWDOWN_CONTROL_ENABLED
    RiskService.DRAWDOWN_CONTROL_ENABLED = True
    
    try:
        # Test with moderate drawdown (10%)
        size_moderate = await RiskService.calculate_position_size(
            "BTC/USDT",
            Decimal("100000"),
            volatility_factor=False,
            current_drawdown=Decimal("0.10")
        )
        
        # Test with severe drawdown (20%)
        size_severe = await RiskService.calculate_position_size(
            "BTC/USDT",
            Decimal("100000"),
            volatility_factor=False,
            current_drawdown=Decimal("0.20")
        )
        
        # Test with critical drawdown (30%)
        size_critical = await RiskService.calculate_position_size(
            "BTC/USDT",
            Decimal("100000"),
            volatility_factor=False,
            current_drawdown=Decimal("0.30")
        )
        
        # Verify progressive reduction in position size
        assert size_moderate < Decimal("1000")  # Less than base size
        assert size_severe < size_moderate  # Severe should be less than moderate
        assert size_critical < size_severe  # Critical should be less than severe
        assert size_critical == Decimal("100")  # 10% of normal size for critical drawdown
    finally:
        # Restore original setting
        RiskService.DRAWDOWN_CONTROL_ENABLED = original_setting

@pytest.mark.asyncio
async def test_custom_risk_tolerance():
    """Test custom risk tolerance parameter"""
    # Test with default risk tolerance (1%)
    size_default = await RiskService.calculate_position_size(
        "BTC/USDT",
        Decimal("100000"),
        volatility_factor=False
    )
    
    # Test with custom risk tolerance (0.5%)
    size_conservative = await RiskService.calculate_position_size(
        "BTC/USDT",
        Decimal("100000"),
        volatility_factor=False,
        risk_tolerance=Decimal("0.005")
    )
    
    # Test with custom risk tolerance (2%)
    size_aggressive = await RiskService.calculate_position_size(
        "BTC/USDT",
        Decimal("100000"),
        volatility_factor=False,
        risk_tolerance=Decimal("0.02")
    )
    
    # Verify position sizes scale with risk tolerance
    assert size_default == Decimal("1000")  # 1% of 100,000
    assert size_conservative == Decimal("500")  # 0.5% of 100,000
    assert size_aggressive == Decimal("2000")  # 2% of 100,000

@pytest.mark.asyncio
async def test_validate_order_with_risk_params():
    """Test order validation with risk parameters"""
    # Create order with risk parameters
    order = MarketOrder(
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        amount=Decimal("0.1"),
        type="market",
        risk_params=RiskParameters(
            stop_loss_pct=Decimal("0.05"),
            risk_tolerance=Decimal("0.02"),
            volatility_adjustment=True
        )
    )
    
    # Mock get_risk_metrics
    with patch.object(RiskService, 'get_risk_metrics') as mock_metrics:
        mock_metrics.return_value = {
            'volatility': 0.6,
            'downside_volatility': 0.5,
            'current_drawdown': Decimal('0.08'),
            'max_drawdown': Decimal('0.15'),
        }
        
        # Should pass validation
        await RiskService.validate_order(
            order,
            account_equity=Decimal("50000"),
            current_drawdown=Decimal("0.08")
        )

@pytest.mark.asyncio
async def test_validate_order_halts_on_critical_drawdown():
    """Test trading halt on critical drawdown"""
    order = MarketOrder(
        exchange="binance",
        symbol="BTC/USDT",
        side="buy",
        amount=Decimal("0.1"),
        type="market"
    )
    
    # Set critical drawdown
    critical_drawdown = RiskService.CRITICAL_DRAWDOWN_THRESHOLD + Decimal("0.01")
    
    # Should raise ValueError due to critical drawdown
    with pytest.raises(ValueError, match="Trading halted"):
        await RiskService.validate_order(
            order,
            account_equity=Decimal("50000"),
            current_drawdown=critical_drawdown
        )