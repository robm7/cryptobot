# Cryptobot Ingress Controllers

This directory contains Kubernetes Ingress resources for the Cryptobot application, providing external access to the various services.

## Overview

The ingress controllers are configured to route external traffic to the appropriate internal services based on path-based routing. We use NGINX Ingress Controller for this purpose, but the configuration is designed to be adaptable to other ingress controllers if needed.

## Ingress Resources

### API Ingress (`ingress.yaml`)

Routes external traffic to the backend API services:

- `/api/trade/*` → Trade Service
- `/api/strategy/*` → Strategy Service
- `/api/data/*` → Data Service
- `/api/backtest/*` → Backtest Service

### Dashboard Ingress (`dashboard-ingress.yaml`)

Routes traffic to the frontend dashboard service:

- `dashboard.cryptobot.example.com` → Dashboard Service

## TLS Configuration

Both ingress resources are configured with TLS for HTTPS. The TLS certificates are stored in Kubernetes secrets:

- `cryptobot-tls-secret` for the API ingress
- `dashboard-tls-secret` for the dashboard ingress

The `tls-secret.yaml` file contains placeholder secrets that should be replaced with actual certificates in a production environment.

## Annotations

The ingress resources include various annotations for the NGINX Ingress Controller:

- SSL redirection
- CORS configuration
- Security headers
- Rate limiting
- WebSocket support (for the dashboard)

## Customization

To adapt these ingress resources for your environment:

1. Update the hostnames in the `tls` and `rules` sections
2. Replace the TLS secrets with actual certificates
3. Adjust the annotations as needed for your specific requirements
4. If using a different ingress controller, modify the `kubernetes.io/ingress.class` annotation and other controller-specific annotations

## Deployment

Apply these resources to your Kubernetes cluster:

```bash
kubectl apply -f deploy/kubernetes/ingress/
```

## Troubleshooting

If you encounter issues with the ingress controllers:

1. Check that the NGINX Ingress Controller is installed in your cluster
2. Verify that the services referenced in the ingress resources exist and are running
3. Check the ingress controller logs for any errors
4. Ensure that the TLS certificates are valid and properly configured