# Horizontal Pod Autoscaling (HPA) for Cryptobot Services

This directory contains Horizontal Pod Autoscaler (HPA) configurations for all Cryptobot microservices. HPA automatically scales the number of pods in a deployment based on observed CPU/memory utilization or other custom metrics.

## HPA Configuration Overview

All services are configured with the following default settings:

- **Minimum Replicas**: 2 (ensures high availability)
- **Maximum Replicas**: 10 (prevents runaway scaling)
- **CPU Utilization Target**: 70% (scales when average CPU usage exceeds this threshold)
- **Memory Utilization Target**: 80% (scales when average memory usage exceeds this threshold)

### Scaling Behavior Configuration

Each HPA includes behavior rules to control scaling dynamics:

#### Scale Down Behavior
- 300-second stabilization window (prevents rapid scale down)
- Maximum 50% reduction in pods per minute (gradual scaling)

#### Scale Up Behavior
- No stabilization window (immediate response to increased load)
- 100% increase in pods per minute (aggressive scaling up)
- Maximum 4 new pods per minute (controlled growth)

## Monitoring Autoscaling Behavior

You can monitor HPA status and scaling events using the following commands:

### View HPA Status

```bash
# List all HPAs
kubectl get hpa -n <namespace>

# Get detailed information about a specific HPA
kubectl describe hpa <hpa-name> -n <namespace>
```

### Monitor Scaling Events

```bash
# View events related to scaling
kubectl get events -n <namespace> --field-selector involvedObject.kind=HorizontalPodAutoscaler

# Stream logs for scaling events
kubectl get events -n <namespace> --field-selector involvedObject.kind=HorizontalPodAutoscaler --watch
```

### Visualizing HPA Metrics

For better visualization, consider using:

1. **Kubernetes Dashboard**: Provides a visual representation of HPA status
2. **Prometheus + Grafana**: Set up dashboards to monitor:
   - Current/target replica counts
   - CPU/memory utilization vs thresholds
   - Scaling events over time

## Adjusting Scaling Parameters

To modify HPA settings, edit the corresponding YAML file and apply the changes:

```bash
# Edit the HPA configuration
kubectl edit hpa <hpa-name> -n <namespace>

# Or apply updated YAML file
kubectl apply -f <updated-hpa-file.yaml> -n <namespace>
```

### Key Parameters to Consider Adjusting

1. **Resource Targets**:
   - Lower CPU/memory targets (e.g., 50%) for more aggressive scaling
   - Higher targets (e.g., 90%) for more conservative scaling

2. **Replica Limits**:
   - Adjust `minReplicas` based on minimum required availability
   - Adjust `maxReplicas` based on cluster capacity and budget constraints

3. **Scaling Behavior**:
   - Modify `stabilizationWindowSeconds` to control scaling sensitivity
   - Adjust scaling policies to change how quickly pods are added/removed

### Service-Specific Considerations

- **Trade Service**: May need faster scaling for handling trading volume spikes
- **Data Service**: Consider higher memory thresholds for data processing workloads
- **Backtest Service**: May benefit from higher max replicas during heavy backtesting
- **Dashboard Service**: Frontend scaling can be more conservative (slower to scale up/down)

## Troubleshooting

If HPA is not scaling as expected:

1. **Check Metrics Availability**:
   ```bash
   kubectl describe hpa <hpa-name> -n <namespace>
   ```
   Look for "unable to fetch metrics" errors

2. **Verify Resource Requests**:
   Ensure deployments have appropriate resource requests defined, as HPA uses these as the baseline for percentage calculations

3. **Check Pod Resource Usage**:
   ```bash
   kubectl top pods -n <namespace>
   ```
   Compare actual usage against HPA thresholds

4. **Review Events**:
   ```bash
   kubectl get events -n <namespace> | grep HorizontalPodAutoscaler
   ```
   Look for any error events related to the HPA