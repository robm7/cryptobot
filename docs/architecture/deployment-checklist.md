# Phase 2 Deployment Checklist

## Infrastructure Setup
- [ ] Provision Kafka cluster (3 brokers + Zookeeper)
- [ ] Configure TimescaleDB with 1 primary + 2 replicas
- [ ] Set up Kubernetes namespace and resource quotas
- [ ] Deploy monitoring stack (Prometheus + Grafana)

## Configuration
- [ ] Create Kafka topics with proper partitioning
- [ ] Set up schema registry
- [ ] Configure TimescaleDB hypertables
- [ ] Establish network policies
- [ ] Configure TLS certificates

## Service Deployment
1. **Data Collectors**
   - [ ] Binance adapter
   - [ ] Coinbase adapter
   - [ ] Kraken adapter
   - [ ] Health checks configured

2. **Stream Processors**
   - [ ] OHLCV normalizer
   - [ ] Indicator calculator
   - [ ] Aggregator
   - [ ] State stores initialized

3. **Real-time Services**
   - [ ] WebSocket gateway
   - [ ] Subscription manager
   - [ ] Connection pool

## Verification
- [ ] End-to-end test with mock data
- [ ] Load test (10,000 msg/sec per symbol)
- [ ] Failover testing
- [ ] Data consistency validation

## Monitoring
- [ ] Dashboard for key metrics
- [ ] Alert rules configured
- [ ] Log aggregation setup
- [ ] Tracing instrumentation

## Rollout Plan
1. **Phase 1**: Shadow mode (dual write)
2. **Phase 2**: 10% traffic cutover
3. **Phase 3**: 50% traffic
4. **Phase 4**: 100% traffic

## Rollback Procedure
1. Revert traffic routing
2. Verify old system stability
3. Drain new system connections
4. Perform data reconciliation