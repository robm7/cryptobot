import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union

def calculate_sortino_ratio(returns, risk_free_rate=0.0, periods_per_year=252):
    """
    Calculate the Sortino ratio for a series of returns.
    Sortino ratio measures the risk-adjusted return, penalizing only downside volatility.
    
    Args:
        returns (pd.Series): Series of returns
        risk_free_rate (float): Annual risk-free rate
        periods_per_year (int): Number of periods in a year (252 for daily data)
        
    Returns:
        float: Sortino ratio
    """
    # Convert annual risk-free rate to per-period rate
    rf_per_period = (1 + risk_free_rate) ** (1/periods_per_year) - 1
    
    # Calculate excess returns
    excess_returns = returns - rf_per_period
    
    # Calculate downside returns
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return np.inf if excess_returns.mean() > 0 else -np.inf
    
    # Calculate downside deviation
    downside_std = np.sqrt(np.mean(downside_returns ** 2) * periods_per_year)
    
    # Calculate Sortino ratio
    sortino_ratio = np.sqrt(periods_per_year) * excess_returns.mean() / downside_std
    
    return sortino_ratio

def calculate_calmar_ratio(returns, max_drawdown, periods_per_year=252):
    """
    Calculate the Calmar ratio for a series of returns.
    Calmar ratio measures the relationship between compounded annual growth rate and maximum drawdown risk.
    
    Args:
        returns (pd.Series): Series of returns
        max_drawdown (float): Maximum drawdown value (positive number)
        periods_per_year (int): Number of periods in a year (252 for daily data)
        
    Returns:
        float: Calmar ratio
    """
    if max_drawdown == 0:
        return np.inf if returns.mean() > 0 else -np.inf
    
    # Calculate annualized return
    annualized_return = (1 + returns.mean()) ** periods_per_year - 1
    
    # Calculate Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown)
    
    return calmar_ratio

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """
    Calculate the Sharpe ratio for a series of returns.
    Sharpe ratio measures the risk-adjusted return, considering both upside and downside volatility.
    
    Args:
        returns (pd.Series): Series of returns
        risk_free_rate (float): Annual risk-free rate
        periods_per_year (int): Number of periods in a year (252 for daily data)
        
    Returns:
        float: Sharpe ratio
    """
    if len(returns) == 0:
        raise ValueError("Returns series cannot be empty")
        
    # Convert annual risk-free rate to per-period rate
    rf_per_period = (1 + risk_free_rate) ** (1/periods_per_year) - 1
    
    # Calculate excess returns
    excess_returns = returns - rf_per_period
    
    # Check if all returns are identical (zero standard deviation)
    unique_returns = returns.unique()
    if len(unique_returns) == 1:
        return float('inf') if excess_returns.mean() > 0 else float('-inf')
    
    # Calculate Sharpe ratio
    sharpe_ratio = np.sqrt(periods_per_year) * excess_returns.mean() / returns.std()
    
    return sharpe_ratio

def calculate_max_consecutive(returns: pd.Series, win: bool = True) -> int:
    """
    Calculate maximum consecutive wins or losses.
    
    Args:
        returns (pd.Series): Series of returns
        win (bool): If True, calculate max consecutive wins, else max consecutive losses
        
    Returns:
        int: Maximum consecutive wins or losses
    """
    if len(returns) == 0:
        return 0
        
    # Convert returns to binary series (1 for win, 0 for loss)
    binary = (returns > 0) if win else (returns < 0)
    
    # If no wins/losses, return 0
    if not binary.any():
        return 0
    
    # Initialize variables for counting
    max_streak = 0
    current_streak = 0
    
    # Count consecutive occurrences
    for value in binary:
        if value:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
            
    return max_streak

def calculate_profit_factor(returns: pd.Series) -> float:
    """
    Calculate profit factor (sum of profits / sum of losses).
    
    Args:
        returns (pd.Series): Series of returns
        
    Returns:
        float: Profit factor
    """
    if len(returns) == 0:
        return 0.0
        
    profits = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    
    if losses == 0:
        return np.inf if profits > 0 else 0.0
    
    return profits / losses

def calculate_risk_metrics(returns: pd.Series, risk_free_rate: float = 0.0) -> Dict[str, float]:
    """
    Calculate comprehensive risk metrics for a trading strategy.
    
    Args:
        returns (pd.Series): Series of returns
        risk_free_rate (float): Annual risk-free rate
        
    Returns:
        dict: Dictionary containing risk metrics
    """
    if len(returns) == 0:
        raise ValueError("Returns series cannot be empty")
        
    # Calculate cumulative returns
    cum_returns = (1 + returns).cumprod()
    
    # Calculate drawdown series
    rolling_max = cum_returns.expanding().max()
    drawdowns = cum_returns / rolling_max - 1
    
    # Calculate maximum drawdown
    max_drawdown = drawdowns.min()
    
    # Calculate Sortino ratio
    sortino = calculate_sortino_ratio(returns, risk_free_rate)
    
    # Calculate Calmar ratio
    calmar = calculate_calmar_ratio(returns, abs(max_drawdown))
    
    # Calculate Sharpe ratio
    sharpe = calculate_sharpe_ratio(returns, risk_free_rate)
    
    # Calculate additional metrics
    total_return = cum_returns.iloc[-1] - 1
    annualized_return = (1 + total_return) ** (252/len(returns)) - 1
    volatility = returns.std() * np.sqrt(252)
    max_consecutive_wins = calculate_max_consecutive(returns, win=True)
    max_consecutive_losses = calculate_max_consecutive(returns, win=False)
    profit_factor = calculate_profit_factor(returns)
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'sortino_ratio': sortino,
        'calmar_ratio': calmar,
        'sharpe_ratio': sharpe,
        'volatility': volatility,
        'avg_daily_return': returns.mean(),
        'win_rate': len(returns[returns > 0]) / len(returns),
        'max_consecutive_wins': max_consecutive_wins,
        'max_consecutive_losses': max_consecutive_losses,
        'profit_factor': profit_factor
    }

def get_historical_volatility(symbol: str, lookback_days: int = 30) -> float:
    """
    Calculate historical volatility for a given symbol.
    
    Args:
        symbol: Trading pair symbol
        lookback_days: Number of days to calculate volatility over
        
    Returns:
        float: Annualized volatility (standard deviation of returns)
    """
    # TODO: Implement actual data fetching from exchange/DB
    # For now return mock volatility values based on symbol
    volatility_map = {
        'BTC/USDT': 0.65,
        'ETH/USDT': 0.55,
        'SOL/USDT': 0.75,
        'ADA/USDT': 0.85,
        'DEFAULT': 0.50
    }
    
    return volatility_map.get(symbol, volatility_map['DEFAULT'])