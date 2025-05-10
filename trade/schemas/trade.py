from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class OrderSide(str, Enum):
    buy = "buy"
    sell = "sell"

class OrderType(str, Enum):
    market = "market"
    limit = "limit"

class TradeStatus(str, Enum):
    open = "open"
    filled = "filled"
    canceled = "canceled"

class MarketOrder(BaseModel):
    exchange: str = Field(..., example="binance")
    symbol: str = Field(..., example="BTC/USDT")
    side: OrderSide
    amount: float = Field(..., gt=0, example=0.1)

class LimitOrder(BaseModel):
    exchange: str = Field(..., example="binance")
    symbol: str = Field(..., example="BTC/USDT")
    side: OrderSide
    amount: float = Field(..., gt=0, example=0.1)
    price: float = Field(..., gt=0, example=50000.0)

class TradeResponse(BaseModel):
    id: str
    exchange: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    amount: float
    price: Optional[float] = None
    status: TradeStatus
    created_at: datetime
    updated_at: datetime

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[int] = None