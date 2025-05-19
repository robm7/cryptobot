from pydantic import BaseModel, Field
from datetime import datetime

class OHLCVBase(BaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the OHLCV data point (UTC).", example="2023-05-17T10:00:00Z")
    open: float = Field(..., description="Opening price.", example=50000.0)
    high: float = Field(..., description="Highest price.", example=50500.0)
    low: float = Field(..., description="Lowest price.", example=49900.0)
    close: float = Field(..., description="Closing price.", example=50300.0)
    volume: float = Field(..., description="Trading volume.", example=100.5)

class OHLCVCreate(OHLCVBase):
    exchange: str = Field(..., description="Name of the exchange.", example="binance")
    symbol: str = Field(..., description="Trading symbol.", example="BTC/USDT")
    timeframe: str = Field(..., description="Timeframe of the OHLCV data (e.g., 1m, 5m, 1h).", example="1m")

class OHLCVSchema(OHLCVBase):
    exchange: str = Field(..., description="Name of the exchange.", example="binance")
    symbol: str = Field(..., description="Trading symbol.", example="BTC/USDT")
    timeframe: str = Field(..., description="Timeframe of the OHLCV data.", example="1m")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat().replace('+00:00', 'Z')
        }


class OHLCVWebSocketMessage(BaseModel):
    event: str = Field("ohlcv_update", description="Type of WebSocket event.", example="ohlcv_update")
    data: OHLCVSchema = Field(..., description="The OHLCV data payload.")