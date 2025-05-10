# Cryptobot Test Suite Documentation

## Test Categories

### 1. Unit Tests
- Location: `tests/unit/`
- Purpose: Test individual components in isolation
- Coverage: 100% of core business logic
- Key Tests:
  - Exchange connectivity (`test_kraken_connectivity.py`)
  - Strategy logic (`test_breakout_reset.py`)
  - Model validation (`test_models.py`)

### 2. Integration Tests  
- Location: `tests/integration/`
- Purpose: Test interactions between components
- Coverage: All major service boundaries
- Key Tests:
  - Data pipeline (`test_data_pipeline.py`)
  - Service interactions (`test_service_interactions.py`)
  - WebSocket communication (`test_websocket.py`)

### 3. Performance Benchmarks
- Location: `tests/benchmarks/`
- Purpose: Measure and monitor system performance
- Coverage: Critical execution paths
- Key Metrics:
  - Trade execution latency (<50ms)
  - Data processing throughput (>1000 msg/sec)
  - Strategy evaluation time (<10ms)

### 4. Stress Tests
- Location: `tests/benchmarks/`
- Purpose: Validate system behavior under load
- Scenarios:
  - High frequency trading (1000+ trades/min)
  - Market data spikes (10,000+ ticks/sec)
  - Concurrent strategy execution

## Coverage Targets

| Component           | Target Coverage |
|---------------------|-----------------|
| Core Strategies     | 95%             |
| Trade Execution     | 90%             |  
| Data Services       | 85%             |
| Risk Management     | 90%             |
| Exchange Interfaces | 95%             |

## Running Tests

```bash
# Run all tests with coverage
pytest --cov=./ --cov-report=html

# Run specific test category  
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/benchmarks/ -v

# Generate coverage report
coverage html
```

## Test Maintenance

- All new features require corresponding tests
- Bug fixes must include regression tests
- Performance benchmarks run nightly
- Coverage reports generated on CI