import psycopg2
from psycopg2.extras import execute_values
from confluent_kafka import Consumer
from ..config import KafkaConfig, KafkaTopics
import json
import logging
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server
import signal
import os
import asyncio
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Metrics
MESSAGES_PROCESSED = Counter('historical_messages_processed', 'Messages processed')
DB_INSERTS = Counter('historical_db_inserts', 'Database inserts')
PROCESSING_ERRORS = Counter('historical_errors', 'Processing errors')
BUFFER_SIZE = Gauge('historical_buffer_size', 'Number of records in buffer')

class HistoricalDataLoader:
    def __init__(self):
        self.conn = self._create_db_connection()
        self.consumer = Consumer({
            **KafkaConfig.from_env().__dict__,
            'group.id': 'historical-loader',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False
        })
        self.buffer: List[Dict] = []
        self.buffer_size = 1000
        self.running = True

    def _create_db_connection(self):
        """Create TimescaleDB connection"""
        return psycopg2.connect(
            host=os.getenv('TIMESCALE_HOST'),
            port=os.getenv('TIMESCALE_PORT', '5432'),
            database=os.getenv('TIMESCALE_DB'),
            user=os.getenv('TIMESCALE_USER'),
            password=os.getenv('TIMESCALE_PASSWORD')
        )

    def process(self):
        """Main processing loop"""
        self._create_tables()
        self.consumer.subscribe([KafkaTopics.NORMALIZED_OHLCV])
        
        try:
            while self.running:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    if self.buffer:
                        self._flush_buffer()
                    continue
                
                try:
                    data = json.loads(msg.value())
                    self.buffer.append(data)
                    BUFFER_SIZE.set(len(self.buffer))
                    MESSAGES_PROCESSED.inc()
                    
                    if len(self.buffer) >= self.buffer_size:
                        self._flush_buffer()
                        
                    self.consumer.commit(asynchronous=False)
                except Exception as e:
                    PROCESSING_ERRORS.inc()
                    logger.error(f"Error processing message: {e}")
                    
        finally:
            self.consumer.close()
            self.conn.close()

    def _flush_buffer(self):
        """Flush buffer to database"""
        if not self.buffer:
            return
            
        try:
            with self.conn.cursor() as cur:
                execute_values(
                    cur,
                    """
                    INSERT INTO ohlcv (timestamp, exchange, symbol, timeframe, open, high, low, close, volume)
                    VALUES %s
                    ON CONFLICT (timestamp, exchange, symbol, timeframe) DO UPDATE
                    SET open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                    """,
                    [(
                        datetime.fromtimestamp(item['timestamp']/1000),
                        item['exchange'],
                        item['symbol'],
                        item['timeframe'],
                        item['open'],
                        item['high'],
                        item['low'],
                        item['close'],
                        item['volume']
                    ) for item in self.buffer],
                    page_size=len(self.buffer)
                )
                self.conn.commit()
                DB_INSERTS.inc(len(self.buffer))
                logger.debug(f"Inserted {len(self.buffer)} records")
                
        except Exception as e:
            self.conn.rollback()
            PROCESSING_ERRORS.inc()
            logger.error(f"Failed to insert records: {e}")
        finally:
            self.buffer.clear()
            BUFFER_SIZE.set(0)

    def _create_tables(self):
        """Create hypertables if they don't exist"""
        with self.conn.cursor() as cur:
            # Create regular table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    timestamp TIMESTAMPTZ NOT NULL,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open NUMERIC NOT NULL,
                    high NUMERIC NOT NULL,
                    low NUMERIC NOT NULL,
                    close NUMERIC NOT NULL,
                    volume NUMERIC NOT NULL,
                    PRIMARY KEY (timestamp, exchange, symbol, timeframe)
                );
            """)
            
            # Convert to hypertable
            cur.execute("""
                SELECT create_hypertable(
                    'ohlcv',
                    'timestamp',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)
            
            # Create indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_timeframe 
                ON ohlcv (symbol, timeframe, timestamp DESC);
            """)
            
            self.conn.commit()

    def shutdown(self):
        """Graceful shutdown"""
        self.running = False
        logger.info("Shutting down historical data loader")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_http_server(8003)
    loader = HistoricalDataLoader()
    
    # Handle signals
    def signal_handler(sig, frame):
        loader.shutdown()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    loader.process()