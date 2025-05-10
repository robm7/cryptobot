from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import logging
from config import settings
import redis
import json
from utils.exchange_interface import CcxtExchangeInterface
from utils.exchange_clients import get_exchange_client

logger = logging.getLogger(__name__)

# Redis connection
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

class OHLCV(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    exchange: str
    symbol: str
    timeframe: str

    @classmethod
    def normalize_symbol(cls, exchange: str, symbol: str) -> str:
        """Normalize symbol format across exchanges"""
        # Example: BTC/USDT -> BTCUSDT, BTC-USDT -> BTCUSDT
        return symbol.replace('/', '').replace('-', '').upper()

    @classmethod
    def normalize_timeframe(cls, exchange: str, timeframe: str) -> str:
        """Normalize timeframe format across exchanges"""
        # Example: '1m' -> '1m', '1min' -> '1m', '60' -> '1h'
        timeframe = timeframe.lower()
        if 'min' in timeframe:
            return timeframe.replace('min', 'm')
        if 'h' in timeframe:
            return timeframe.replace('h', 'h')
        if 'd' in timeframe:
            return timeframe.replace('d', 'd')
        # Handle numeric timeframes
        try:
            minutes = int(timeframe)
            if minutes % 1440 == 0:
                return f"{minutes//1440}d"
            if minutes % 60 == 0:
                return f"{minutes//60}h"
            return f"{minutes}m"
        except ValueError:
            return timeframe

    @classmethod
    async def get_latest(cls, exchange: str, symbol: str, timeframe: str) -> dict:
        """Get latest OHLCV data for a symbol from exchange"""
        cache_key = f"ohlcv_latest:{exchange}:{symbol}:{timeframe}"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        try:
            # Get exchange client
            client = get_exchange_client(exchange)
            
            # Normalize inputs
            norm_symbol = cls.normalize_symbol(exchange, symbol)
            norm_timeframe = cls.normalize_timeframe(exchange, timeframe)
            
            # Fetch ticker or OHLCV data
            ticker = await client.exchange.fetch_ticker(norm_symbol)
            
            ohlcv_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "open": float(ticker['open']),
                "high": float(ticker['high']),
                "low": float(ticker['low']),
                "close": float(ticker['close']),
                "volume": float(ticker['baseVolume']),
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe
            }
            
            redis_client.setex(cache_key, 60, json.dumps(ohlcv_data))
            return ohlcv_data
        except Exception as e:
            logger.error(f"Error fetching latest OHLCV for {exchange}:{symbol}: {e}")
            raise

    @classmethod
    async def get_historical(
        cls,
        exchange: str,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int = 1000
    ) -> List['OHLCV']:
        """Get historical OHLCV data for a symbol from exchange"""
        cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{start}:{end}"
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            return [cls(**item) for item in json.loads(cached_data)]
        
        try:
            # Get exchange client
            client = get_exchange_client(exchange)
            
            # Normalize inputs
            norm_symbol = cls.normalize_symbol(exchange, symbol)
            norm_timeframe = cls.normalize_timeframe(exchange, timeframe)
            
            # Convert to milliseconds since epoch
            since = int(start.timestamp() * 1000)
            
            # Fetch OHLCV data
            ohlcv_data = await client.exchange.fetch_ohlcv(
                norm_symbol,
                norm_timeframe,
                since=since,
                limit=limit
            )
            
            # Convert to standardized format
            normalized_data = []
            for item in ohlcv_data:
                normalized_data.append(cls(
                    timestamp=datetime.fromtimestamp(item[0]/1000),
                    open=float(item[1]),
                    high=float(item[2]),
                    low=float(item[3]),
                    close=float(item[4]),
                    volume=float(item[5]),
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe
                ))
            
            # Cache the data
            redis_client.setex(
                cache_key,
                settings.DATA_CACHE_TTL,
                json.dumps([item.dict() for item in normalized_data])
            )
            
            return normalized_data
        except Exception as e:
            logger.error(f"Error fetching historical OHLCV for {exchange}:{symbol}: {e}")
            raise