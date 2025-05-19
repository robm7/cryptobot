from typing import Union, Optional, Dict
import logging
from decimal import Decimal
import numpy as np
from ..schemas.trade import MarketOrder, LimitOrder # Corrected import
from utils.performance_metrics import (
    get_historical_volatility,
    calculate_downside_volatility,
    calculate_ulcer_index,
    calculate_pain_index
)

logger = logging.getLogger(__name__)

class RiskService:
    MAX_ORDER_SIZE = Decimal('10000')  # Max order size in quote currency
    MAX_EXPOSURE = Decimal('50000')    # Max total exposure
    RISK_PER_TRADE = Decimal('0.01')   # 1% of account per trade
    MAX_DRAWDOWN_THRESHOLD = Decimal('0.15')  # 15% max drawdown threshold
    CRITICAL_DRAWDOWN_THRESHOLD = Decimal('0.25')  # 25% critical drawdown threshold
    
    # Volatility scaling factors
    VOLATILITY_SCALING_ENABLED = True
    VOLATILITY_BASELINE = Decimal('0.50')  # Baseline volatility (considered "normal")
    VOLATILITY_MAX_ADJUSTMENT = Decimal('0.75')  # Maximum reduction due to volatility (75%)
    
    # Drawdown control settings
    DRAWDOWN_CONTROL_ENABLED = True
    DRAWDOWN_SCALING_FACTOR = Decimal('2.0')  # How aggressively to scale down on drawdown
    
    @classmethod
    async def calculate_position_size(cls,
                                   symbol: str,
                                   account_equity: Decimal,
                                   stop_loss_pct: Optional[Decimal] = None,
                                   volatility_factor: bool = True,
                                   current_drawdown: Optional[Decimal] = None,
                                   risk_tolerance: Optional[Decimal] = None) -> Decimal:
        """
        Calculate optimal position size based on risk parameters
        
        Args:
            symbol: Trading pair symbol
            account_equity: Current account equity
            stop_loss_pct: Stop loss percentage (if applicable)
            volatility_factor: Whether to adjust for volatility
            current_drawdown: Current drawdown as a decimal (e.g., 0.05 for 5%)
            risk_tolerance: Custom risk tolerance (overrides default RISK_PER_TRADE)
            
        Returns:
            Decimal: Calculated position size in quote currency
        """
        # Use custom risk tolerance if provided, otherwise use default
        risk_per_trade = risk_tolerance if risk_tolerance is not None else cls.RISK_PER_TRADE
        
        # Base position size calculation
        base_size = account_equity * risk_per_trade
        
        # Adjust for stop loss if provided
        if stop_loss_pct:
            base_size = base_size / stop_loss_pct
        
        # Apply dynamic volatility scaling if enabled
        if volatility_factor and cls.VOLATILITY_SCALING_ENABLED:
            volatility = await get_historical_volatility(symbol)
            volatility_decimal = Decimal(str(volatility))
            
            # Calculate volatility adjustment factor (more sophisticated than before)
            # Higher volatility = smaller position sizes
            if volatility_decimal > cls.VOLATILITY_BASELINE:
                # Calculate how much volatility exceeds baseline (as a ratio)
                excess_volatility_ratio = (volatility_decimal / cls.VOLATILITY_BASELINE) - Decimal('1.0')
                
                # Apply non-linear scaling (square root) to avoid too drastic reductions
                # for extremely volatile assets while still being responsive
                adjustment_factor = Decimal('1.0') - (cls.VOLATILITY_MAX_ADJUSTMENT *
                                                    (Decimal(str(np.sqrt(float(excess_volatility_ratio)))))
                                                   )
                
                # Ensure adjustment doesn't go below minimum threshold (25% of original size)
                adjustment_factor = max(adjustment_factor, Decimal('0.25'))
                
                # Apply adjustment
                base_size = base_size * adjustment_factor
                logger.info(f"Volatility adjustment for {symbol}: {float(adjustment_factor):.2f}x (vol: {float(volatility_decimal):.2f})")
        
        # Apply drawdown controls if enabled and drawdown is provided
        if current_drawdown is not None and cls.DRAWDOWN_CONTROL_ENABLED:
            base_size = cls._apply_drawdown_control(base_size, current_drawdown)
            
        # Apply maximum order size limit
        return min(base_size, cls.MAX_ORDER_SIZE)
    
    @classmethod
    def _apply_drawdown_control(cls, position_size: Decimal, current_drawdown: Decimal) -> Decimal:
        """
        Apply drawdown control to position sizing
        
        Args:
            position_size: Calculated position size before drawdown control
            current_drawdown: Current drawdown as a decimal (positive number)
            
        Returns:
            Decimal: Adjusted position size
        """
        # Convert drawdown to positive number if it's negative
        drawdown_abs = abs(current_drawdown)
        
        # No adjustment needed if drawdown is minimal
        if drawdown_abs < Decimal('0.05'):  # Less than 5% drawdown
            return position_size
            
        # Apply progressive scaling based on drawdown severity
        if drawdown_abs < cls.MAX_DRAWDOWN_THRESHOLD:
            # Scale down linearly between 5% and MAX_DRAWDOWN_THRESHOLD
            # Calculate how far between 5% and threshold (0.0 to 1.0)
            severity = (drawdown_abs - Decimal('0.05')) / (cls.MAX_DRAWDOWN_THRESHOLD - Decimal('0.05'))
            # Apply scaling factor (more aggressive with higher DRAWDOWN_SCALING_FACTOR)
            reduction_factor = Decimal('1.0') - (severity * Decimal('0.5') * cls.DRAWDOWN_SCALING_FACTOR)
            adjusted_size = position_size * reduction_factor
            logger.info(f"Drawdown control: {float(drawdown_abs):.2%} drawdown, reducing position to {float(reduction_factor):.2%} of normal size")
            return adjusted_size
            
        elif drawdown_abs < cls.CRITICAL_DRAWDOWN_THRESHOLD:
            # Severe drawdown - more aggressive reduction (25% of normal size)
            logger.warning(f"Severe drawdown detected: {float(drawdown_abs):.2%}, reducing position to 25% of normal size")
            return position_size * Decimal('0.25')
            
        else:
            # Critical drawdown - minimal position size (10% of normal) or consider halting trading
            logger.critical(f"Critical drawdown detected: {float(drawdown_abs):.2%}, reducing position to 10% of normal size")
            return position_size * Decimal('0.1')
    
    @classmethod
    async def get_risk_metrics(cls, symbol: str, returns=None) -> Dict:
        """
        Get comprehensive risk metrics for a symbol
        
        Args:
            symbol: Trading pair symbol
            returns: Optional historical returns data
            
        Returns:
            Dict containing risk metrics
        """
        # Get volatility metrics
        volatility = await get_historical_volatility(symbol)
        
        # For now, return basic metrics
        # In a real implementation, this would use actual returns data
        # and calculate more comprehensive metrics
        return {
            'volatility': volatility,
            'downside_volatility': volatility * 0.8,  # Simplified approximation
            'current_drawdown': Decimal('0.07'),  # Example value, would be calculated from actual data
            'max_drawdown': Decimal('0.12'),  # Example value, would be calculated from actual data
            'ulcer_index': 0.05,  # Example value
            'pain_index': 0.04,  # Example value
        }
    
    @classmethod
    async def validate_order(cls, order: Union[MarketOrder, LimitOrder],
                          account_equity: Optional[Decimal] = None,
                          current_drawdown: Optional[Decimal] = None,
                          risk_tolerance: Optional[Decimal] = None):
        """
        Validate order against risk rules
        
        Args:
            order: The order to validate
            account_equity: Current account equity
            current_drawdown: Current drawdown as a decimal
            risk_tolerance: Custom risk tolerance level
        
        Raises:
            ValueError: If order violates risk rules
        """
        # Check max order size
        if order.amount > cls.MAX_ORDER_SIZE:
            logger.warning(f"Order exceeds max size: {order.amount} > {cls.MAX_ORDER_SIZE}")
            raise ValueError(f"Order size exceeds maximum allowed ({cls.MAX_ORDER_SIZE})")
        
        # Get risk metrics for the symbol
        risk_metrics = await cls.get_risk_metrics(order.symbol)
        
        # Check if trading should be halted due to excessive drawdown
        if current_drawdown is not None and current_drawdown > cls.CRITICAL_DRAWDOWN_THRESHOLD:
            logger.critical(f"Trading halted due to excessive drawdown: {float(current_drawdown):.2%}")
            raise ValueError(f"Trading halted - drawdown exceeds critical threshold ({float(cls.CRITICAL_DRAWDOWN_THRESHOLD):.0%})")
            
        # Validate position sizing if account equity provided
        if account_equity:
            # Get stop loss percentage if available
            stop_loss_pct = order.stop_loss_pct if hasattr(order, 'stop_loss_pct') else None
            
            # Calculate recommended size with enhanced parameters
            recommended_size = await cls.calculate_position_size(
                order.symbol,
                account_equity,
                stop_loss_pct=stop_loss_pct,
                volatility_factor=True,
                current_drawdown=current_drawdown,
                risk_tolerance=risk_tolerance
            )
            
            # Check if order exceeds recommended size (with tolerance)
            if order.amount > recommended_size * Decimal('1.1'):  # Allow 10% tolerance
                logger.warning(f"Order size {order.amount} exceeds recommended {recommended_size}")
                
                # If significantly over recommended size, reject the order
                if order.amount > recommended_size * Decimal('1.5'):  # 50% over limit
                    raise ValueError(f"Order size {order.amount} significantly exceeds risk-adjusted recommended size {recommended_size}")
                
        # Check portfolio correlation risk if portfolio service available
        if hasattr(order, 'portfolio_service'):
            risk_metrics = await order.portfolio_service.get_position_risk(
                order.symbol,
                order.amount * (order.price if hasattr(order, 'price') else Decimal('1'))
            )
            
            # Enhanced correlation risk checks
            if risk_metrics['correlation_risk'] > 0.7:  # High correlation threshold
                logger.warning(f"High correlation risk: {risk_metrics['correlation_risk']}")
                
                # If extremely high correlation, reject the order
                if risk_metrics['correlation_risk'] > 0.9:
                    raise ValueError(f"Order rejected - extremely high correlation risk: {risk_metrics['correlation_risk']:.2f}")
                    
            # Enhanced concentration checks
            if risk_metrics['concentration'] > 0.3:  # 30% concentration threshold
                logger.warning(f"High concentration: {risk_metrics['concentration']*100:.1f}%")
                
                # If extremely high concentration, reject the order
                if risk_metrics['concentration'] > 0.5:  # 50% concentration
                    raise ValueError(f"Order rejected - position would exceed maximum concentration: {risk_metrics['concentration']*100:.1f}%")
        
        # Additional validation for limit orders
        if isinstance(order, LimitOrder):
            if order.price <= 0:
                raise ValueError("Limit price must be positive")