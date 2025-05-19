import pytest
import pandas as pd
import numpy as np
from utils.performance_metrics import (
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_downside_volatility,
    calculate_ulcer_index,
    calculate_pain_index,
    calculate_pain_ratio,
    calculate_risk_metrics,
    get_historical_volatility,
    identify_drawdown_periods
)

@pytest.fixture
def sample_returns():
    """Generate sample returns for testing"""
    np.random.seed(42)
    return pd.Series(np.random.normal(0.001, 0.02, 252))

@pytest.fixture
def extreme_returns():
    """Generate extreme returns for edge case testing"""
    np.random.seed(42)
    # Create a series with some extreme values
    returns = np.random.normal(0.001, 0.02, 252)
    # Add some extreme values
    returns[50] = -0.15  # Large loss
    returns[100] = 0.20  # Large gain
    returns[150:160] = -0.05  # Consecutive losses
    returns[200:210] = 0.03   # Consecutive gains
    return pd.Series(returns)

@pytest.fixture
def zero_returns():
    """Generate zero returns for edge case testing"""
    return pd.Series([0.0] * 100)

@pytest.fixture
def negative_returns():
    """Generate all negative returns for edge case testing"""
    np.random.seed(42)
    return pd.Series(-np.abs(np.random.normal(0.001, 0.02, 100)))

def test_max_drawdown_calculation():
    """Test max drawdown calculation with various scenarios"""
    # Test with simple equity curve
    equity_curve = [100, 110, 105, 95, 100, 105, 110, 105, 100, 95]
    max_dd = calculate_max_drawdown(equity_curve)
    assert max_dd == pytest.approx(0.1364, abs=1e-4)  # 13.64% drawdown
    
    # Test with all increasing values (no drawdown)
    equity_curve = [100, 101, 102, 103, 104, 105]
    max_dd = calculate_max_drawdown(equity_curve)
    assert max_dd == 0.0
    
    # Test with all decreasing values
    equity_curve = [100, 95, 90, 85, 80, 75]
    max_dd = calculate_max_drawdown(equity_curve)
    assert max_dd == pytest.approx(0.25, abs=1e-4)  # 25% drawdown
    
    # Test with empty or single value
    assert calculate_max_drawdown([]) == 0.0
    assert calculate_max_drawdown([100]) == 0.0

def test_omega_ratio(sample_returns):
    """Test Omega ratio calculation"""
    # Calculate risk metrics which includes omega ratio
    metrics = calculate_risk_metrics(sample_returns)
    
    # Verify omega ratio is calculated
    assert 'omega_ratio' in metrics
    assert isinstance(metrics['omega_ratio'], float)
    assert not np.isnan(metrics['omega_ratio'])
    
    # Test with all positive returns
    positive_returns = pd.Series([0.01] * 10)
    positive_metrics = calculate_risk_metrics(positive_returns)
    assert positive_metrics['omega_ratio'] == np.inf
    
    # Test with all negative returns
    negative_returns = pd.Series([-0.01] * 10)
    negative_metrics = calculate_risk_metrics(negative_returns)
    assert negative_metrics['omega_ratio'] == 0.0

def test_historical_volatility():
    """Test historical volatility lookup"""
    # Test with known symbols
    btc_vol = get_historical_volatility('BTC/USDT')
    eth_vol = get_historical_volatility('ETH/USDT')
    
    # Verify values match expected mock values
    assert btc_vol == 0.65
    assert eth_vol == 0.55
    
    # Test with unknown symbol (should return default)
    unknown_vol = get_historical_volatility('UNKNOWN/USDT')
    assert unknown_vol == 0.50

def test_sortino_ratio_edge_cases(extreme_returns, zero_returns, negative_returns):
    """Test Sortino ratio with edge cases"""
    # Test with extreme returns
    sortino_extreme = calculate_sortino_ratio(extreme_returns)
    assert isinstance(sortino_extreme, float)
    assert not np.isnan(sortino_extreme)
    
    # Test with zero returns
    sortino_zero = calculate_sortino_ratio(zero_returns)
    assert sortino_zero == -np.inf  # No excess return, but also no downside deviation
    
    # Test with all negative returns
    sortino_negative = calculate_sortino_ratio(negative_returns)
    assert sortino_negative < 0
    
    # Test with custom risk-free rate
    sortino_custom_rf = calculate_sortino_ratio(extreme_returns, risk_free_rate=0.05)
    assert sortino_custom_rf < sortino_extreme  # Higher risk-free rate should lower the ratio

def test_calmar_ratio_edge_cases(extreme_returns, zero_returns, negative_returns):
    """Test Calmar ratio with edge cases"""
    # Calculate max drawdowns
    extreme_cum_returns = (1 + extreme_returns).cumprod()
    extreme_rolling_max = extreme_cum_returns.expanding().max()
    extreme_drawdowns = extreme_cum_returns / extreme_rolling_max - 1
    extreme_max_drawdown = abs(extreme_drawdowns.min())
    
    zero_max_drawdown = 0.0  # No drawdown with zero returns
    
    negative_cum_returns = (1 + negative_returns).cumprod()
    negative_rolling_max = negative_cum_returns.expanding().max()
    negative_drawdowns = negative_cum_returns / negative_rolling_max - 1
    negative_max_drawdown = abs(negative_drawdowns.min())
    
    # Test with extreme returns
    calmar_extreme = calculate_calmar_ratio(extreme_returns, extreme_max_drawdown)
    assert isinstance(calmar_extreme, float)
    assert not np.isnan(calmar_extreme)
    
    # Test with zero returns and zero drawdown
    calmar_zero = calculate_calmar_ratio(zero_returns, zero_max_drawdown)
    assert calmar_zero == -np.inf  # Zero returns with zero drawdown
    
    # Test with negative returns
    calmar_negative = calculate_calmar_ratio(negative_returns, negative_max_drawdown)
    assert calmar_negative < 0

def test_drawdown_periods_identification(extreme_returns):
    """Test drawdown period identification with extreme returns"""
    # Create a date index for the extreme returns
    dates = pd.date_range(start='2023-01-01', periods=len(extreme_returns))
    extreme_returns_dated = pd.Series(extreme_returns.values, index=dates)
    
    # Identify drawdown periods
    drawdown_periods = identify_drawdown_periods(extreme_returns_dated)
    
    # Verify structure and content
    assert isinstance(drawdown_periods, list)
    assert len(drawdown_periods) > 0
    
    # Check the largest drawdown period
    largest_drawdown = min(drawdown_periods, key=lambda x: x['max_drawdown'])
    assert largest_drawdown['max_drawdown'] < -0.10  # Should have at least a 10% drawdown
    
    # Check consecutive drawdown days
    consecutive_drawdown = max(drawdown_periods, key=lambda x: x['duration'])
    assert consecutive_drawdown['duration'] >= 5  # Should have at least 5 days of consecutive drawdown

def test_risk_metrics_comprehensive(extreme_returns):
    """Test comprehensive risk metrics calculation with extreme returns"""
    metrics = calculate_risk_metrics(extreme_returns)
    
    # Check all metrics are present and have reasonable values
    assert metrics['max_drawdown'] < -0.10  # Should have at least a 10% drawdown
    assert metrics['downside_volatility'] > metrics['volatility'] * 0.5  # Downside vol should be significant
    assert metrics['ulcer_index'] > 0.05  # Should have a significant ulcer index
    assert metrics['pain_index'] > 0.03  # Should have a significant pain index
    
    # Check drawdown durations
    assert metrics['max_drawdown_duration'] >= 5  # Should have at least 5 days of consecutive drawdown
    
    # Check win rate is reasonable
    assert 0 <= metrics['win_rate'] <= 1
    
    # Check consecutive wins/losses
    assert metrics['max_consecutive_losses'] >= 5  # Should have at least 5 consecutive losses