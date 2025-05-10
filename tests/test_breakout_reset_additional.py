import pytest
import pandas as pd
import numpy as np
from strategies.breakout_reset import BreakoutResetStrategy

def test_position_entry_exit():
    """Test position entry and exit logic"""
    # Create data with clear breakout and duration-based exit
    test_data = pd.DataFrame({
        'close': [100] * 5 +  # Initial lookback
                 [105, 106, 107, 108, 109, 110]  # Breakout + continuation
    })

    strategy = BreakoutResetStrategy(
        lookback_period=5,
        volatility_multiplier=0.5,
        reset_threshold=0.5,  # Large enough to not trigger
        position_duration=3,  # Force exit after 3 periods (entry + 2)
        take_profit=1.0,  # Large enough to not trigger
        stop_loss=1.0  # Large enough to not trigger
    )

    result = strategy.generate_signals(test_data)

    # Verify entry (index 5 is first bar after lookback)
    assert result['signal'].iloc[5] == 1, "Should enter at breakout"
    assert result['position'].iloc[5] == 1, "Should be long after entry"

    # Verify exit after position_duration (entry at 5, exits at 8)
    assert result['signal'].iloc[8] == -1, "Should exit after duration"
    assert result['position'].iloc[8] == 0, "Should be flat after exit"

def test_reset_threshold_edge_cases():
    """Test reset threshold behavior"""
    test_data = pd.DataFrame({
        'close': [100] * 5 +  # Lookback
                 [105, 106, 107, 105, 103, 101]  # Breakout + pullback
    })

    strategy = BreakoutResetStrategy(
        lookback_period=5,
        volatility_multiplier=0.5,
        reset_threshold=0.03,  # 3% threshold
        position_duration=10  # Long enough to test threshold first
    )

    result = strategy.generate_signals(test_data)
    
    # Entry at breakout (105)
    assert result['position'].iloc[5] == 1
    
    # Should exit when price drops 3% from peak (107)
    # 107 * 0.97 = 103.79, so exit at 103
    assert result['position'].iloc[-3] == 1  # Still open at 105
    assert result['position'].iloc[-2] == 0  # Closed at 103
    assert result['signal'].iloc[-2] == -1  # Exit signal

def test_empty_nan_data():
    """Test error handling for invalid data"""
    strategy = BreakoutResetStrategy(
        lookback_period=2,  # Reduced for test
        volatility_multiplier=1.0,
        reset_threshold=0.1
    )
    
    # Test empty DataFrame
    with pytest.raises(ValueError, match="Data cannot be empty"):
        strategy.generate_signals(pd.DataFrame())
        
    # Test negative prices (needs enough data for lookback)
    with pytest.raises(ValueError, match="Price cannot be negative"):
        strategy.generate_signals(pd.DataFrame({'close': [100, 100, -1]}))
        
    # Test insufficient data
    with pytest.raises(ValueError, match="Insufficient data"):
        strategy.generate_signals(pd.DataFrame({'close': [100]}))

def test_band_calculations():
    """Test volatility band calculations"""
    test_data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104, 105]  # Increasing prices
    })
    
    strategy = BreakoutResetStrategy(
        lookback_period=3,
        volatility_multiplier=2.0,
        reset_threshold=0.1
    )
    
    result = strategy.calculate_bands(test_data.copy())
    
    # Verify bands are calculated correctly
    assert 'middle_band' in result.columns
    assert 'upper_band' in result.columns
    assert 'lower_band' in result.columns
    
    # Middle band should be rolling mean
    assert np.isclose(result['middle_band'].iloc[3], 102.0)  # (101+102+103)/3
    assert np.isclose(result['middle_band'].iloc[4], 103.0)  # (102+103+104)/3
    
    # Upper/lower bands should be mean ± 2*std
    expected_std = test_data['close'].rolling(3).std().iloc[3]
    expected_upper = 102.0 + 2 * expected_std  # middle_band is 102.0 at index 3
    expected_lower = 102.0 - 2 * expected_std
    assert np.isclose(result['upper_band'].iloc[3], expected_upper)
    assert np.isclose(result['lower_band'].iloc[3], expected_lower)

def test_take_profit_stop_loss():
    """Test take profit and stop loss triggers"""
    # Setup data with clear breakout and price movements
    test_data = pd.DataFrame({
        'close': [100] * 5 +  # Lookback
                 [105, 106, 107, 108, 109, 110, 110.5,  # Breakout + continuation
                  104, 103, 102, 101, 100, 99.5]  # Pullback with sufficient drop
    })
    
    # Test take profit trigger (5% from entry)
    strategy = BreakoutResetStrategy(
        lookback_period=5,
        volatility_multiplier=0.5,
        reset_threshold=0.5,  # Large enough to not trigger
        take_profit=0.05,
        stop_loss=0.10,  # Large enough to not trigger
        position_duration=100
    )
    result = strategy.generate_signals(test_data)
    assert any(result['profit_loss'] >= 0.05), f"Should hit take profit. Max profit: {result['profit_loss'].max()}"
    
    # Test stop loss trigger (5% from entry)
    strategy = BreakoutResetStrategy(
        lookback_period=5,
        volatility_multiplier=0.5,
        reset_threshold=0.5,  # Large enough to not trigger
        take_profit=0.10,  # Large enough to not trigger
        stop_loss=0.05,
        position_duration=100
    )
    result = strategy.generate_signals(test_data)
    assert any(result['profit_loss'] <= -0.05), "Should hit stop loss"

def test_multiple_positions():
    """Test multiple position entry/exit"""
    test_data = pd.DataFrame({
        'close': [100] * 5 +  # Lookback
                 [105, 106, 107, 104, 103, 102,  # First breakout + pullback
                  108, 109, 110, 107, 106]  # Second breakout + pullback
    })
    
    strategy = BreakoutResetStrategy(
        lookback_period=5,
        volatility_multiplier=0.5,
        reset_threshold=0.03,  # 3% threshold
        position_duration=100
    )
    
    result = strategy.generate_signals(test_data)
    
    # Verify two distinct position entries
    signals = result['signal'].values
    assert sum(signals == 1) >= 2, "Should have multiple entries"
    assert sum(signals == -1) >= 2, "Should have multiple exits"

def test_get_parameters():
    """Test parameter getter method"""
    params = {
        'lookback_period': 10,
        'volatility_multiplier': 1.5,
        'reset_threshold': 0.2,
        'take_profit': 0.05,
        'stop_loss': 0.03
    }
    
    strategy = BreakoutResetStrategy(**params)
    retrieved_params = strategy.get_parameters()
    
    for key in params:
        assert key in retrieved_params
        assert retrieved_params[key] == params[key]

def test_zero_price_handling():
    """Test handling of zero prices"""
    strategy = BreakoutResetStrategy(
        lookback_period=3,
        volatility_multiplier=0.5,
        reset_threshold=0.1
    )
    
    # Test zero price in lookback period
    with pytest.raises(ValueError, match="Price cannot be zero"):
        strategy.generate_signals(pd.DataFrame({'close': [100, 100, 0]}))
    
    # Test zero price after lookback
    with pytest.raises(ValueError, match="Price cannot be zero"):
        strategy.generate_signals(pd.DataFrame({'close': [100, 100, 100, 0]}))

def test_nan_handling():
    """Test handling of NaN values"""
    strategy = BreakoutResetStrategy(
        lookback_period=3,
        volatility_multiplier=0.5,
        reset_threshold=0.1
    )
    
    # Test NaN in lookback period
    with pytest.raises(ValueError, match="contains NaN values"):
        strategy.generate_signals(pd.DataFrame({'close': [100, np.nan, 100]}))
    
    # Test NaN after lookback
    with pytest.raises(ValueError, match="contains NaN values"):
        strategy.generate_signals(pd.DataFrame({'close': [100, 100, 100, np.nan]}))