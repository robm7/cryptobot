from typing import Dict, Any, Optional, List
import websockets
import asyncio
from confluent_kafka import Producer
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config.kafka import KafkaConfig, KafkaTopics
from auth.config import settings
import json
import logging
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server
from circuitbreaker import circuit
from .auth_middleware import JWTBearer

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication middleware
auth_scheme = JWTBearer()

# Metrics
MESSAGES_RECEIVED = Counter('data_collector_messages_received', 'Messages received from exchange')
MESSAGES_PUBLISHED = Counter('data_collector_messages_published', 'Messages published to Kafka')
CONNECTION_ERRORS = Counter('data_collector_connection_errors', 'WebSocket connection errors')
PROCESSING_ERRORS = Counter('data_collector_processing_errors', 'Message processing errors')
LATENCY = Gauge('data_collector_latency_ms', 'Processing latency in milliseconds')

class ExchangeCollector:
    def __init__(self, exchange: str, symbols: list):
        self.exchange = exchange
        self.symbols = symbols
        self.producer = self._create_kafka_producer()
        self.websocket_uri = self._get_websocket_uri()
        self.connection_timeout = 30
        self.reconnect_delay = 5

    def _create_kafka_producer(self) -> Producer:
        """Create and configure Kafka producer"""
        config = KafkaConfig.from_env().__dict__
        config.update({
            'message.timeout.ms': 5000,
            'queue.buffering.max.messages': 100000,
            'queue.buffering.max.ms': 100,
            'compression.type': 'zstd'
        })
        return Producer(config)

    @circuit(failure_threshold=5, recovery_timeout=60)
    async def connect(self):
        """Connect to exchange WebSocket with retry logic"""
        while True:
            try:
                async with websockets.connect(
                    self.websocket_uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                ) as websocket:
                    logger.info(f"Connected to {self.exchange} WebSocket")
                    await self._authenticate(websocket)
                    await self._subscribe(websocket)
                    await self._process_messages(websocket)
            except Exception as e:
                CONNECTION_ERRORS.inc()
                logger.error(f"WebSocket connection error: {e}. Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)

    async def _process_messages(self, websocket):
        """Process incoming WebSocket messages"""
        async for message in websocket:
            try:
                start_time = datetime.now()
                data = self._parse_message(message)
                if data:
                    await self._publish_to_kafka(data)
                    MESSAGES_RECEIVED.inc()
                    LATENCY.set((datetime.now() - start_time).total_seconds() * 1000)
            except Exception as e:
                PROCESSING_ERRORS.inc()
                logger.error(f"Error processing message: {e}")

    async def _publish_to_kafka(self, data: Dict[str, Any]):
        """Publish normalized data to Kafka with error handling"""
        try:
            self.producer.produce(
                topic=KafkaTopics.RAW_MARKET_DATA,
                key=f"{self.exchange}-{data['symbol']}",
                value=json.dumps(data),
                callback=self._delivery_report
            )
            MESSAGES_PUBLISHED.inc()
        except BufferError:
            logger.warning("Kafka producer queue full - flushing messages")
            self.producer.flush()
            raise
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            raise

    def _delivery_report(self, err, msg):
        """Callback for Kafka delivery reports"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def _get_websocket_uri(self) -> str:
        """Get exchange-specific WebSocket URI"""
        uris = {
            "binance": "wss://stream.binance.com:9443/ws",
            "coinbase": "wss://ws-feed.pro.coinbase.com",
            "kraken": "wss://ws.kraken.com"
        }
        return uris[self.exchange]

    def _parse_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse exchange-specific message format"""
        try:
            data = json.loads(message)
            return {
                "exchange": self.exchange,
                "symbol": data["s"],
                "price": float(data["p"]),
                "volume": float(data.get("v", 0)),
                "timestamp": int(data.get("E", datetime.now().timestamp() * 1000))
            }
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            return None

    async def _authenticate(self, websocket):
        """Authenticate with exchange if needed"""
        if self.exchange == "kraken":
            auth_msg = {
                "event": "auth",
                "apiKey": os.getenv(f"{self.exchange.upper()}_API_KEY"),
                "authSig": self._generate_signature()
            }
            await websocket.send(json.dumps(auth_msg))

    async def _subscribe(self, websocket):
        """Subscribe to market data channels"""
        for symbol in self.symbols:
            sub_msg = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@ticker"],
                "id": 1
            }
            await websocket.send(json.dumps(sub_msg))

    def _generate_signature(self) -> str:
        """Generate authentication signature"""
        # Implementation varies by exchange
        pass

# Start metrics server
start_http_server(8000)

# API Endpoints
@app.get("/subscriptions", dependencies=[Depends(JWTBearer(required_roles=["data_read"]))])
async def get_subscriptions():
    """Get currently subscribed symbols"""
    return {"symbols": collector.symbols}

@app.post("/subscriptions", dependencies=[Depends(JWTBearer(required_roles=["data_write"]))])
async def add_subscription(symbol: str):
    """Add a new symbol subscription"""
    if symbol not in collector.symbols:
        collector.symbols.append(symbol)
        await collector._subscribe()
    return {"status": "success"}

@app.delete("/subscriptions/{symbol}", dependencies=[Depends(JWTBearer(required_roles=["data_write"]))])
async def remove_subscription(symbol: str):
    """Remove a symbol subscription"""
    if symbol in collector.symbols:
        collector.symbols.remove(symbol)
    return {"status": "success"}

@app.get("/status", dependencies=[Depends(JWTBearer(required_roles=["data_read"]))])
async def get_status():
    """Get connection status"""
    return {
        "exchange": collector.exchange,
        "connected": collector.connected,
        "last_message": collector.last_message_time
    }

@app.get("/metrics", dependencies=[Depends(JWTBearer(required_roles=["monitoring"]))])
async def get_metrics():
    """Get Prometheus metrics"""
    from prometheus_client import generate_latest
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

if __name__ == "__main__":
    import uvicorn
    collector = ExchangeCollector("binance", ["BTCUSDT", "ETHUSDT"])
    uvicorn.run(app, host="0.0.0.0", port=8001)