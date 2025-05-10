#!/bin/bash

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl apply -k ./k8s/

# Verify deployments
echo "Verifying deployments..."
kubectl get deployments -n cryptobot-prod

# Verify services
echo "Verifying services..."
kubectl get services -n cryptobot-prod

# Verify pods
echo "Verifying pods..."
kubectl get pods -n cryptobot-prod --watch