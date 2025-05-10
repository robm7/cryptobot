from prometheus_client import start_http_server, Counter, Gauge, Histogram
import time

# Metrics setup
MESSAGES_RECEIVED = Counter(
    'data_collector_messages_received_total',
    'Total messages received from exchange',
    ['exchange', 'symbol']
)

MESSAGES_PUBLISHED = Counter(
    'data_collector_messages_published_total',
    'Total messages published to Kafka',
    ['exchange', 'symbol']
)

PROCESSING_LATENCY = Histogram(
    'data_collector_processing_latency_seconds',
    'Message processing latency distribution',
    ['exchange'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1]
)

CONNECTION_ERRORS = Counter(
    'data_collector_connection_errors_total',
    'Total WebSocket connection errors',
    ['exchange']
)

class CollectorMetrics:
    def __init__(self, exchange: str):
        self.exchange = exchange
        start_http_server(8000)

    def record_message_received(self, symbol: str):
        MESSAGES_RECEIVED.labels(
            exchange=self.exchange,
            symbol=symbol
        ).inc()

    def record_message_published(self, symbol: str):
        MESSAGES_PUBLISHED.labels(
            exchange=self.exchange,
            symbol=symbol
        ).inc()

    def record_processing_time(self, symbol: str, start_time: float):
        PROCESSING_LATENCY.labels(
            exchange=self.exchange
        ).observe(time.time() - start_time)

    def record_connection_error(self):
        CONNECTION_ERRORS.labels(
            exchange=self.exchange
        ).inc()