from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from typing import Dict, List
import json
import asyncio
from models.ohlcv import OHLCV
from schemas.ohlcv import OHLCVSchema
from config import settings
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

@router.websocket("/ws/ohlcv/{exchange}/{symbol}/{timeframe}")
async def websocket_ohlcv(
    websocket: WebSocket,
    exchange: str,
    symbol: str,
    timeframe: str
):
    client_id = f"{exchange}_{symbol}_{timeframe}"
    await manager.connect(websocket, client_id)
    try:
        while True:
            try:
                ohlcv_data = await OHLCV.get_latest(exchange, symbol, timeframe)
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
                logger.error(f"Error in WebSocket data feed for {client_id}: {e}")
                await websocket.send_json({"error": str(e)})
                await asyncio.sleep(5)  # Wait before retrying
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Client {client_id} disconnected")

@router.get("/ohlcv/{exchange}/{symbol}/{timeframe}")
async def get_historical_ohlcv(
    exchange: str,
    symbol: str,
    timeframe: str,
    start: datetime = None,
    end: datetime = None,
    limit: int = 1000
):
    cache_key = f"ohlcv:{exchange}:{symbol}:{timeframe}:{start}:{end}"
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        return JSONResponse(content=json.loads(cached_data))
    
    try:
        data = await OHLCV.get_historical(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            start=start or datetime.utcnow() - timedelta(days=1),
            end=end or datetime.utcnow(),
            limit=limit
        )
        
        # Cache the data
        redis_client.setex(
            cache_key,
            settings.DATA_CACHE_TTL,
            json.dumps([item.dict() for item in data])
        )
        
        return data
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )