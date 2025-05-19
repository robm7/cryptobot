from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from decimal import Decimal
import logging
from utils.performance_metrics import (
    get_historical_volatility,
    calculate_downside_volatility,
    calculate_ulcer_index,
    calculate_pain_index,
    calculate_max_drawdown
)

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self):
        self.positions = {}
        self.correlation_matrix = None
        self.historical_equity = []  # Track account equity over time
        self.max_drawdown = Decimal('0')
        self.current_drawdown = Decimal('0')
        
    async def calculate_correlations(self, symbols: List[str], lookback_days: int = 90) -> Dict[str, Dict[str, float]]:
        """Calculate pairwise correlations between assets in portfolio.
        
        Args:
            symbols: List of trading pair symbols
            lookback_days: Number of days to calculate correlations over
            
        Returns:
            Dictionary of correlation coefficients between each pair
        """
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
        
        # Convert to nested dict format
        return {
            sym1: {
                sym2: float(corr_matrix.loc[sym1, sym2]) 
                for sym2 in symbols if sym2 != sym1
            }
            for sym1 in symbols
        }
        
    async def update_account_equity(self, equity: Decimal):
        """
        Update account equity history and recalculate drawdown metrics
        
        Args:
            equity: Current account equity
        """
        # Add to historical equity
        self.historical_equity.append(float(equity))
        
        # Calculate current drawdown if we have enough data
        if len(self.historical_equity) > 1:
            peak = max(self.historical_equity)
            current = self.historical_equity[-1]
            
            if peak > current:
                self.current_drawdown = Decimal(str((peak - current) / peak))
                # Update max drawdown if current is greater
                self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
            else:
                self.current_drawdown = Decimal('0')
                
        logger.info(f"Updated account equity: {float(equity):.2f}, current drawdown: {float(self.current_drawdown):.2%}")
    
    def get_drawdown_metrics(self) -> Dict:
        """
        Get current drawdown metrics
        
        Returns:
            Dict containing current and max drawdown
        """
        return {
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown
        }
    
    async def get_position_risk(self, symbol: str, amount: Decimal) -> Dict:
        """
        Calculate risk metrics for a potential position.
        
        Args:
            symbol: Trading pair symbol
            amount: Position size in quote currency
            
        Returns:
            Dict containing:
            - volatility: Historical volatility
            - downside_volatility: Downside volatility
            - correlation_risk: Weighted correlation risk score
            - concentration: Percentage of portfolio
            - current_drawdown: Current portfolio drawdown
            - max_drawdown: Maximum historical drawdown
        """
        # Get volatility metrics
        volatility = await get_historical_volatility(symbol)
        
        # If this is the first position, return basic metrics
        if not self.positions:
            return {
                'volatility': volatility,
                'downside_volatility': volatility * 0.8,  # Simplified approximation
                'correlation_risk': 0,
                'concentration': 1.0,  # 100% if first position
                'current_drawdown': self.current_drawdown,
                'max_drawdown': self.max_drawdown
            }
            
        # Calculate position concentration
        total_value = sum(p['value'] for p in self.positions.values())
        position_pct = float(amount) / (total_value + float(amount))
        
        # Calculate weighted correlation risk
        corr_risk = 0
        if self.correlation_matrix is not None and symbol in self.correlation_matrix:
            for other_symbol, pos in self.positions.items():
                if other_symbol in self.correlation_matrix.columns:
                    weight = pos['value'] / total_value
                    corr = self.correlation_matrix.loc[symbol, other_symbol]
                    corr_risk += weight * corr
        
        # Calculate portfolio impact score - higher means more diversification benefit
        diversification_score = 1.0 - corr_risk
                    
        return {
            'volatility': volatility,
            'downside_volatility': volatility * 0.8,  # Simplified approximation
            'correlation_risk': corr_risk,
            'concentration': position_pct,
            'diversification_score': diversification_score,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown
        }
    
    async def calculate_portfolio_risk(self) -> Dict:
        """
        Calculate comprehensive portfolio risk metrics
        
        Returns:
            Dict containing portfolio risk metrics
        """
        if not self.positions:
            return {
                'total_exposure': 0,
                'volatility': 0,
                'correlation_avg': 0,
                'concentration_max': 0,
                'current_drawdown': self.current_drawdown,
                'max_drawdown': self.max_drawdown
            }
            
        total_value = sum(p['value'] for p in self.positions.values())
        
        # Calculate weighted average volatility
        weighted_vol = sum(
            p['value'] / total_value * p.get('volatility', 0.5)
            for p in self.positions.values()
        )
        
        # Find highest concentration
        max_concentration = max(
            p['value'] / total_value for p in self.positions.values()
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
        
        return {
            'total_exposure': total_value,
            'volatility': weighted_vol,
            'correlation_avg': avg_correlation,
            'concentration_max': max_concentration,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'position_count': len(self.positions)
        }