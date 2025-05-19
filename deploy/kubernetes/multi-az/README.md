# Multi-AZ Deployment Configuration for Cryptobot

This directory contains Kubernetes manifests for deploying the Cryptobot application in a multi-Availability Zone (multi-AZ) configuration to ensure high availability and fault tolerance.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Pod Distribution Strategy](#pod-distribution-strategy)
- [Deployment Components](#deployment-components)
- [Implementation Details](#implementation-details)
- [Verifying Multi-AZ Deployment](#verifying-multi-az-deployment)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

The multi-AZ architecture is designed to distribute Cryptobot services across multiple availability zones to ensure the application remains available even if an entire zone experiences an outage.

![Multi-AZ Architecture](https://placeholder-for-architecture-diagram.png)

Key components of the multi-AZ architecture:

1. **Node Distribution**: Kubernetes nodes are distributed across multiple availability zones.
2. **Pod Distribution**: Pods are distributed across zones using node affinity, pod anti-affinity, and topology spread constraints.
3. **Service Resilience**: Each service has multiple replicas distributed across zones.
4. **Load Balancing**: Kubernetes services automatically load balance traffic across pods in different zones.

## Pod Distribution Strategy

The pod distribution strategy ensures that:

1. **Zone Redundancy**: Each service has at least one pod running in each availability zone.
2. **Node Redundancy**: Pods from the same service are scheduled on different nodes to avoid single points of failure.
3. **Even Distribution**: Pods are evenly distributed across zones to balance load and resource usage.

This is achieved through a combination of:

- **Node Affinity**: Ensures pods are scheduled on nodes with specific zone labels.
- **Pod Anti-Affinity**: Prevents pods from the same service from being scheduled on the same node.
- **Topology Spread Constraints**: Ensures pods are evenly distributed across zones.

## Deployment Components

The multi-AZ deployment includes the following components:

1. **Service Deployments**:
   - `trade-deployment.yaml`: Trade service deployment with multi-AZ configuration
   - `strategy-deployment.yaml`: Strategy service deployment with multi-AZ configuration
   - `backtest-deployment.yaml`: Backtest service deployment with multi-AZ configuration
   - `data-deployment.yaml`: Data service deployment with multi-AZ configuration
   - `dashboard-deployment.yaml`: Dashboard service deployment with multi-AZ configuration

2. **Node Configuration**:
   - `node-labels.yaml`: Example commands for labeling nodes with their availability zone and node selector configurations

## Implementation Details

### Node Affinity

Node affinity rules ensure that pods are scheduled on nodes in specific availability zones:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: Exists
```

### Pod Anti-Affinity

Pod anti-affinity rules ensure that pods from the same service don't run on the same node:

```yaml
podAntiAffinity:
  preferredDuringSchedulingIgnoredDuringExecution:
  - weight: 100
    podAffinityTerm:
      labelSelector:
        matchExpressions:
        - key: service
          operator: In
          values:
          - <service-name>
      topologyKey: kubernetes.io/hostname
```

### Topology Spread Constraints

Topology spread constraints ensure that pods are evenly distributed across zones:

```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: DoNotSchedule
  labelSelector:
    matchLabels:
      service: <service-name>
```

### Tolerations

Tolerations allow pods to be scheduled on nodes with specific taints:

```yaml
tolerations:
- key: node-role.kubernetes.io/master
  operator: Exists
  effect: NoSchedule
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoSchedule
  tolerationSeconds: 300
```

## Verifying Multi-AZ Deployment

To verify that your multi-AZ deployment is working correctly, follow these steps:

1. **Verify Node Labels**:
   ```bash
   kubectl get nodes --show-labels | grep topology.kubernetes.io/zone
   ```

2. **Check Pod Distribution**:
   ```bash
   # Get pods with node information
   kubectl get pods -o wide
   
   # Get pods grouped by node
   kubectl get pods -o wide --sort-by="{.spec.nodeName}"
   
   # Get pods for a specific service
   kubectl get pods -l service=trade -o wide
   ```

3. **Verify Zone Distribution**:
   ```bash
   # For each service, check which nodes the pods are running on
   # Then check which zone each node is in
   
   # Example for trade service
   kubectl get pods -l service=trade -o wide
   
   # Get node zone information
   kubectl get nodes -L topology.kubernetes.io/zone
   ```

4. **Test Failover**:
   To test failover capabilities, you can simulate a zone failure by cordoning and draining nodes in a specific zone:
   ```bash
   # Cordon nodes in a specific zone (replace <zone> with the actual zone)
   kubectl cordon -l topology.kubernetes.io/zone=<zone>
   
   # Drain nodes in that zone
   kubectl drain -l topology.kubernetes.io/zone=<zone> --ignore-daemonsets --delete-emptydir-data
   ```
   
   Then verify that the application remains available and that pods are rescheduled to other zones.

## Best Practices

To maintain high availability in a multi-AZ deployment, follow these best practices:

1. **Minimum Replicas**: Ensure each service has at least 3 replicas (one per AZ) to maintain availability during zone failures.

2. **Resource Requests and Limits**: Set appropriate resource requests and limits to ensure pods have the resources they need and don't overcommit nodes.

3. **Pod Disruption Budgets**: Define Pod Disruption Budgets (PDBs) to limit the number of pods that can be down simultaneously during voluntary disruptions:
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: trade-pdb
   spec:
     minAvailable: 2  # At least 2 pods must be available
     selector:
       matchLabels:
         service: trade
   ```

4. **Regular Testing**: Regularly test zone failure scenarios to ensure the system behaves as expected during actual failures.

5. **Monitoring and Alerting**: Implement monitoring and alerting to detect zone failures and service disruptions.

6. **Stateful Services**: For stateful services, use StatefulSets with appropriate storage classes that support multi-AZ deployments.

7. **Database Redundancy**: Ensure databases and other stateful components are also deployed in a multi-AZ configuration.

8. **Network Policies**: Implement network policies to control traffic between pods and ensure services can communicate across zones.

9. **Load Balancer Configuration**: Configure load balancers to distribute traffic across all available zones.

10. **Regular Updates**: Keep your Kubernetes cluster and application components up to date with security patches and bug fixes.

## Troubleshooting

Common issues and their solutions:

1. **Pods Not Distributing Across Zones**:
   - Verify node labels are correctly set
   - Check that topology spread constraints are correctly configured
   - Ensure there are enough resources available in each zone

2. **Pod Scheduling Failures**:
   - Check node affinity and anti-affinity rules
   - Verify that nodes have the required labels
   - Check for resource constraints that might prevent scheduling

3. **Service Unavailability During Zone Failure**:
   - Verify that pods are distributed across all zones
   - Check that the minimum number of replicas is sufficient
   - Ensure load balancers are correctly configured to detect and route around failures

4. **Slow Failover**:
   - Adjust liveness and readiness probe settings
   - Check node controller settings for faster node failure detection
   - Review pod eviction timeout settings