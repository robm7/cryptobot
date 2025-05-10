# Administrator Guide

This guide provides detailed information for administrators of the non-Docker version of Cryptobot, covering advanced configuration, performance tuning, security, backup and recovery, and troubleshooting.

## Table of Contents
- [Advanced Configuration Options](#advanced-configuration-options)
- [Performance Tuning](#performance-tuning)
- [Security Considerations](#security-considerations)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Advanced Configuration Options

### Service Configuration

Each service in Cryptobot can be configured with advanced options beyond the basic settings available in the Quick Start Launcher.

#### Authentication Service

```json
{
  "auth": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8000,
    "jwt_secret": "your-secret-key",
    "jwt_algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "password_hashing": {
      "algorithm": "bcrypt",
      "rounds": 12
    },
    "rate_limiting": {
      "enabled": true,
      "max_requests": 100,
      "timeframe_seconds": 60
    },
    "api_key_rotation": {
      "enabled": true,
      "rotation_days": 90,
      "grace_period_days": 7
    }
  }
}
```

#### Strategy Service

```json
{
  "strategy": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8001,
    "max_active_strategies": 10,
    "strategy_execution_interval": 60,
    "signal_timeout_seconds": 300,
    "backtest_timeout_seconds": 1800,
    "optimization_timeout_seconds": 3600,
    "max_historical_data_days": 365,
    "cache_enabled": true,
    "cache_ttl_seconds": 3600
  }
}
```

#### Data Service

```json
{
  "data": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8002,
    "max_connections_per_exchange": 5,
    "connection_timeout_seconds": 30,
    "request_timeout_seconds": 10,
    "retry_attempts": 3,
    "retry_delay_seconds": 1,
    "cache_enabled": true,
    "cache_ttl_seconds": 60,
    "websocket_reconnect_attempts": 5,
    "websocket_reconnect_delay_seconds": 5,
    "rate_limiting": {
      "enabled": true,
      "max_requests_per_minute": {
        "binance": 1200,
        "coinbase": 300,
        "kraken": 600
      }
    }
  }
}
```

#### Trade Service

```json
{
  "trade": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8003,
    "max_concurrent_orders": 10,
    "order_timeout_seconds": 60,
    "retry_attempts": 3,
    "retry_delay_seconds": 1,
    "position_update_interval_seconds": 10,
    "risk_management": {
      "max_position_size_percent": 5.0,
      "max_total_exposure_percent": 50.0,
      "max_drawdown_percent": 10.0,
      "stop_loss_percent": 2.0,
      "take_profit_percent": 5.0
    }
  }
}
```

#### Backtest Service

```json
{
  "backtest": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8004,
    "max_concurrent_backtests": 3,
    "max_backtest_duration_seconds": 1800,
    "max_optimization_duration_seconds": 3600,
    "max_data_points": 1000000,
    "cache_enabled": true,
    "cache_ttl_seconds": 86400,
    "result_storage_days": 30
  }
}
```

### Database Configuration

Cryptobot supports multiple database backends:

#### SQLite (Default)

```json
{
  "database": {
    "type": "sqlite",
    "url": "sqlite:///cryptobot.db",
    "pool_size": 5,
    "max_overflow": 10,
    "pool_recycle": 3600,
    "pool_timeout": 30
  }
}
```

#### PostgreSQL

```json
{
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432,
    "username": "cryptobot",
    "password": "your-password",
    "database": "cryptobot",
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 3600,
    "pool_timeout": 30,
    "ssl_mode": "require"
  }
}
```

#### MySQL/MariaDB

```json
{
  "database": {
    "type": "mysql",
    "host": "localhost",
    "port": 3306,
    "username": "cryptobot",
    "password": "your-password",
    "database": "cryptobot",
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 3600,
    "pool_timeout": 30,
    "charset": "utf8mb4"
  }
}
```

### Logging Configuration

Cryptobot provides advanced logging configuration options:

```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "file": "cryptobot.log",
    "max_size_mb": 10,
    "backup_count": 5,
    "console_output": true,
    "syslog": {
      "enabled": false,
      "address": "localhost",
      "port": 514,
      "facility": "local0"
    },
    "service_levels": {
      "auth": "INFO",
      "strategy": "INFO",
      "data": "INFO",
      "trade": "INFO",
      "backtest": "INFO"
    }
  }
}
```

### Notification Configuration

Configure notifications for important events:

```json
{
  "notifications": {
    "enabled": true,
    "email": {
      "enabled": true,
      "smtp_server": "smtp.example.com",
      "smtp_port": 587,
      "smtp_username": "your-username",
      "smtp_password": "your-password",
      "from_address": "cryptobot@example.com",
      "to_addresses": ["admin@example.com"],
      "use_tls": true
    },
    "telegram": {
      "enabled": false,
      "bot_token": "your-bot-token",
      "chat_id": "your-chat-id"
    },
    "webhook": {
      "enabled": false,
      "url": "https://example.com/webhook",
      "headers": {
        "Authorization": "Bearer your-token"
      }
    },
    "events": {
      "system_startup": true,
      "system_shutdown": true,
      "service_error": true,
      "trade_executed": true,
      "position_opened": true,
      "position_closed": true,
      "strategy_started": true,
      "strategy_stopped": true,
      "backtest_completed": true
    }
  }
}
```

## Performance Tuning

### Hardware Recommendations

For optimal performance, consider the following hardware recommendations:

| Component | Minimum | Recommended | High Performance |
|-----------|---------|-------------|------------------|
| CPU | 2 cores, 2.0 GHz | 4 cores, 2.5 GHz | 8+ cores, 3.0+ GHz |
| RAM | 4 GB | 8 GB | 16+ GB |
| Storage | 1 GB SSD | 10 GB SSD | 50+ GB NVMe SSD |
| Network | 10 Mbps | 50 Mbps | 100+ Mbps |

### Service Scaling

Each service can be scaled independently based on your needs:

#### Memory Allocation

Adjust the memory allocation for each service:

```json
{
  "services": {
    "auth": {
      "memory_limit_mb": 256
    },
    "strategy": {
      "memory_limit_mb": 512
    },
    "data": {
      "memory_limit_mb": 1024
    },
    "trade": {
      "memory_limit_mb": 512
    },
    "backtest": {
      "memory_limit_mb": 2048
    }
  }
}
```

#### Process Configuration

Configure the number of worker processes for each service:

```json
{
  "services": {
    "auth": {
      "workers": 2
    },
    "strategy": {
      "workers": 2
    },
    "data": {
      "workers": 4
    },
    "trade": {
      "workers": 2
    },
    "backtest": {
      "workers": 2
    }
  }
}
```

### Database Optimization

Optimize database performance:

#### Connection Pooling

```json
{
  "database": {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 3600,
    "pool_timeout": 30
  }
}
```

#### Query Optimization

For PostgreSQL:

```sql
CREATE INDEX idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_ohlcv_symbol_timeframe ON ohlcv(symbol, timeframe);
CREATE INDEX idx_ohlcv_timestamp ON ohlcv(timestamp);
```

### Caching

Configure caching to improve performance:

```json
{
  "cache": {
    "enabled": true,
    "type": "redis",
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "password": null,
    "ttl_seconds": 3600,
    "max_memory_mb": 256,
    "eviction_policy": "allkeys-lru"
  }
}
```

### Network Optimization

Optimize network settings:

```json
{
  "network": {
    "timeout_seconds": 10,
    "keepalive": true,
    "max_connections": 100,
    "connection_timeout_seconds": 30,
    "retry_attempts": 3,
    "retry_delay_seconds": 1,
    "proxy": {
      "enabled": false,
      "http": "http://proxy.example.com:8080",
      "https": "http://proxy.example.com:8080",
      "no_proxy": "localhost,127.0.0.1"
    }
  }
}
```

## Security Considerations

### Authentication and Authorization

#### Password Policy

Configure password policy:

```json
{
  "auth": {
    "password_policy": {
      "min_length": 12,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true,
      "require_special_chars": true,
      "max_age_days": 90,
      "history_count": 5
    }
  }
}
```

#### Two-Factor Authentication

Enable two-factor authentication:

```json
{
  "auth": {
    "two_factor": {
      "enabled": true,
      "type": "totp",
      "issuer": "CryptoBot",
      "digits": 6,
      "period": 30,
      "algorithm": "SHA1"
    }
  }
}
```

#### API Key Security

Secure API keys:

```json
{
  "auth": {
    "api_key_security": {
      "encryption_enabled": true,
      "encryption_algorithm": "AES-256-GCM",
      "rotation_days": 90,
      "ip_restriction_enabled": true,
      "allowed_ips": ["192.168.1.0/24"],
      "permission_scopes": ["read", "trade", "withdraw"]
    }
  }
}
```

### Network Security

#### TLS Configuration

Configure TLS for secure communications:

```json
{
  "tls": {
    "enabled": true,
    "cert_file": "/path/to/cert.pem",
    "key_file": "/path/to/key.pem",
    "ca_file": "/path/to/ca.pem",
    "verify_client": true,
    "min_version": "TLSv1.2",
    "ciphers": "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256"
  }
}
```

#### Firewall Rules

Recommended firewall rules:

| Service | Port | Protocol | Access |
|---------|------|----------|--------|
| Auth | 8000 | TCP | Internal |
| Strategy | 8001 | TCP | Internal |
| Data | 8002 | TCP | Internal |
| Trade | 8003 | TCP | Internal |
| Backtest | 8004 | TCP | Internal |
| Dashboard | 8080 | TCP | Restricted |

### Data Security

#### Data Encryption

Configure data encryption:

```json
{
  "security": {
    "data_encryption": {
      "enabled": true,
      "algorithm": "AES-256-GCM",
      "key_rotation_days": 90,
      "sensitive_fields": [
        "api_key",
        "api_secret",
        "password",
        "private_key"
      ]
    }
  }
}
```

#### Secure Storage

Secure storage recommendations:

1. Use encrypted filesystems for sensitive data
2. Implement proper file permissions
3. Use secure key management solutions
4. Regularly audit access to sensitive data

### Audit Logging

Configure audit logging:

```json
{
  "audit": {
    "enabled": true,
    "log_file": "audit.log",
    "max_size_mb": 10,
    "backup_count": 5,
    "events": [
      "login",
      "logout",
      "password_change",
      "api_key_creation",
      "api_key_deletion",
      "strategy_creation",
      "strategy_modification",
      "strategy_deletion",
      "trade_execution",
      "withdrawal",
      "configuration_change",
      "permission_change"
    ]
  }
}
```

## Backup and Recovery

### Database Backup

#### Automated Backups

Configure automated database backups:

```json
{
  "backup": {
    "database": {
      "enabled": true,
      "schedule": "0 0 * * *",  // Daily at midnight
      "retention_days": 30,
      "compression": true,
      "storage_path": "/path/to/backups",
      "remote_storage": {
        "enabled": false,
        "type": "s3",
        "bucket": "cryptobot-backups",
        "path": "database",
        "access_key": "your-access-key",
        "secret_key": "your-secret-key",
        "region": "us-west-1"
      }
    }
  }
}
```

#### Manual Backup

SQLite:
```bash
sqlite3 cryptobot.db .dump > backup.sql
```

PostgreSQL:
```bash
pg_dump -U cryptobot -d cryptobot -f backup.sql
```

MySQL/MariaDB:
```bash
mysqldump -u cryptobot -p cryptobot > backup.sql
```

### Configuration Backup

#### Automated Configuration Backups

Configure automated configuration backups:

```json
{
  "backup": {
    "configuration": {
      "enabled": true,
      "schedule": "0 0 * * 0",  // Weekly on Sunday
      "retention_count": 10,
      "compression": true,
      "storage_path": "/path/to/backups",
      "include_paths": [
        "config/",
        "strategies/"
      ],
      "exclude_paths": [
        "config/local.json"
      ]
    }
  }
}
```

#### Manual Configuration Backup

```bash
# Windows
xcopy /E /I %APPDATA%\CryptoBot\config backup\config

# macOS
cp -R ~/Library/Application\ Support/CryptoBot/config backup/config

# Linux
cp -R /etc/cryptobot/config backup/config
```

### Recovery Procedures

#### Database Recovery

SQLite:
```bash
sqlite3 cryptobot.db < backup.sql
```

PostgreSQL:
```bash
psql -U cryptobot -d cryptobot -f backup.sql
```

MySQL/MariaDB:
```bash
mysql -u cryptobot -p cryptobot < backup.sql
```

#### Configuration Recovery

```bash
# Windows
xcopy /E /I backup\config %APPDATA%\CryptoBot\config

# macOS
cp -R backup/config ~/Library/Application\ Support/CryptoBot/config

# Linux
cp -R backup/config /etc/cryptobot/config
```

#### Full System Recovery

1. Install CryptoBot using the standard installation procedure
2. Restore the configuration files
3. Restore the database
4. Restart all services

### Disaster Recovery Planning

1. **Regular Backups**: Implement automated backups
2. **Offsite Storage**: Store backups in a separate location
3. **Recovery Testing**: Regularly test recovery procedures
4. **Documentation**: Document recovery procedures
5. **Monitoring**: Monitor backup success/failure

## Troubleshooting Common Issues

### Service Startup Issues

#### Service Fails to Start

**Symptoms**:
- Service shows "Failed" status in the launcher
- Error messages in the logs

**Possible Causes and Solutions**:

1. **Port Conflict**:
   - Check if another application is using the same port
   - Change the port in the configuration file
   - Restart the service

2. **Database Connection Issues**:
   - Verify database connection settings
   - Check if the database server is running
   - Check database permissions

3. **Missing Dependencies**:
   - Reinstall the application
   - Check for missing Python packages
   - Install required system libraries

#### Service Crashes After Starting

**Symptoms**:
- Service starts but crashes shortly after
- Error messages in the logs

**Possible Causes and Solutions**:

1. **Memory Issues**:
   - Increase memory allocation
   - Check for memory leaks
   - Reduce the number of worker processes

2. **Configuration Errors**:
   - Check for syntax errors in configuration files
   - Verify configuration values are within valid ranges
   - Reset to default configuration

### Database Issues

#### Database Connection Errors

**Symptoms**:
- "Could not connect to database" errors
- Services fail to start

**Possible Causes and Solutions**:

1. **Database Server Not Running**:
   - Start the database server
   - Check database server logs

2. **Incorrect Connection Settings**:
   - Verify host, port, username, and password
   - Check database name
   - Test connection with a database client

3. **Network Issues**:
   - Check network connectivity
   - Verify firewall rules
   - Check for network configuration changes

#### Database Performance Issues

**Symptoms**:
- Slow response times
- High CPU or disk usage

**Possible Causes and Solutions**:

1. **Missing Indexes**:
   - Add indexes to frequently queried columns
   - Optimize query patterns

2. **Database Growth**:
   - Implement data retention policies
   - Archive old data
   - Increase storage capacity

3. **Connection Pool Exhaustion**:
   - Increase pool size
   - Reduce query duration
   - Check for connection leaks

### Exchange Connectivity Issues

#### Unable to Connect to Exchange

**Symptoms**:
- "Could not connect to exchange" errors
- Timeout errors

**Possible Causes and Solutions**:

1. **API Key Issues**:
   - Verify API key and secret
   - Check API key permissions
   - Generate new API keys

2. **Network Issues**:
   - Check network connectivity
   - Verify firewall rules
   - Check for IP restrictions

3. **Exchange Maintenance**:
   - Check exchange status page
   - Wait for maintenance to complete
   - Switch to a different exchange

#### Rate Limiting

**Symptoms**:
- "Rate limit exceeded" errors
- Temporary connection failures

**Possible Causes and Solutions**:

1. **Too Many Requests**:
   - Reduce request frequency
   - Implement request throttling
   - Increase rate limit settings if possible

2. **Multiple Instances**:
   - Ensure only one instance is running
   - Coordinate API usage across instances

### Strategy Execution Issues

#### Strategy Not Generating Signals

**Symptoms**:
- No trading signals generated
- No trades executed

**Possible Causes and Solutions**:

1. **Configuration Issues**:
   - Verify strategy parameters
   - Check for invalid settings
   - Reset to default parameters

2. **Data Issues**:
   - Check for missing or invalid market data
   - Verify data source connectivity
   - Refresh historical data

3. **Logic Issues**:
   - Review strategy logic
   - Check for conditional errors
   - Test with different market conditions

#### Unexpected Trading Behavior

**Symptoms**:
- Trades executed at unexpected times
- Incorrect position sizing

**Possible Causes and Solutions**:

1. **Risk Management Settings**:
   - Verify position sizing rules
   - Check stop-loss and take-profit settings
   - Review risk management configuration

2. **Strategy Logic**:
   - Check entry and exit conditions
   - Verify signal generation logic
   - Test with historical data

3. **Market Conditions**:
   - Analyze market volatility
   - Check for extreme market conditions
   - Adjust strategy for current market environment

### System Resource Issues

#### High CPU Usage

**Symptoms**:
- System becomes slow or unresponsive
- High CPU usage reported by task manager

**Possible Causes and Solutions**:

1. **Too Many Worker Processes**:
   - Reduce the number of worker processes
   - Limit concurrent operations

2. **Inefficient Algorithms**:
   - Optimize strategy calculations
   - Reduce data processing frequency
   - Implement caching

3. **Background Tasks**:
   - Check for resource-intensive background tasks
   - Schedule tasks during off-peak hours

#### Memory Leaks

**Symptoms**:
- Increasing memory usage over time
- System becomes slow or crashes after running for a while

**Possible Causes and Solutions**:

1. **Service Restart**:
   - Restart the affected service
   - Implement automatic service restarts

2. **Update Application**:
   - Check for updates that fix memory leaks
   - Apply patches and updates

3. **Limit Resource Usage**:
   - Set memory limits for services
   - Monitor memory usage
   - Implement garbage collection

### Logging and Diagnostics

#### Enabling Debug Logging

To enable debug logging for troubleshooting:

1. Edit the configuration file:
   ```json
   {
     "logging": {
       "level": "DEBUG",
       "service_levels": {
         "auth": "DEBUG",
         "strategy": "DEBUG",
         "data": "DEBUG",
         "trade": "DEBUG",
         "backtest": "DEBUG"
       }
     }
   }
   ```

2. Restart the services

3. Check the log files for detailed information

#### Diagnostic Tools

1. **System Diagnostics**:
   ```bash
   cryptobot --diagnostics
   ```

2. **Service Health Check**:
   ```bash
   cryptobot --health-check
   ```

3. **Database Integrity Check**:
   ```bash
   cryptobot --db-check
   ```

4. **Network Connectivity Test**:
   ```bash
   cryptobot --network-test
   ```

5. **Performance Profiling**:
   ```bash
   cryptobot --profile
   ```

### Getting Support

If you encounter issues that you can't resolve:

1. **Check Documentation**:
   - Review the troubleshooting guide
   - Check for known issues

2. **Community Support**:
   - Post on the community forum
   - Check for similar issues and solutions

3. **Professional Support**:
   - Contact support at support@example.com
   - Provide detailed information about the issue
   - Include logs and diagnostic information