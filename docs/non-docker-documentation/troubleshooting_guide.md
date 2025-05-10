# Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using the non-Docker version of Cryptobot.

## Table of Contents
- [Service Issues](#service-issues)
- [Database Issues](#database-issues)
- [Exchange Connectivity Issues](#exchange-connectivity-issues)
- [Strategy Execution Issues](#strategy-execution-issues)
- [Performance Issues](#performance-issues)
- [Security Issues](#security-issues)
- [Update Issues](#update-issues)
- [Dashboard Issues](#dashboard-issues)
- [Diagnostic Tools](#diagnostic-tools)
- [Getting Support](#getting-support)

## Service Issues

### Service Fails to Start

**Symptoms**:
- Service shows "Failed" status in the launcher
- Error messages in the logs

**Possible Causes and Solutions**:

1. **Port Conflict**:
   - Check if another application is using the same port
   - Change the port in the configuration file
   - Restart the service

   ```bash
   # Check if port is in use (Windows)
   netstat -ano | findstr :8000

   # Check if port is in use (Linux/macOS)
   netstat -tuln | grep 8000
   ```

2. **Database Connection Issues**:
   - Verify database connection settings
   - Check if the database server is running
   - Check database permissions

   ```bash
   # Check SQLite database
   sqlite3 cryptobot.db .tables

   # Check PostgreSQL connection
   psql -U cryptobot -h localhost -d cryptobot -c "SELECT 1"

   # Check MySQL connection
   mysql -u cryptobot -p -h localhost -e "SELECT 1" cryptobot
   ```

3. **Missing Dependencies**:
   - Reinstall the application
   - Check for missing Python packages
   - Install required system libraries

   ```bash
   # Check Python dependencies
   pip list | grep -E "cryptobot|pandas|numpy|sqlalchemy"

   # Reinstall dependencies
   pip install -r requirements.txt
   ```

4. **Configuration Errors**:
   - Check for syntax errors in configuration files
   - Verify configuration values are within valid ranges
   - Reset to default configuration

   ```bash
   # Validate JSON syntax (Windows PowerShell)
   Get-Content config.json | ConvertFrom-Json

   # Validate JSON syntax (Linux/macOS)
   cat config.json | jq
   ```

### Service Crashes After Starting

**Symptoms**:
- Service starts but crashes shortly after
- Error messages in the logs

**Possible Causes and Solutions**:

1. **Memory Issues**:
   - Increase memory allocation
   - Check for memory leaks
   - Reduce the number of worker processes

   ```bash
   # Check memory usage (Windows)
   tasklist /FI "IMAGENAME eq python.exe" /FO LIST

   # Check memory usage (Linux)
   ps -o pid,user,%mem,command ax | grep python

   # Check memory usage (macOS)
   ps -o pid,user,%mem,command ax | grep python
   ```

2. **Unhandled Exceptions**:
   - Check logs for exception details
   - Update to the latest version
   - Apply patches if available

3. **Resource Limitations**:
   - Check disk space
   - Check file descriptors limit
   - Check CPU usage

   ```bash
   # Check disk space (Windows)
   dir

   # Check disk space (Linux/macOS)
   df -h

   # Check file descriptors limit (Linux/macOS)
   ulimit -n
   ```

### Service Communication Issues

**Symptoms**:
- Services cannot communicate with each other
- "Connection refused" errors in logs

**Possible Causes and Solutions**:

1. **Network Configuration**:
   - Verify that all services are running
   - Check service URLs in configuration files
   - Ensure that localhost is used for service communication

   ```json
   {
     "services": {
       "strategy": {
         "auth_url": "http://localhost:8000",
         "data_url": "http://localhost:8002",
         "trade_url": "http://localhost:8003"
       }
     }
   }
   ```

2. **Firewall Issues**:
   - Check firewall settings
   - Allow communication on required ports
   - Disable firewall temporarily for testing

   ```bash
   # Check Windows Firewall
   netsh advfirewall show currentprofile

   # Check Linux firewall (iptables)
   sudo iptables -L

   # Check macOS firewall
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
   ```

3. **DNS Issues**:
   - Check hosts file
   - Verify DNS resolution
   - Use IP addresses instead of hostnames

## Database Issues

### Database Connection Errors

**Symptoms**:
- "Could not connect to database" errors
- Services fail to start

**Possible Causes and Solutions**:

1. **Database Server Not Running**:
   - Start the database server
   - Check database server logs
   - Restart the database server

   ```bash
   # Start PostgreSQL (Windows)
   net start postgresql

   # Start PostgreSQL (Linux)
   sudo systemctl start postgresql

   # Start PostgreSQL (macOS)
   brew services start postgresql
   ```

2. **Incorrect Connection Settings**:
   - Verify host, port, username, and password
   - Check database name
   - Test connection with a database client

   ```bash
   # Test PostgreSQL connection
   psql -U cryptobot -h localhost -d cryptobot -c "SELECT 1"

   # Test MySQL connection
   mysql -u cryptobot -p -h localhost -e "SELECT 1" cryptobot
   ```

3. **Authentication Issues**:
   - Check database user permissions
   - Reset database user password
   - Create a new database user

   ```bash
   # PostgreSQL: Reset password
   sudo -u postgres psql -c "ALTER USER cryptobot WITH PASSWORD 'new-password';"

   # MySQL: Reset password
   mysql -u root -p -e "ALTER USER 'cryptobot'@'localhost' IDENTIFIED BY 'new-password';"
   ```

### Database Performance Issues

**Symptoms**:
- Slow response times
- High CPU or disk usage
- Timeout errors

**Possible Causes and Solutions**:

1. **Missing Indexes**:
   - Add indexes to frequently queried columns
   - Optimize query patterns
   - Analyze query performance

   ```sql
   -- PostgreSQL: Add index
   CREATE INDEX idx_trades_timestamp ON trades(timestamp);

   -- MySQL: Add index
   CREATE INDEX idx_trades_timestamp ON trades(timestamp);

   -- SQLite: Add index
   CREATE INDEX idx_trades_timestamp ON trades(timestamp);
   ```

2. **Database Growth**:
   - Implement data retention policies
   - Archive old data
   - Increase storage capacity

   ```sql
   -- Delete old data
   DELETE FROM trades WHERE timestamp < NOW() - INTERVAL '90 days';

   -- Archive old data
   INSERT INTO trades_archive SELECT * FROM trades WHERE timestamp < NOW() - INTERVAL '90 days';
   DELETE FROM trades WHERE timestamp < NOW() - INTERVAL '90 days';
   ```

3. **Connection Pool Exhaustion**:
   - Increase pool size
   - Reduce query duration
   - Check for connection leaks

   ```json
   {
     "database": {
       "pool_size": 20,
       "max_overflow": 30,
       "pool_recycle": 3600,
       "pool_timeout": 30
     }
   }
   ```

### Database Corruption

**Symptoms**:
- "Database is corrupted" errors
- Unexpected query results
- Database crashes

**Possible Causes and Solutions**:

1. **SQLite Corruption**:
   - Run integrity check
   - Restore from backup
   - Rebuild the database

   ```bash
   # Check SQLite integrity
   sqlite3 cryptobot.db "PRAGMA integrity_check;"

   # Backup and restore
   sqlite3 cryptobot.db .dump > backup.sql
   sqlite3 new_cryptobot.db < backup.sql
   ```

2. **PostgreSQL Corruption**:
   - Run database check
   - Repair database
   - Restore from backup

   ```bash
   # Check PostgreSQL database
   sudo -u postgres pg_dump -F c -v -d cryptobot > backup.dump
   sudo -u postgres dropdb cryptobot
   sudo -u postgres createdb cryptobot
   sudo -u postgres pg_restore -v -d cryptobot backup.dump
   ```

3. **MySQL Corruption**:
   - Run database check
   - Repair tables
   - Restore from backup

   ```bash
   # Check and repair MySQL tables
   mysqlcheck -u cryptobot -p --auto-repair --check cryptobot

   # Backup and restore
   mysqldump -u cryptobot -p cryptobot > backup.sql
   mysql -u cryptobot -p cryptobot < backup.sql
   ```

## Exchange Connectivity Issues

### Unable to Connect to Exchange

**Symptoms**:
- "Could not connect to exchange" errors
- Timeout errors
- API key errors

**Possible Causes and Solutions**:

1. **API Key Issues**:
   - Verify API key and secret
   - Check API key permissions
   - Generate new API keys

   ```bash
   # Test API key (using curl)
   curl -H "X-MBX-APIKEY: your-api-key" -X GET "https://api.binance.com/api/v3/account"
   ```

2. **Network Issues**:
   - Check network connectivity
   - Verify firewall rules
   - Check for IP restrictions

   ```bash
   # Test connectivity
   ping api.binance.com

   # Check DNS resolution
   nslookup api.binance.com

   # Trace route
   tracert api.binance.com  # Windows
   traceroute api.binance.com  # Linux/macOS
   ```

3. **Exchange Maintenance**:
   - Check exchange status page
   - Wait for maintenance to complete
   - Switch to a different exchange

4. **API Endpoint Changes**:
   - Update to the latest version
   - Check for API endpoint changes
   - Update API endpoint configuration

### Rate Limiting

**Symptoms**:
- "Rate limit exceeded" errors
- Temporary connection failures
- Delayed responses

**Possible Causes and Solutions**:

1. **Too Many Requests**:
   - Reduce request frequency
   - Implement request throttling
   - Increase rate limit settings if possible

   ```json
   {
     "data": {
       "rate_limiting": {
         "enabled": true,
         "max_requests_per_minute": {
           "binance": 600,  # Reduced from 1200
           "coinbase": 150,  # Reduced from 300
           "kraken": 300  # Reduced from 600
         }
       }
     }
   }
   ```

2. **Multiple Instances**:
   - Ensure only one instance is running
   - Coordinate API usage across instances
   - Use a shared rate limiter

3. **Weight-Based Rate Limits**:
   - Optimize API calls to reduce weight
   - Batch requests where possible
   - Cache frequently accessed data

### Order Execution Issues

**Symptoms**:
- Orders not executed
- Unexpected order status
- Order execution delays

**Possible Causes and Solutions**:

1. **Insufficient Funds**:
   - Check account balance
   - Verify available funds
   - Reduce order size

2. **Market Conditions**:
   - Check for high volatility
   - Verify market liquidity
   - Adjust order parameters

3. **Exchange Restrictions**:
   - Check minimum order size
   - Verify trading pair restrictions
   - Check for trading pair delisting

4. **Order Validation Issues**:
   - Check order parameters
   - Verify price precision
   - Check quantity precision

## Strategy Execution Issues

### Strategy Not Generating Signals

**Symptoms**:
- No trading signals generated
- No trades executed
- Strategy appears inactive

**Possible Causes and Solutions**:

1. **Configuration Issues**:
   - Verify strategy parameters
   - Check for invalid settings
   - Reset to default parameters

   ```json
   {
     "strategies": {
       "mean_reversion": {
         "enabled": true,
         "pairs": ["BTC/USD", "ETH/USD"],
         "timeframe": "1h",
         "parameters": {
           "window": 20,
           "std_dev": 2.0,
           "take_profit": 0.05,
           "stop_loss": 0.02
         }
       }
     }
   }
   ```

2. **Data Issues**:
   - Check for missing or invalid market data
   - Verify data source connectivity
   - Refresh historical data

   ```bash
   # Check data availability
   curl -X GET "http://localhost:8002/api/v1/data/ohlcv?symbol=BTC/USD&timeframe=1h&limit=100"
   ```

3. **Logic Issues**:
   - Review strategy logic
   - Check for conditional errors
   - Test with different market conditions

4. **Market Conditions**:
   - Check if current market conditions match strategy criteria
   - Adjust strategy parameters for current market conditions
   - Consider using a different strategy

### Unexpected Trading Behavior

**Symptoms**:
- Trades executed at unexpected times
- Incorrect position sizing
- Unexpected entry or exit points

**Possible Causes and Solutions**:

1. **Risk Management Settings**:
   - Verify position sizing rules
   - Check stop-loss and take-profit settings
   - Review risk management configuration

   ```json
   {
     "trade": {
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

2. **Strategy Logic**:
   - Check entry and exit conditions
   - Verify signal generation logic
   - Test with historical data

3. **Time Zone Issues**:
   - Check system time zone
   - Verify exchange time zone
   - Ensure consistent time zone usage

   ```bash
   # Check system time zone
   date

   # Set system time zone (Linux)
   sudo timedatectl set-timezone UTC
   ```

### Backtest Results Differ from Live Trading

**Symptoms**:
- Backtest results show different performance than live trading
- Unexpected discrepancies in trade execution
- Different trade timing or sizing

**Possible Causes and Solutions**:

1. **Slippage and Fees**:
   - Verify fee configuration in backtest
   - Add realistic slippage to backtest
   - Account for spread in backtest

   ```json
   {
     "backtest": {
       "slippage_percent": 0.1,
       "fee_percent": 0.1,
       "include_spread": true
     }
   }
   ```

2. **Data Quality**:
   - Use the same data source for backtest and live trading
   - Check for data gaps or anomalies
   - Verify data accuracy

3. **Market Impact**:
   - Account for market impact in backtest
   - Adjust position sizing based on liquidity
   - Consider using realistic fill models

## Performance Issues

### High CPU Usage

**Symptoms**:
- System becomes slow or unresponsive
- High CPU usage reported by task manager
- Services taking longer to respond

**Possible Causes and Solutions**:

1. **Too Many Worker Processes**:
   - Reduce the number of worker processes
   - Limit concurrent operations
   - Adjust process configuration

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

2. **Inefficient Algorithms**:
   - Optimize strategy calculations
   - Reduce data processing frequency
   - Implement caching

   ```json
   {
     "cache": {
       "enabled": true,
       "type": "redis",
       "ttl_seconds": 3600
     }
   }
   ```

3. **Background Tasks**:
   - Check for resource-intensive background tasks
   - Schedule tasks during off-peak hours
   - Limit the scope of background tasks

### Memory Leaks

**Symptoms**:
- Increasing memory usage over time
- System becomes slow or crashes after running for a while
- Out of memory errors

**Possible Causes and Solutions**:

1. **Service Restart**:
   - Restart the affected service
   - Implement automatic service restarts
   - Monitor memory usage

   ```bash
   # Restart service (Windows)
   net stop cryptobot_auth
   net start cryptobot_auth

   # Restart service (Linux)
   sudo systemctl restart cryptobot-auth

   # Restart service (macOS)
   brew services restart cryptobot-auth
   ```

2. **Update Application**:
   - Check for updates that fix memory leaks
   - Apply patches and updates
   - Update dependencies

3. **Limit Resource Usage**:
   - Set memory limits for services
   - Monitor memory usage
   - Implement garbage collection

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

### Disk I/O Bottlenecks

**Symptoms**:
- High disk activity
- Slow file operations
- Database operations taking longer than usual

**Possible Causes and Solutions**:

1. **Database Optimization**:
   - Add indexes to frequently queried columns
   - Optimize query patterns
   - Use connection pooling

2. **Logging Volume**:
   - Reduce log level
   - Implement log rotation
   - Move logs to a separate disk

   ```json
   {
     "logging": {
       "level": "INFO",  # Change from DEBUG to INFO
       "max_size_mb": 10,
       "backup_count": 5
     }
   }
   ```

3. **Disk Space Issues**:
   - Clean up temporary files
   - Implement data retention policies
   - Increase disk space

   ```bash
   # Check disk space (Windows)
   dir

   # Check disk space (Linux/macOS)
   df -h

   # Clean up temporary files (Windows)
   del /q %TEMP%\*

   # Clean up temporary files (Linux/macOS)
   rm -rf /tmp/cryptobot-*
   ```

## Security Issues

### Authentication Issues

**Symptoms**:
- Unable to log in
- "Invalid credentials" errors
- Session expiration issues

**Possible Causes and Solutions**:

1. **Incorrect Credentials**:
   - Verify username and password
   - Reset password if necessary
   - Check for caps lock or keyboard layout issues

2. **JWT Issues**:
   - Check JWT secret key
   - Verify JWT expiration settings
   - Clear browser cookies and cache

   ```json
   {
     "auth": {
       "jwt_secret": "your-secret-key",
       "jwt_algorithm": "HS256",
       "access_token_expire_minutes": 30,
       "refresh_token_expire_days": 7
     }
   }
   ```

3. **Two-Factor Authentication Issues**:
   - Verify time synchronization
   - Check TOTP configuration
   - Use backup codes if available

### API Key Security

**Symptoms**:
- Unauthorized API usage
- Unexpected trades or withdrawals
- API key revoked by exchange

**Possible Causes and Solutions**:

1. **Compromised API Keys**:
   - Revoke and regenerate API keys
   - Check for unauthorized access
   - Enable IP restrictions

2. **Insufficient Permissions**:
   - Check API key permissions
   - Update API key permissions
   - Create new API keys with appropriate permissions

3. **API Key Rotation**:
   - Implement regular API key rotation
   - Monitor API key usage
   - Use different API keys for different purposes

   ```json
   {
     "auth": {
       "api_key_rotation": {
         "enabled": true,
         "rotation_days": 90,
         "grace_period_days": 7
       }
     }
   }
   ```

### Data Security

**Symptoms**:
- Unauthorized data access
- Data corruption or loss
- Privacy concerns

**Possible Causes and Solutions**:

1. **Insufficient Access Controls**:
   - Implement proper authentication and authorization
   - Use role-based access control
   - Audit access to sensitive data

2. **Unencrypted Data**:
   - Enable data encryption
   - Use secure storage for sensitive data
   - Implement transport layer security

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

3. **Insecure Configurations**:
   - Use secure default settings
   - Implement security best practices
   - Regularly audit security configurations

## Update Issues

### Update Fails to Install

**Symptoms**:
- Update process fails
- Error messages during update
- Application remains on old version

**Possible Causes and Solutions**:

1. **Insufficient Permissions**:
   - Run the updater with administrator privileges
   - Check file permissions
   - Close all running instances of the application

2. **Disk Space Issues**:
   - Check available disk space
   - Clean up temporary files
   - Free up disk space

3. **Corrupted Download**:
   - Clear download cache
   - Re-download the update
   - Verify download integrity

### Application Crashes After Update

**Symptoms**:
- Application crashes immediately after update
- Services fail to start after update
- Unexpected errors after update

**Possible Causes and Solutions**:

1. **Incompatible Configuration**:
   - Reset to default configuration
   - Update configuration to match new version
   - Check for configuration format changes

2. **Missing Dependencies**:
   - Install required dependencies
   - Update dependencies to compatible versions
   - Check for dependency conflicts

3. **Rollback to Previous Version**:
   - Use the rollback feature
   - Restore from backup
   - Reinstall the previous version

   ```bash
   # Rollback using the Quick Start Launcher
   # 1. Open the CryptoBot Quick Start Launcher
   # 2. Click "Check for Updates"
   # 3. In the update dialog, click "Rollback"
   ```

## Dashboard Issues

### Dashboard Not Loading

**Symptoms**:
- Dashboard shows blank page
- "Cannot connect to server" errors
- Dashboard loads partially

**Possible Causes and Solutions**:

1. **Service Not Running**:
   - Verify that all services are running
   - Start missing services
   - Check service status

2. **Browser Issues**:
   - Clear browser cache and cookies
   - Try a different browser
   - Disable browser extensions

3. **Network Issues**:
   - Check network connectivity
   - Verify firewall rules
   - Check for proxy settings

### Dashboard Shows Incorrect Data

**Symptoms**:
- Dashboard shows outdated information
- Inconsistent data across different sections
- Missing data in dashboard

**Possible Causes and Solutions**:

1. **Caching Issues**:
   - Clear browser cache
   - Refresh the dashboard
   - Adjust cache settings

2. **Data Synchronization Issues**:
   - Check data service connectivity
   - Verify database consistency
   - Restart data service

3. **Rendering Issues**:
   - Check for JavaScript errors
   - Update browser to latest version
   - Disable conflicting browser extensions

## Diagnostic Tools

### Enabling Debug Logging

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

3. Check the log files for detailed information:
   - **Windows**: `%APPDATA%\CryptoBot\logs\`
   - **macOS**: `~/Library/Logs/CryptoBot/`
   - **Linux**: `/var/log/cryptobot/`

### Built-in Diagnostic Tools

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

### Log Analysis

1. **Viewing Logs**:
   ```bash
   # Windows PowerShell
   Get-Content -Path "%APPDATA%\CryptoBot\logs\cryptobot.log" -Tail 100

   # Linux/macOS
   tail -n 100 /var/log/cryptobot/cryptobot.log
   ```

2. **Searching Logs**:
   ```bash
   # Windows PowerShell
   Select-String -Path "%APPDATA%\CryptoBot\logs\cryptobot.log" -Pattern "error"

   # Linux/macOS
   grep "error" /var/log/cryptobot/cryptobot.log
   ```

3. **Analyzing Log Patterns**:
   ```bash
   # Windows PowerShell
   Select-String -Path "%APPDATA%\CryptoBot\logs\cryptobot.log" -Pattern "error|warning|critical" | Measure-Object

   # Linux/macOS
   grep -E "error|warning|critical" /var/log/cryptobot/cryptobot.log | wc -l
   ```

## Getting Support

If you encounter issues that you can't resolve:

1. **Check Documentation**:
   - Review this troubleshooting guide
   - Check the [administrator guide](administrator-guide.md)
   - Check for known issues in the [release notes](https://github.com/yourusername/cryptobot/releases)

2. **Community Support**:
   - Post on the community forum
   - Check for similar issues and solutions
   - Share your logs and configuration (with sensitive information removed)

3. **Professional Support**:
   - Contact support at support@example.com
   - Provide detailed information about the issue:
     - System information (OS, hardware, etc.)
     - CryptoBot version
     - Steps to reproduce the issue
     - Error messages and logs
     - Configuration files (with sensitive information removed)
   - Follow up with additional information if requested