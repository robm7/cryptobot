"""
Performance Metrics Utility

This module provides functions for calculating various performance and risk metrics.
"""
from typing import List, Dict, Optional, Union, Tuple
from decimal import Decimal
import numpy as np
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def get_historical_volatility(symbol: str, lookback_days: int = 30) -> float:
    """
    Calculate historical volatility for a symbol.
    
    Args:
        symbol: Trading pair symbol
        lookback_days: Number of days to look back
        
    Returns:
        float: Annualized volatility
    """
    # TODO: Implement actual price data fetching
    # For now, return mock volatility based on symbol
    
    # Use first characters of symbol to generate deterministic but different volatilities
    # This is just for testing purposes
    base_volatility = 0.5  # 50% base volatility
    
    # Use hash of symbol to generate a modifier between 0.5 and 1.5
    symbol_hash = sum(ord(c) for c in symbol[:4])
    modifier = 0.5 + (symbol_hash % 100) / 100.0
    
    volatility = base_volatility * modifier
    
    # Cap at reasonable values
    return min(max(volatility, 0.2), 1.2)

def calculate_downside_volatility(returns: List[float], threshold: float = 0.0) -> float:
    """
    Calculate downside volatility (semi-deviation).
    
    Args:
        returns: List of return values
        threshold: Minimum acceptable return (usually 0)
        
    Returns:
        float: Downside volatility
    """
    if not returns:
        return 0.0
    
    # Filter returns below threshold
    downside_returns = [r for r in returns if r < threshold]
    
    if not downside_returns:
        return 0.0
    
    # Calculate semi-deviation
    return np.std(downside_returns) * np.sqrt(252)  # Annualized

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio.
    
    Args:
        returns: List of daily return values
        risk_free_rate: Risk-free rate (annualized)
        
    Returns:
        float: Sharpe ratio
    """
    if not returns:
        return 0.0
    
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1
    
    excess_returns = [r - daily_rf for r in returns]
    avg_excess_return = np.mean(excess_returns)
    std_dev = np.std(excess_returns)
    
    if std_dev == 0:
        return 0.0
    
    # Annualize
    return (avg_excess_return / std_dev) * np.sqrt(252)

def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sortino ratio.
    
    Args:
        returns: List of daily return values
        risk_free_rate: Risk-free rate (annualized)
        
    Returns:
        float: Sortino ratio
    """
    if not returns:
        return 0.0
    
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1
    
    excess_returns = [r - daily_rf for r in returns]
    avg_excess_return = np.mean(excess_returns)
    downside_dev = calculate_downside_volatility(excess_returns)
    
    if downside_dev == 0:
        return 0.0
    
    # Annualize
    return (avg_excess_return / downside_dev) * np.sqrt(252)

def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        equity_curve: List of equity values over time
        
    Returns:
        float: Maximum drawdown as a decimal (e.g., 0.25 for 25%)
    """
    if not equity_curve:
        return 0.0
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(equity_curve)
    
    # Calculate drawdown at each point
    drawdowns = (running_max - equity_curve) / running_max
    
    # Return maximum drawdown
    return float(np.max(drawdowns))

def calculate_ulcer_index(equity_curve: List[float], lookback_days: int = 14) -> float:
    """
    Calculate Ulcer Index (UI).
    
    Args:
        equity_curve: List of equity values over time
        lookback_days: Number of days to look back
        
    Returns:
        float: Ulcer Index
    """
    if not equity_curve or len(equity_curve) < lookback_days:
        return 0.0
    
    # Use only the lookback period
    values = equity_curve[-lookback_days:]
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(values)
    
    # Calculate percentage drawdown at each point
    drawdowns = (running_max - values) / running_max
    
    # Square the drawdowns and take the mean
    squared_drawdowns = np.square(drawdowns)
    mean_squared_drawdown = np.mean(squared_drawdowns)
    
    # Return square root of mean squared drawdown
    return float(np.sqrt(mean_squared_drawdown))

def calculate_pain_index(equity_curve: List[float], lookback_days: int = 14) -> float:
    """
    Calculate Pain Index.
    
    Args:
        equity_curve: List of equity values over time
        lookback_days: Number of days to look back
        
    Returns:
        float: Pain Index
    """
    if not equity_curve or len(equity_curve) < lookback_days:
        return 0.0
    
    # Use only the lookback period
    values = equity_curve[-lookback_days:]
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(values)
    
    # Calculate percentage drawdown at each point
    drawdowns = (running_max - values) / running_max
    
    # Return mean drawdown
    return float(np.mean(drawdowns))

def calculate_calmar_ratio(returns: List[float], equity_curve: List[float], 
                         lookback_years: float = 3.0) -> float:
    """
    Calculate Calmar ratio.
    
    Args:
        returns: List of daily return values
        equity_curve: List of equity values over time
        lookback_years: Number of years to look back
        
    Returns:
        float: Calmar ratio
    """
    if not returns or not equity_curve:
        return 0.0
    
    # Calculate annualized return
    total_return = (equity_curve[-1] / equity_curve[0]) - 1
    days = len(returns)
    annualized_return = (1 + total_return) ** (252 / days) - 1
    
    # Calculate max drawdown
    max_dd = calculate_max_drawdown(equity_curve)
    
    if max_dd == 0:
        return 0.0
    
    return annualized_return / max_dd

def calculate_var(returns: List[float], confidence: float = 0.95) -> float:
    """
    Calculate Value at Risk (VaR).
    
    Args:
        returns: List of daily return values
        confidence: Confidence level (e.g., 0.95 for 95%)
        
    Returns:
        float: Value at Risk
    """
    if not returns:
        return 0.0
    
    # Sort returns
    sorted_returns = sorted(returns)
    
    # Find the index at the confidence level
    index = int(len(sorted_returns) * (1 - confidence))
    
    # Return the value at that index
    return abs(sorted_returns[max(0, index)])

def calculate_cvar(returns: List[float], confidence: float = 0.95) -> float:
    """
    Calculate Conditional Value at Risk (CVaR) / Expected Shortfall.
    
    Args:
        returns: List of daily return values
        confidence: Confidence level (e.g., 0.95 for 95%)
        
    Returns:
        float: Conditional Value at Risk
    """
    if not returns:
        return 0.0
    
    # Sort returns
    sorted_returns = sorted(returns)
    
    # Find the index at the confidence level
    index = int(len(sorted_returns) * (1 - confidence))
    
    # Calculate average of returns beyond VaR
    tail_returns = sorted_returns[:max(1, index)]
    
    return abs(np.mean(tail_returns))

def calculate_correlation(returns1: List[float], returns2: List[float]) -> float:
    """
    Calculate correlation between two return series.
    
    Args:
        returns1: First list of return values
        returns2: Second list of return values
        
    Returns:
        float: Correlation coefficient
    """
    if not returns1 or not returns2:
        return 0.0
    
    # Ensure equal length
    min_length = min(len(returns1), len(returns2))
    returns1 = returns1[-min_length:]
    returns2 = returns2[-min_length:]
    
    return float(np.corrcoef(returns1, returns2)[0, 1])

def calculate_beta(returns: List[float], market_returns: List[float]) -> float:
    """
    Calculate beta relative to market.
    
    Args:
        returns: List of asset return values
        market_returns: List of market return values
        
    Returns:
        float: Beta coefficient
    """
    if not returns or not market_returns:
        return 1.0
    
    # Ensure equal length
    min_length = min(len(returns), len(market_returns))
    returns = returns[-min_length:]
    market_returns = market_returns[-min_length:]
    
    # Calculate covariance and variance
    covariance = np.cov(returns, market_returns)[0, 1]
    market_variance = np.var(market_returns)
    
    if market_variance == 0:
        return 1.0
    
    return covariance / market_variance

def calculate_alpha(returns: List[float], market_returns: List[float], 
                  risk_free_rate: float = 0.0, beta: Optional[float] = None) -> float:
    """
    Calculate Jensen's alpha.
    
    Args:
        returns: List of asset return values
        market_returns: List of market return values
        risk_free_rate: Risk-free rate (annualized)
        beta: Optional pre-calculated beta
        
    Returns:
        float: Alpha
    """
    if not returns or not market_returns:
        return 0.0
    
    # Ensure equal length
    min_length = min(len(returns), len(market_returns))
    returns = returns[-min_length:]
    market_returns = market_returns[-min_length:]
    
    # Convert annual risk-free rate to daily
    daily_rf = (1 + risk_free_rate) ** (1/252) - 1
    
    # Calculate average returns
    avg_return = np.mean(returns)
    avg_market_return = np.mean(market_returns)
    
    # Calculate beta if not provided
    if beta is None:
        beta = calculate_beta(returns, market_returns)
    
    # Calculate alpha
    alpha = avg_return - (daily_rf + beta * (avg_market_return - daily_rf))
    
    # Annualize
    return alpha * 252