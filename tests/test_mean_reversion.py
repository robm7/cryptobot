import pytest
import pandas as pd
import numpy as np
import logging
import sys
logger = logging.getLogger(__name__)
from strategies.mean_reversion import MeanReversionStrategy

# Enable verbose output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def test_parameter_validation():
    # Test missing required parameters
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=None, entry_z_score=2.0)
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=20, entry_z_score=None)

    # Test type validation
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period="20", entry_z_score=2.0)
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=20, entry_z_score="2.0")

    # Test range validation
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=4, entry_z_score=2.0)  # Below min
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=201, entry_z_score=2.0)  # Above max
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=20, entry_z_score=0.9)  # Below min
    with pytest.raises(ValueError):
        MeanReversionStrategy(lookback_period=20, entry_z_score=3.1)  # Above max

def test_z_score_calculation():
    # Create test data with known mean/std
    test_data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=2.0,
        exit_z_score=0.5
    )
    result = strategy.calculate_z_scores(test_data)
    
    # Verify calculations
    assert 'mean' in result.columns
    assert 'std_dev' in result.columns
    assert 'z_score' in result.columns
    
    # Check first valid calculation (index 4)
    expected_mean = test_data['close'].iloc[:5].mean()
    expected_std = test_data['close'].iloc[:5].std()
    expected_z = (test_data['close'].iloc[4] - expected_mean) / expected_std
    
    assert np.isclose(result['mean'].iloc[4], expected_mean)
    assert np.isclose(result['std_dev'].iloc[4], expected_std)
    assert np.isclose(result['z_score'].iloc[4], expected_z)

def test_long_entry_signals():
    # Create test data with price below mean
    test_data = pd.DataFrame({
        'close': [100]*5 + [90, 89, 88, 87, 86]  # Price drops below mean
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5
    )
    result = strategy.generate_signals(test_data)
    
    # Verify long entry signal
    assert 1 in result['signal'].values
    assert 1 in result['position'].values

def test_short_entry_signals():
    # Create test data with price above mean
    test_data = pd.DataFrame({
        'close': [100]*5 + [110, 111, 112, 113, 114]  # Price rises above mean
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5
    )
    result = strategy.generate_signals(test_data)
    
    # Verify short entry signal
    assert -1 in result['signal'].values
    assert -1 in result['position'].values

def test_exit_conditions():
    # Create test data that triggers each exit condition
    test_data = pd.DataFrame({
        'close': [100]*5 + [90, 91, 92, 93, 94, 95, 96, 97, 98, 99]  # Price reverts
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,
        take_profit=0.03,
        stop_loss=0.02
    )
    result = strategy.generate_signals(test_data)
    
    # Verify exit occurred
    assert 0 in result['position'].values[-5:]  # Should have exited

def test_profit_tracking():
    # Create test data with clear profitable trade
    test_data = pd.DataFrame({
        'close': [100]*5 + [80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130]  # Strong profitable long
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,  # Lower exit threshold to allow more profit
        take_profit=0.5,   # Large enough to not trigger
        stop_loss=0.5      # Large enough to not trigger
    )
    result = strategy.generate_signals(test_data)
    
    # Debug print to see where profit is stored
    print("\nTrade profit values:")
    print(result['trade_profit'].to_string())
    
    # Verify profits are tracked
    assert 'trade_profit' in result.columns
    assert 'cumulative_profit' in result.columns
    
    # Find the non-zero profit row
    profit_row = result[result['trade_profit'] > 0]
    assert len(profit_row) > 0, "No profitable trade found"
    
    # Debug print the exact row being checked
    print("\nProfit row being checked:")
    print(profit_row.iloc[0][['trade_profit', 'cumulative_profit']])
    
    assert profit_row['trade_profit'].iloc[0] > 0
    assert float(profit_row['cumulative_profit'].iloc[0]) > 0

def test_stop_loss_trigger():
    """Test stop loss condition triggers correctly"""
    test_data = pd.DataFrame({
        'close': [100]*5 + [90, 85, 80, 75, 70, 65, 60]  # Price keeps falling
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.1,  # Smaller exit threshold to allow take profit to trigger first
        take_profit=0.5,   # Won't trigger
        stop_loss=0.1      # 10% stop loss
    )
    result = strategy.generate_signals(test_data)
    
    # Verify stop loss triggered
    assert result['position'].iloc[-1] == 0  # Position closed
    assert any(result['trade_profit'] <= -0.1)  # Hit stop loss

def test_take_profit_trigger():
    """Test take profit condition triggers correctly"""
    test_data = pd.DataFrame({
        'close': [100]*5 + [80, 85, 90, 95, 100, 105, 110, 115, 120]  # Steeper drop and recovery
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,
        take_profit=0.2,   # 20% take profit
        stop_loss=0.5      # Won't trigger
    )
    result = strategy.generate_signals(test_data)
    
    # Verify take profit triggered
    assert result['position'].iloc[-1] == 0  # Position closed
    assert any(result['trade_profit'] >= 0.2)  # Hit take profit

def test_get_parameters():
    """Test parameter retrieval"""
    params = {
        'lookback_period': 20,
        'entry_z_score': 2.0,
        'exit_z_score': 0.5,
        'take_profit': 0.03,
        'stop_loss': 0.02
    }
    strategy = MeanReversionStrategy(**params)
    retrieved_params = strategy.get_parameters()
    assert retrieved_params == params

def test_multiple_trade_cycles():
    """Test strategy handles multiple consecutive trades correctly"""
    # Create data with multiple mean reversion opportunities
    # More extreme deviations to ensure clear entry signals
    test_data = pd.DataFrame({
        'close': [100]*5 + [80, 75, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 120, 115, 110, 105, 100, 95, 90, 85, 80, 75, 70, 75, 80, 85, 90, 95, 100]
    })
    
    # Parameters adjusted to stay within validation bounds
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.0,  # Minimum allowed value
        exit_z_score=0.2,   # Lowered to minimum allowed (0.1)
        take_profit=0.5,    # High profit target
        stop_loss=0.25      # Wider stop loss
    )
    result = strategy.generate_signals(test_data)
    
    # Verify trade execution and state clearing
    trade_count = len(result[result['signal'] != 0])
    logger.info(f"Executed {trade_count} trades")
    assert trade_count >= 2, f"Expected at least 2 trades, got {trade_count}"
    
    # Verify positions were properly cleared between trades
    for i in range(1, len(result)):
        if result.iloc[i]['signal'] != 0 and result.iloc[i-1]['position'] != 0:
            raise AssertionError(f"Position not cleared between trades at index {i}")
    
    # Verify positions were properly cleared between trades
    for i in range(1, len(result)):
        if result.iloc[i]['signal'] != 0 and result.iloc[i-1]['position'] != 0:
            raise AssertionError(f"Position not cleared between trades at index {i}")
    
    # Verify cumulative profit is sum of individual trades
    individual_profits = result[result['trade_profit'] != 0]['trade_profit']
    assert np.isclose(result['cumulative_profit'].iloc[-1], individual_profits.sum())
    
    # Verify position state resets between trades
    for i in range(1, len(result)):
        if result['signal'].iloc[i] != 0:  # New trade entry
            assert result['position'].iloc[i-1] == 0  # Previous position was closed

def test_position_state_consistency():
    """Test that internal position state matches exchange interface after trades"""
    class DummyExchange:
        def __init__(self):
            self.position = 0
            self.last_price = None
        def execute_trade(self, side, amount, price):
            if side == 'buy':
                self.position += amount
            elif side == 'sell':
                self.position -= amount
            self.last_price = price
        def get_position(self):
            return self.position
        def get_last_price(self):
            return self.last_price
    # Simulate price data for a long and short trade
    test_data = pd.DataFrame({
        'close': [100]*5 + [80, 75, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 120, 115, 110, 105, 100]
    })
    exchange = DummyExchange()
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,
        take_profit=0.5,
        stop_loss=0.5,
        exchange_interface=exchange
    )
    result = strategy.generate_signals(test_data)
    # Simulate trades and check position state
    for i in range(strategy.lookback_period, len(result)):
        signal = result['signal'].iloc[i]
        price = result['close'].iloc[i]
        if signal == 1:
            exchange.execute_trade('buy', 1.0, price)
        elif signal == -1:
            exchange.execute_trade('sell', 1.0, price)
        # After each trade, check that strategy and exchange agree
        assert (strategy.position_size == exchange.get_position()), f"Mismatch at index {i}: strategy {strategy.position_size}, exchange {exchange.get_position()}"
        # Optionally check average entry price if needed
    # After all trades, ensure final position is consistent
    assert strategy.position_size == exchange.get_position()

def test_insufficient_data():
    """Test error when data is shorter than lookback period"""
    test_data = pd.DataFrame({
        'close': [100, 101, 102]  # Only 3 periods when 5 needed
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5
    )
    
    with pytest.raises(ValueError, match="Insufficient data"):
        strategy.generate_signals(test_data)

def test_missing_close_column():
    """Test error when required 'close' column is missing"""
    test_data = pd.DataFrame({
        'price': [100, 101, 102]  # Wrong column name
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5
    )
    
    with pytest.raises(ValueError, match="must contain 'close' column"):
        strategy.generate_signals(test_data)

def test_invalid_data_types():
    """Test error when data contains invalid types"""
    test_data = pd.DataFrame({
        'close': ['100', '101', '102']  # Strings instead of numbers
    })
    
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5
    )
    
    with pytest.raises(ValueError):
        strategy.generate_signals(test_data)


def test_dynamic_position_sizing():
    """Test dynamic position sizing logic"""
    test_data = pd.DataFrame({
        'close': [100]*5 + [80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130]
    })
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,
        position_sizing_mode='dynamic',
        max_position_size=2.0,
        min_position_size=0.5
    )
    result = strategy.generate_signals(test_data)
    assert 'position_size' in result.columns
    assert result['position_size'].max() <= 2.0
    assert result['position_size'].min() >= 0.5
    assert result['position_size'].iloc[-1] > 0

def test_risk_management_edge_cases():
    """Test risk management edge cases: zero, negative, and extreme values"""
    test_data = pd.DataFrame({'close': [100]*5 + [50, 200, 50, 200, 50, 200]})
    # Zero stop loss
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,
        take_profit=0.1,
        stop_loss=0.0
    )
    result = strategy.generate_signals(test_data)
    assert 'trade_profit' in result.columns
    # Negative stop loss (should raise error)
    with pytest.raises(ValueError):
        MeanReversionStrategy(
            lookback_period=5,
            entry_z_score=1.5,
            exit_z_score=0.5,
            take_profit=0.1,
            stop_loss=-0.1
        )
    # Extremely high take profit
    strategy = MeanReversionStrategy(
        lookback_period=5,
        entry_z_score=1.5,
        exit_z_score=0.5,
        take_profit=10.0,
        stop_loss=0.1
    )
    result = strategy.generate_signals(test_data)
    assert result['trade_profit'].max() <= 10.0