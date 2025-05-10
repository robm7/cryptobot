import pytest
import asyncio # Added for async testing
import pandas as pd # Added for creating test data
import numpy as np # Added for creating test data
from flask import jsonify
from auth.auth_service import get_password_hash
from database.models import User, Trade # Added Trade import
from strategies.breakout_reset import BreakoutResetStrategy
# Use MockExchangeInterface for testing trade execution
from utils.exchange_interface import MockExchangeInterface
# Removed ExchangeClient and get_exchange_client as we use Mock

@pytest.mark.integration
def test_auth_and_protected_route(client, session):
    """Test full auth flow with protected route"""
    # Create test user
    test_user = User(email='integration@test.com')
    test_user.set_password('testpass123')
    session.add(test_user)
    session.commit()

    # Login and get token
    response = client.post('/api/auth/login', json={
        'email': 'integration@test.com',
        'password': 'testpass123'
    })
    assert response.status_code == 200
    assert 'data' in response.json
    access_token = response.json['data']['access_token']

    # Access protected route
    response = client.get('/api/protected/route', headers={
        'Authorization': f'Bearer {access_token}'
    })
    assert response.status_code == 200

@pytest.mark.integration
@pytest.mark.asyncio # Mark test as async
async def test_strategy_realtime_execution_with_mock_exchange(session):
    """Test strategy real-time execution with the mock exchange interface."""
    # Initialize components
    mock_exchange = MockExchangeInterface()
    symbol = 'BTC/USDT'
    strategy = BreakoutResetStrategy(
        symbol=symbol,
        exchange_interface=mock_exchange,
        lookback_period=5, # Use smaller lookback for faster testing
        volatility_multiplier=2.0,
        reset_threshold=0.5,
        take_profit=0.03,
        stop_loss=0.02,
        position_size_pct=0.1 # Define position size
    )

    # Create realistic mock data that triggers signals
    dates = pd.date_range(start='2023-01-01', periods=20, freq='1min')
    base_price = 30000
    # Create a pattern: dip, rise above band, fall below band
    prices = np.array([
        base_price, base_price-50, base_price-100, base_price-50, # Initial
        base_price+100, base_price+200, base_price+350, base_price+300, # Breakout high
        base_price+100, base_price, base_price-100, base_price-200, # Revert
        base_price-300, base_price-400, base_price-550, base_price-500, # Breakout low
        base_price-300, base_price-200, base_price-100, base_price # Recover
    ])
    mock_data = pd.DataFrame({
        'open': prices - 5,
        'high': prices + 10,
        'low': prices - 10,
        'close': prices,
        'volume': np.random.randint(10, 100, size=len(prices))
    }, index=dates)

    # Simulate feeding data points to the strategy
    initial_balance = await mock_exchange.get_balance()
    for i in range(len(mock_data)):
        data_point = mock_data.iloc[i].to_dict()
        # Convert timestamp to milliseconds for the strategy
        data_point['timestamp'] = int(mock_data.index[i].timestamp() * 1000)
        await strategy.process_realtime_data(data_point)
        # Small delay to allow async operations (optional)
        # await asyncio.sleep(0.001)

    # Assertions: Check if orders were placed and balances/positions changed
    final_balance = await mock_exchange.get_balance()
    final_position = mock_exchange.get_position(symbol)

    print(f"Initial Balance: {initial_balance}")
    print(f"Final Balance: {final_balance}")
    print(f"Final Position {symbol}: {final_position}")
    print(f"Mock Orders: {mock_exchange._orders}")

    # Check if any orders were actually processed (status changed from 'open')
    processed_orders = [o for o in mock_exchange._orders.values() if o['status'] != 'open']
    assert len(processed_orders) > 0, "No orders seem to have been processed by the mock exchange."

    # Check if balance changed (indicating trades occurred)
    # Be mindful of floating point comparisons
    assert abs(initial_balance['USDT'] - final_balance['USDT']) > 1e-6 or \
           abs(initial_balance.get('BTC', 0) - final_balance.get('BTC', 0)) > 1e-9, \
           "Balances did not change, indicating no trades were simulated."

    # Check if position is non-zero or zero depending on the final state of mock_data
    # Based on the mock data, it should likely end flat or in a position.
    # We can be more specific if we trace the exact signals generated.
    # For now, just check that orders were attempted.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_exchange_connection():
    """Test connection to the real exchange using CcxtExchangeInterface."""
    use_real = os.getenv('USE_REAL_EXCHANGE', 'false').lower() == 'true'
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    exchange_id = os.getenv('EXCHANGE_ID')
    use_testnet = os.getenv('USE_TESTNET', 'false').lower() == 'true'

    if not use_real:
        pytest.skip("Skipping real exchange test: USE_REAL_EXCHANGE is not 'true'.")
        return

    if not all([api_key, api_secret, exchange_id]):
        pytest.skip("Skipping real exchange test: API_KEY, API_SECRET, or EXCHANGE_ID missing.")
        return

    try:
        exchange_interface = CcxtExchangeInterface(
            api_key=api_key,
            api_secret=api_secret,
            testnet=use_testnet,
            exchange_id=exchange_id
        )
        
        # Attempt to fetch balance as a basic connection test
        balance = await exchange_interface.get_balance()
        
        assert isinstance(balance, dict), "Balance should be a dictionary."
        # Add more specific assertions if needed, e.g., check for expected currency keys
        print(f"Successfully connected to {exchange_id} ({'Testnet' if use_testnet else 'Live'}) and fetched balance: {balance}")

    except Exception as e:
        pytest.fail(f"Failed to connect to real exchange or fetch balance: {e}")

# Keep the old test for basic signal generation if needed, but mark it clearly
@pytest.mark.integration
def test_strategy_signal_generation_only(session):
    """Test strategy signal generation logic only (no exchange interaction)."""
    strategy = BreakoutResetStrategy(symbol='BTC/USDT', lookback_period=20)
    # Fetch some data using a real client (or use pre-saved mock data)
    try:
        client = ExchangeClient('binance') # Assumes ExchangeClient can fetch data without keys
        candles = client.get_ohlcv('BTC/USDT', '1h', limit=100)
    except Exception as e:
        pytest.skip(f"Skipping signal generation test due to data fetch error: {e}")
        return

    if candles.empty:
         pytest.skip("Skipping signal generation test because no candle data was fetched.")
         return

    signals = strategy.generate_signals(candles)

    assert isinstance(signals, pd.Series)
    assert len(signals) == len(candles)
    # Check if signals contains expected values (0, 1, -1)
    assert all(s in [0, 1, -1] for s in signals.unique())

@pytest.mark.integration
def test_trade_workflow(client, session, auth_headers):
    """Test complete trade workflow"""
    # Create test order
    response = client.post('/api/trades', json={
        'pair': 'BTC/USDT',
        'side': 'buy',
        'quantity': 0.01,
        'strategy': 'breakout_reset'
    }, headers=auth_headers)
    assert response.status_code == 201
    
    # Verify order in database
    assert 'data' in response.json
    trade_id = response.json['data']['id']
    trade = session.get(Trade, trade_id)
    assert trade is not None
    assert trade.status == 'open'

@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connection():
    """Test Redis connection from Data Service"""
    import redis.asyncio as redis
    from data.config import settings
    
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )
        await r.ping()
        print(f"Successfully connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    except Exception as e:
        pytest.fail(f"Failed to connect to Redis: {e}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_connection():
    """Test PostgreSQL database connection"""
    from database.db import engine
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute("SELECT 1")
            assert result.scalar() == 1
            print("Successfully connected to PostgreSQL database")
    except Exception as e:
        pytest.fail(f"Failed to connect to PostgreSQL: {e}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_backtest_integration():
    """Test Data Service integration with Backtest Service"""
    from data.routers.data import get_ohlcv
    from backtest.tasks import run_backtest
    from strategies.breakout_reset import BreakoutResetStrategy
    
    # Get sample data from Data Service
    data = await get_ohlcv(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1d",
        limit=100
    )
    assert len(data) > 0
    
    # Run backtest with the data
    strategy = BreakoutResetStrategy(symbol="BTC/USDT")
    results = await run_backtest(
        strategy=strategy,
        data=data,
        initial_balance=10000
    )
    assert 'final_balance' in results
    assert 'performance_metrics' in results

@pytest.mark.integration
@pytest.mark.asyncio
async def test_trade_strategy_integration():
    """Test Trade Execution Service with Strategy Service"""
    from trade.routers.trades import execute_trade
    from strategies.breakout_reset import BreakoutResetStrategy
    from utils.exchange_interface import MockExchangeInterface
    
    # Setup mock exchange
    mock_exchange = MockExchangeInterface()
    await mock_exchange.set_balance({'USDT': 10000})
    
    # Create strategy instance
    strategy = BreakoutResetStrategy(
        symbol="BTC/USDT",
        exchange_interface=mock_exchange
    )
    
    # Execute test trade
    trade_result = await execute_trade(
        strategy=strategy,
        symbol="BTC/USDT",
        amount=0.01,
        side="buy"
    )
    assert trade_result['status'] == 'filled'
    assert trade_result['amount'] == 0.01