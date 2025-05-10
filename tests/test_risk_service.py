import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from trade.services.risk import RiskService
from trade.schemas.trade import MarketOrder, LimitOrder

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
        Decimal("100000")
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
        mock_vol.return_value = 0.2  # 20% volatility
        size = await RiskService.calculate_position_size(
            "BTC/USDT",
            Decimal("100000"),
            volatility_factor=True
        )
        assert size == Decimal("833.33")  # 1000 / 1.2

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