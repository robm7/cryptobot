# Alert Manager for Cryptobot

This directory contains Kubernetes manifests for setting up Alert Manager to handle alerts from Prometheus for the Cryptobot application.

## Alerting Architecture

The alerting architecture consists of the following components:

1. **Prometheus**: Monitors services and generates alerts based on defined rules.
2. **Alert Manager**: Receives alerts from Prometheus, groups them, and routes them to appropriate notification channels.
3. **Notification Channels**: Various methods to notify teams about alerts (email, Slack, PagerDuty, webhooks).

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
                           │ Alerts
                           ▼
┌──────────────────────────────────────────────────────┐
│                   Alert Manager                       │
└──────────────────────────┬───────────────────────────┘
                           │
                           │ Notifications
                           ▼
┌─────────┬─────────┬──────────┬────────────┬──────────┐
│  Email  │  Slack  │ PagerDuty│  Webhook   │   ...    │
└─────────┴─────────┴──────────┴────────────┴──────────┘
```

## Components

### Alert Manager

- **alertmanager-configmap.yaml**: Contains the Alert Manager configuration, including notification channels and routing.
- **alertmanager-deployment.yaml**: Deploys the Alert Manager server.
- **alertmanager-service.yaml**: Exposes Alert Manager as a service.
- **alertmanager-pvc.yaml**: Persistent Volume Claim for Alert Manager data.
- **silence-template.yaml**: Examples of how to silence alerts during maintenance.

### Prometheus Alert Rules

- **prometheus-rules.yaml**: Defines alert rules for various aspects of the Cryptobot application.

## Alert Categories

The alert rules are organized into the following categories:

1. **Service Availability Alerts**: Detect when services are down or experiencing high error rates.
2. **Resource Utilization Alerts**: Monitor CPU, memory, and storage usage.
3. **Kubernetes-specific Alerts**: Track node and pod health issues.
4. **Cryptobot-specific Alerts**: Monitor application-specific metrics for each service.

## Deployment

To deploy the Alert Manager stack, apply the manifests in the following order:

```bash
# Create PVC for Alert Manager
kubectl apply -f alertmanager-pvc.yaml

# Create ConfigMap for Alert Manager
kubectl apply -f alertmanager-configmap.yaml

# Deploy Alert Manager
kubectl apply -f alertmanager-deployment.yaml
kubectl apply -f alertmanager-service.yaml

# Create Prometheus alert rules
kubectl apply -f ../prometheus/prometheus-rules.yaml

# Restart Prometheus to pick up the new configuration
kubectl rollout restart deployment prometheus
```

## Accessing Alert Manager

Alert Manager is exposed as a ClusterIP service. To access it, you can:

1. Use port-forwarding:
   ```bash
   kubectl port-forward svc/alertmanager 9093:9093
   ```

2. Then access Alert Manager at: http://localhost:9093

## Configuring Notification Channels

### Email Notifications

To configure email notifications, update the `alertmanager-configmap.yaml` file:

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'
  smtp_auth_username: 'alertmanager'
  smtp_auth_password: 'password'
  smtp_require_tls: true
```

### Slack Notifications

To configure Slack notifications, update the `alertmanager-configmap.yaml` file:

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'

receivers:
- name: 'slack-notifications'
  slack_configs:
  - channel: '#alerts'
    send_resolved: true
```

### PagerDuty Notifications

To configure PagerDuty notifications, update the `alertmanager-configmap.yaml` file:

```yaml
receivers:
- name: 'pagerduty-critical'
  pagerduty_configs:
  - service_key: '0123456789abcdef0123456789abcdef'
    send_resolved: true
```

### Webhook Notifications

To configure webhook notifications, update the `alertmanager-configmap.yaml` file:

```yaml
receivers:
- name: 'webhook-receiver'
  webhook_configs:
  - url: 'http://custom-integration-service:8080/alert'
    send_resolved: true
```

## Alert Routing

Alert Manager routes alerts to different notification channels based on labels. The routing configuration is defined in the `alertmanager-configmap.yaml` file:

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 3h
  receiver: 'slack-notifications'  # Default receiver
  routes:
  - match:
      severity: critical
    receiver: 'pagerduty-critical'
  - match:
      team: trading
    receiver: 'trading-team-slack'
```

## Adding Custom Alert Rules

To add custom alert rules, update the `prometheus-rules.yaml` file. Here's an example of a new alert rule:

```yaml
- alert: CustomAlert
  expr: custom_metric > threshold
  for: 5m
  labels:
    severity: warning
    team: your-team
  annotations:
    summary: "Custom alert for your service"
    description: "Detailed description of the alert."
```

After updating the file, apply the changes:

```bash
kubectl apply -f prometheus-rules.yaml
```

## Silencing Alerts

During maintenance or known issues, you can silence alerts to prevent unnecessary notifications. See `silence-template.yaml` for examples of how to create silences.

To create a silence using the Alert Manager UI:

1. Access the Alert Manager UI at http://localhost:9093
2. Click on "Silences" in the top navigation
3. Click "New Silence"
4. Fill in the matchers, start time, end time, and comment
5. Click "Create"

To create a silence using the API, see the examples in `silence-template.yaml`.

## Best Practices for Alert Management

1. **Use Meaningful Labels**: Add labels like `severity`, `team`, and `service` to route alerts effectively.

2. **Set Appropriate Thresholds**: Avoid alert fatigue by setting thresholds that balance between early detection and false positives.

3. **Use the "for" Clause**: Ensure alerts persist for a certain duration before firing to avoid alerts for transient issues.

4. **Group Related Alerts**: Use `group_by` to combine related alerts into a single notification.

5. **Include Actionable Information**: Provide clear descriptions and links to runbooks in alert annotations.

6. **Implement Escalation Policies**: Route critical alerts to multiple channels or use escalation services like PagerDuty.

7. **Regularly Review Alerts**: Periodically review alert history to identify noisy alerts or missing alerts.

8. **Document Silences**: Always include a detailed comment when creating a silence, including the reason and expected resolution time.

9. **Test Alert Pipeline**: Regularly test the entire alert pipeline to ensure notifications are delivered correctly.

10. **Maintain Runbooks**: Keep up-to-date runbooks for each alert to guide responders on how to address issues.

## Troubleshooting

### Alert Manager Not Receiving Alerts

1. Check if Prometheus is configured correctly to send alerts to Alert Manager:
   ```bash
   kubectl get configmap prometheus-config -o yaml
   ```

2. Verify that Alert Manager is running:
   ```bash
   kubectl get pods -l app=alertmanager
   ```

3. Check Alert Manager logs:
   ```bash
   kubectl logs -l app=alertmanager
   ```

### Notifications Not Being Sent

1. Check Alert Manager configuration:
   ```bash
   kubectl get configmap alertmanager-config -o yaml
   ```

2. Verify that the notification channel credentials are correct.

3. Check Alert Manager logs for errors related to sending notifications:
   ```bash
   kubectl logs -l app=alertmanager | grep -i error
   ```

### Alert Rules Not Firing

1. Check if the alert rules are loaded correctly:
   ```bash
   kubectl port-forward svc/prometheus 9090:9090
   ```
   Then access http://localhost:9090/rules

2. Verify that the metrics used in alert expressions exist:
   ```bash
   kubectl port-forward svc/prometheus 9090:9090
   ```
   Then access http://localhost:9090/graph and query the metrics

3. Check Prometheus logs for errors:
   ```bash
   kubectl logs -l app=prometheus