# Cryptobot Deployment Guide

This guide provides detailed instructions for deploying the Cryptobot application in a non-Docker environment. It covers production deployment procedures, environment setup, configuration, and verification steps.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Planning](#deployment-planning)
3. [Environment Setup](#environment-setup)
4. [Configuration](#configuration)
5. [Database Setup](#database-setup)
6. [Service Installation](#service-installation)
7. [Security Configuration](#security-configuration)
8. [Deployment Procedure](#deployment-procedure)
9. [Verification](#verification)
10. [Rollback Procedure](#rollback-procedure)
11. [Troubleshooting](#troubleshooting)
12. [Appendix](#appendix)

## Prerequisites

### System Requirements

- **Operating System**: 
  - Windows 10/11 or Windows Server 2019/2022
  - Ubuntu 20.04/22.04 LTS or other major Linux distributions
  - macOS 12 (Monterey) or newer

- **Hardware Requirements**:
  - CPU: 4+ cores recommended (2 cores minimum)
  - RAM: 8GB+ recommended (4GB minimum)
  - Disk Space: 20GB+ free space recommended
  - Network: Stable internet connection

- **Software Requirements**:
  - Python 3.8 or newer
  - PostgreSQL 12 or newer (or SQLite for smaller deployments)
  - Redis 6.0 or newer (optional, for caching)
  - Node.js 16 or newer (for monitoring dashboards)

### Required Access

- Administrative/root access to the server
- Database administrator credentials
- Network access to required external services (exchanges, etc.)
- Firewall access for required ports

### Preparation Checklist

- [ ] Verify system meets all requirements
- [ ] Obtain all necessary credentials
- [ ] Prepare backup strategy
- [ ] Plan deployment schedule
- [ ] Notify stakeholders of deployment

## Deployment Planning

### Deployment Strategies

#### Single-Server Deployment

Suitable for small to medium deployments where all components run on a single server.

**Advantages**:
- Simpler setup and maintenance
- Lower infrastructure costs
- Easier troubleshooting

**Disadvantages**:
- Single point of failure
- Limited scalability
- Resource contention

#### Multi-Server Deployment

Suitable for larger deployments where components are distributed across multiple servers.

**Advantages**:
- Better scalability
- Improved fault tolerance
- Optimized resource allocation

**Disadvantages**:
- More complex setup and maintenance
- Higher infrastructure costs
- More complex troubleshooting

### Deployment Phases

1. **Preparation Phase**
   - System requirements verification
   - Backup of existing system (if applicable)
   - Configuration preparation

2. **Installation Phase**
   - Environment setup
   - Database installation and configuration
   - Application installation
   - Service configuration

3. **Configuration Phase**
   - Application configuration
   - Security configuration
   - Integration configuration

4. **Verification Phase**
   - Service verification
   - Functionality testing
   - Performance testing
   - Security verification

5. **Finalization Phase**
   - Documentation
   - Monitoring setup
   - Backup configuration
   - Knowledge transfer

### Deployment Schedule

Plan your deployment during low-traffic periods to minimize disruption. Consider the following:

- Time of day: Off-hours deployment reduces impact on users
- Day of week: Weekend deployments provide more recovery time
- Market conditions: Avoid deploying during high market volatility
- Maintenance windows: Coordinate with other system maintenance

## Environment Setup

### Operating System Preparation

#### Windows

1. Install latest Windows updates:
   ```powershell
   Install-WindowsUpdate -AcceptAll -AutoReboot
   ```

2. Configure Windows features:
   ```powershell
   Install-WindowsFeature -Name Web-Server, NET-Framework-45-Features
   ```

3. Configure Windows Defender exclusions (if needed):
   ```powershell
   Add-MpPreference -ExclusionPath "C:\path\to\cryptobot"
   ```

#### Linux (Ubuntu/Debian)

1. Update system packages:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. Install required packages:
   ```bash
   sudo apt install -y build-essential libssl-dev libffi-dev python3-dev python3-pip
   ```

3. Configure system limits:
   ```bash
   sudo bash -c 'cat > /etc/security/limits.d/cryptobot.conf << EOF
   cryptobot soft nofile 65536
   cryptobot hard nofile 65536
   EOF'
   ```

#### macOS

1. Install Homebrew (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install required packages:
   ```bash
   brew install openssl readline sqlite3 xz zlib
   ```

### Python Environment Setup

1. Install Python (if not already installed):
   - Windows: Download and install from [python.org](https://www.python.org/downloads/)
   - Linux: `sudo apt install python3 python3-pip python3-venv`
   - macOS: `brew install python`

2. Create a virtual environment:
   - Windows:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

### Directory Structure Setup

Create the necessary directory structure for the application:

```bash
mkdir -p cryptobot/{config,data,logs,backups}
```

## Configuration

### Configuration Files

The Cryptobot application uses several configuration files located in the `config` directory:

1. **Main Configuration**: `config/cryptobot_config.json`
2. **Exchange Configuration**: `config/exchange_config.py`
3. **Database Configuration**: `config/database_config.json`
4. **Logging Configuration**: `config/logging_config.json`
5. **Service Configuration**: `config/service_config.json`

### Configuration Templates

Use the provided configuration templates as a starting point:

1. Copy the template files:
   - Windows:
     ```powershell
     Copy-Item -Path "config/templates/*" -Destination "config/" -Recurse
     ```
   - Linux/macOS:
     ```bash
     cp -r config/templates/* config/
     ```

2. Edit the configuration files to match your environment:
   - Update database connection details
   - Configure exchange API credentials
   - Set appropriate logging levels
   - Configure service parameters

### Environment Variables

Some sensitive configuration can be stored in environment variables instead of configuration files:

1. Create an environment variable file:
   - Windows: Create a `setenv.ps1` script
   - Linux/macOS: Create a `.env` file

2. Set the required environment variables:
   ```
   CRYPTOBOT_DB_PASSWORD=your_secure_password
   CRYPTOBOT_EXCHANGE_API_KEY=your_api_key
   CRYPTOBOT_EXCHANGE_API_SECRET=your_api_secret
   ```

3. Load the environment variables:
   - Windows: Run the `setenv.ps1` script
   - Linux/macOS: Source the `.env` file

## Database Setup

### PostgreSQL Setup

1. Install PostgreSQL:
   - Windows: Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)
   - Linux: `sudo apt install postgresql postgresql-contrib`
   - macOS: `brew install postgresql`

2. Start PostgreSQL service:
   - Windows: Use the PostgreSQL service manager
   - Linux: `sudo systemctl start postgresql`
   - macOS: `brew services start postgresql`

3. Create a database and user:
   ```sql
   CREATE USER cryptobot WITH PASSWORD 'your_secure_password';
   CREATE DATABASE cryptobot OWNER cryptobot;
   GRANT ALL PRIVILEGES ON DATABASE cryptobot TO cryptobot;
   ```

4. Configure PostgreSQL for performance:
   - Edit `postgresql.conf` to adjust memory settings
   - Configure connection pooling if needed
   - Set appropriate logging levels

### SQLite Setup (Alternative for smaller deployments)

1. No installation required (included with Python)

2. Configure the database path in the configuration file:
   ```json
   {
     "database": {
       "type": "sqlite",
       "path": "database/cryptobot.db"
     }
   }
   ```

3. Ensure the database directory exists:
   ```bash
   mkdir -p database
   ```

### Database Migration

1. Run the database migration script:
   - Windows:
     ```powershell
     .\scripts\non-docker-setup\migrate_database.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-setup/migrate_database.sh
     ```

2. Verify the database schema:
   - PostgreSQL: `\d` in psql
   - SQLite: `.schema` in sqlite3

## Service Installation

### Core Services Installation

1. Install the core services:
   - Windows:
     ```powershell
     .\scripts\non-docker-setup\install_services.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-setup/install_services.sh
     ```

2. Verify service installation:
   - Windows: `Get-Service -Name "Cryptobot*"`
   - Linux: `systemctl status cryptobot-*`
   - macOS: `launchctl list | grep com.cryptobot`

### Individual Service Installation

If you need to install services individually:

1. Auth Service:
   - Windows: `.\scripts\non-docker-setup\install_auth.ps1`
   - Linux/macOS: `./scripts/non-docker-setup/install_auth.sh`

2. Strategy Service:
   - Windows: `.\scripts\non-docker-setup\install_strategy.ps1`
   - Linux/macOS: `./scripts/non-docker-setup/install_strategy.sh`

3. Backtest Service:
   - Windows: `.\scripts\non-docker-setup\install_backtest.ps1`
   - Linux/macOS: `./scripts/non-docker-setup/install_backtest.sh`

4. Trade Service:
   - Windows: `.\scripts\non-docker-setup\install_trade.ps1`
   - Linux/macOS: `./scripts/non-docker-setup/install_trade.sh`

5. Data Service:
   - Windows: `.\scripts\non-docker-setup\install_data.ps1`
   - Linux/macOS: `./scripts/non-docker-setup/install_data.sh`

### MCP Services Installation

1. Install the MCP services:
   - Windows:
     ```powershell
     .\scripts\non-docker-setup\install_mcp_services.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-setup/install_mcp_services.sh
     ```

2. Verify MCP service installation:
   - Windows: `Get-Service -Name "CryptobotMCP*"`
   - Linux: `systemctl status cryptobot-mcp-*`
   - macOS: `launchctl list | grep com.cryptobot.mcp`

## Security Configuration

### Firewall Configuration

1. Configure the firewall:
   - Windows:
     ```powershell
     .\scripts\non-docker-security\setup_firewall.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-security/setup_firewall.sh
     ```

2. Verify firewall configuration:
   - Windows: `Get-NetFirewallRule -DisplayName "Cryptobot*"`
   - Linux: `sudo ufw status`
   - macOS: `sudo pfctl -s rules`

### SSL/TLS Configuration

1. Configure SSL/TLS:
   - Windows:
     ```powershell
     .\scripts\non-docker-security\setup_ssl.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-security/setup_ssl.sh
     ```

2. Verify SSL/TLS configuration:
   - Test HTTPS connectivity
   - Verify certificate validity

### Permissions Configuration

1. Configure file and directory permissions:
   - Windows:
     ```powershell
     .\scripts\non-docker-security\setup_permissions.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-security/setup_permissions.sh
     ```

2. Verify permissions:
   - Windows: `Get-Acl -Path "path\to\cryptobot"`
   - Linux/macOS: `ls -la path/to/cryptobot`

### Secure Configuration

1. Apply secure configuration:
   - Windows:
     ```powershell
     .\scripts\non-docker-security\secure_config.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-security/secure_config.sh
     ```

2. Verify secure configuration:
   - Check configuration files for secure settings
   - Verify environment variables are properly set

## Deployment Procedure

### Pre-Deployment Checklist

- [ ] Verify all prerequisites are met
- [ ] Backup existing system (if applicable)
- [ ] Prepare configuration files
- [ ] Notify stakeholders of deployment

### Deployment Steps

1. **Create a backup** (if upgrading an existing system):
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\backup.ps1 -BackupName "pre_deployment"
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/backup.sh -n pre_deployment
     ```

2. **Stop existing services** (if upgrading):
   - Windows:
     ```powershell
     Get-Service -Name "Cryptobot*" | Stop-Service
     ```
   - Linux:
     ```bash
     sudo systemctl stop cryptobot-*
     ```
   - macOS:
     ```bash
     for service in $(launchctl list | grep com.cryptobot | awk '{print $3}'); do
       sudo launchctl stop $service
     done
     ```

3. **Deploy the application**:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\deploy_production.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/deploy_production.sh
     ```

4. **Verify deployment**:
   - Check service status
   - Verify application functionality
   - Check logs for errors

### Post-Deployment Steps

1. **Set up monitoring**:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\setup_monitoring.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/setup_monitoring.sh
     ```

2. **Set up logging**:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\setup_logging.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/setup_logging.sh
     ```

3. **Set up alerting**:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\setup_alerts.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/setup_alerts.sh
     ```

4. **Create a post-deployment backup**:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\backup.ps1 -BackupName "post_deployment"
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/backup.sh -n post_deployment
     ```

## Verification

### Service Verification

1. Verify all services are running:
   - Windows: `Get-Service -Name "Cryptobot*"`
   - Linux: `systemctl status cryptobot-*`
   - macOS: `launchctl list | grep com.cryptobot`

2. Check service logs for errors:
   - Review logs in the `logs` directory
   - Check system logs for service-related errors

### Functionality Verification

1. Run the verification tests:
   - Windows:
     ```powershell
     .\scripts\non-docker-tests\run_all_tests.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-tests/run_all_tests.sh
     ```

2. Verify specific functionality:
   - Test authentication
   - Test strategy execution
   - Test data retrieval
   - Test trading functionality

### Performance Verification

1. Run performance tests:
   - Windows:
     ```powershell
     .\scripts\non-docker-tests\test_performance.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-tests/test_performance.sh
     ```

2. Monitor system performance:
   - Check CPU, memory, and disk usage
   - Monitor database performance
   - Check network performance

### Security Verification

1. Run security verification:
   - Windows:
     ```powershell
     .\scripts\non-docker-security\assess_vulnerabilities.ps1
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-security/assess_vulnerabilities.sh
     ```

2. Verify security configurations:
   - Check firewall rules
   - Verify SSL/TLS configuration
   - Check file and directory permissions

## Rollback Procedure

### When to Rollback

Consider rolling back the deployment if:
- Critical functionality is not working
- Performance is significantly degraded
- Security vulnerabilities are discovered
- Data integrity issues are detected

### Rollback Steps

1. **Stop all services**:
   - Windows:
     ```powershell
     Get-Service -Name "Cryptobot*" | Stop-Service
     ```
   - Linux:
     ```bash
     sudo systemctl stop cryptobot-*
     ```
   - macOS:
     ```bash
     for service in $(launchctl list | grep com.cryptobot | awk '{print $3}'); do
       sudo launchctl stop $service
     done
     ```

2. **Restore from backup**:
   - Windows:
     ```powershell
     .\scripts\non-docker-deployment\restore.ps1 -BackupName "pre_deployment"
     ```
   - Linux/macOS:
     ```bash
     ./scripts/non-docker-deployment/restore.sh -n pre_deployment
     ```

3. **Verify rollback**:
   - Check service status
   - Verify application functionality
   - Check logs for errors

4. **Document rollback**:
   - Document the reason for rollback
   - Document any issues encountered during rollback
   - Plan for addressing the issues before attempting deployment again

## Troubleshooting

### Common Deployment Issues

1. **Service fails to start**:
   - Check logs for error messages
   - Verify configuration files
   - Check dependencies
   - Verify file permissions

2. **Database connection issues**:
   - Verify database service is running
   - Check database credentials
   - Verify network connectivity
   - Check database logs

3. **Configuration errors**:
   - Verify configuration file syntax
   - Check for missing required configuration
   - Verify environment variables are set correctly

4. **Permission issues**:
   - Check file and directory permissions
   - Verify service account permissions
   - Check database user permissions

### Troubleshooting Steps

1. **Check logs**:
   - Application logs in the `logs` directory
   - System logs for service-related errors
   - Database logs for database-related issues

2. **Verify configuration**:
   - Check configuration files for errors
   - Verify environment variables are set correctly
   - Compare with known working configuration

3. **Check dependencies**:
   - Verify all required dependencies are installed
   - Check dependency versions
   - Verify dependency configurations

4. **Test components individually**:
   - Test database connectivity
   - Test service functionality
   - Test integration points

## Appendix

### Reference Architecture

```
+------------------+     +------------------+     +------------------+
|  Auth Service    |     |  Strategy Service|     |  Backtest Service|
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
|  Database        |<--->|  Trade Service   |<--->|  Data Service    |
|                  |     |                  |     |                  |
+------------------+     +------------------+     +------------------+
                                 |
                                 v
                         +------------------+
                         |  MCP Services    |
                         |                  |
                         +------------------+
```

### Port Reference

| Service           | Default Port | Protocol |
|-------------------|--------------|----------|
| Auth Service      | 8000         | HTTP     |
| Strategy Service  | 8001         | HTTP     |
| Backtest Service  | 8002         | HTTP     |
| Trade Service     | 8003         | HTTP     |
| Data Service      | 8004         | HTTP     |
| MCP Services      | 8010-8014    | HTTP     |
| Prometheus        | 9090         | HTTP     |
| Grafana           | 3000         | HTTP     |
| Alertmanager      | 9093         | HTTP     |
| PostgreSQL        | 5432         | TCP      |
| Redis             | 6379         | TCP      |

### Script Reference

| Script                                   | Description                                |
|------------------------------------------|--------------------------------------------|
| `scripts/non-docker-deployment/deploy_production.ps1/.sh`   | Production deployment script              |
| `scripts/non-docker-deployment/backup.ps1/.sh`              | Backup script                             |
| `scripts/non-docker-deployment/restore.ps1/.sh`             | Restore script                            |
| `scripts/non-docker-deployment/setup_monitoring.ps1/.sh`    | Monitoring setup script                   |
| `scripts/non-docker-deployment/setup_logging.ps1/.sh`       | Logging setup script                      |
| `scripts/non-docker-deployment/setup_alerts.ps1/.sh`        | Alerting setup script                     |
| `scripts/non-docker-security/setup_firewall.ps1/.sh`        | Firewall configuration script             |
| `scripts/non-docker-security/setup_ssl.ps1/.sh`             | SSL/TLS configuration script              |
| `scripts/non-docker-security/setup_permissions.ps1/.sh`     | Permissions configuration script          |
| `scripts/non-docker-security/secure_config.ps1/.sh`         | Secure configuration script               |
| `scripts/non-docker-security/assess_vulnerabilities.ps1/.sh`| Vulnerability assessment script           |
| `scripts/non-docker-tests/run_all_tests.ps1/.sh`            | Test execution script                     |
| `scripts/non-docker-tests/test_performance.ps1/.sh`         | Performance test script                   |

### Configuration Reference

| Configuration File                | Description                                |
|-----------------------------------|--------------------------------------------|
| `config/cryptobot_config.json`    | Main application configuration             |
| `config/exchange_config.py`       | Exchange API configuration                 |
| `config/database_config.json`     | Database connection configuration          |
| `config/logging_config.json`      | Logging configuration                      |
| `config/service_config.json`      | Service configuration                      |
| `config/non-docker/monitoring/prometheus.yml` | Prometheus configuration       |
| `config/non-docker/monitoring/grafana_dashboards/` | Grafana dashboard configurations |

### Log Reference

| Log File                          | Description                                |
|-----------------------------------|--------------------------------------------|
| `logs/auth.log`                   | Auth service logs                          |
| `logs/strategy.log`               | Strategy service logs                      |
| `logs/backtest.log`               | Backtest service logs                      |
| `logs/trade.log`                  | Trade service logs                         |
| `logs/data.log`                   | Data service logs                          |
| `logs/mcp.log`                    | MCP services logs                          |
| `logs/deployment.log`             | Deployment logs                            |
| `logs/backup.log`                 | Backup logs                                |
| `logs/restore.log`                | Restore logs                               |