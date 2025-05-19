from fastapi import APIRouter, Path, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import asyncio
import time # Added for latency measurement
from ..models.ohlcv import OHLCV # Corrected import
from ..schemas.ohlcv import OHLCVSchema # Corrected import
from ..config import settings # Corrected import
from ..metrics import ( # Added metrics import
    MESSAGES_RECEIVED_TOTAL,
    PROCESSING_LATENCY_SECONDS,
    CONNECTION_ERRORS_TOTAL,
    CACHE_HITS_TOTAL,
    CACHE_MISSES_TOTAL
)
import redis
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Redis connection for caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

# Note: FastAPI doesn't generate full OpenAPI specs for WebSockets in the same way as HTTP.
# However, adding a docstring and potentially a related HTTP endpoint for info can be helpful.
# For actual WebSocket message schemas, they are often documented separately or via AsyncAPI.
@router.websocket(
    "/ws/ohlcv/{exchange}/{symbol}/{timeframe}",
    name="WebSocket OHLCV Stream"
)
async def websocket_ohlcv(
    websocket: WebSocket,
    exchange: str = Path(..., description="Name of the exchange", example="binance"),
    symbol: str = Path(..., description="Trading symbol (e.g., BTC/USDT)", example="BTC/USDT"),
    timeframe: str = Path(..., description="Data timeframe (e.g., 1m, 5m, 1h)", example="1m")
):
    """
    WebSocket endpoint to stream real-time OHLCV (Open, High, Low, Close, Volume) data.

    - Connect to this endpoint to receive live updates for the specified exchange, symbol, and timeframe.
    - Messages are sent as JSON, conforming to the `OHLCVWebSocketMessage` schema.
    - If an error occurs fetching data, an error message `{"error": "description"}` will be sent.
    """
    client_id = f"{exchange}_{symbol}_{timeframe}"
    await manager.connect(websocket, client_id)
    try:
        while True:
            start_time = time.monotonic()
            try:
                ohlcv_data = await OHLCV.get_latest(exchange, symbol, timeframe)
                # Successfully got data
                MESSAGES_RECEIVED_TOTAL.labels(exchange=exchange, symbol=symbol, type="ohlcv_latest").inc()
                processing_time = time.monotonic() - start_time
                PROCESSING_LATENCY_SECONDS.labels(exchange=exchange, symbol=symbol, type="ohlcv_latest").observe(processing_time)
                
                await websocket.send_json(ohlcv_data)
                
                # Adjust sleep based on timeframe
                if timeframe.endswith('m'):
                    sleep_time = int(timeframe[:-1]) * 60
                elif timeframe.endswith('h'):
                    sleep_time = int(timeframe[:-1]) * 3600
                elif timeframe.endswith('d'):
                    sleep_time = int(timeframe[:-1]) * 86400
                else:
                    sleep_time = 60  # Default to 1 minute
                    
                await asyncio.sleep(min(sleep_time, 60))  # Max 1 minute between updates
            except Exception as e:
                processing_time = time.monotonic() - start_time
                PROCESSING_LATENCY_SECONDS.labels(exchange=exchange, symbol=symbol, type="ohlcv_latest_error").observe(processing_time)
                # Determine if it's a connection error (this is a simplification)
                # In a real scenario, you'd check the type of exception or its content
                reason = "unknown_error"
                if "timeout" in str(e).lower() or "connection" in str(e).lower(): # Basic check
                    reason = "connection_issue"
                CONNECTION_ERRORS_TOTAL.labels(exchange=exchange, symbol=symbol, reason=reason).inc()
                
                logger.error(f"Error in WebSocket data feed for {client_id}: {e}")
                await websocket.send_json({"error": str(e)})
                await asyncio.sleep(5)  # Wait before retrying
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")

@router.get(
    "/ohlcv/{exchange}/{symbol}/{timeframe}",
    response_model=List[OHLCVSchema],
    summary="Get historical OHLCV data",
    description="Retrieves historical Open, High, Low, Close, and Volume data for a specific trading pair and timeframe from an exchange.",
    response_description="A list of OHLCV data points.",
    responses={
        200: {
            "description": "Successful retrieval of OHLCV data.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "timestamp": "2023-05-17T10:00:00Z", "open": 50000.0, "high": 50500.0,
                            "low": 49900.0, "close": 50300.0, "volume": 100.5,
                            "exchange": "binance", "symbol": "BTC/USDT", "timeframe": "1h"
                        },
                        {
                            "timestamp": "2023-05-17T11:00:00Z", "open": 50300.0, "high": 50800.0,
                            "low": 50200.0, "close": 50750.0, "volume": 120.0,
                            "exchange": "binance", "symbol": "BTC/USDT", "timeframe": "1h"
                        }
                    ]
                }
            }
        },
        500: {"description": "Internal server error or error fetching data from the exchange."}
        # Add 404 if applicable for invalid exchange/symbol/timeframe combinations if validated before hitting exchange
    }
)
async def get_historical_ohlcv(
    exchange: str = Path(..., description="Name of the exchange (e.g., binance, coinbasepro)", example="binance"),
    symbol: str = Path(..., description="Trading symbol (e.g., BTC/USDT, ETH-BTC). Use URL-encoded slashes if needed.", example="BTC/USDT"),
    timeframe: str = Path(..., description="Data timeframe (e.g., 1m, 5m, 1h, 1d)", example="1h"),
    start: Optional[datetime] = Query(None, description="Start timestamp for data (ISO 8601 format). Defaults to 1 day ago.", example="2023-05-16T00:00:00Z"),
    end: Optional[datetime] = Query(None, description="End timestamp for data (ISO 8601 format). Defaults to now.", example="2023-05-17T00:00:00Z"),
    limit: int = Query(1000, description="Maximum number of data points to return.", example=100, gt=0, le=1000)
):
    """
    Retrieve historical OHLCV data.
    
    - **exchange**: Name of the exchange.
    - **symbol**: Trading pair.
    - **timeframe**: Desired candle interval.
    - **start** (optional): Start date/time for the data.
    - **end** (optional): End date/time for the data.
    - **limit** (optional): Number of data points to retrieve.
    """
    # Path parameters are automatically URL-decoded by FastAPI
    # Symbol might contain '/', which is fine as a path parameter.
    
    cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{start.isoformat() if start else 'none'}:{end.isoformat() if end else 'none'}:{limit}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        CACHE_HITS_TOTAL.labels(endpoint="ohlcv_historical").inc()
        return JSONResponse(content=json.loads(cached_data))
    
    CACHE_MISSES_TOTAL.labels(endpoint="ohlcv_historical").inc()
    start_time = time.monotonic()
    try:
        data = await OHLCV.get_historical(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            start=start or datetime.utcnow() - timedelta(days=1),
            end=end or datetime.utcnow(),
            limit=limit
        )
        MESSAGES_RECEIVED_TOTAL.labels(exchange=exchange, symbol=symbol, type="ohlcv_historical").inc()
        processing_time = time.monotonic() - start_time
        PROCESSING_LATENCY_SECONDS.labels(exchange=exchange, symbol=symbol, type="ohlcv_historical").observe(processing_time)
        
        # Cache the data
        redis_client.setex(
            cache_key,
            settings.DATA_CACHE_TTL,
            json.dumps([OHLCVSchema.from_orm(item).dict(exclude_none=True) for item in data]) # Use schema for consistent output
        )
        
        return [OHLCVSchema.from_orm(item) for item in data] # Return list of schema instances
    except Exception as e:
        processing_time = time.monotonic() - start_time
        PROCESSING_LATENCY_SECONDS.labels(exchange=exchange, symbol=symbol, type="ohlcv_historical_error").observe(processing_time)
        reason = "unknown_error"
        if "timeout" in str(e).lower() or "connection" in str(e).lower():
            reason = "connection_issue"
        CONNECTION_ERRORS_TOTAL.labels(exchange=exchange, symbol=symbol, reason=reason).inc()
        
        logger.error(f"Error fetching historical data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )