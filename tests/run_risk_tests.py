import asyncio
from decimal import Decimal
from unittest.mock import patch
from trade.services.risk import RiskService

async def test_calculate_position_size_basic():
    with patch('trade.services.risk.get_historical_volatility', return_value=0.5):
        size = await RiskService.calculate_position_size(
            'BTC/USDT',
            Decimal('100000'),
            volatility_factor=False
        )
        print(f'Basic position size test: {size}')
        assert size == Decimal('1000')

async def test_drawdown_control():
    with patch('trade.services.risk.get_historical_volatility', return_value=0.5):
        RiskService.DRAWDOWN_CONTROL_ENABLED = True
        size = await RiskService.calculate_position_size(
            'BTC/USDT',
            Decimal('100000'),
            volatility_factor=False,
            current_drawdown=Decimal('0.20')
        )
        print(f'Position size with 20% drawdown: {size}')
        assert size < Decimal('1000')

async def test_volatility_adjustment():
    with patch('trade.services.risk.get_historical_volatility', return_value=0.8):
        RiskService.VOLATILITY_SCALING_ENABLED = True
        size = await RiskService.calculate_position_size(
            'BTC/USDT',
            Decimal('100000'),
            volatility_factor=True
        )
        print(f'Position size with high volatility (0.8): {size}')
        assert size < Decimal('1000')

async def test_custom_risk_tolerance():
    with patch('trade.services.risk.get_historical_volatility', return_value=0.5):
        size = await RiskService.calculate_position_size(
            'BTC/USDT',
            Decimal('100000'),
            volatility_factor=False,
            risk_tolerance=Decimal('0.02')
        )
        print(f'Position size with 2% risk tolerance: {size}')
        assert size == Decimal('2000')

async def run_tests():
    print("Running enhanced position sizing tests...")
    
    try:
        await test_calculate_position_size_basic()
        print("✅ Basic position sizing test passed")
    except AssertionError as e:
        print(f"❌ Basic position sizing test failed: {e}")
    
    try:
        await test_drawdown_control()
        print("✅ Drawdown control test passed")
    except AssertionError as e:
        print(f"❌ Drawdown control test failed: {e}")
    
    try:
        await test_volatility_adjustment()
        print("✅ Volatility adjustment test passed")
    except AssertionError as e:
        print(f"❌ Volatility adjustment test failed: {e}")
    
    try:
        await test_custom_risk_tolerance()
        print("✅ Custom risk tolerance test passed")
    except AssertionError as e:
        print(f"❌ Custom risk tolerance test failed: {e}")
    
    print("All tests completed")

if __name__ == "__main__":
    asyncio.run(run_tests())