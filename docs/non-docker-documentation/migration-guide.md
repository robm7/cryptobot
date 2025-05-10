# Migration Guide

This guide provides instructions for migrating from the Docker version of Cryptobot to the non-Docker version. It covers the migration process, data migration, and configuration migration.

## Table of Contents
- [Overview](#overview)
- [Migration Process](#migration-process)
- [Data Migration](#data-migration)
- [Configuration Migration](#configuration-migration)
- [Verification and Testing](#verification-and-testing)
- [Troubleshooting](#troubleshooting)

## Overview

### Docker vs. Non-Docker Versions

The Docker version of Cryptobot runs each service in a separate container, with Docker Compose managing the containers and their interactions. The non-Docker version runs all services directly on the host machine, providing better performance and easier integration with the host system.

### Key Differences

| Feature | Docker Version | Non-Docker Version |
|---------|---------------|-------------------|
| Deployment | Container-based | Native installation |
| Performance | Slightly lower due to containerization | Better performance |
| Resource Usage | Higher due to container overhead | Lower resource usage |
| Isolation | Strong isolation between services | Services share the host environment |
| Configuration | Docker Compose and environment variables | Configuration files and environment variables |
| Data Storage | Docker volumes | Local filesystem |
| Updates | Container image updates | Native application updates |
| Scaling | Easy horizontal scaling | Vertical scaling on a single machine |

### Migration Benefits

- **Improved Performance**: Native execution without container overhead
- **Reduced Resource Usage**: Lower memory and CPU usage
- **Simplified Management**: No need to manage Docker containers
- **Better Integration**: Easier integration with host system tools
- **Direct Access**: Direct access to files and processes

## Migration Process

### Pre-Migration Checklist

Before migrating from Docker to non-Docker, ensure you have:

1. **Backup of All Data**:
   - Database dumps
   - Configuration files
   - Custom strategies
   - API keys and credentials

2. **System Requirements**:
   - Verify that your system meets the [requirements](getting-started.md#system-requirements)
   - Ensure you have Python 3.8 or newer installed

3. **Service Inventory**:
   - List all running services in your Docker setup
   - Note any custom configurations or modifications

4. **Dependency Check**:
   - Identify any external dependencies (Redis, PostgreSQL, etc.)
   - Ensure these are installed on the host system

### Step-by-Step Migration

1. **Stop Docker Services**:
   ```bash
   cd /path/to/docker/cryptobot
   docker-compose down
   ```

2. **Install Non-Docker Version**:
   Follow the [installation instructions](getting-started.md#installation-instructions) for your platform.

3. **Migrate Configuration**:
   Follow the [Configuration Migration](#configuration-migration) section below.

4. **Migrate Data**:
   Follow the [Data Migration](#data-migration) section below.

5. **Start Non-Docker Services**:
   ```bash
   # Using the Quick Start Launcher
   cryptobot-launcher
   
   # Or using the command line
   cryptobot --all
   ```

6. **Verify Migration**:
   Follow the [Verification and Testing](#verification-and-testing) section below.

## Data Migration

### Database Migration

#### SQLite Database

If you're using SQLite in the Docker version:

1. **Locate the SQLite Database File**:
   ```bash
   # Find the Docker volume containing the database
   docker volume inspect cryptobot_db_data
   
   # Copy the database file from the Docker volume
   sudo cp /var/lib/docker/volumes/cryptobot_db_data/_data/cryptobot.db /tmp/
   ```

2. **Copy the Database to the Non-Docker Location**:
   ```bash
   # Windows
   copy /tmp/cryptobot.db %APPDATA%\CryptoBot\
   
   # macOS
   cp /tmp/cryptobot.db ~/Library/Application\ Support/CryptoBot/
   
   # Linux
   cp /tmp/cryptobot.db /etc/cryptobot/
   ```

#### PostgreSQL Database

If you're using PostgreSQL in the Docker version:

1. **Dump the Database**:
   ```bash
   # Connect to the PostgreSQL container
   docker exec -it cryptobot_postgres pg_dump -U cryptobot -d cryptobot > cryptobot_backup.sql
   ```

2. **Restore the Database**:
   ```bash
   # Restore to the local PostgreSQL instance
   psql -U cryptobot -d cryptobot -f cryptobot_backup.sql
   ```

3. **Update Database Configuration**:
   Update the database configuration in the non-Docker version to point to the local PostgreSQL instance.

#### MySQL/MariaDB Database

If you're using MySQL/MariaDB in the Docker version:

1. **Dump the Database**:
   ```bash
   # Connect to the MySQL container
   docker exec -it cryptobot_mysql mysqldump -u cryptobot -p cryptobot > cryptobot_backup.sql
   ```

2. **Restore the Database**:
   ```bash
   # Restore to the local MySQL instance
   mysql -u cryptobot -p cryptobot < cryptobot_backup.sql
   ```

3. **Update Database Configuration**:
   Update the database configuration in the non-Docker version to point to the local MySQL instance.

### Historical Data Migration

1. **Locate Historical Data**:
   ```bash
   # Find the Docker volume containing historical data
   docker volume inspect cryptobot_historical_data
   
   # Create a temporary directory
   mkdir -p /tmp/historical_data
   
   # Copy historical data from the Docker volume
   sudo cp -r /var/lib/docker/volumes/cryptobot_historical_data/_data/* /tmp/historical_data/
   ```

2. **Copy Historical Data to the Non-Docker Location**:
   ```bash
   # Windows
   xcopy /E /I /Y \tmp\historical_data %APPDATA%\CryptoBot\historical_data
   
   # macOS
   cp -R /tmp/historical_data ~/Library/Application\ Support/CryptoBot/
   
   # Linux
   cp -R /tmp/historical_data /etc/cryptobot/
   ```

### Custom Strategies Migration

1. **Locate Custom Strategies**:
   ```bash
   # Find the Docker volume containing custom strategies
   docker volume inspect cryptobot_strategies
   
   # Create a temporary directory
   mkdir -p /tmp/strategies
   
   # Copy custom strategies from the Docker volume
   sudo cp -r /var/lib/docker/volumes/cryptobot_strategies/_data/* /tmp/strategies/
   ```

2. **Copy Custom Strategies to the Non-Docker Location**:
   ```bash
   # Windows
   xcopy /E /I /Y \tmp\strategies %APPDATA%\CryptoBot\strategies
   
   # macOS
   cp -R /tmp/strategies ~/Library/Application\ Support/CryptoBot/
   
   # Linux
   cp -R /tmp/strategies /etc/cryptobot/
   ```

### API Keys and Credentials

1. **Export API Keys from Docker Version**:
   - Log in to the Docker version's dashboard
   - Navigate to Settings > API Keys
   - Export API keys to a secure file

2. **Import API Keys to Non-Docker Version**:
   - Log in to the non-Docker version's dashboard
   - Navigate to Settings > API Keys
   - Import API keys from the exported file

## Configuration Migration

### Docker Compose to Configuration Files

The Docker version uses `docker-compose.yml` and environment variables for configuration. The non-Docker version uses configuration files in JSON format.

#### Example Docker Compose Configuration

```yaml
version: '3'
services:
  auth:
    image: cryptobot/auth:latest
    environment:
      - CRYPTOBOT_ENV=production
      - CRYPTOBOT_DB_URL=postgresql://cryptobot:password@postgres/cryptobot
      - CRYPTOBOT_JWT_SECRET=your-secret-key
    ports:
      - "8000:8000"
  
  strategy:
    image: cryptobot/strategy:latest
    environment:
      - CRYPTOBOT_ENV=production
      - CRYPTOBOT_DB_URL=postgresql://cryptobot:password@postgres/cryptobot
      - CRYPTOBOT_AUTH_URL=http://auth:8000
    ports:
      - "8001:8001"
  
  # Other services...
  
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_USER=cryptobot
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=cryptobot
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

#### Equivalent Non-Docker Configuration

```json
{
  "services": {
    "auth": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8000,
      "jwt_secret": "your-secret-key"
    },
    "strategy": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8001,
      "auth_url": "http://localhost:8000"
    }
  },
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "username": "cryptobot",
    "password": "password",
    "database": "cryptobot"
  },
  "environment": "production"
}
```

### Environment Variables Migration

If you're using environment variables in the Docker version, you'll need to migrate them to the non-Docker version.

#### Docker Environment Variables

```
CRYPTOBOT_ENV=production
CRYPTOBOT_DB_URL=postgresql://cryptobot:password@postgres/cryptobot
CRYPTOBOT_JWT_SECRET=your-secret-key
CRYPTOBOT_LOG_LEVEL=INFO
```

#### Non-Docker Environment Variables

```bash
# Windows
set CRYPTOBOT_ENV=production
set CRYPTOBOT_DB_URL=postgresql://cryptobot:password@localhost/cryptobot
set CRYPTOBOT_JWT_SECRET=your-secret-key
set CRYPTOBOT_LOG_LEVEL=INFO

# Linux/macOS
export CRYPTOBOT_ENV=production
export CRYPTOBOT_DB_URL=postgresql://cryptobot:password@localhost/cryptobot
export CRYPTOBOT_JWT_SECRET=your-secret-key
export CRYPTOBOT_LOG_LEVEL=INFO
```

### Service-Specific Configuration

For each service, you'll need to migrate the configuration from the Docker version to the non-Docker version.

#### Auth Service

Docker:
```yaml
auth:
  image: cryptobot/auth:latest
  environment:
    - CRYPTOBOT_ENV=production
    - CRYPTOBOT_DB_URL=postgresql://cryptobot:password@postgres/cryptobot
    - CRYPTOBOT_JWT_SECRET=your-secret-key
    - CRYPTOBOT_JWT_ALGORITHM=HS256
    - CRYPTOBOT_ACCESS_TOKEN_EXPIRE_MINUTES=30
    - CRYPTOBOT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

Non-Docker (`config/auth.json`):
```json
{
  "enabled": true,
  "host": "0.0.0.0",
  "port": 8000,
  "jwt_secret": "your-secret-key",
  "jwt_algorithm": "HS256",
  "access_token_expire_minutes": 30,
  "refresh_token_expire_days": 7
}
```

#### Strategy Service

Docker:
```yaml
strategy:
  image: cryptobot/strategy:latest
  environment:
    - CRYPTOBOT_ENV=production
    - CRYPTOBOT_DB_URL=postgresql://cryptobot:password@postgres/cryptobot
    - CRYPTOBOT_AUTH_URL=http://auth:8000
    - CRYPTOBOT_DATA_URL=http://data:8002
    - CRYPTOBOT_TRADE_URL=http://trade:8003
```

Non-Docker (`config/strategy.json`):
```json
{
  "enabled": true,
  "host": "0.0.0.0",
  "port": 8001,
  "auth_url": "http://localhost:8000",
  "data_url": "http://localhost:8002",
  "trade_url": "http://localhost:8003"
}
```

### Network Configuration

In the Docker version, services communicate using Docker's internal network. In the non-Docker version, services communicate using localhost.

Docker:
```yaml
services:
  auth:
    # ...
  strategy:
    # ...
    environment:
      - CRYPTOBOT_AUTH_URL=http://auth:8000
```

Non-Docker:
```json
{
  "services": {
    "auth": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8000
    },
    "strategy": {
      "enabled": true,
      "host": "0.0.0.0",
      "port": 8001,
      "auth_url": "http://localhost:8000"
    }
  }
}
```

## Verification and Testing

After migrating from Docker to non-Docker, it's important to verify that everything is working correctly.

### Service Health Check

1. **Check Service Status**:
   - Open the Quick Start Launcher
   - Verify that all services are running
   - Check for any error messages in the logs

2. **API Health Check**:
   ```bash
   # Check Auth Service
   curl http://localhost:8000/health
   
   # Check Strategy Service
   curl http://localhost:8001/health
   
   # Check Data Service
   curl http://localhost:8002/health
   
   # Check Trade Service
   curl http://localhost:8003/health
   
   # Check Backtest Service
   curl http://localhost:8004/health
   ```

### Data Verification

1. **Database Verification**:
   - Log in to the dashboard
   - Verify that all user accounts are present
   - Check that API keys are correctly migrated
   - Verify that strategies are correctly migrated

2. **Historical Data Verification**:
   - Run a backtest on a strategy that worked in the Docker version
   - Compare the results with the Docker version
   - Verify that the results are similar

### Functionality Testing

1. **Authentication Testing**:
   - Log in to the dashboard
   - Create a new API key
   - Verify that the API key works

2. **Strategy Testing**:
   - Create a new strategy
   - Run a backtest
   - Deploy the strategy for paper trading
   - Verify that signals are generated

3. **Trading Testing**:
   - Set up paper trading
   - Execute a test trade
   - Verify that the trade is executed correctly

## Troubleshooting

### Common Migration Issues

#### Database Connection Issues

**Issue**: Services cannot connect to the database after migration.

**Solution**:
1. Verify that the database is running
2. Check database connection settings
3. Ensure that the database user has the correct permissions
4. Check for network issues between services and the database

#### Missing Data

**Issue**: Some data is missing after migration.

**Solution**:
1. Verify that all data was exported from the Docker version
2. Check that data was imported correctly
3. Check file permissions on imported data
4. Restore from backup if necessary

#### Service Communication Issues

**Issue**: Services cannot communicate with each other.

**Solution**:
1. Verify that all services are running
2. Check service URLs in configuration files
3. Ensure that localhost is used instead of Docker service names
4. Check for firewall issues

#### Authentication Issues

**Issue**: Cannot log in after migration.

**Solution**:
1. Verify that the Auth Service is running
2. Check JWT secret key in configuration
3. Ensure that user accounts were migrated correctly
4. Reset passwords if necessary

### Getting Help

If you encounter issues during migration that you can't resolve:

1. **Check Documentation**:
   - Review this migration guide
   - Check the [troubleshooting section](administrator-guide.md#troubleshooting-common-issues) in the Administrator Guide

2. **Community Support**:
   - Post on the community forum
   - Check for similar migration issues and solutions

3. **Professional Support**:
   - Contact support at support@example.com
   - Provide detailed information about the issue
   - Include logs and configuration files (with sensitive information removed)