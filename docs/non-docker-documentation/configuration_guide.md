# Configuration Guide

This guide provides detailed instructions for configuring the non-Docker version of Cryptobot, including service configuration, database configuration, logging, and more.

## Table of Contents
- [Configuration Overview](#configuration-overview)
- [Configuration Files](#configuration-files)
- [Environment Variables](#environment-variables)
- [Service Configuration](#service-configuration)
- [Database Configuration](#database-configuration)
- [Logging Configuration](#logging-configuration)
- [Network Configuration](#network-configuration)
- [Security Configuration](#security-configuration)
- [Notification Configuration](#notification-configuration)
- [Exchange Configuration](#exchange-configuration)
- [Strategy Configuration](#strategy-configuration)
- [Configuration Best Practices](#configuration-best-practices)

## Configuration Overview

Cryptobot uses a combination of configuration files and environment variables to configure its behavior. The configuration is organized hierarchically, with global settings and service-specific settings.

### Configuration Hierarchy

1. **Default Configuration**: Built-in default settings
2. **Global Configuration**: Settings that apply to all services
3. **Environment-Specific Configuration**: Settings for specific environments (dev, test, stage, prod)
4. **Service-Specific Configuration**: Settings for individual services
5. **Environment Variables**: Override settings from configuration files
6. **Command-Line Arguments**: Override settings from environment variables

## Configuration Files

The main configuration file is located at:

- **Windows**: `%APPDATA%\CryptoBot\config.json`
- **macOS**: `~/Library/Application Support/CryptoBot/config.json`
- **Linux**: `/etc/cryptobot/config.json`

Service-specific configuration files are located in the `config` directory:

- `config/auth.json`: Authentication Service configuration
- `config/strategy.json`: Strategy Service configuration
- `config/data.json`: Data Service configuration
- `config/trade.json`: Trade Service configuration
- `config/backtest.json`: Backtest Service configuration

### Configuration File Format

Configuration files use JSON format:

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
      "port": 8001
    }
  },
  "database": {
    "url": "sqlite:///cryptobot.db"
  },
  "logging": {
    "level": "INFO",
    "file": "cryptobot.log"
  }
}
```

## Environment Variables

You can override configuration settings using environment variables:

```bash
# Windows
set CRYPTOBOT_ENV=production
set CRYPTOBOT_DB_URL=sqlite:///cryptobot.db
set CRYPTOBOT_REDIS_HOST=localhost
set CRYPTOBOT_REDIS_PORT=6379
set CRYPTOBOT_LOG_LEVEL=INFO

# Linux/macOS
export CRYPTOBOT_ENV=production
export CRYPTOBOT_DB_URL=sqlite:///cryptobot.db
export CRYPTOBOT_REDIS_HOST=localhost
export CRYPTOBOT_REDIS_PORT=6379
export CRYPTOBOT_LOG_LEVEL=INFO
```

### Environment Variable Naming Convention

Environment variables use the following naming convention:

- Prefix: `CRYPTOBOT_`
- Section: Uppercase section name (e.g., `DB`, `REDIS`, `LOG`)
- Setting: Uppercase setting name (e.g., `URL`, `HOST`, `PORT`, `LEVEL`)

For example:
- `CRYPTOBOT_DB_URL` corresponds to `database.url` in the configuration file
- `CRYPTOBOT_REDIS_HOST` corresponds to `redis.host` in the configuration file
- `CRYPTOBOT_LOG_LEVEL` corresponds to `logging.level` in the configuration file

## Service Configuration

### Authentication Service

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

### Strategy Service

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

### Data Service

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

### Trade Service

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

### Backtest Service

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

## Database Configuration

Cryptobot supports multiple database backends:

### SQLite (Default)

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

### PostgreSQL

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

### MySQL/MariaDB

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

## Logging Configuration

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

## Network Configuration

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

## Security Configuration

### Authentication and Authorization

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
    },
    "two_factor": {
      "enabled": true,
      "type": "totp",
      "issuer": "CryptoBot",
      "digits": 6,
      "period": 30,
      "algorithm": "SHA1"
    },
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

### TLS Configuration

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

### Data Encryption

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

## Notification Configuration

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

## Exchange Configuration

Exchange configuration is typically managed through the dashboard, but you can also configure exchanges in the configuration file:

```json
{
  "exchanges": {
    "binance": {
      "enabled": true,
      "api_key": "your-api-key",
      "api_secret": "your-api-secret",
      "testnet": false,
      "timeout_seconds": 10,
      "rate_limiting": {
        "enabled": true,
        "max_requests_per_minute": 1200
      }
    },
    "kraken": {
      "enabled": true,
      "api_key": "your-api-key",
      "api_secret": "your-api-secret",
      "timeout_seconds": 10,
      "rate_limiting": {
        "enabled": true,
        "max_requests_per_minute": 600
      }
    }
  }
}
```

## Strategy Configuration

Strategy configuration is typically managed through the dashboard, but you can also configure strategies in the configuration file:

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
    },
    "breakout": {
      "enabled": true,
      "pairs": ["BTC/USD", "ETH/USD"],
      "timeframe": "4h",
      "parameters": {
        "breakout_periods": 20,
        "atr_periods": 14,
        "atr_multiplier": 2.0
      }
    }
  }
}
```

## Configuration Best Practices

### Security Best Practices

1. **Secure Secrets**:
   - Don't store sensitive information (API keys, passwords) in plain text
   - Use environment variables for secrets
   - Consider using a secrets management solution

2. **Restrict Access**:
   - Set appropriate file permissions for configuration files
   - Limit access to configuration directories

3. **Use TLS**:
   - Enable TLS for all services
   - Use strong ciphers and protocols
   - Keep certificates up to date

### Performance Best Practices

1. **Database Connection Pooling**:
   - Configure appropriate pool sizes based on your hardware
   - Set reasonable timeouts and recycling intervals

2. **Caching**:
   - Enable caching for frequently accessed data
   - Configure appropriate TTL values

3. **Rate Limiting**:
   - Configure rate limiting to avoid hitting exchange limits
   - Set reasonable limits for API endpoints

### Maintenance Best Practices

1. **Configuration Backups**:
   - Regularly back up configuration files
   - Store backups securely

2. **Version Control**:
   - Consider using version control for configuration files
   - Document changes to configuration

3. **Environment-Specific Configuration**:
   - Use different configurations for different environments
   - Test configuration changes in non-production environments first