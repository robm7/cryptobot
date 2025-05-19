"""
Portfolio Manager Service

This module provides a comprehensive portfolio management system that tracks
positions, calculates risk metrics, and manages portfolio-level risk.
"""
from typing import Dict, List, Tuple, Optional, Any, Union
from decimal import Decimal
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import asyncio
import json

from ..utils.performance_metrics import (
    get_historical_volatility,
    calculate_downside_volatility,
    calculate_ulcer_index,
    calculate_pain_index,
    calculate_max_drawdown
)

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Enhanced portfolio management service with comprehensive risk tracking.
    
    This service:
    - Tracks positions and their values
    - Calculates portfolio-level risk metrics
    - Monitors drawdown and exposure
    - Provides correlation analysis between assets
    - Tracks historical performance
    """
    
    def __init__(self, initial_equity: Optional[Decimal] = None):
        """
        Initialize the portfolio manager.
        
        Args:
            initial_equity: Optional initial account equity
        """
        # Position tracking
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: Dict[str, List[Dict[str, Any]]] = {}
        
        # Portfolio metrics
        self.account_equity = initial_equity or Decimal("100000")
        self.historical_equity: List[Dict[str, Any]] = []
        self.max_drawdown = Decimal("0")
        self.current_drawdown = Decimal("0")
        
        # Correlation data
        self.correlation_matrix = None
        self.last_correlation_update = None
        
        # Performance metrics
        self.daily_returns: List[float] = []
        self.monthly_returns: Dict[str, float] = {}  # YYYY-MM -> return
        
        # Initialize with current equity
        if initial_equity:
            self._record_equity(initial_equity)
        
        logger.info(f"Portfolio Manager initialized with equity: {float(self.account_equity):.2f}")
    
    async def add_position(self, symbol: str, quantity: Decimal, price: Decimal, 
                         timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Add a new position or update an existing one.
        
        Args:
            symbol: Trading pair symbol
            quantity: Position quantity (positive for long, negative for short)
            price: Entry price
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Dict containing the updated position
        """
        current_time = timestamp or datetime.now()
        
        # Calculate position value
        value = abs(quantity * price)
        
        # Get volatility for the symbol
        volatility = await get_historical_volatility(symbol)
        
        # Check if position already exists
        if symbol in self.positions:
            # Update existing position
            old_position = self.positions[symbol].copy()
            old_quantity = old_position["quantity"]
            old_value = old_position["value"]
            
            # Calculate new average price
            if (old_quantity > 0 and quantity > 0) or (old_quantity < 0 and quantity < 0):
                # Same direction, calculate weighted average price
                total_quantity = old_quantity + quantity
                avg_price = (old_position["avg_price"] * old_quantity + price * quantity) / total_quantity
            else:
                # Opposite direction, use new price
                avg_price = price
            
            # Update position
            self.positions[symbol].update({
                "quantity": old_quantity + quantity,
                "avg_price": avg_price,
                "value": abs((old_quantity + quantity) * price),
                "last_price": price,
                "last_update": current_time,
                "volatility": volatility
            })
            
            # Record position change in history
            if symbol not in self.position_history:
                self.position_history[symbol] = []
            
            self.position_history[symbol].append({
                "timestamp": current_time,
                "action": "update",
                "old_quantity": old_quantity,
                "quantity_change": quantity,
                "new_quantity": old_quantity + quantity,
                "price": price,
                "value_change": value,
                "new_value": self.positions[symbol]["value"]
            })
            
            logger.info(f"Updated position: {symbol}, Quantity: {float(old_quantity + quantity)}, Value: {float(self.positions[symbol]['value']):.2f}")
        else:
            # Create new position
            self.positions[symbol] = {
                "quantity": quantity,
                "avg_price": price,
                "value": value,
                "last_price": price,
                "entry_time": current_time,
                "last_update": current_time,
                "volatility": volatility,
                "pnl": Decimal("0"),
                "pnl_pct": Decimal("0")
            }
            
            # Initialize position history
            self.position_history[symbol] = [{
                "timestamp": current_time,
                "action": "open",
                "quantity_change": quantity,
                "new_quantity": quantity,
                "price": price,
                "value_change": value,
                "new_value": value
            }]
            
            logger.info(f"New position: {symbol}, Quantity: {float(quantity)}, Value: {float(value):.2f}")
        
        # Update correlation matrix if we have multiple positions
        if len(self.positions) > 1:
            await self._update_correlations()
        
        return self.positions[symbol]
    
    async def update_position_price(self, symbol: str, price: Decimal) -> Dict[str, Any]:
        """
        Update a position's current price and value.
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            
        Returns:
            Dict containing the updated position
        """
        if symbol not in self.positions:
            logger.warning(f"Cannot update price for non-existent position: {symbol}")
            return {}
        
        position = self.positions[symbol]
        old_value = position["value"]
        
        # Update position
        position["last_price"] = price
        position["value"] = abs(position["quantity"] * price)
        position["last_update"] = datetime.now()
        
        # Calculate PnL
        if position["quantity"] > 0:  # Long position
            position["pnl"] = (price - position["avg_price"]) * position["quantity"]
        else:  # Short position
            position["pnl"] = (position["avg_price"] - price) * abs(position["quantity"])
        
        # Calculate percentage PnL
        entry_value = abs(position["quantity"] * position["avg_price"])
        if entry_value > 0:
            position["pnl_pct"] = position["pnl"] / entry_value
        
        logger.debug(f"Updated position price: {symbol}, Price: {float(price):.2f}, Value: {float(position['value']):.2f}, PnL: {float(position['pnl']):.2f}")
        
        return position
    
    async def close_position(self, symbol: str, price: Decimal, 
                           timestamp: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Close an existing position.
        
        Args:
            symbol: Trading pair symbol
            price: Exit price
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Dict containing the closed position details
        """
        if symbol not in self.positions:
            logger.warning(f"Cannot close non-existent position: {symbol}")
            return {}
        
        current_time = timestamp or datetime.now()
        position = self.positions[symbol]
        
        # Calculate final PnL
        if position["quantity"] > 0:  # Long position
            pnl = (price - position["avg_price"]) * position["quantity"]
        else:  # Short position
            pnl = (position["avg_price"] - price) * abs(position["quantity"])
        
        # Calculate percentage PnL
        entry_value = abs(position["quantity"] * position["avg_price"])
        pnl_pct = pnl / entry_value if entry_value > 0 else Decimal("0")
        
        # Record position close in history
        self.position_history[symbol].append({
            "timestamp": current_time,
            "action": "close",
            "old_quantity": position["quantity"],
            "quantity_change": -position["quantity"],
            "new_quantity": Decimal("0"),
            "price": price,
            "value_change": -position["value"],
            "new_value": Decimal("0"),
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "duration": (current_time - position["entry_time"]).total_seconds() / 3600  # hours
        })
        
        # Create closed position record
        closed_position = {
            "symbol": symbol,
            "quantity": position["quantity"],
            "avg_price": position["avg_price"],
            "exit_price": price,
            "entry_time": position["entry_time"],
            "exit_time": current_time,
            "duration_hours": (current_time - position["entry_time"]).total_seconds() / 3600,
            "pnl": pnl,
            "pnl_pct": pnl_pct
        }
        
        # Remove from active positions
        del self.positions[symbol]
        
        logger.info(f"Closed position: {symbol}, PnL: {float(pnl):.2f} ({float(pnl_pct):.2%})")
        
        # Update account equity with realized PnL
        await self.update_account_equity(self.account_equity + pnl)
        
        return closed_position
    
    async def update_account_equity(self, equity: Decimal) -> Dict[str, Any]:
        """
        Update account equity and recalculate drawdown metrics.
        
        Args:
            equity: Current account equity
            
        Returns:
            Dict containing updated drawdown metrics
        """
        self.account_equity = equity
        
        # Record equity point
        self._record_equity(equity)
        
        # Calculate drawdown metrics
        drawdown_metrics = self._calculate_drawdown()
        
        logger.info(f"Updated account equity: {float(equity):.2f}, current drawdown: {float(self.current_drawdown):.2%}")
        
        return drawdown_metrics
    
    def _record_equity(self, equity: Decimal):
        """Record an equity data point"""
        timestamp = datetime.now()
        
        self.historical_equity.append({
            "timestamp": timestamp,
            "equity": float(equity)
        })
        
        # Limit history size to prevent memory issues
        if len(self.historical_equity) > 10000:
            self.historical_equity = self.historical_equity[-10000:]
        
        # Record daily return if we have at least two data points
        if len(self.historical_equity) >= 2:
            prev_equity = self.historical_equity[-2]["equity"]
            if prev_equity > 0:
                daily_return = (float(equity) - prev_equity) / prev_equity
                self.daily_returns.append(daily_return)
                
                # Limit daily returns history
                if len(self.daily_returns) > 365:
                    self.daily_returns = self.daily_returns[-365:]
        
        # Record monthly return
        month_key = timestamp.strftime("%Y-%m")
        if month_key not in self.monthly_returns:
            # Find last equity from previous month
            prev_month = (timestamp.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            prev_month_equity = None
            
            for point in reversed(self.historical_equity[:-1]):
                point_month = point["timestamp"].strftime("%Y-%m")
                if point_month == prev_month:
                    prev_month_equity = point["equity"]
                    break
            
            if prev_month_equity:
                monthly_return = (float(equity) - prev_month_equity) / prev_month_equity
                self.monthly_returns[month_key] = monthly_return
    
    def _calculate_drawdown(self) -> Dict[str, Decimal]:
        """
        Calculate current drawdown metrics.
        
        Returns:
            Dict containing current and max drawdown
        """
        if len(self.historical_equity) <= 1:
            return {
                "current_drawdown": Decimal("0"),
                "max_drawdown": Decimal("0")
            }
        
        # Extract equity values
        equity_values = [point["equity"] for point in self.historical_equity]
        
        # Calculate current drawdown
        peak = max(equity_values)
        current = equity_values[-1]
        
        if peak > current:
            self.current_drawdown = Decimal(str((peak - current) / peak))
            # Update max drawdown if current is greater
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        else:
            self.current_drawdown = Decimal("0")
        
        return {
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown
        }
    
    def get_drawdown_metrics(self) -> Dict[str, Decimal]:
        """
        Get current drawdown metrics.
        
        Returns:
            Dict containing current and max drawdown
        """
        return {
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown
        }
    
    async def get_account_equity(self) -> Decimal:
        """
        Get current account equity.
        
        Returns:
            Decimal: Current account equity
        """
        return self.account_equity
    
    async def get_portfolio_value(self) -> Decimal:
        """
        Get total portfolio value (sum of all positions).
        
        Returns:
            Decimal: Total portfolio value
        """
        return sum(p["value"] for p in self.positions.values())
    
    async def get_total_exposure(self) -> Decimal:
        """
        Get total portfolio exposure.
        
        Returns:
            Decimal: Total exposure
        """
        return sum(p["value"] for p in self.positions.values())
    
    async def get_symbol_exposure(self, symbol: str) -> Decimal:
        """
        Get exposure for a specific symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Decimal: Symbol exposure
        """
        if symbol in self.positions:
            return self.positions[symbol]["value"]
        return Decimal("0")
    
    async def _update_correlations(self, lookback_days: int = 90):
        """
        Update correlation matrix for portfolio assets.
        
        Args:
            lookback_days: Number of days to calculate correlations over
        """
        # Only update if we haven't updated recently (once per hour)
        current_time = datetime.now()
        if (self.last_correlation_update and 
            (current_time - self.last_correlation_update).total_seconds() < 3600):
            return
        
        symbols = list(self.positions.keys())
        if len(symbols) <= 1:
            return
        
        # TODO: Implement actual price data fetching
        # For now generate mock correlations
        num_assets = len(symbols)
        mock_returns = pd.DataFrame(
            np.random.normal(0, 0.01, (lookback_days, num_assets)),
            columns=symbols
        )
        
        # Calculate correlation matrix
        corr_matrix = mock_returns.corr()
        self.correlation_matrix = corr_matrix
        self.last_correlation_update = current_time
        
        logger.debug(f"Updated correlation matrix for {len(symbols)} symbols")
    
    async def get_position_risk(self, symbol: str, amount: Decimal) -> Dict[str, Any]:
        """
        Calculate risk metrics for a potential position.
        
        Args:
            symbol: Trading pair symbol
            amount: Position size in quote currency
            
        Returns:
            Dict containing risk metrics
        """
        # Get volatility metrics
        volatility = await get_historical_volatility(symbol)
        downside_vol = volatility * 0.8  # Simplified approximation
        
        # If this is the first position, return basic metrics
        if not self.positions:
            return {
                "volatility": volatility,
                "downside_volatility": downside_vol,
                "correlation_risk": 0,
                "concentration": 1.0,  # 100% if first position
                "diversification_score": 1.0,
                "current_drawdown": self.current_drawdown,
                "max_drawdown": self.max_drawdown,
                "var_95": float(amount) * 0.02 * volatility,  # Simplified VaR calculation
                "cvar_95": float(amount) * 0.03 * volatility  # Simplified CVaR calculation
            }
        
        # Calculate position concentration
        total_value = await self.get_portfolio_value()
        position_pct = float(amount) / (float(total_value) + float(amount))
        
        # Calculate weighted correlation risk
        corr_risk = 0
        if self.correlation_matrix is not None:
            # Ensure correlation matrix is updated
            await self._update_correlations()
            
            # Calculate correlation risk if symbol exists in matrix
            if symbol in self.correlation_matrix:
                for other_symbol, pos in self.positions.items():
                    if other_symbol in self.correlation_matrix.columns:
                        weight = pos["value"] / total_value
                        corr = self.correlation_matrix.loc[symbol, other_symbol]
                        corr_risk += weight * corr
        
        # Calculate portfolio impact score - higher means more diversification benefit
        diversification_score = 1.0 - corr_risk
        
        # Calculate Value at Risk (VaR) - simplified
        var_95 = float(amount) * 0.02 * volatility
        
        # Calculate Conditional VaR (CVaR) - simplified
        cvar_95 = float(amount) * 0.03 * volatility
        
        return {
            "volatility": volatility,
            "downside_volatility": downside_vol,
            "correlation_risk": corr_risk,
            "concentration": position_pct,
            "diversification_score": diversification_score,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "var_95": var_95,
            "cvar_95": cvar_95
        }
    
    async def calculate_portfolio_risk(self) -> Dict[str, Any]:
        """
        Calculate comprehensive portfolio risk metrics.
        
        Returns:
            Dict containing portfolio risk metrics
        """
        if not self.positions:
            return {
                "total_exposure": 0,
                "volatility": 0,
                "downside_volatility": 0,
                "correlation_avg": 0,
                "concentration_max": 0,
                "current_drawdown": self.current_drawdown,
                "max_drawdown": self.max_drawdown,
                "position_count": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "var_95": 0,
                "cvar_95": 0
            }
        
        total_value = sum(p["value"] for p in self.positions.values())
        
        # Calculate weighted average volatility
        weighted_vol = sum(
            p["value"] / total_value * p.get("volatility", 0.5)
            for p in self.positions.values()
        )
        
        # Calculate weighted average downside volatility
        weighted_downside_vol = weighted_vol * 0.8  # Simplified approximation
        
        # Find highest concentration
        max_concentration = max(
            p["value"] / total_value for p in self.positions.values()
        ) if self.positions else 0
        
        # Calculate average correlation if we have correlation data
        avg_correlation = 0
        if self.correlation_matrix is not None and len(self.positions) > 1:
            symbols = list(self.positions.keys())
            correlations = []
            
            for i in range(len(symbols)):
                for j in range(i+1, len(symbols)):
                    if symbols[i] in self.correlation_matrix.columns and symbols[j] in self.correlation_matrix.columns:
                        correlations.append(self.correlation_matrix.loc[symbols[i], symbols[j]])
            
            avg_correlation = np.mean(correlations) if correlations else 0
        
        # Calculate Sharpe ratio if we have daily returns
        sharpe_ratio = 0
        if self.daily_returns:
            avg_return = np.mean(self.daily_returns)
            std_dev = np.std(self.daily_returns) if len(self.daily_returns) > 1 else 0.01
            if std_dev > 0:
                sharpe_ratio = (avg_return / std_dev) * np.sqrt(252)  # Annualized
        
        # Calculate Sortino ratio (using downside deviation)
        sortino_ratio = 0
        if self.daily_returns:
            avg_return = np.mean(self.daily_returns)
            downside_returns = [r for r in self.daily_returns if r < 0]
            downside_dev = np.std(downside_returns) if downside_returns else 0.01
            if downside_dev > 0:
                sortino_ratio = (avg_return / downside_dev) * np.sqrt(252)  # Annualized
        
        # Calculate portfolio VaR and CVaR
        portfolio_var = total_value * 0.02 * weighted_vol  # Simplified 95% VaR
        portfolio_cvar = total_value * 0.03 * weighted_vol  # Simplified 95% CVaR
        
        return {
            "total_exposure": total_value,
            "volatility": weighted_vol,
            "downside_volatility": weighted_downside_vol,
            "correlation_avg": avg_correlation,
            "concentration_max": max_concentration,
            "current_drawdown": self.current_drawdown,
            "max_drawdown": self.max_drawdown,
            "position_count": len(self.positions),
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "var_95": portfolio_var,
            "cvar_95": portfolio_cvar
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.
        
        Returns:
            Dict containing performance metrics
        """
        # Calculate returns
        daily_return = 0
        weekly_return = 0
        monthly_return = 0
        
        if len(self.historical_equity) >= 2:
            current = self.historical_equity[-1]["equity"]
            
            # Daily return (from previous data point)
            prev = self.historical_equity[-2]["equity"]
            daily_return = (current - prev) / prev if prev > 0 else 0
            
            # Find data points for weekly and monthly returns
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)
            
            week_equity = None
            month_equity = None
            
            for point in reversed(self.historical_equity):
                if not week_equity and point["timestamp"] <= week_ago:
                    week_equity = point["equity"]
                if not month_equity and point["timestamp"] <= month_ago:
                    month_equity = point["equity"]
                if week_equity and month_equity:
                    break
            
            # Calculate weekly and monthly returns
            if week_equity:
                weekly_return = (current - week_equity) / week_equity if week_equity > 0 else 0
            
            if month_equity:
                monthly_return = (current - month_equity) / month_equity if month_equity > 0 else 0
        
        # Calculate Sharpe and Sortino ratios
        sharpe_ratio = 0
        sortino_ratio = 0
        
        if self.daily_returns:
            avg_return = np.mean(self.daily_returns)
            std_dev = np.std(self.daily_returns) if len(self.daily_returns) > 1 else 0.01
            
            if std_dev > 0:
                sharpe_ratio = (avg_return / std_dev) * np.sqrt(252)  # Annualized
            
            downside_returns = [r for r in self.daily_returns if r < 0]
            downside_dev = np.std(downside_returns) if downside_returns else 0.01
            
            if downside_dev > 0:
                sortino_ratio = (avg_return / downside_dev) * np.sqrt(252)  # Annualized
        
        # Get monthly returns for last 12 months
        last_12_months = {}
        now = datetime.now()
        
        for i in range(12):
            month = (now - timedelta(days=30*i)).strftime("%Y-%m")
            if month in self.monthly_returns:
                last_12_months[month] = self.monthly_returns[month]
        
        return {
            "current_equity": float(self.account_equity),
            "daily_return": daily_return,
            "weekly_return": weekly_return,
            "monthly_return": monthly_return,
            "current_drawdown": float(self.current_drawdown),
            "max_drawdown": float(self.max_drawdown),
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "monthly_returns": last_12_months,
            "position_count": len(self.positions),
            "total_exposure": float(sum(p["value"] for p in self.positions.values()))
        }