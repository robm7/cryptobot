from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, validator, root_validator
from decimal import Decimal

class OrderSide(str, Enum):
    buy = "buy"
    sell = "sell"

class OrderType(str, Enum):
    market = "market"
    limit = "limit"
    stop_loss = "stop_loss"
    take_profit = "take_profit"
    stop_limit = "stop_limit"

class TradeStatus(str, Enum):
    open = "open"
    filled = "filled"
    partially_filled = "partially_filled"
    canceled = "canceled"
    rejected = "rejected"
    expired = "expired"

class TimeInForce(str, Enum):
    gtc = "GTC"  # Good Till Canceled
    ioc = "IOC"  # Immediate or Cancel
    fok = "FOK"  # Fill or Kill

class RiskParameters(BaseModel):
    """Risk parameters for order placement"""
    # Stop loss parameters
    stop_loss_pct: Optional[Decimal] = Field(None, description="Stop loss percentage", gt=0, le=1, example=0.05)
    stop_loss_price: Optional[Decimal] = Field(None, description="Stop loss price", gt=0)
    
    # Risk sizing parameters
    risk_tolerance: Optional[Decimal] = Field(None, description="Risk per trade as percentage of account", gt=0, le=1, example=0.01)
    position_size_pct: Optional[Decimal] = Field(None, description="Position size as percentage of account", gt=0, le=1, example=0.1)
    
    # Risk control parameters
    max_drawdown: Optional[Decimal] = Field(None, description="Maximum acceptable drawdown", gt=0, le=1, example=0.15)
    max_correlation: Optional[Decimal] = Field(None, description="Maximum correlation with existing positions", gt=0, le=1, example=0.7)
    max_concentration: Optional[Decimal] = Field(None, description="Maximum concentration in portfolio", gt=0, le=1, example=0.2)
    
    # Risk adjustment flags
    volatility_adjustment: bool = Field(True, description="Whether to adjust position size based on volatility")
    drawdown_adjustment: bool = Field(True, description="Whether to adjust position size based on drawdown")
    correlation_adjustment: bool = Field(True, description="Whether to adjust position size based on correlation")
    
    # Take profit parameters
    take_profit_pct: Optional[Decimal] = Field(None, description="Take profit percentage", gt=0, example=0.1)
    take_profit_price: Optional[Decimal] = Field(None, description="Take profit price", gt=0)
    
    # Trailing parameters
    trailing_stop_pct: Optional[Decimal] = Field(None, description="Trailing stop percentage", gt=0, le=1, example=0.03)
    
    @validator('stop_loss_pct', 'risk_tolerance', 'max_drawdown', 'position_size_pct',
               'max_correlation', 'max_concentration', 'take_profit_pct', 'trailing_stop_pct', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    @validator('stop_loss_price', 'take_profit_price', pre=True)
    def convert_price_to_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v
    
    @root_validator(skip_on_failure=True)
    def check_stop_loss(cls, values):
        """Validate that either stop_loss_pct or stop_loss_price is provided, but not both"""
        stop_loss_pct = values.get('stop_loss_pct')
        stop_loss_price = values.get('stop_loss_price')
        
        if stop_loss_pct is not None and stop_loss_price is not None:
            raise ValueError("Provide either stop_loss_pct or stop_loss_price, not both")
        
        return values
    
    @root_validator(skip_on_failure=True)
    def check_take_profit(cls, values):
        """Validate that either take_profit_pct or take_profit_price is provided, but not both"""
        take_profit_pct = values.get('take_profit_pct')
        take_profit_price = values.get('take_profit_price')
        
        if take_profit_pct is not None and take_profit_price is not None:
            raise ValueError("Provide either take_profit_pct or take_profit_price, not both")
        
        return values

class OrderBase(BaseModel):
    """Base class for all order types"""
    exchange: str = Field(..., example="binance")
    symbol: str = Field(..., example="BTC/USDT")
    side: OrderSide
    amount: Decimal = Field(..., gt=0, example=0.1)
    client_order_id: Optional[str] = Field(None, description="Client-assigned order ID")
    risk_params: Optional[RiskParameters] = None
    
    @validator('amount', pre=True)
    def convert_amount_to_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class MarketOrder(OrderBase):
    """Market order - executed immediately at current market price"""
    type: Literal["market"] = "market"
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.gtc, description="Time in force")

class LimitOrder(OrderBase):
    """Limit order - executed only at specified price or better"""
    type: Literal["limit"] = "limit"
    price: Decimal = Field(..., gt=0, example=50000.0)
    time_in_force: Optional[TimeInForce] = Field(TimeInForce.gtc, description="Time in force")
    post_only: Optional[bool] = Field(False, description="Whether the order should only be a maker order")
    
    @validator('price', pre=True)
    def convert_price_to_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class StopLossOrder(OrderBase):
    """Stop loss order - market order triggered when price reaches stop price"""
    type: Literal["stop_loss"] = "stop_loss"
    stop_price: Decimal = Field(..., gt=0, example=48000.0)
    
    @validator('stop_price', pre=True)
    def convert_stop_price_to_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class TakeProfitOrder(OrderBase):
    """Take profit order - market order triggered when price reaches target price"""
    type: Literal["take_profit"] = "take_profit"
    take_profit_price: Decimal = Field(..., gt=0, example=52000.0)
    
    @validator('take_profit_price', pre=True)
    def convert_take_profit_price_to_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class StopLimitOrder(OrderBase):
    """Stop limit order - limit order triggered when price reaches stop price"""
    type: Literal["stop_limit"] = "stop_limit"
    stop_price: Decimal = Field(..., gt=0, example=48000.0)
    limit_price: Decimal = Field(..., gt=0, example=47900.0)
    
    @validator('stop_price', 'limit_price', pre=True)
    def convert_prices_to_decimal(cls, v):
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class TradeRequest(BaseModel):
    """Request to place a trade"""
    user_id: int = Field(..., description="User ID")
    symbol: str = Field(..., example="BTC/USDT")
    side: OrderSide
    type: str = Field(..., example="limit")
    quantity: Optional[Decimal] = Field(None, gt=0, example=0.1)
    price: Optional[Decimal] = Field(None, gt=0, example=50000.0)
    stop_price: Optional[Decimal] = Field(None, gt=0, example=48000.0)
    strategy_id: Optional[int] = Field(None, description="Strategy ID if trade is from a strategy")
    risk_percentage: Optional[Decimal] = Field(None, gt=0, le=1, example=0.01)
    stop_loss_price: Optional[Decimal] = Field(None, gt=0, example=48000.0)
    take_profit_price: Optional[Decimal] = Field(None, gt=0, example=52000.0)
    
    @validator('quantity', 'price', 'stop_price', 'risk_percentage',
               'stop_loss_price', 'take_profit_price', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class TradeResponse(BaseModel):
    """Response after placing a trade"""
    id: str
    exchange: str
    symbol: str
    order_type: str
    side: OrderSide
    amount: Decimal
    price: Optional[Decimal] = None
    status: TradeStatus
    created_at: datetime
    updated_at: datetime
    risk_metrics: Optional[Dict[str, Any]] = None
    
    @validator('amount', 'price', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    code: Optional[int] = None
    context: Optional[Dict[str, Any]] = None

class RiskLimitResponse(BaseModel):
    """Response containing risk limits"""
    limits: Dict[str, Any]
    user_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class RiskMetricsResponse(BaseModel):
    """Response containing risk metrics"""
    metrics: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)