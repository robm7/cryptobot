import asyncio
import websockets
from typing import Dict, Set, Optional
from confluent_kafka import Consumer
from ..config import KafkaConfig, KafkaTopics
import json
import logging
from datetime import datetime
from collections import defaultdict
from prometheus_client import Counter, Gauge, start_http_server
import uuid
import signal
import os

logger = logging.getLogger(__name__)

# Metrics
ACTIVE_CONNECTIONS = Gauge('realtime_active_connections', 'Active WebSocket connections')
MESSAGES_DELIVERED = Counter('realtime_messages_delivered', 'Messages delivered to clients')
CONNECTION_ERRORS = Counter('realtime_connection_errors', 'WebSocket connection errors')
SUBSCRIPTIONS = Gauge('realtime_subscriptions', 'Active subscriptions by symbol')

class WebSocketGateway:
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # symbol -> connection_ids
        self.consumer = Consumer({
            **KafkaConfig.from_env().__dict__,
            'group.id': 'websocket-gateway',
            'auto.offset.reset': 'latest',
            'enable.auto.commit': False
        })
        self.running = True
        self.loop = asyncio.get_event_loop()

    async def start(self, host: str = '0.0.0.0', port: int = 8765):
        """Start WebSocket server and Kafka consumer"""
        # Setup signal handlers
        self.loop.add_signal_handler(signal.SIGTERM, self.shutdown)
        self.loop.add_signal_handler(signal.SIGINT, self.shutdown)

        # Start metrics server
        start_http_server(8002)

        # Start WebSocket server
        server = await websockets.serve(
            self.handle_connection,
            host,
            port,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        )
        logger.info(f"WebSocket server started on ws://{host}:{port}")

        # Start Kafka consumer
        self.consumer.subscribe([KafkaTopics.NORMALIZED_OHLCV])
        asyncio.create_task(self._consume_messages())

        await server.wait_closed()

    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        ACTIVE_CONNECTIONS.inc()

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('action') == 'subscribe':
                        await self._handle_subscription(connection_id, data)
                    elif data.get('action') == 'unsubscribe':
                        await self._handle_unsubscription(connection_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid message from {connection_id}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection {connection_id} closed")
        finally:
            await self._cleanup_connection(connection_id)

    async def _handle_subscription(self, connection_id: str, data: Dict):
        """Handle subscription request"""
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', '1m')

        if not symbol:
            return

        key = f"{symbol}-{timeframe}"
        self.subscriptions[key].add(connection_id)
        SUBSCRIPTIONS.inc()
        logger.info(f"Connection {connection_id} subscribed to {key}")

    async def _handle_unsubscription(self, connection_id: str, data: Dict):
        """Handle unsubscription request"""
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', '1m')

        if not symbol:
            return

        key = f"{symbol}-{timeframe}"
        if connection_id in self.subscriptions[key]:
            self.subscriptions[key].remove(connection_id)
            SUBSCRIPTIONS.dec()
            logger.info(f"Connection {connection_id} unsubscribed from {key}")

    async def _cleanup_connection(self, connection_id: str):
        """Clean up connection resources"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            ACTIVE_CONNECTIONS.dec()

        # Remove from all subscriptions
        for key in list(self.subscriptions.keys()):
            if connection_id in self.subscriptions[key]:
                self.subscriptions[key].remove(connection_id)
                SUBSCRIPTIONS.dec()

    async def _consume_messages(self):
        """Consume messages from Kafka and broadcast to subscribers"""
        while self.running:
            msg = self.consumer.poll(1.0)
            
            if msg is None:
                continue
                
            try:
                data = json.loads(msg.value())
                symbol = data['symbol']
                timeframe = data['timeframe']
                key = f"{symbol}-{timeframe}"
                
                if key in self.subscriptions:
                    for connection_id in list(self.subscriptions[key]):
                        if connection_id in self.connections:
                            try:
                                await self.connections[connection_id].send(json.dumps(data))
                                MESSAGES_DELIVERED.inc()
                            except Exception as e:
                                logger.warning(f"Failed to send to {connection_id}: {e}")
                                await self._cleanup_connection(connection_id)
                                
                self.consumer.commit(asynchronous=False)
            except Exception as e:
                logger.error(f"Error processing Kafka message: {e}")

    def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        self.consumer.close()
        logger.info("Shutting down WebSocket gateway")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gateway = WebSocketGateway()
    asyncio.run(gateway.start())