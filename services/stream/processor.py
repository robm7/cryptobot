from confluent_kafka import Consumer, Producer
from ..config import KafkaConfig, KafkaTopics
import json
from datetime import datetime, timedelta
from collections import defaultdict
import time
import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from typing import Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)

# Metrics
MESSAGES_CONSUMED = Counter('processor_messages_consumed', 'Messages consumed from Kafka')
CANDLES_GENERATED = Counter('processor_candles_generated', 'OHLCV candles generated')
PROCESSING_ERRORS = Counter('processor_errors', 'Processing errors')
PROCESSING_LATENCY = Histogram('processor_latency_seconds', 'Processing latency in seconds')
BUFFER_SIZE = Gauge('processor_buffer_size', 'Number of ticks in buffer')

class OHLCVProcessor:
    def __init__(self, timeframes: List[str] = ['1m', '5m', '15m', '1h', '4h', '1d']):
        self.timeframes = timeframes
        self.buffers = {
            tf: defaultdict(list) for tf in timeframes
        }
        self.consumer = Consumer({
            **KafkaConfig.from_env().__dict__,
            'group.id': 'ohlcv-processor',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'isolation.level': 'read_committed'
        })
        self.producer = Producer({
            **KafkaConfig.from_env().__dict__,
            'compression.type': 'zstd',
            'queue.buffering.max.messages': 100000
        })
        self.running = True

    def process(self):
        """Main processing loop"""
        self.consumer.subscribe([KafkaTopics.RAW_MARKET_DATA])
        
        try:
            while self.running:
                start_time = time.time()
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    self._flush_old_buffers()
                    continue
                
                try:
                    data = json.loads(msg.value())
                    for timeframe in self.timeframes:
                        self._update_buffer(timeframe, data)
                    
                    # Check if we should publish candles
                    current_ts = int(time.time())
                    for timeframe in self.timeframes:
                        interval = self._timeframe_to_seconds(timeframe)
                        if current_ts % interval == 0:
                            self._publish_ohlcv(timeframe)
                    
                    self.consumer.commit(asynchronous=False)
                    MESSAGES_CONSUMED.inc()
                    PROCESSING_LATENCY.observe(time.time() - start_time)
                    
                except Exception as e:
                    PROCESSING_ERRORS.inc()
                    logger.error(f"Error processing message: {e}")
                    
        finally:
            self.consumer.close()
            self.producer.flush()

    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds"""
        if timeframe.endswith('m'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 3600
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 86400
        return 60  # Default to 1 minute

    def _update_buffer(self, timeframe: str, data: Dict[str, Any]):
        """Update buffer with new tick data"""
        symbol = data['symbol']
        self.buffers[timeframe][symbol].append({
            'price': float(data['price']),
            'timestamp': data['timestamp'],
            'volume': float(data.get('volume', 0))
        })
        BUFFER_SIZE.set(len(self.buffers[timeframe][symbol]))

    def _flush_old_buffers(self):
        """Flush buffers for incomplete intervals"""
        current_ts = int(time.time())
        for timeframe in self.timeframes:
            interval = self._timeframe_to_seconds(timeframe)
            cutoff = current_ts - interval
            
            for symbol in list(self.buffers[timeframe].keys()):
                self.buffers[timeframe][symbol] = [
                    tick for tick in self.buffers[timeframe][symbol]
                    if (int(tick['timestamp']) // 1000) >= cutoff
                ]

    def _publish_ohlcv(self, timeframe: str):
        """Calculate and publish OHLCV for each symbol"""
        for symbol, ticks in self.buffers[timeframe].items():
            if not ticks:
                continue
                
            prices = [t['price'] for t in ticks]
            volumes = [t['volume'] for t in ticks]
            
            ohlcv = {
                "open": prices[0],
                "high": max(prices),
                "low": min(prices),
                "close": prices[-1],
                "volume": sum(volumes),
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": int(time.time() * 1000),
                "exchange": ticks[0].get('exchange', 'unknown')
            }
            
            try:
                self.producer.produce(
                    topic=KafkaTopics.NORMALIZED_OHLCV,
                    key=f"{symbol}-{timeframe}",
                    value=json.dumps(ohlcv),
                    callback=self._delivery_report
                )
                CANDLES_GENERATED.inc()
            except Exception as e:
                logger.error(f"Failed to publish OHLCV: {e}")
                
        self.producer.flush()
        self.buffers[timeframe].clear()

    def _delivery_report(self, err, msg):
        """Callback for Kafka delivery reports"""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def shutdown(self):
        """Graceful shutdown"""
        self.running = False

# Start metrics server
start_http_server(8001)