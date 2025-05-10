# Data Service Component Architecture

```mermaid
graph TD
    subgraph Exchange Layer
        A[Binance]
        B[Coinbase]
        C[Kraken]
    end

    subgraph Data Collection
        D[Adapter 1]
        E[Adapter 2]
        F[Adapter 3]
    end

    subgraph Event Streaming
        G[Kafka Cluster]
    end

    subgraph Processing Layer
        H[OHLCV Normalizer]
        I[Indicator Calculator]
        J[Aggregator]
    end

    subgraph Services
        K[Real-time WS]
        L[Historical API]
    end

    A --> D
    B --> E
    C --> F
    D --> G
    E --> G
    F --> G
    G --> H
    G --> I
    G --> J
    H --> G
    I --> G
    J --> G
    G --> K
    G --> L
    K --> M[Frontend]
    L --> N[Backtesting]
```

## Key Components
1. **Exchange Adapters**
   - Exchange-specific WebSocket connections
   - Normalized message format
   - Connection management

2. **Kafka Cluster**
   - Topics for raw and processed data
   - Schema registry
   - Consumer groups

3. **Processing Layer**
   - Stateful stream processing
   - Exactly-once semantics
   - Windowed operations

4. **Services**
   - WebSocket gateway
   - REST API endpoints
   - Subscription management