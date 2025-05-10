# System Requirements for Non-Docker Deployment

This document outlines the hardware, software, and network requirements for deploying the Cryptobot application without Docker.

## Hardware Requirements

### Minimum Requirements
- **CPU**: 4 cores (8 threads recommended)
- **RAM**: 8GB (16GB recommended)
- **Disk Space**: 50GB SSD (100GB recommended)
- **Network**: Stable internet connection with minimum 10Mbps bandwidth

### Recommended Requirements for Production
- **CPU**: 8+ cores
- **RAM**: 32GB
- **Disk Space**: 200GB+ SSD
- **Network**: Stable internet connection with minimum 50Mbps bandwidth

## Software Requirements

### Operating System
- **Linux**: Ubuntu 20.04 LTS or newer
- **Windows**: Windows 10/11 with WSL2 support
- **macOS**: macOS 11 (Big Sur) or newer

### Python Environment
- **Python Version**: 3.10 (required for strategy and trade services)
  - Some services use Python 3.9, but all are compatible with Python 3.10
- **Virtual Environment**: venv or conda recommended for isolation

### Database Systems
- **PostgreSQL**: Version 13.0 or newer
  - Required for auth, strategy, and trade services
- **SQLite**: Version 3.35.0 or newer
  - Used by backtest service
- **Redis**: Version 6.2 or newer
  - Required for caching and session management

### Additional Software
- **Git**: For source code management
- **pip**: For Python package management
- **curl**: For health checks and API testing
- **systemd** (Linux) or **Windows Services**: For service management

## Network Requirements

### Port Availability
The following ports must be available for the services:
- **8000**: Auth Service
- **8000**: Strategy Service (requires different host or port configuration)
- **8000**: Trade Service (requires different host or port configuration)
- **8001**: Data Service
- **8000**: Backtest Service (requires different host or port configuration)
- **6379**: Redis
- **5432**: PostgreSQL

### Firewall Configuration
- Allow inbound/outbound traffic on the above ports
- Allow outbound HTTPS (port 443) for external API calls to exchanges

### DNS Requirements
- Local hostname resolution for service-to-service communication
- External DNS resolution for cryptocurrency exchange APIs

## Security Requirements

- **TLS/SSL**: Certificates for secure communication
- **Firewall**: Properly configured to restrict access
- **User Permissions**: Non-root user for running services
- **API Keys**: Secure storage for exchange API keys
- **Environment Variables**: Secure management of sensitive configuration

## Monitoring Requirements

- **Logging**: Filesystem access for log files
- **Metrics**: Ability to expose metrics endpoints
- **Alerting**: Email or webhook capabilities for notifications

## Backup Requirements

- **Database Backup**: Regular automated backups
- **Configuration Backup**: Version-controlled configuration files
- **Data Backup**: Historical market data backup capability

## Scaling Considerations

- **Vertical Scaling**: Ability to increase resources on a single machine
- **Horizontal Scaling**: Potential for multiple instances of services
- **Load Balancing**: Optional for production deployments

This document serves as a baseline for system requirements. Specific deployment environments may require adjustments based on usage patterns, data volume, and performance needs.