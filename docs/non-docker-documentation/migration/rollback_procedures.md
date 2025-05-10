# Cryptobot Migration Rollback Procedures

This document outlines the comprehensive rollback procedures for the Cryptobot migration from Docker to non-Docker deployment. These procedures are designed to quickly restore service in the event of issues during the migration process.

## Table of Contents

1. [Rollback Decision Matrix](#rollback-decision-matrix)
2. [Preparation for Rollback](#preparation-for-rollback)
3. [Service-Level Rollback Procedures](#service-level-rollback-procedures)
4. [Full System Rollback Procedure](#full-system-rollback-procedure)
5. [Data Recovery Procedures](#data-recovery-procedures)
6. [Post-Rollback Actions](#post-rollback-actions)
7. [Communication Templates](#communication-templates)

## Rollback Decision Matrix

Use this matrix to determine when a rollback is necessary and which type of rollback to perform.

| Issue | Severity | Rollback Type | Decision Criteria |
|-------|----------|---------------|-------------------|
| Service not starting | High | Service-level | If service fails to start after 3 attempts |
| Service crashes | Medium | Service-level | If service crashes more than 3 times in 1 hour |
| Data inconsistency | High | Service-level or Full | Depends on extent of inconsistency |
| Performance degradation | Medium | Service-level | If response time increases by >300% |
| Authentication failure | Critical | Service-level or Full | If users cannot log in for >5 minutes |
| Trade execution issues | Critical | Service-level or Full | Any failure in order execution |
| Multiple service failures | Critical | Full | If 2+ critical services fail simultaneously |
| Data corruption | Critical | Full | Any evidence of data corruption |
| Security breach | Critical | Full | Any evidence of unauthorized access |

### Severity Levels

- **Low**: Minor issues that don't affect core functionality
- **Medium**: Issues that affect functionality but have workarounds
- **High**: Issues that significantly impact system usability
- **Critical**: Issues that make the system unusable or pose security/financial risks

## Preparation for Rollback

Before initiating any rollback procedure, complete these preparation steps:

1. **Assess the Situation**
   - Identify the specific issue and affected components
   - Determine the severity and impact
   - Consult the decision matrix to determine rollback type
   - Document the issue with timestamps and affected services

2. **Notify Stakeholders**
   - Alert the migration team about the issue
   - Notify system administrators
   - Prepare user communication if service interruption is expected
   - Activate the incident response team if necessary

3. **Secure Current State**
   - Create backup of current configuration
   - Take snapshot of database state
   - Capture logs from all services
   - Document current environment state

4. **Prepare Rollback Environment**
   - Verify Docker environment is available
   - Ensure Docker services can be started
   - Check backup data accessibility
   - Verify rollback scripts are ready

## Service-Level Rollback Procedures

### Data Service Rollback

1. **Stop Non-Docker Data Service**
   ```bash
   # Linux/macOS
   sudo systemctl stop cryptobot-data
   # or
   kill $(lsof -t -i:9004)
   
   # Windows
   Stop-Service cryptobot-data
   # or
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 9004).OwningProcess -Force
   ```

2. **Backup Current Data**
   ```bash
   # Linux/macOS
   timestamp=$(date +%Y%m%d%H%M%S)
   tar -czf /opt/cryptobot/backups/data_service_$timestamp.tar.gz /opt/cryptobot/non-docker/data
   
   # Windows
   $timestamp = Get-Date -Format "yyyyMMddHHmmss"
   Compress-Archive -Path C:\cryptobot\non-docker\data -DestinationPath C:\cryptobot\backups\data_service_$timestamp.zip
   ```

3. **Restore Docker Data Service**
   ```bash
   # Navigate to Docker environment
   cd /opt/cryptobot/docker  # Linux/macOS
   cd C:\cryptobot\docker    # Windows
   
   # Start Docker service
   docker-compose up -d data
   ```

4. **Verify Docker Service**
   - Check service logs: `docker-compose logs --tail=100 data`
   - Verify API endpoints are accessible
   - Test data retrieval functionality
   - Confirm service is properly connected to other services

5. **Update Service Registry**
   - Update service discovery to point to Docker service
   - Verify routing configuration
   - Test service connectivity from other services

### Backtest Service Rollback

1. **Stop Non-Docker Backtest Service**
   ```bash
   # Linux/macOS
   sudo systemctl stop cryptobot-backtest
   # or
   kill $(lsof -t -i:9002)
   
   # Windows
   Stop-Service cryptobot-backtest
   # or
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 9002).OwningProcess -Force
   ```

2. **Backup Current Data**
   ```bash
   # Linux/macOS
   timestamp=$(date +%Y%m%d%H%M%S)
   tar -czf /opt/cryptobot/backups/backtest_service_$timestamp.tar.gz /opt/cryptobot/non-docker/backtest
   
   # Windows
   $timestamp = Get-Date -Format "yyyyMMddHHmmss"
   Compress-Archive -Path C:\cryptobot\non-docker\backtest -DestinationPath C:\cryptobot\backups\backtest_service_$timestamp.zip
   ```

3. **Restore Docker Backtest Service**
   ```bash
   # Navigate to Docker environment
   cd /opt/cryptobot/docker  # Linux/macOS
   cd C:\cryptobot\docker    # Windows
   
   # Start Docker service
   docker-compose up -d backtest
   ```

4. **Verify Docker Service**
   - Check service logs: `docker-compose logs --tail=100 backtest`
   - Verify API endpoints are accessible
   - Test backtest execution functionality
   - Confirm service is properly connected to other services

5. **Update Service Registry**
   - Update service discovery to point to Docker service
   - Verify routing configuration
   - Test service connectivity from other services

### Strategy Service Rollback

1. **Stop Non-Docker Strategy Service**
   ```bash
   # Linux/macOS
   sudo systemctl stop cryptobot-strategy
   # or
   kill $(lsof -t -i:9001)
   
   # Windows
   Stop-Service cryptobot-strategy
   # or
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 9001).OwningProcess -Force
   ```

2. **Backup Current Data**
   ```bash
   # Linux/macOS
   timestamp=$(date +%Y%m%d%H%M%S)
   tar -czf /opt/cryptobot/backups/strategy_service_$timestamp.tar.gz /opt/cryptobot/non-docker/strategy
   
   # Windows
   $timestamp = Get-Date -Format "yyyyMMddHHmmss"
   Compress-Archive -Path C:\cryptobot\non-docker\strategy -DestinationPath C:\cryptobot\backups\strategy_service_$timestamp.zip
   ```

3. **Restore Docker Strategy Service**
   ```bash
   # Navigate to Docker environment
   cd /opt/cryptobot/docker  # Linux/macOS
   cd C:\cryptobot\docker    # Windows
   
   # Start Docker service
   docker-compose up -d strategy
   ```

4. **Verify Docker Service**
   - Check service logs: `docker-compose logs --tail=100 strategy`
   - Verify API endpoints are accessible
   - Test strategy management functionality
   - Confirm service is properly connected to other services

5. **Update Service Registry**
   - Update service discovery to point to Docker service
   - Verify routing configuration
   - Test service connectivity from other services

### Auth Service Rollback

1. **Stop Non-Docker Auth Service**
   ```bash
   # Linux/macOS
   sudo systemctl stop cryptobot-auth
   # or
   kill $(lsof -t -i:9000)
   
   # Windows
   Stop-Service cryptobot-auth
   # or
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 9000).OwningProcess -Force
   ```

2. **Backup Current Data**
   ```bash
   # Linux/macOS
   timestamp=$(date +%Y%m%d%H%M%S)
   tar -czf /opt/cryptobot/backups/auth_service_$timestamp.tar.gz /opt/cryptobot/non-docker/auth
   
   # Windows
   $timestamp = Get-Date -Format "yyyyMMddHHmmss"
   Compress-Archive -Path C:\cryptobot\non-docker\auth -DestinationPath C:\cryptobot\backups\auth_service_$timestamp.zip
   ```

3. **Restore Docker Auth Service**
   ```bash
   # Navigate to Docker environment
   cd /opt/cryptobot/docker  # Linux/macOS
   cd C:\cryptobot\docker    # Windows
   
   # Start Docker service
   docker-compose up -d auth
   ```

4. **Verify Docker Service**
   - Check service logs: `docker-compose logs --tail=100 auth`
   - Verify API endpoints are accessible
   - Test authentication functionality
   - Confirm service is properly connected to other services

5. **Update Service Registry**
   - Update service discovery to point to Docker service
   - Verify routing configuration
   - Test service connectivity from other services

### Trade Service Rollback

1. **Stop Non-Docker Trade Service**
   ```bash
   # Linux/macOS
   sudo systemctl stop cryptobot-trade
   # or
   kill $(lsof -t -i:9003)
   
   # Windows
   Stop-Service cryptobot-trade
   # or
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 9003).OwningProcess -Force
   ```

2. **Backup Current Data**
   ```bash
   # Linux/macOS
   timestamp=$(date +%Y%m%d%H%M%S)
   tar -czf /opt/cryptobot/backups/trade_service_$timestamp.tar.gz /opt/cryptobot/non-docker/trade
   
   # Windows
   $timestamp = Get-Date -Format "yyyyMMddHHmmss"
   Compress-Archive -Path C:\cryptobot\non-docker\trade -DestinationPath C:\cryptobot\backups\trade_service_$timestamp.zip
   ```

3. **Restore Docker Trade Service**
   ```bash
   # Navigate to Docker environment
   cd /opt/cryptobot/docker  # Linux/macOS
   cd C:\cryptobot\docker    # Windows
   
   # Start Docker service
   docker-compose up -d trade
   ```

4. **Verify Docker Service**
   - Check service logs: `docker-compose logs --tail=100 trade`
   - Verify API endpoints are accessible
   - Test trade execution functionality
   - Confirm service is properly connected to other services

5. **Update Service Registry**
   - Update service discovery to point to Docker service
   - Verify routing configuration
   - Test service connectivity from other services

### MCP Services Rollback

1. **Stop Non-Docker MCP Services**
   ```bash
   # Linux/macOS
   sudo systemctl stop cryptobot-mcp-paper-trading
   sudo systemctl stop cryptobot-mcp-portfolio-management
   sudo systemctl stop cryptobot-mcp-reporting
   sudo systemctl stop cryptobot-mcp-risk-management
   sudo systemctl stop cryptobot-mcp-strategy-execution
   
   # Windows
   Stop-Service cryptobot-mcp-paper-trading
   Stop-Service cryptobot-mcp-portfolio-management
   Stop-Service cryptobot-mcp-reporting
   Stop-Service cryptobot-mcp-risk-management
   Stop-Service cryptobot-mcp-strategy-execution
   ```

2. **Backup Current Data**
   ```bash
   # Linux/macOS
   timestamp=$(date +%Y%m%d%H%M%S)
   tar -czf /opt/cryptobot/backups/mcp_services_$timestamp.tar.gz /opt/cryptobot/non-docker/services/mcp
   
   # Windows
   $timestamp = Get-Date -Format "yyyyMMddHHmmss"
   Compress-Archive -Path C:\cryptobot\non-docker\services\mcp -DestinationPath C:\cryptobot\backups\mcp_services_$timestamp.zip
   ```

3. **Restore Docker MCP Services**
   ```bash
   # Navigate to Docker environment
   cd /opt/cryptobot/docker  # Linux/macOS
   cd C:\cryptobot\docker    # Windows
   
   # Start Docker services
   docker-compose up -d mcp-paper-trading mcp-portfolio-management mcp-reporting mcp-risk-management mcp-strategy-execution
   ```

4. **Verify Docker Services**
   - Check service logs for each MCP service
   - Verify API endpoints are accessible
   - Test MCP functionality
   - Confirm services are properly connected to other services

5. **Update Service Registry**
   - Update service discovery to point to Docker services
   - Verify routing configuration
   - Test service connectivity from other services

## Full System Rollback Procedure

Use this procedure when multiple services are affected or when a critical issue requires reverting the entire system.

### 1. Emergency System Shutdown

```bash
# Linux/macOS
sudo /opt/cryptobot/non-docker/scripts/emergency_shutdown.sh

# Windows
& "C:\cryptobot\non-docker\scripts\emergency_shutdown.ps1"
```

### 2. Notify Users

- Deploy maintenance page
- Send emergency notification to all users
- Update status page
- Alert support team

### 3. Backup Current State

```bash
# Linux/macOS
sudo /opt/cryptobot/non-docker/scripts/backup_all.sh

# Windows
& "C:\cryptobot\non-docker\scripts\backup_all.ps1"
```

### 4. Restore Docker Environment

```bash
# Linux/macOS
cd /opt/cryptobot/docker
docker-compose down
docker-compose up -d

# Windows
cd C:\cryptobot\docker
docker-compose down
docker-compose up -d
```

### 5. Synchronize Data

```bash
# Linux/macOS
sudo /opt/cryptobot/scripts/non-docker-migration/sync_data.sh --reverse

# Windows
& "C:\cryptobot\scripts\non-docker-migration\sync_data.ps1" -Reverse
```

### 6. Verify Docker Environment

- Check all service logs
- Verify database connectivity
- Test authentication
- Test critical workflows
- Verify external API connections

### 7. Update DNS and Load Balancers

- Redirect all traffic to Docker environment
- Update service discovery
- Verify routing configuration

### 8. Remove Maintenance Page

- Restore normal access
- Monitor system performance
- Watch for any issues

### 9. Notify Users of Restoration

- Send all-clear notification
- Update status page
- Provide support contact information

## Data Recovery Procedures

### Database Recovery

1. **Identify Latest Valid Backup**
   - Check backup timestamps
   - Verify backup integrity
   - Select most recent valid backup

2. **Restore Database**
   ```bash
   # Linux/macOS
   pg_restore -h localhost -U cryptobot -d cryptobot /opt/cryptobot/backups/database/backup_TIMESTAMP.sql
   
   # Windows
   pg_restore -h localhost -U cryptobot -d cryptobot C:\cryptobot\backups\database\backup_TIMESTAMP.sql
   ```

3. **Apply Transaction Logs**
   - Replay transaction logs since backup
   - Verify data consistency
   - Check for any missing transactions

4. **Verify Database Integrity**
   - Run database consistency checks
   - Verify foreign key constraints
   - Check for orphaned records

### User Data Recovery

1. **Restore User Data from Backup**
   ```bash
   # Linux/macOS
   tar -xzf /opt/cryptobot/backups/user_data_TIMESTAMP.tar.gz -C /opt/cryptobot/shared_data/
   
   # Windows
   Expand-Archive -Path C:\cryptobot\backups\user_data_TIMESTAMP.zip -DestinationPath C:\cryptobot\shared_data\
   ```

2. **Verify User Data Integrity**
   - Check file permissions
   - Verify file integrity
   - Test access to user data

### Historical Data Recovery

1. **Restore Historical Data from Backup**
   ```bash
   # Linux/macOS
   tar -xzf /opt/cryptobot/backups/historical_data_TIMESTAMP.tar.gz -C /opt/cryptobot/shared_data/
   
   # Windows
   Expand-Archive -Path C:\cryptobot\backups\historical_data_TIMESTAMP.zip -DestinationPath C:\cryptobot\shared_data\
   ```

2. **Verify Historical Data Integrity**
   - Check file permissions
   - Verify file integrity
   - Test access to historical data

## Post-Rollback Actions

### 1. Document the Rollback

- Record timestamp of rollback
- Document affected services
- Note any data loss or inconsistencies
- Record rollback procedure used
- Document any issues encountered during rollback

### 2. Root Cause Analysis

- Investigate the cause of the failure
- Review logs and monitoring data
- Interview team members involved
- Document findings
- Develop preventive measures

### 3. Update Migration Plan

- Revise migration approach based on findings
- Update rollback procedures if needed
- Adjust timeline for next migration attempt
- Enhance testing procedures
- Review decision criteria

### 4. Communicate with Stakeholders

- Provide detailed incident report
- Share root cause analysis
- Present revised migration plan
- Set expectations for next steps
- Address concerns and questions

### 5. Verify System Stability

- Monitor system for 24-48 hours
- Watch for any delayed effects
- Verify all functionality
- Check system performance
- Ensure data consistency

## Communication Templates

### Emergency Maintenance Notification

```
Subject: URGENT: Cryptobot Emergency Maintenance

Dear Cryptobot User,

We are currently experiencing technical issues with our recent system upgrade. 
To ensure the security and integrity of your data and trading activities, 
we have initiated emergency maintenance procedures.

During this time, the Cryptobot platform will be unavailable. We anticipate 
the maintenance to last approximately [DURATION].

What this means for you:
- All active trading has been safely paused
- Your funds and data remain secure
- No action is required on your part

We will notify you as soon as the system is back online. We sincerely 
apologize for any inconvenience this may cause.

For urgent inquiries, please contact our support team at support@cryptobot.com.

Thank you for your patience and understanding.

The Cryptobot Team
```

### Rollback Completion Notification

```
Subject: Cryptobot Service Restored

Dear Cryptobot User,

We're pleased to inform you that the Cryptobot platform has been fully restored 
and is now operational. Our team has successfully addressed the technical issues 
that required the emergency maintenance.

What you should know:
- All services are now functioning normally
- Your funds and data remain secure
- Trading functionality has been restored
- No action is required on your part

We have temporarily reverted to our previous stable system while we address 
the issues encountered during the upgrade. We will provide further updates 
on the rescheduled upgrade in the coming days.

If you experience any issues or have questions, please contact our support 
team at support@cryptobot.com.

We sincerely apologize for the inconvenience and thank you for your patience 
and understanding.

The Cryptobot Team
```

### Status Update During Extended Rollback

```
Subject: Cryptobot Maintenance Status Update

Dear Cryptobot User,

We wanted to provide you with an update on the ongoing maintenance of the 
Cryptobot platform.

Current Status:
- Our team is actively working to restore full functionality
- We have identified the root cause of the issue
- Recovery procedures are in progress
- Estimated completion time: [TIME]

Your funds and data remain secure. We are taking all necessary precautions 
to ensure a safe and complete restoration of services.

We will continue to provide updates every [TIMEFRAME] until service is fully restored.

For urgent inquiries, please contact our support team at support@cryptobot.com.

Thank you for your continued patience and understanding.

The Cryptobot Team