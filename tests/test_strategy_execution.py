import pytest
import pandas as pd
from strategies.breakout_reset import BreakoutResetStrategy
from utils.exchange_interface import MockExchangeInterface

@pytest.fixture
def mock_interface():
    """Provides a fresh MockExchangeInterface for each test."""
    MockExchangeInterface._orders = {}
    MockExchangeInterface._order_id_counter = 1
    MockExchangeInterface._balances = {'USDT': 10000.0, 'BTC': 1.0}
    return MockExchangeInterface(testnet=True)

@pytest.fixture
def strategy(mock_interface): # Strategy needs the interface
    """Provides a BreakoutResetStrategy instance with default params and mock interface."""
    return BreakoutResetStrategy(
        symbol='BTCUSDT',
        exchange_interface=mock_interface,
        lookback_period=5, # Use smaller lookback for easier testing
        volatility_multiplier=1.5,
        reset_threshold=0.5,
        take_profit=0.03,
        stop_loss=0.02,
        position_size_pct=0.1 # Define a position size for testing orders
    )

# Helper function to create a sample data point
def create_data_point(timestamp, price):
    return {
        'timestamp': timestamp,
        'open': price - 1,
        'high': price + 1,
        'low': price - 2,
        'close': price,
        'volume': 100
    }

@pytest.mark.asyncio
async def test_strategy_places_buy_order_on_breakout(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # 1. Feed initial data to establish bands (less than lookback)
    for i in range(strategy.lookback_period - 1):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    
    assert len(strategy.data_buffer) == strategy.lookback_period - 1
    assert len(mock_interface._orders) == 0 # No orders placed yet
    assert strategy.position == 0

    # 2. Feed data point just below the upper band (needs calculation)
    # Need enough data first
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 4000, 30004))
    assert len(strategy.data_buffer) == strategy.lookback_period
    # Manually calculate approximate bands for this simple case
    # Prices: 30000, 30001, 30002, 30003, 30004. Mean ~30002. Std ~1.58
    # Upper band ~ 30002 + 1.58 * 1.5 = 30004.37
    assert len(mock_interface._orders) == 0 # Still no order

    # 3. Feed data point that breaks above the upper band
    breakout_price = 30005
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 5000, breakout_price))

    # Assertions
    assert len(mock_interface._orders) == 1, "An order should have been placed"
    order = mock_interface._orders['1'] # First order ID is '1'
    assert order['symbol'] == strategy.symbol
    assert order['side'] == 'buy'
    assert order['type'] == 'market'
    assert order['amount'] == strategy.params['position_size_pct']
    assert order['status'] == 'filled' # Mock fills market orders
    assert strategy.position == 1, "Strategy should be in a long position"
    assert strategy.entry_price == breakout_price

@pytest.mark.asyncio
async def test_strategy_places_sell_order_on_breakdown(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # 1. Feed initial data (prices decreasing)
    for i in range(strategy.lookback_period - 1):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 - i))
    assert len(mock_interface._orders) == 0

    # 2. Feed data point just above lower band
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 4000, 29996))
    # Prices: 30000, 29999, 29998, 29997, 29996. Mean ~29998. Std ~1.58
    # Lower band ~ 29998 - 1.58 * 1.5 = 29995.63
    assert len(mock_interface._orders) == 0

    # 3. Feed data point that breaks below the lower band
    breakdown_price = 29995
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 5000, breakdown_price))

    # Assertions
    assert len(mock_interface._orders) == 1, "An order should have been placed"
    order = mock_interface._orders['1']
    assert order['symbol'] == strategy.symbol
    assert order['side'] == 'sell'
    assert order['type'] == 'market'
    assert order['amount'] == strategy.params['position_size_pct']
    assert order['status'] == 'filled'
    assert strategy.position == -1, "Strategy should be in a short position"
    assert strategy.entry_price == breakdown_price

@pytest.mark.asyncio
async def test_strategy_exits_long_on_stop_loss(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # 1. Enter long position first (similar to test_strategy_places_buy_order_on_breakout)
    entry_price = 30005
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 5000, entry_price))
    assert strategy.position == 1
    assert len(mock_interface._orders) == 1 # Entry order

    # 2. Feed data point that triggers stop loss
    stop_loss_price = entry_price * (1 - strategy.stop_loss) - 0.01 # Just below stop loss level
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, stop_loss_price))

    # Assertions
    assert len(mock_interface._orders) == 2, "An exit order should have been placed"
    exit_order = mock_interface._orders['2'] # Second order
    assert exit_order['symbol'] == strategy.symbol
    assert exit_order['side'] == 'sell' # Exit long means sell
    assert exit_order['type'] == 'market'
    assert exit_order['amount'] == strategy.params['position_size_pct'] # Assumes closing full position
    assert exit_order['status'] == 'filled'
    assert strategy.position == 0, "Strategy should be flat after stop loss"
    assert strategy.entry_price is None

@pytest.mark.asyncio
async def test_strategy_exits_short_on_take_profit(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # 1. Enter short position first
    entry_price = 29995
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 - i))
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 5000, entry_price))
    assert strategy.position == -1
    assert len(mock_interface._orders) == 1 # Entry order

    # 2. Feed data point that triggers take profit
    take_profit_price = entry_price * (1 - strategy.take_profit) - 0.01 # Just below take profit level
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, take_profit_price))

    # Assertions
    assert len(mock_interface._orders) == 2, "An exit order should have been placed"
    exit_order = mock_interface._orders['2']
    assert exit_order['symbol'] == strategy.symbol
    assert exit_order['side'] == 'buy' # Exit short means buy
    assert exit_order['type'] == 'market'
    assert exit_order['amount'] == strategy.params['position_size_pct']
    assert exit_order['status'] == 'filled'
    assert strategy.position == 0, "Strategy should be flat after take profit"
    assert strategy.entry_price is None

@pytest.mark.asyncio
async def test_no_order_if_not_enough_data(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Feed less data than lookback period
    for i in range(strategy.lookback_period - 2):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    
    # Even if price breaks out, no order should be placed
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + (strategy.lookback_period-1)*1000, 35000))

    assert len(mock_interface._orders) == 0
    assert strategy.position == 0

@pytest.mark.asyncio
async def test_partial_fill_and_reentry(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Simulate partial fill scenario
    # 1. Enter long position
    entry_price = 30005
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 5000, entry_price))
    assert strategy.position == 1
    assert len(mock_interface._orders) == 1

    # Simulate partial fill by manually adjusting order status
    order = mock_interface._orders['1']
    order['status'] = 'partially_filled'
    # Strategy should not consider position closed
    assert strategy.position == 1

    # Now fill the rest
    order['status'] = 'filled'
    # Feed price to trigger exit
    exit_price = entry_price * (1 - strategy.stop_loss) - 0.01
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, exit_price))
    assert strategy.position == 0
    assert strategy.entry_price is None

    # Re-entry after exit
    reentry_price = 30010
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 7000, reentry_price))
    assert strategy.position == 1
    assert len(mock_interface._orders) == 3  # Entry, exit, re-entry

@pytest.mark.asyncio
async def test_simultaneous_signals(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Simulate a scenario where both upper and lower bands are crossed in rapid succession
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000))
    # Breakout up
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, 31000))
    assert strategy.position == 1
    assert len(mock_interface._orders) == 1
    # Immediate reversal below lower band
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 7000, 29000))
    # Should exit long and possibly enter short
    assert strategy.position in [0, -1]
    assert len(mock_interface._orders) >= 2
    # Check mock exchange consistency
    for order in mock_interface._orders.values():
        assert order['symbol'] == strategy.symbol
        assert order['status'] == 'filled'

@pytest.mark.asyncio
async def test_rapid_market_reversal(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Enter long
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 5000, 30500))
    assert strategy.position == 1
    # Rapid drop triggers stop loss
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, 29500))
    assert strategy.position == 0
    # Rapid rise triggers new breakout
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 7000, 31000))
    assert strategy.position == 1
    # Check orders and state
    assert len(mock_interface._orders) >= 3
    for order in mock_interface._orders.values():
        assert order['symbol'] == strategy.symbol
        assert order['status'] == 'filled'

@pytest.mark.asyncio
async def test_missing_data_points(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Feed data with missing points (simulate gaps)
    for i in range(strategy.lookback_period - 1):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*2000, 30000 + i))
    # Skip a timestamp (gap)
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 10000, 30010))
    # Should still not place order if not enough data
    assert len(mock_interface._orders) == 0
    # Now enough data, trigger breakout
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 12000, 31000))
    assert len(mock_interface._orders) == 1
    assert strategy.position == 1

@pytest.mark.asyncio
async def test_corrupted_data_point(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Feed valid data
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    # Feed corrupted data (missing 'close')
    corrupted = create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, 30010)
    corrupted.pop('close')
    try:
        await strategy.process_realtime_data(corrupted)
    except Exception:
        pass
    # Feed valid breakout
    await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 7000, 31000))
    assert len(mock_interface._orders) == 1
    assert strategy.position == 1

@pytest.mark.asyncio
async def test_consistency_after_multiple_trades(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Simulate a sequence of alternating long and short trades
    prices = [30000, 30001, 30002, 30003, 30004, 30010, 29990, 30015, 29985, 30020]
    timestamps = [pd.Timestamp.now().timestamp() * 1000 + i*1000 for i in range(len(prices))]
    for ts, price in zip(timestamps, prices):
        await strategy.process_realtime_data(create_data_point(ts, price))
    # After several trades, check position and orders
    assert isinstance(strategy.position, int)
    assert all(order['status'] == 'filled' for order in mock_interface._orders.values())
    # Ensure no duplicate open positions
    open_positions = [order for order in mock_interface._orders.values() if order['status'] == 'filled']
    assert len(open_positions) == len(mock_interface._orders)


@pytest.mark.asyncio
async def test_strategy_handles_unexpected_data_type(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface):
    # Feed a data point with a string price (should be handled or raise ValueError)
    data_point = create_data_point(pd.Timestamp.now().timestamp() * 1000, "not_a_number")
    try:
        await strategy.process_realtime_data(data_point)
        assert False, "Should raise an exception for invalid data type"
    except (ValueError, TypeError):
        assert True

@pytest.mark.asyncio
async def test_strategy_handles_network_interruption(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface, monkeypatch):
    # Simulate network error by patching the exchange interface
    async def raise_network_error(*args, **kwargs):
        raise ConnectionError("Simulated network interruption")
    monkeypatch.setattr(mock_interface, "place_order", raise_network_error)
    # Fill buffer to trigger order
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    # Trigger breakout
    try:
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, 31000))
        assert False, "Should raise ConnectionError on network interruption"
    except ConnectionError:
        assert True

@pytest.mark.asyncio
async def test_strategy_handles_exchange_error(strategy: BreakoutResetStrategy, mock_interface: MockExchangeInterface, monkeypatch):
    # Simulate exchange error (e.g., insufficient funds)
    async def raise_exchange_error(*args, **kwargs):
        raise RuntimeError("Insufficient funds")
    monkeypatch.setattr(mock_interface, "place_order", raise_exchange_error)
    # Fill buffer to trigger order
    for i in range(strategy.lookback_period):
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + i*1000, 30000 + i))
    # Trigger breakout
    try:
        await strategy.process_realtime_data(create_data_point(pd.Timestamp.now().timestamp() * 1000 + 6000, 31000))
        assert False, "Should raise RuntimeError on exchange error"
    except RuntimeError as e:
        assert "Insufficient funds" in str(e)