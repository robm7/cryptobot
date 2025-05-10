# Data Flow Sequence Diagrams

## Real-time OHLCV Processing
```mermaid
sequenceDiagram
    participant Exchange
    participant Collector
    participant Kafka
    participant Processor
    participant RealTimeService
    participant Frontend

    Exchange->>Collector: WebSocket Stream (Raw)
    Collector->>Kafka: Publish to raw.market-data
    Kafka->>Processor: Consume raw data
    Processor->>Processor: Normalize OHLCV
    Processor->>Kafka: Publish to normalized.ohlcv
    Kafka->>RealTimeService: Consume OHLCV
    RealTimeService->>Frontend: WebSocket Push
```

## Historical Data Loading
```mermaid
sequenceDiagram
    participant Processor
    participant Kafka
    participant HistoricalLoader
    participant TimescaleDB
    participant API

    Processor->>Kafka: Publish normalized OHLCV
    Kafka->>HistoricalLoader: Consume OHLCV
    HistoricalLoader->>TimescaleDB: Batch Insert
    API->>TimescaleDB: Query Historical Data
    TimescaleDB-->>API: Return OHLCV Series
```

## Key Flows
1. **Real-time Path**: <100ms latency
2. **Batch Path**: 5 minute SLA
3. **Query Path**: Sub-second response for 30d of 1m data