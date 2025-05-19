from prometheus_client import Counter, Histogram

# Define custom metrics for the data service/collector

MESSAGES_RECEIVED_TOTAL = Counter(
    "data_collector_messages_received_total",
    "Total number of messages/data points successfully received/processed.",
    ["exchange", "symbol", "type"]  # Labels: e.g., type="ohlcv_latest", type="ohlcv_historical"
)

PROCESSING_LATENCY_SECONDS = Histogram(
    "data_collector_processing_latency_seconds",
    "Latency of data fetching and processing.",
    ["exchange", "symbol", "type"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf")]
)

CONNECTION_ERRORS_TOTAL = Counter(
    "data_collector_connection_errors_total",
    "Total number of connection errors encountered while fetching data.",
    ["exchange", "symbol", "reason"] # Labels: e.g., reason="timeout", reason="apifailure"
)

# You can add more metrics here as needed, e.g., cache hit/miss ratios
CACHE_HITS_TOTAL = Counter(
    "data_collector_cache_hits_total",
    "Total number of cache hits.",
    ["endpoint"] # e.g., "ohlcv_historical"
)

CACHE_MISSES_TOTAL = Counter(
    "data_collector_cache_misses_total",
    "Total number of cache misses.",
    ["endpoint"]
)