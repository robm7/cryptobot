from pydantic import BaseModel
from datetime import datetime

class OHLCVBase(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class OHLCVCreate(OHLCVBase):
    exchange: str
    symbol: str
    timeframe: str

class OHLCVSchema(OHLCVBase):
    exchange: str
    symbol: str
    timeframe: str

    class Config:
        orm_mode = True

class OHLCVWebSocketMessage(BaseModel):
    event: str = "ohlcv_update"
    data: OHLCVSchema