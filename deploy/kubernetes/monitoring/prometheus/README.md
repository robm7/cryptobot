# Prometheus Monitoring for Cryptobot

This directory contains Kubernetes manifests for setting up Prometheus monitoring for the Cryptobot application.

## Monitoring Architecture

The monitoring architecture consists of the following components:

1. **Prometheus Server**: Central metrics collection and storage system that scrapes metrics from various targets.
2. **Service Monitors**: Custom resources that define how Prometheus should scrape metrics from services.
3. **Kube State Metrics**: Provides metrics about the state of Kubernetes objects.
4. **Node Exporter**: Collects hardware and OS metrics from Kubernetes nodes.
5. **Grafana**: Visualization platform for metrics with pre-configured dashboards.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Trade Service  │     │ Strategy Service│     │ Backtest Service│
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         │     ┌─────────────────┐     ┌─────────────────┐
         │     │  Data Service   │     │Dashboard Service│
         │     └────────┬────────┘     └────────┬────────┘
         │              │                       │
         │              │                       │
         ▼              ▼                       ▼
┌──────────────────────────────────────────────────────┐
│                     Prometheus                        │
└──────────────────────────┬───────────────────────────┘
                           │
                           │
                           ▼
┌──────────────────────────────────────────────────────┐
│                      Grafana                          │
└──────────────────────────────────────────────────────┘
```

## Components

### Prometheus

- **prometheus-configmap.yaml**: Contains the Prometheus configuration.
- **prometheus-deployment.yaml**: Deploys the Prometheus server.
- **prometheus-service.yaml**: Exposes Prometheus as a service.
- **prometheus-rbac.yaml**: RBAC rules for Prometheus to access Kubernetes API.
- **prometheus-pvc.yaml**: Persistent Volume Claim for Prometheus data.

### Service Monitors

- **trade-service-monitor.yaml**: Monitors the trade service.
- **strategy-service-monitor.yaml**: Monitors the strategy service.
- **backtest-service-monitor.yaml**: Monitors the backtest service.
- **data-service-monitor.yaml**: Monitors the data service.
- **dashboard-service-monitor.yaml**: Monitors the dashboard service.

### Kubernetes Monitoring

- **kube-state-metrics.yaml**: Deploys kube-state-metrics to monitor Kubernetes objects.
- **node-exporter.yaml**: Deploys node-exporter to collect node-level metrics.

### Visualization

- **grafana.yaml**: Deploys Grafana with pre-configured dashboards for Cryptobot services.

## Deployment

To deploy the monitoring stack, apply the manifests in the following order:

```bash
# Create RBAC resources
kubectl apply -f prometheus-rbac.yaml

# Create PVC for Prometheus
kubectl apply -f prometheus-pvc.yaml

# Create ConfigMap for Prometheus
kubectl apply -f prometheus-configmap.yaml

# Deploy Prometheus
kubectl apply -f prometheus-deployment.yaml
kubectl apply -f prometheus-service.yaml

# Deploy Kubernetes monitoring components
kubectl apply -f kube-state-metrics.yaml
kubectl apply -f node-exporter.yaml

# Deploy service monitors
kubectl apply -f trade-service-monitor.yaml
kubectl apply -f strategy-service-monitor.yaml
kubectl apply -f backtest-service-monitor.yaml
kubectl apply -f data-service-monitor.yaml
kubectl apply -f dashboard-service-monitor.yaml

# Deploy Grafana
kubectl apply -f grafana.yaml
```

## Accessing Prometheus and Grafana

### Prometheus

Prometheus is exposed as a ClusterIP service. To access it, you can:

1. Use port-forwarding:
   ```bash
   kubectl port-forward svc/prometheus 9090:9090
   ```

2. Then access Prometheus at: http://localhost:9090

### Grafana

Grafana is exposed as a ClusterIP service. To access it, you can:

1. Use port-forwarding:
   ```bash
   kubectl port-forward svc/grafana 3000:3000
   ```

2. Then access Grafana at: http://localhost:3000

3. Login with the default credentials:
   - Username: admin
   - Password: admin

## Metrics Being Collected

### System Metrics

- **Node Metrics**: CPU, memory, disk, and network usage for each node.
- **Kubernetes Metrics**: Pod status, deployment status, resource usage, etc.

### Application Metrics

The following metrics are collected from the Cryptobot services:

1. **Trade Service**:
   - HTTP request rate and latency
   - Trade execution count and latency
   - Order success/failure rates
   - Portfolio value and changes

2. **Strategy Service**:
   - Strategy evaluation rate
   - Strategy execution time
   - Signal generation metrics

3. **Backtest Service**:
   - Backtest execution count and duration
   - Simulation performance metrics

4. **Data Service**:
   - Data fetch rate and latency
   - Data processing time
   - API call rates to external services

5. **Dashboard Service**:
   - HTTP request rate and latency
   - User session metrics
   - UI rendering performance

## Adding Custom Metrics

### Instrumenting Your Code

To add custom metrics to your services, you need to instrument your code with Prometheus client libraries. Here are examples for common languages:

#### Python (using prometheus_client)

```python
from prometheus_client import Counter, Histogram, start_http_server

# Create metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])

# Use metrics
def process_request(method, endpoint, status_code, latency):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

# Start metrics server
start_http_server(8000)
```

#### JavaScript/Node.js (using prom-client)

```javascript
const prometheus = require('prom-client');

// Create metrics
const requestCount = new prometheus.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP Requests',
  labelNames: ['method', 'endpoint', 'status']
});

const requestLatency = new prometheus.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request latency',
  labelNames: ['method', 'endpoint']
});

// Use metrics
function processRequest(method, endpoint, statusCode, latency) {
  requestCount.inc({ method, endpoint, status: statusCode });
  requestLatency.observe({ method, endpoint }, latency);
}

// Start metrics server
const express = require('express');
const app = express();
app.get('/metrics', (req, res) => {
  res.set('Content-Type', prometheus.register.contentType);
  res.end(prometheus.register.metrics());
});
app.listen(8000);
```

### Exposing Metrics in Kubernetes

1. Add the following annotations to your service:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"  # Port where metrics are exposed
    prometheus.io/path: "/metrics"  # Path where metrics are exposed
```

2. Ensure your application exposes metrics on the specified port and path.

3. Update the Prometheus configuration if needed to include the new scrape target.

### Creating Custom Dashboards in Grafana

1. Log in to Grafana.
2. Click on "+" > "Dashboard" > "Add new panel".
3. Select "Prometheus" as the data source.
4. Use PromQL to query your metrics. For example:
   - `rate(http_requests_total{service="trade-service"}[5m])` - Request rate for trade service
   - `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service="trade-service"}[5m])) by (le))` - 95th percentile request latency
5. Customize the visualization and save the dashboard.

## Best Practices

1. **Use Labels Effectively**: Add meaningful labels to your metrics to enable better filtering and aggregation.
2. **Monitor the Right Things**: Focus on the Four Golden Signals:
   - Latency: How long it takes to service a request
   - Traffic: How much demand is placed on your system
   - Errors: Rate of requests that fail
   - Saturation: How "full" your service is

3. **Keep Cardinality Under Control**: Avoid creating metrics with high cardinality (too many label combinations) as it can impact Prometheus performance.

4. **Set Up Alerts**: Configure alerts for critical metrics to be notified of issues before they impact users.

5. **Regularly Review Dashboards**: Keep your dashboards updated as your application evolves.