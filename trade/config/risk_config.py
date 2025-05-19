"""
Risk Management Configuration

This module contains configuration settings for the risk management system.
"""
from decimal import Decimal
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class RiskConfig:
    """Risk management configuration settings"""
    
    def __init__(self):
        # Per-trade risk limits
        self.MAX_ORDER_SIZE = Decimal(os.getenv("RISK_MAX_ORDER_SIZE", "10000"))  # Max order size in quote currency
        self.RISK_PER_TRADE = Decimal(os.getenv("RISK_PER_TRADE", "0.01"))  # 1% of account per trade
        self.MAX_SLIPPAGE_PCT = Decimal(os.getenv("RISK_MAX_SLIPPAGE_PCT", "0.01"))  # 1% max slippage
        
        # Per-symbol risk limits
        self.MAX_SYMBOL_EXPOSURE = Decimal(os.getenv("RISK_MAX_SYMBOL_EXPOSURE", "20000"))  # Max exposure per symbol
        self.MAX_SYMBOL_CONCENTRATION = Decimal(os.getenv("RISK_MAX_SYMBOL_CONCENTRATION", "0.20"))  # 20% max concentration
        
        # Portfolio-level risk limits
        self.MAX_PORTFOLIO_EXPOSURE = Decimal(os.getenv("RISK_MAX_PORTFOLIO_EXPOSURE", "50000"))  # Max total exposure
        self.MAX_LEVERAGE = Decimal(os.getenv("RISK_MAX_LEVERAGE", "2.0"))  # Max leverage
        self.MAX_CORRELATION = Decimal(os.getenv("RISK_MAX_CORRELATION", "0.7"))  # Max correlation between positions
        
        # Time-based risk limits
        self.MAX_DAILY_DRAWDOWN = Decimal(os.getenv("RISK_MAX_DAILY_DRAWDOWN", "0.05"))  # 5% max daily drawdown
        self.MAX_WEEKLY_DRAWDOWN = Decimal(os.getenv("RISK_MAX_WEEKLY_DRAWDOWN", "0.10"))  # 10% max weekly drawdown
        self.MAX_TRADES_PER_DAY = int(os.getenv("RISK_MAX_TRADES_PER_DAY", "20"))  # Max trades per day
        
        # Drawdown control settings
        self.DRAWDOWN_CONTROL_ENABLED = os.getenv("RISK_DRAWDOWN_CONTROL_ENABLED", "true").lower() == "true"
        self.MAX_DRAWDOWN_THRESHOLD = Decimal(os.getenv("RISK_MAX_DRAWDOWN_THRESHOLD", "0.15"))  # 15% max drawdown threshold
        self.CRITICAL_DRAWDOWN_THRESHOLD = Decimal(os.getenv("RISK_CRITICAL_DRAWDOWN_THRESHOLD", "0.25"))  # 25% critical drawdown threshold
        self.DRAWDOWN_SCALING_FACTOR = Decimal(os.getenv("RISK_DRAWDOWN_SCALING_FACTOR", "2.0"))  # How aggressively to scale down on drawdown
        
        # Volatility scaling settings
        self.VOLATILITY_SCALING_ENABLED = os.getenv("RISK_VOLATILITY_SCALING_ENABLED", "true").lower() == "true"
        self.VOLATILITY_BASELINE = Decimal(os.getenv("RISK_VOLATILITY_BASELINE", "0.50"))  # Baseline volatility (considered "normal")
        self.VOLATILITY_MAX_ADJUSTMENT = Decimal(os.getenv("RISK_VOLATILITY_MAX_ADJUSTMENT", "0.75"))  # Maximum reduction due to volatility (75%)
        
        # Circuit breaker settings
        self.CIRCUIT_BREAKER_ENABLED = os.getenv("RISK_CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
        self.CIRCUIT_BREAKER_THRESHOLD = Decimal(os.getenv("RISK_CIRCUIT_BREAKER_THRESHOLD", "0.10"))  # 10% market move triggers circuit breaker
        self.CIRCUIT_BREAKER_COOLDOWN_MINUTES = int(os.getenv("RISK_CIRCUIT_BREAKER_COOLDOWN_MINUTES", "60"))  # 60 minute cooldown
        
        # Risk monitoring settings
        self.RISK_MONITORING_INTERVAL_SECONDS = int(os.getenv("RISK_MONITORING_INTERVAL_SECONDS", "60"))  # Check risk every 60 seconds
        self.RISK_ALERT_THRESHOLD = Decimal(os.getenv("RISK_ALERT_THRESHOLD", "0.80"))  # Alert at 80% of risk limit
        
    def get_risk_limits(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get risk limits, optionally customized for a specific user
        
        Args:
            user_id: Optional user ID to get custom risk limits
            
        Returns:
            Dictionary of risk limits
        """
        # In a real implementation, this would fetch user-specific risk limits from a database
        # For now, return the default limits
        return {
            "max_order_size": self.MAX_ORDER_SIZE,
            "risk_per_trade": self.RISK_PER_TRADE,
            "max_slippage_pct": self.MAX_SLIPPAGE_PCT,
            "max_symbol_exposure": self.MAX_SYMBOL_EXPOSURE,
            "max_symbol_concentration": self.MAX_SYMBOL_CONCENTRATION,
            "max_portfolio_exposure": self.MAX_PORTFOLIO_EXPOSURE,
            "max_leverage": self.MAX_LEVERAGE,
            "max_correlation": self.MAX_CORRELATION,
            "max_daily_drawdown": self.MAX_DAILY_DRAWDOWN,
            "max_weekly_drawdown": self.MAX_WEEKLY_DRAWDOWN,
            "max_trades_per_day": self.MAX_TRADES_PER_DAY,
        }

# Singleton instance
risk_config = RiskConfig()