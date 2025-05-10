import json
from typing import Dict, Any
from ...kafka.base_client import KafkaProducer
from ...config import KafkaTopics

class BinanceCollector:
    def __init__(self, symbols: list):
        self.symbols = symbols
        self.producer = KafkaProducer(KafkaConfig.from_env())

    async def _subscribe(self, websocket):
        """Subscribe to Binance WebSocket streams"""
        streams = [f"{symbol.lower()}@ticker" for symbol in self.symbols]
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_msg))

    def _parse_message(self, message: str) -> Dict[str, Any]:
        """Parse Binance WebSocket message"""
        try:
            data = json.loads(message)
            if 'e' in data and data['e'] == '24hrTicker':
                return {
                    "exchange": "binance",
                    "symbol": data['s'],
                    "price": float(data['c']),
                    "volume": float(data['v']),
                    "timestamp": data['E'],
                    "event_type": "ticker"
                }
        except json.JSONDecodeError:
            pass
        return None

    async def _process_messages(self, websocket):
        """Process Binance messages with reconnection logic"""
        while True:
            try:
                async for message in websocket:
                    data = self._parse_message(message)
                    if data:
                        await self._publish_to_kafka(data)
            except websockets.ConnectionClosed:
                print("Connection closed, reconnecting...")
                await asyncio.sleep(5)
                await self.connect()