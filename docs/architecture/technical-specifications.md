# Data Service Decoupling - Technical Specifications

## 1. System Requirements

### Hardware
| Component              | Minimum Specs          | Recommended Specs      |
|------------------------|------------------------|------------------------|
| Kafka Brokers          | 4 vCPU, 16GB RAM       | 8 vCPU, 32GB RAM       |
| Stream Processors      | 2 vCPU, 4GB RAM        | 4 vCPU, 8GB RAM        |
| TimescaleDB Primary    | 8 vCPU, 32GB RAM       | 16 vCPU, 64GB RAM      |
| Data Collectors        | 1 vCPU, 2GB RAM        | 2 vCPU, 4GB RAM        |

### Software
- Kafka 3.5.0
- Python 3.10+
- TimescaleDB 2.10
- Kubernetes 1.25+
- Prometheus 2.40+

## 2. Kafka Configuration

### Cluster Setup
```yaml
broker:
  count: 3
  config:
    num.network.threads: 3
    num.io.threads: 8
    socket.send.buffer.bytes: 102400
    socket.receive.buffer.bytes: 102400
    socket.request.max.bytes: 104857600
```

### Topic Configuration
| Topic                | Partitions | Retention | Replication |
|----------------------|------------|-----------|-------------|
| raw.market-data      | 30         | 7 days    | 3           |
| normalized.ohlcv     | 60         | 30 days   | 3           |
| processed.indicators | 30         | 1 day     | 2           |

## 3. Data Collection Specifications

### Exchange Adapters
| Exchange | Rate Limit     | WebSocket Endpoints           | Special Requirements         |
|----------|----------------|--------------------------------|------------------------------|
| Binance  | 1000 msg/sec   | wss://stream.binance.com:9443 | IP whitelisting recommended  |
| Coinbase | 500 msg/sec    | wss://ws-feed.pro.coinbase.com | Message signing required     |
| Kraken   | 300 msg/sec    | wss://ws.kraken.com           | Connection limit: 20 per IP  |

### Collector Configuration
```python
class CollectorConfig:
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 5.0  # seconds
    MESSAGE_QUEUE_SIZE = 1000
    HEARTBEAT_INTERVAL = 30.0  # seconds
```

## 4. Processing Specifications

### Stream Processing
```java
properties.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, "exactly_once_v2");
properties.put(StreamsConfig.NUM_STREAM_THREADS_CONFIG, 4);
properties.put(StreamsConfig.STATE_DIR_CONFIG, "/data/state");
```

### Performance Targets
| Metric                          | Target Value          |
|---------------------------------|-----------------------|
| End-to-end latency (99%)        | < 200ms               |
| Maximum throughput per symbol   | 10,000 msg/sec        |
| Recovery time (failure)         | < 60 seconds          |
| State store rebuild time        | < 5 minutes           |

## 5. Database Schema

### TimescaleDB Hypertable
```sql
CREATE TABLE ohlcv (
    time TIMESTAMPTZ NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume DOUBLE PRECISION
) USING TimescaleDB;

SELECT create_hypertable('ohlcv', 'time');
```

## 6. Monitoring & Alerting

### Key Metrics
- Kafka: Consumer lag, broker CPU
- Collectors: Connection status, message rate
- Processors: State store size, commit rate
- Database: Query latency, replication lag

### Alert Thresholds
| Metric                | Warning | Critical |
|-----------------------|---------|----------|
| Consumer lag (msgs)   | 1000    | 5000     |
| CPU utilization (%)   | 70      | 90       |
| Memory utilization (%)| 75      | 90       |
| Disk utilization (%)  | 80      | 95       |

## 7. Security Specifications

### Encryption
- TLS 1.3 for all external communications
- SASL/SCRAM for Kafka authentication
- Column-level encryption for sensitive fields

### Access Control
- RBAC for all services
- Network policies restricting pod-to-pod communication
- VPC peering for database access