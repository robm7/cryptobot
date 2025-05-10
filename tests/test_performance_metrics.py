import pytest
import pandas as pd
import numpy as np
from utils.performance_metrics import (
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_sharpe_ratio,
    calculate_max_consecutive,
    calculate_profit_factor,
    calculate_risk_metrics
)

@pytest.fixture
def sample_returns():
    """Generate sample returns for testing"""
    np.random.seed(42)
    return pd.Series(np.random.normal(0.001, 0.02, 252))

def test_sortino_ratio(sample_returns):
    """Test Sortino ratio calculation"""
    sortino = calculate_sortino_ratio(sample_returns)
    assert isinstance(sortino, float)
    assert not np.isnan(sortino)
    
    # Test with all positive returns
    positive_returns = pd.Series([0.01] * 10)
    assert calculate_sortino_ratio(positive_returns) == np.inf
    
    # Test with all negative returns
    negative_returns = pd.Series([-0.01] * 10)
    assert calculate_sortino_ratio(negative_returns) < 0

def test_calmar_ratio(sample_returns):
    """Test Calmar ratio calculation"""
    # Calculate max drawdown for testing
    cum_returns = (1 + sample_returns).cumprod()
    rolling_max = cum_returns.expanding().max()
    drawdowns = cum_returns / rolling_max - 1
    max_drawdown = abs(drawdowns.min())
    
    calmar = calculate_calmar_ratio(sample_returns, max_drawdown)
    assert isinstance(calmar, float)
    assert not np.isnan(calmar)
    
    # Test with zero drawdown
    assert calculate_calmar_ratio(pd.Series([0.01] * 10), 0) == np.inf
    assert calculate_calmar_ratio(pd.Series([-0.01] * 10), 0) == -np.inf

def test_sharpe_ratio(sample_returns):
    """Test Sharpe ratio calculation"""
    sharpe = calculate_sharpe_ratio(sample_returns)
    assert isinstance(sharpe, float)
    assert not np.isnan(sharpe)
    
    # Test with all positive returns
    positive_returns = pd.Series([0.01] * 10)
    assert np.isinf(calculate_sharpe_ratio(positive_returns))
    assert calculate_sharpe_ratio(positive_returns) > 0
    
    # Test with all negative returns
    negative_returns = pd.Series([-0.01] * 10)
    assert calculate_sharpe_ratio(negative_returns) < 0
    
    # Test with empty returns
    with pytest.raises(ValueError):
        calculate_sharpe_ratio(pd.Series([]))

def test_max_consecutive():
    """Test maximum consecutive wins/losses calculation"""
    # Test consecutive wins
    returns = pd.Series([0.01, 0.02, 0.01, -0.01, -0.02, 0.01, 0.02, 0.03])
    assert calculate_max_consecutive(returns, win=True) == 3
    
    # Test consecutive losses
    assert calculate_max_consecutive(returns, win=False) == 2
    
    # Test all wins
    all_wins = pd.Series([0.01] * 5)
    assert calculate_max_consecutive(all_wins, win=True) == 5
    assert calculate_max_consecutive(all_wins, win=False) == 0
    
    # Test all losses
    all_losses = pd.Series([-0.01] * 5)
    assert calculate_max_consecutive(all_losses, win=True) == 0
    assert calculate_max_consecutive(all_losses, win=False) == 5
    
    # Test empty series
    assert calculate_max_consecutive(pd.Series([]), win=True) == 0
    assert calculate_max_consecutive(pd.Series([]), win=False) == 0

def test_profit_factor():
    """Test profit factor calculation"""
    # Test mixed returns
    returns = pd.Series([0.01, 0.02, -0.01, -0.02, 0.03])
    profit_factor = calculate_profit_factor(returns)
    assert isinstance(profit_factor, float)
    assert profit_factor == (0.01 + 0.02 + 0.03) / (0.01 + 0.02)
    
    # Test all profits
    all_profits = pd.Series([0.01, 0.02, 0.03])
    assert calculate_profit_factor(all_profits) == np.inf
    
    # Test all losses
    all_losses = pd.Series([-0.01, -0.02, -0.03])
    assert calculate_profit_factor(all_losses) == 0.0
    
    # Test empty series
    assert calculate_profit_factor(pd.Series([])) == 0.0

def test_risk_metrics(sample_returns):
    """Test comprehensive risk metrics calculation"""
    metrics = calculate_risk_metrics(sample_returns)
    
    # Check all required metrics are present
    required_metrics = [
        'total_return',
        'annualized_return',
        'max_drawdown',
        'sortino_ratio',
        'calmar_ratio',
        'sharpe_ratio',
        'volatility',
        'avg_daily_return',
        'win_rate',
        'max_consecutive_wins',
        'max_consecutive_losses',
        'profit_factor'
    ]
    
    for metric in required_metrics:
        assert metric in metrics
        if metric in ['max_consecutive_wins', 'max_consecutive_losses']:
            assert isinstance(metrics[metric], (int, np.integer))
        else:
            assert isinstance(metrics[metric], float)
        assert not np.isnan(metrics[metric])
    
    # Test win rate calculation
    assert 0 <= metrics['win_rate'] <= 1
    
    # Test with empty returns
    with pytest.raises(ValueError):
        calculate_risk_metrics(pd.Series([]))