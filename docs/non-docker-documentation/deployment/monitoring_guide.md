# Cryptobot Monitoring Guide

This guide provides comprehensive information on monitoring the Cryptobot application in a non-Docker environment. It covers monitoring setup, configuration, dashboards, alerting, and best practices for maintaining system health and performance.

## Table of Contents

1. [Monitoring Architecture](#monitoring-architecture)
2. [Monitoring Components](#monitoring-components)
3. [Installation and Setup](#installation-and-setup)
4. [Prometheus Configuration](#prometheus-configuration)
5. [Grafana Dashboards](#grafana-dashboards)
6. [Alerting Configuration](#alerting-configuration)
7. [Log Aggregation](#log-aggregation)
8. [Performance Monitoring](#performance-monitoring)
9. [Security Monitoring](#security-monitoring)
10. [Custom Metrics](#custom-metrics)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)

## Monitoring Architecture

The Cryptobot monitoring system uses a multi-layered approach to provide comprehensive visibility into the application's health, performance, and security. The architecture consists of the following components:

1. **Metrics Collection**: Prometheus collects metrics from all Cryptobot services and system components.
2. **Metrics Visualization**: Grafana provides dashboards for visualizing metrics and trends.
3. **Alerting**: Alertmanager processes alerts and sends notifications through various channels.
4. **Log Aggregation**: Filebeat, Elasticsearch, and Kibana collect, store, and visualize logs.
5. **System Monitoring**: Node Exporter provides system-level metrics for the host machine.

### Architecture Diagram

```
+----------------+     +----------------+     +----------------+
| Cryptobot      |     | System         |     | Database       |
| Services       |     | (Node Exporter)|     | (PostgreSQL)   |
+-------+--------+     +-------+--------+     +-------+--------+
        |                      |                      |
        v                      v                      v
+-------+--------------------------------------------+--------+
|                         Prometheus                          |
+-------+--------------------------------------------+--------+
        |                                            |
        v                                            v
+-------+--------+                          +-------+--------+
| Grafana        |                          | Alertmanager   |
+----------------+                          +-------+--------+
                                                    |
                                                    v
                                            +-------+--------+
                                            | Notification   |
                                            | Channels       |
                                            +----------------+

+----------------+     +----------------+     +----------------+
| Cryptobot      |     | System         |     | Application    |
| Logs           |     | Logs           |     | Logs           |
+-------+--------+     +-------+--------+     +-------+--------+
        |                      |                      |
        v                      v                      v
+-------+--------------------------------------------+--------+
|                         Filebeat                            |
+-------+--------------------------------------------+--------+
        |
        v
+-------+--------+
| Elasticsearch  |
+-------+--------+
        |
        v
+-------+--------+
| Kibana         |
+----------------+
```

## Monitoring Components

### Prometheus

[Prometheus](https://prometheus.io/) is an open-source systems monitoring and alerting toolkit. It collects metrics from configured targets at given intervals, evaluates rule expressions, displays the results, and can trigger alerts when specified conditions are observed.

Key features:
- Multi-dimensional data model with time series data identified by metric name and key/value pairs
- Flexible query language (PromQL) to leverage this dimensionality
- No reliance on distributed storage; single server nodes are autonomous
- Time series collection via a pull model over HTTP
- Pushing time series is supported via an intermediary gateway
- Targets are discovered via service discovery or static configuration
- Multiple modes of graphing and dashboarding support

### Grafana

[Grafana](https://grafana.com/) is an open-source platform for monitoring and observability. It allows you to query, visualize, alert on, and understand your metrics no matter where they are stored.

Key features:
- Visualize metrics with various chart types
- Create dynamic and reusable dashboards
- Explore metrics with ad-hoc queries
- Set up alerts based on metric thresholds
- Mix different data sources in the same graph
- Annotate graphs with events

### Alertmanager

[Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) handles alerts sent by client applications such as the Prometheus server. It takes care of deduplicating, grouping, and routing them to the correct receiver integration such as email, PagerDuty, or Slack.

Key features:
- Grouping of similar alerts
- Silencing of specific alerts
- Inhibition of alerts when other alerts are present
- Routing to different receivers based on alert labels
- Deduplication of similar alerts

### Node Exporter

[Node Exporter](https://github.com/prometheus/node_exporter) is a Prometheus exporter for hardware and OS metrics exposed by *NIX kernels, written in Go with pluggable metric collectors.

Key features:
- CPU usage metrics
- Memory usage metrics
- Disk usage metrics
- Network metrics
- System load metrics

### Filebeat

[Filebeat](https://www.elastic.co/beats/filebeat) is a lightweight shipper for forwarding and centralizing log data. Installed as an agent on your servers, Filebeat monitors the log files or locations that you specify, collects log events, and forwards them to Elasticsearch or Logstash for indexing.

Key features:
- Lightweight log shipping
- Centralized log collection
- Log parsing and enrichment
- Secure communication with TLS
- Automatic discovery of log sources

### Elasticsearch

[Elasticsearch](https://www.elastic.co/elasticsearch/) is a distributed, RESTful search and analytics engine capable of addressing a growing number of use cases. As the heart of the Elastic Stack, it centrally stores your data for lightning-fast search, fine‑tuned relevancy, and powerful analytics.

Key features:
- Distributed and highly available search engine
- Multi-tenancy
- Full-text search
- Document-oriented
- Schema-free
- RESTful API

### Kibana

[Kibana](https://www.elastic.co/kibana/) is an open-source data visualization dashboard for Elasticsearch. It provides visualization capabilities on top of the content indexed on an Elasticsearch cluster.

Key features:
- Real-time data visualization
- Interactive dashboards
- Advanced analytics
- Machine learning features
- Graph exploration
- Application monitoring

## Installation and Setup

The monitoring system can be installed using the provided scripts. These scripts automate the installation and configuration of all monitoring components.

### Prerequisites

- Administrative/root access to the server
- Internet access for downloading components
- Sufficient disk space (at least 10GB recommended)
- Sufficient memory (at least 4GB recommended)

### Automated Installation

Use the provided script to install and configure the monitoring system:

- Windows:
  ```powershell
  .\scripts\non-docker-deployment\setup_monitoring.ps1
  ```

- Linux/macOS:
  ```bash
  ./scripts/non-docker-deployment/setup_monitoring.sh
  ```

This script will:
1. Install Prometheus, Grafana, Alertmanager, and Node Exporter
2. Configure each component with default settings
3. Set up service management for automatic startup
4. Import default dashboards and alert rules

### Manual Installation

If you prefer to install components manually or need a customized setup, follow these steps:

#### Prometheus Installation

1. Download Prometheus from the [official website](https://prometheus.io/download/)
2. Extract the archive to your preferred location
3. Create a configuration file (see [Prometheus Configuration](#prometheus-configuration))
4. Set up Prometheus as a service

#### Grafana Installation

1. Download Grafana from the [official website](https://grafana.com/grafana/download)
2. Install according to your operating system's requirements
3. Configure Grafana to connect to Prometheus
4. Import dashboards (see [Grafana Dashboards](#grafana-dashboards))

#### Alertmanager Installation

1. Download Alertmanager from the [official website](https://prometheus.io/download/#alertmanager)
2. Extract the archive to your preferred location
3. Create a configuration file (see [Alerting Configuration](#alerting-configuration))
4. Set up Alertmanager as a service

#### Node Exporter Installation

1. Download Node Exporter from the [official website](https://prometheus.io/download/#node_exporter)
2. Extract the archive to your preferred location
3. Set up Node Exporter as a service

#### Log Aggregation Installation

1. Install Elasticsearch, Kibana, and Filebeat using the provided script:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\setup_logging.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/setup_logging.sh
     ```

2. Or install each component manually following the official documentation

## Prometheus Configuration

Prometheus is configured using a YAML file. The default configuration file is located at:

- Windows: `<install_dir>\monitoring\prometheus\prometheus.yml`
- Linux/macOS: `/etc/prometheus/prometheus.yml` or `<install_dir>/monitoring/prometheus/prometheus.yml`

### Basic Configuration

The basic Prometheus configuration includes:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093

rule_files:
  - "rules/alert_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
    
  - job_name: 'cryptobot-auth'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8000']
    
  - job_name: 'cryptobot-strategy'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8001']
    
  - job_name: 'cryptobot-backtest'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8002']
    
  - job_name: 'cryptobot-trade'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8003']
    
  - job_name: 'cryptobot-data'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8004']
    
  - job_name: 'cryptobot-mcp'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['localhost:8010', 'localhost:8011', 'localhost:8012', 'localhost:8013', 'localhost:8014']
```

### Advanced Configuration

For advanced use cases, consider the following configurations:

#### Service Discovery

Instead of static configuration, you can use service discovery to automatically find targets:

```yaml
scrape_configs:
  - job_name: 'file-based-discovery'
    file_sd_configs:
      - files:
        - 'targets/*.json'
        refresh_interval: 5m
```

#### Relabeling

Use relabeling to modify labels before scraping:

```yaml
scrape_configs:
  - job_name: 'cryptobot'
    static_configs:
      - targets: ['localhost:8000', 'localhost:8001', 'localhost:8002']
    relabel_configs:
      - source_labels: [__address__]
        regex: 'localhost:800([0-2])'
        target_label: service
        replacement: 'service-$1'
```

#### Remote Storage

Configure remote storage for long-term metric storage:

```yaml
remote_write:
  - url: "http://remote-storage-server:9201/write"

remote_read:
  - url: "http://remote-storage-server:9201/read"
```

## Grafana Dashboards

Grafana dashboards provide visual representations of your metrics. The Cryptobot monitoring system includes several pre-configured dashboards.

### Accessing Grafana

Access Grafana through your web browser:

```
http://your-server-ip:3000
```

Default credentials:
- Username: admin
- Password: admin

You will be prompted to change the password on first login.

### Default Dashboards

The following dashboards are included by default:

#### System Overview Dashboard

This dashboard provides an overview of system metrics:
- CPU usage
- Memory usage
- Disk usage
- Network traffic
- System load

![System Dashboard](../images/system_dashboard.png)

#### Cryptobot Application Dashboard

This dashboard provides metrics specific to the Cryptobot application:
- Request rate
- Error rate
- Response time
- Active trades
- Strategy performance

![Application Dashboard](../images/application_dashboard.png)

#### Database Performance Dashboard

This dashboard focuses on database performance:
- Query performance
- Connection count
- Transaction rate
- Cache hit ratio
- Index usage

![Database Dashboard](../images/database_dashboard.png)

### Creating Custom Dashboards

To create a custom dashboard:

1. Click the "+" icon in the left sidebar
2. Select "Dashboard"
3. Click "Add new panel"
4. Configure the panel with your desired metrics
5. Save the dashboard

### Importing Dashboards

To import a dashboard:

1. Click the "+" icon in the left sidebar
2. Select "Import"
3. Enter the dashboard ID or upload a JSON file
4. Configure the data source
5. Click "Import"

### Exporting Dashboards

To export a dashboard:

1. Open the dashboard
2. Click the "Share" button in the top navigation
3. Select the "Export" tab
4. Click "Save to file"

## Alerting Configuration

Alerting is configured using Alertmanager and Prometheus alert rules.

### Alert Rules

Alert rules are defined in YAML files. The default alert rules file is located at:

- Windows: `<install_dir>\monitoring\prometheus\rules\alert_rules.yml`
- Linux/macOS: `/etc/prometheus/rules/alert_rules.yml` or `<install_dir>/monitoring/prometheus/rules/alert_rules.yml`

Example alert rules:

```yaml
groups:
- name: cryptobot_alerts
  rules:
  - alert: InstanceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Instance {{ $labels.instance }} down"
      description: "{{ $labels.instance }} of job {{ $labels.job }} has been down for more than 1 minute."

  - alert: HighCpuUsage
    expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage on {{ $labels.instance }}"
      description: "CPU usage is above 80% for more than 5 minutes on {{ $labels.instance }}."

  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage on {{ $labels.instance }}"
      description: "Memory usage is above 80% for more than 5 minutes on {{ $labels.instance }}."

  - alert: HighDiskUsage
    expr: 100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High disk usage on {{ $labels.instance }}"
      description: "Disk usage is above 80% for more than 5 minutes on {{ $labels.instance }} mount point {{ $labels.mountpoint }}."

  - alert: HighErrorRate
    expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100 > 5
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High HTTP error rate"
      description: "HTTP error rate is above 5% for more than 5 minutes."
```

### Alertmanager Configuration

Alertmanager is configured using a YAML file. The default configuration file is located at:

- Windows: `<install_dir>\monitoring\alertmanager\alertmanager.yml`
- Linux/macOS: `/etc/alertmanager/alertmanager.yml` or `<install_dir>/monitoring/alertmanager/alertmanager.yml`

Example configuration:

```yaml
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'
  smtp_auth_username: 'alertmanager'
  smtp_auth_password: 'password'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'email-notifications'
  routes:
  - match:
      severity: critical
    receiver: 'email-notifications'
    continue: true
  - match:
      severity: warning
    receiver: 'slack-notifications'
    continue: true

receivers:
- name: 'email-notifications'
  email_configs:
  - to: 'admin@example.com'
    send_resolved: true
    
- name: 'slack-notifications'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
    channel: '#alerts'
    send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

### Notification Channels

Alertmanager supports various notification channels:

- Email
- Slack
- PagerDuty
- OpsGenie
- Webhook
- Microsoft Teams
- Discord
- Telegram

To configure a notification channel, add the appropriate configuration to the `receivers` section of the Alertmanager configuration.

### Alert Routing

Alert routing determines which alerts are sent to which notification channels. Configure routing in the `route` section of the Alertmanager configuration.

Example routing configuration:

```yaml
route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default-receiver'
  routes:
  - match:
      severity: critical
    receiver: 'critical-receiver'
  - match:
      service: database
    receiver: 'database-team'
  - match_re:
      service: ^(auth|api)$
    receiver: 'api-team'
```

## Log Aggregation

Log aggregation collects logs from various sources and centralizes them for analysis.

### Filebeat Configuration

Filebeat is configured using a YAML file. The default configuration file is located at:

- Windows: `<install_dir>\monitoring\logging\filebeat\filebeat.yml`
- Linux/macOS: `/etc/filebeat/filebeat.yml` or `<install_dir>/monitoring/logging/filebeat/filebeat.yml`

Example configuration:

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/cryptobot/*.log
    - /var/log/cryptobot/auth/*.log
    - /var/log/cryptobot/strategy/*.log
    - /var/log/cryptobot/backtest/*.log
    - /var/log/cryptobot/trade/*.log
    - /var/log/cryptobot/data/*.log
    - /var/log/cryptobot/mcp/*.log
  fields:
    application: cryptobot
  fields_under_root: true
  multiline:
    pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
    negate: true
    match: after

output.elasticsearch:
  hosts: ["localhost:9200"]
  indices:
    - index: "cryptobot-logs-%{+yyyy.MM.dd}"
      when.contains:
        application: "cryptobot"

setup.kibana:
  host: "localhost:5601"
```

### Elasticsearch Configuration

Elasticsearch is configured using a YAML file. The default configuration file is located at:

- Windows: `<install_dir>\monitoring\logging\elasticsearch\elasticsearch.yml`
- Linux/macOS: `/etc/elasticsearch/elasticsearch.yml` or `<install_dir>/monitoring/logging/elasticsearch/elasticsearch.yml`

Key configuration parameters:

```yaml
cluster.name: cryptobot-monitoring
node.name: node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: localhost
http.port: 9200
discovery.type: single-node
```

### Kibana Configuration

Kibana is configured using a YAML file. The default configuration file is located at:

- Windows: `<install_dir>\monitoring\logging\kibana\kibana.yml`
- Linux/macOS: `/etc/kibana/kibana.yml` or `<install_dir>/monitoring/logging/kibana/kibana.yml`

Key configuration parameters:

```yaml
server.port: 5601
server.host: "localhost"
elasticsearch.hosts: ["http://localhost:9200"]
```

### Log Dashboards

Kibana provides dashboards for log visualization. The default dashboards include:

- Overview Dashboard: General log statistics
- Error Dashboard: Focused on error logs
- Service Dashboard: Logs grouped by service
- Security Dashboard: Security-related logs

To access Kibana dashboards:

```
http://your-server-ip:5601
```

## Performance Monitoring

Performance monitoring focuses on tracking system and application performance metrics.

### System Performance Metrics

Key system performance metrics to monitor:

- CPU Usage: Overall and per-core usage
- Memory Usage: Total, used, and available memory
- Disk Usage: Space usage and I/O operations
- Network Usage: Bandwidth, packets, and errors
- System Load: 1, 5, and 15-minute load averages

### Application Performance Metrics

Key application performance metrics to monitor:

- Request Rate: Number of requests per second
- Error Rate: Percentage of failed requests
- Response Time: Time to process requests
- Database Queries: Number and duration of queries
- Active Connections: Number of active connections
- Resource Usage: CPU and memory usage per service

### Database Performance Metrics

Key database performance metrics to monitor:

- Query Performance: Duration of queries
- Connection Count: Number of active connections
- Transaction Rate: Number of transactions per second
- Cache Hit Ratio: Effectiveness of database caching
- Index Usage: How effectively indexes are being used
- Table Size: Growth of database tables

### Custom Performance Dashboards

Create custom performance dashboards in Grafana to focus on specific performance aspects:

1. Create a new dashboard
2. Add panels for relevant metrics
3. Organize panels logically
4. Set appropriate time ranges
5. Save and share the dashboard

## Security Monitoring

Security monitoring focuses on tracking security-related metrics and events.

### Authentication Monitoring

Monitor authentication events:

- Login attempts (successful and failed)
- Password changes
- Account lockouts
- API key usage

### Network Security Monitoring

Monitor network security:

- Firewall events
- Unusual network traffic
- Connection attempts to restricted ports
- Geolocation anomalies

### System Security Monitoring

Monitor system security:

- File integrity changes
- User account changes
- Privilege escalation
- System configuration changes

### Security Dashboards

Create security dashboards in Grafana and Kibana:

- Authentication Dashboard: Login attempts and failures
- Network Security Dashboard: Firewall and network events
- System Security Dashboard: System security events
- Compliance Dashboard: Compliance-related metrics

## Custom Metrics

Cryptobot exposes custom metrics that provide insights into application-specific behavior.

### Available Custom Metrics

The following custom metrics are available:

#### Trading Metrics

- `cryptobot_active_trades_total`: Total number of active trades
- `cryptobot_trade_executed_total`: Total number of executed trades
- `cryptobot_trade_execution_duration_seconds`: Duration of trade execution
- `cryptobot_trade_value_total`: Total value of trades
- `cryptobot_trade_profit_total`: Total profit from trades

#### Strategy Metrics

- `cryptobot_active_strategies_total`: Total number of active strategies
- `cryptobot_strategy_signals_total`: Total number of strategy signals
- `cryptobot_strategy_execution_duration_seconds`: Duration of strategy execution
- `cryptobot_strategy_performance_ratio`: Performance ratio of strategies

#### Data Metrics

- `cryptobot_data_points_total`: Total number of data points
- `cryptobot_data_processing_duration_seconds`: Duration of data processing
- `cryptobot_data_fetch_errors_total`: Total number of data fetch errors
- `cryptobot_data_storage_bytes`: Size of stored data

### Adding Custom Metrics

To add custom metrics to your application:

1. Define the metrics in your code
2. Expose the metrics via a `/metrics` endpoint
3. Configure Prometheus to scrape the endpoint
4. Create dashboards to visualize the metrics

Example Python code for adding custom metrics:

```python
from prometheus_client import Counter, Gauge, Histogram, Summary

# Counter: Increases monotonically
trade_counter = Counter('cryptobot_trades_total', 'Total number of trades')

# Gauge: Can increase and decrease
active_trades = Gauge('cryptobot_active_trades', 'Number of active trades')

# Histogram: Samples observations and counts them in configurable buckets
trade_duration = Histogram('cryptobot_trade_duration_seconds', 'Duration of trade execution')

# Summary: Similar to histogram but calculates quantiles over a sliding time window
trade_value = Summary('cryptobot_trade_value_dollars', 'Value of trades in dollars')
```

## Troubleshooting

### Common Monitoring Issues

#### Prometheus Issues

1. **Prometheus not scraping targets**
   - Check if targets are reachable
   - Verify Prometheus configuration
   - Check for firewall issues
   - Verify service discovery configuration

2. **High memory usage in Prometheus**
   - Reduce retention period
   - Increase storage space
   - Optimize queries
   - Consider remote storage

#### Grafana Issues

1. **Grafana not showing data**
   - Verify data source configuration
   - Check Prometheus connectivity
   - Verify query syntax
   - Check time range selection

2. **Grafana dashboard loading slowly**
   - Optimize queries
   - Reduce number of panels
   - Increase refresh interval
   - Check browser performance

#### Alertmanager Issues

1. **Alerts not firing**
   - Verify alert rules
   - Check Prometheus and Alertmanager connectivity
   - Verify alert conditions
   - Check for silences or inhibitions

2. **Notifications not being sent**
   - Verify receiver configuration
   - Check notification channel credentials
   - Verify network connectivity
   - Check for rate limiting

#### Log Aggregation Issues

1. **Logs not appearing in Kibana**
   - Verify Filebeat configuration
   - Check Elasticsearch connectivity
   - Verify log file paths
   - Check for parsing errors

2. **Elasticsearch high disk usage**
   - Configure index lifecycle management
   - Reduce log retention period
   - Optimize index settings
   - Add more storage

### Diagnostic Procedures

#### Prometheus Diagnostics

1. Check Prometheus status:
   ```
   curl http://localhost:9090/-/healthy
   ```

2. Check targets status:
   ```
   curl http://localhost:9090/api/v1/targets
   ```

3. Check Prometheus logs:
   - Windows: `<install_dir>\monitoring\prometheus\prometheus.log`
   - Linux/macOS: `/var/log/prometheus/prometheus.log`

#### Grafana Diagnostics

1. Check Grafana status:
   ```
   curl http://localhost:3000/api/health
   ```

2. Check Grafana logs:
   - Windows: `<install_dir>\monitoring\grafana\grafana.log`
   - Linux/macOS: `/var/log/grafana/grafana.log`

#### Alertmanager Diagnostics

1. Check Alertmanager status:
   ```
   curl http://localhost:9093/-/healthy
   ```

2. Check active alerts:
   ```
   curl http://localhost:9093/api/v2/alerts
   ```

3. Check Alertmanager logs:
   - Windows: `<install_dir>\monitoring\alertmanager\alertmanager.log`
   - Linux/macOS: `/var/log/alertmanager/alertmanager.log`

#### Log Aggregation Diagnostics

1. Check Elasticsearch status:
   ```
   curl http://localhost:9200/_cluster/health
   ```

2. Check Filebeat status:
   ```
   filebeat test config -c /etc/filebeat/filebeat.yml
   filebeat test output -c /etc/filebeat/filebeat.yml
   ```

3. Check logs:
   - Elasticsearch: `/var/log/elasticsearch/elasticsearch.log`
   - Filebeat: `/var/log/filebeat/filebeat.log`
   - Kibana: `/var/log/kibana/kibana.log`

## Best Practices

### Monitoring Best Practices

1. **Monitor what matters**
   - Focus on metrics that provide actionable insights
   - Avoid monitoring everything just because you can
   - Prioritize user-facing metrics

2. **Set appropriate thresholds**
   - Base thresholds on historical data
   - Avoid alert fatigue from too many alerts
   - Consider time-of-day patterns

3. **Use aggregation effectively**
   - Aggregate metrics at appropriate levels
   - Use labels to provide context
   - Balance detail and overview

4. **Implement proper retention policies**
   - Keep high-resolution data for short periods
   - Downsample data for long-term storage
   - Archive important historical data

### Alerting Best Practices

1. **Alert on symptoms, not causes**
   - Alert on user-visible issues
   - Use cause-based alerts for diagnostics
   - Focus on actionable alerts

2. **Implement alert severity levels**
   - Critical: Requires immediate attention
   - Warning: Requires attention soon
   - Info: Informational only

3. **Group related alerts**
   - Avoid alert storms
   - Correlate related issues
   - Provide context in alerts

4. **Implement escalation procedures**
   - Define who receives which alerts
   - Implement on-call rotations
   - Set up escalation paths

### Dashboard Best Practices

1. **Design for the audience**
   - Executive dashboards: High-level overview
   - Operator dashboards: Detailed metrics
   - Developer dashboards: Service-specific metrics

2. **Use consistent layouts**
   - Group related metrics
   - Use consistent time ranges
   - Apply consistent color schemes

3. **Provide context**
   - Add documentation to dashboards
   - Include links to related resources
   - Add annotations for important events

4. **Optimize for readability**
   - Use appropriate visualization types
   - Avoid cluttered dashboards
   - Use clear titles and labels

### Log Management Best Practices

1. **Implement structured logging**
   - Use consistent log formats
   - Include context in logs
   - Use appropriate log levels

2. **Set appropriate log levels**
   - Production: Warning and above
   - Development: Info and above
   - Debugging: Debug and above

3. **Implement log rotation**
   - Prevent disk space issues
   - Archive old logs
   - Compress logs when possible

4. **Secure sensitive information**
   - Mask passwords and API keys
   - Encrypt sensitive logs
   - Implement access controls