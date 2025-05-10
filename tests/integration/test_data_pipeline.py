import pytest
import asyncio
from unittest.mock import MagicMock, patch
from confluent_kafka import KafkaException
from services.data.collector import ExchangeCollector
from services.stream.processor import OHLCVProcessor
from services.data.realtime import WebSocketGateway
from services.data.historical import HistoricalDataLoader
import json
import websockets
import psycopg2
from datetime import datetime, timedelta

@pytest.fixture
def mock_kafka_producer():
    with patch('confluent_kafka.Producer') as mock:
        producer = MagicMock()
        mock.return_value = producer
        yield producer

@pytest.fixture
def mock_kafka_consumer():
    with patch('confluent_kafka.Consumer') as mock:
        consumer = MagicMock()
        mock.return_value = consumer
        yield consumer

@pytest.fixture
def mock_websocket():
    with patch('websockets.connect') as mock:
        ws = MagicMock()
        mock.return_value.__aenter__.return_value = ws
        yield ws

@pytest.fixture
def mock_db_connection():
    with patch('psycopg2.connect') as mock:
        conn = MagicMock()
        mock.return_value = conn
        yield conn

class TestExchangeCollector:
    @pytest.mark.asyncio
    async def test_connect_and_publish(self, mock_kafka_producer, mock_websocket):
        collector = ExchangeCollector(exchange="binance", symbols=["BTCUSDT"])
        
        # Mock WebSocket message
        mock_websocket.recv.return_value = json.dumps({
            "s": "BTCUSDT",
            "p": "50000.0",
            "v": "1.0",
            "E": int(datetime.now().timestamp() * 1000)
        })
        
        # Start collector
        task = asyncio.create_task(collector.connect())
        await asyncio.sleep(0.1)  # Allow connection to establish
        
        # Verify Kafka producer was called
        mock_kafka_producer.produce.assert_called()
        
        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_reconnect_on_failure(self, mock_kafka_producer, mock_websocket):
        collector = ExchangeCollector(exchange="binance", symbols=["BTCUSDT"])
        
        # First connection fails, second succeeds
        mock_websocket.side_effect = [
            ConnectionError("First failure"),
            MagicMock()
        ]
        
        task = asyncio.create_task(collector.connect())
        await asyncio.sleep(0.1)
        
        # Should have attempted reconnect
        assert mock_websocket.call_count == 2
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

class TestOHLCVProcessor:
    def test_process_message(self, mock_kafka_consumer, mock_kafka_producer):
        processor = OHLCVProcessor(timeframes=['1m'])
        
        # Mock Kafka message
        test_msg = MagicMock()
        test_msg.value.return_value = json.dumps({
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "price": 50000.0,
            "volume": 1.0,
            "timestamp": int(datetime.now().timestamp() * 1000)
        })
        mock_kafka_consumer.poll.return_value = test_msg
        
        # Process single message
        processor.process()
        
        # Verify buffer was updated
        assert len(processor.buffers['1m']['BTCUSDT']) == 1
        
        # Verify Kafka producer was called
        mock_kafka_producer.produce.assert_called()

class TestWebSocketGateway:
    @pytest.mark.asyncio
    async def test_handle_connection(self, mock_kafka_consumer):
        gateway = WebSocketGateway()
        
        # Mock WebSocket connection
        mock_ws = MagicMock()
        mock_ws.recv.return_value = json.dumps({
            "action": "subscribe",
            "symbol": "BTCUSDT",
            "timeframe": "1m"
        })
        
        # Test connection handling
        await gateway.handle_connection(mock_ws, "/")
        
        # Verify subscription was recorded
        assert "BTCUSDT-1m" in gateway.subscriptions

class TestHistoricalDataLoader:
    def test_process_message(self, mock_kafka_consumer, mock_db_connection):
        loader = HistoricalDataLoader()
        
        # Mock Kafka message
        test_msg = MagicMock()
        test_msg.value.return_value = json.dumps({
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "timeframe": "1m",
            "open": 50000.0,
            "high": 50500.0,
            "low": 49900.0,
            "close": 50300.0,
            "volume": 1.0,
            "timestamp": int(datetime.now().timestamp() * 1000)
        })
        mock_kafka_consumer.poll.return_value = test_msg
        
        # Mock DB cursor
        mock_cursor = MagicMock()
        mock_db_connection.cursor.return_value = mock_cursor
        
        # Process single message
        loader.process()
        
        # Verify buffer was updated
        assert len(loader.buffer) == 1
        
        # Verify DB insert was called
        mock_cursor.execute.assert_called()