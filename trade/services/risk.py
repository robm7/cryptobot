from typing import Union, Optional
import logging
from decimal import Decimal
import numpy as np
from schemas.trade import MarketOrder, LimitOrder
from utils.performance_metrics import get_historical_volatility

logger = logging.getLogger(__name__)

class RiskService:
    MAX_ORDER_SIZE = Decimal('10000')  # Max order size in quote currency
    MAX_EXPOSURE = Decimal('50000')    # Max total exposure
    RISK_PER_TRADE = Decimal('0.01')   # 1% of account per trade
    
    @classmethod
    async def calculate_position_size(cls,
                                   symbol: str,
                                   account_equity: Decimal,
                                   stop_loss_pct: Optional[Decimal] = None,
                                   volatility_factor: bool = False) -> Decimal:
        """Calculate optimal position size based on risk parameters"""
        base_size = account_equity * cls.RISK_PER_TRADE
        
        if stop_loss_pct:
            base_size = base_size / stop_loss_pct
            
        if volatility_factor:
            volatility = await get_historical_volatility(symbol)
            # Reduce size for more volatile assets
            base_size = base_size / (1 + Decimal(str(volatility)))
            
        return min(base_size, cls.MAX_ORDER_SIZE)
    
    @classmethod
    async def validate_order(cls, order: Union[MarketOrder, LimitOrder],
                          account_equity: Optional[Decimal] = None):
        """Validate order against risk rules"""
        # Check max order size
        if order.amount > cls.MAX_ORDER_SIZE:
            logger.warning(f"Order exceeds max size: {order.amount} > {cls.MAX_ORDER_SIZE}")
            raise ValueError(f"Order size exceeds maximum allowed ({cls.MAX_ORDER_SIZE})")
            
        # Validate position sizing if account equity provided
        if account_equity:
            recommended_size = await cls.calculate_position_size(
                order.symbol,
                account_equity,
                order.stop_loss_pct if hasattr(order, 'stop_loss_pct') else None
            )
            if order.amount > recommended_size * Decimal('1.1'):  # Allow 10% tolerance
                logger.warning(f"Order size {order.amount} exceeds recommended {recommended_size}")
                
        # Check portfolio correlation risk if portfolio service available
        if hasattr(order, 'portfolio_service'):
            risk_metrics = await order.portfolio_service.get_position_risk(
                order.symbol,
                order.amount * (order.price if hasattr(order, 'price') else 1)
            )
            if risk_metrics['correlation_risk'] > 0.7:  # High correlation threshold
                logger.warning(f"High correlation risk: {risk_metrics['correlation_risk']}")
            if risk_metrics['concentration'] > 0.3:  # 30% concentration threshold
                logger.warning(f"High concentration: {risk_metrics['concentration']*100:.1f}%")
        
        # Additional validation for limit orders
        if isinstance(order, LimitOrder):
            if order.price <= 0:
                raise ValueError("Limit price must be positive")