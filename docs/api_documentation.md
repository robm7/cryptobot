# Cryptobot API Documentation

## Overview

The Cryptobot API provides programmatic access to the Cryptobot trading system. It allows you to manage strategies, execute trades, access market data, and monitor system status.

## Base URL

All API endpoints are relative to the base URL:

```
http://localhost:8000/api/v1
```

For production deployments, replace `localhost` with your server's domain name or IP address.

## Authentication

### API Key Authentication

Most API endpoints require authentication using an API key. To authenticate, include the API key in the `X-API-Key` header:

```
X-API-Key: your_api_key_here
```

### JWT Authentication

Some endpoints support JWT authentication. To authenticate, include the JWT token in the `Authorization` header:

```
Authorization: Bearer your_jwt_token_here
```

### Obtaining API Keys

API keys can be obtained through the Cryptobot dashboard:

1. Navigate to the **API Keys** section
2. Click **Create API Key**
3. Configure permissions and restrictions
4. Save the API key securely

### API Key Rotation

API keys are automatically rotated every 90 days. When a key is rotated:

1. A new key is generated
2. The old key enters a grace period (24 hours by default)
3. After the grace period, the old key is invalidated

You can also manually rotate keys through the dashboard or API.

## Rate Limiting

API requests are rate-limited to prevent abuse. The default limits are:

- 60 requests per minute per IP address
- 1000 requests per hour per API key

Rate limit headers are included in all API responses:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1620000000
```

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

## Error Handling

The API uses standard HTTP status codes to indicate success or failure:

- `200 OK`: The request was successful
- `201 Created`: The resource was created successfully
- `400 Bad Request`: The request was invalid
- `401 Unauthorized`: Authentication failed
- `403 Forbidden`: The authenticated user doesn't have permission
- `404 Not Found`: The requested resource doesn't exist
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: An error occurred on the server

Error responses include a JSON body with details:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Invalid request parameters",
    "details": {
      "symbol": "Symbol is required"
    }
  }
}
```

## Pagination

List endpoints support pagination using the `page` and `limit` query parameters:

```
GET /api/v1/strategies?page=2&limit=10
```

Paginated responses include metadata:

```json
{
  "data": [...],
  "pagination": {
    "total": 100,
## Endpoints

### Authentication Service

#### Get Authentication Token

```
POST /auth/token
```

Obtain a JWT token for authentication.

**Request Body:**

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### Refresh Token

```
POST /auth/refresh
```

Refresh an expired JWT token.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```
### API Key Management

#### List API Keys

```
GET /api-keys
```

List all API keys for the authenticated user.

**Response:**

```json
{
  "keys": [
    {
      "id": "key_123456789",
      "description": "Trading Bot",
      "exchange": "binance",
      "status": "active",
      "version": 1,
      "created_at": "2025-01-01T00:00:00Z",
      "expires_at": "2025-04-01T00:00:00Z",
      "permissions": ["read", "trade"]
    }
  ],
  "total": 1,
  "active": 1,
  "rotating": 0,
  "expiring_soon": 0
}
```

#### Create API Key

```
POST /api-keys
```

Create a new API key.

**Request Body:**

```json
{
  "description": "Trading Bot",
  "exchange": "binance",
  "is_test": false,
  "expiry_days": 90
}
```

**Response:**

```json
{
  "id": "key_123456789",
  "key": "your_api_key_here",
  "description": "Trading Bot",
  "exchange": "binance",
  "status": "active",
  "version": 1,
  "created_at": "2025-01-01T00:00:00Z",
  "expires_at": "2025-04-01T00:00:00Z",
  "permissions": ["read", "trade"]
}
```

#### Rotate API Key

```
POST /api-keys/rotate
```

Rotate an API key.

**Request Body:**

```json
{
  "key_id": "key_123456789",
  "grace_period_hours": 24
}
```

**Response:**

```json
{
  "id": "key_987654321",
  "key": "your_new_api_key_here",
  "description": "Trading Bot",
  "exchange": "binance",
  "status": "active",
  "version": 2,
  "created_at": "2025-01-01T00:00:00Z",
  "expires_at": "2025-04-01T00:00:00Z",
  "permissions": ["read", "trade"],
  "previous_key_id": "key_123456789"
}
```

#### Revoke API Key

```
POST /api-keys/revoke
```

Revoke an API key.

**Request Body:**

```json
{
  "key_id": "key_123456789",
  "reason": "No longer needed"
}
```

**Response:**
### Strategy Management

#### List Strategies

```
GET /strategies
```

List all strategies for the authenticated user.

**Query Parameters:**

- `status` (optional): Filter by status (active, inactive, all)
- `exchange` (optional): Filter by exchange
- `page` (optional): Page number for pagination
- `limit` (optional): Number of items per page

**Response:**

```json
{
  "data": [
    {
      "id": "strategy_123456789",
      "name": "Mean Reversion",
      "description": "Mean reversion strategy for BTC/USD",
      "status": "active",
      "exchange": "binance",
      "symbol": "BTC/USD",
      "timeframe": "1h",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z",
      "performance": {
        "total_return": 15.5,
        "win_rate": 65.0,
        "sharpe_ratio": 1.2,
        "drawdown": 5.0
      }
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 10,
    "pages": 1
  }
}
```

#### Get Strategy

```
GET /strategies/{strategy_id}
```

Get details for a specific strategy.

**Response:**

```json
{
  "id": "strategy_123456789",
  "name": "Mean Reversion",
  "description": "Mean reversion strategy for BTC/USD",
  "status": "active",
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "parameters": {
    "lookback_period": 20,
    "entry_threshold": 2.0,
    "exit_threshold": 0.5,
    "stop_loss": 2.0,
    "take_profit": 5.0
  },
  "performance": {
    "total_return": 15.5,
    "win_rate": 65.0,
    "sharpe_ratio": 1.2,
    "drawdown": 5.0,
    "trades": 100,
    "winning_trades": 65,
    "losing_trades": 35
  }
}
```

#### Create Strategy

```
POST /strategies
```

Create a new strategy.

**Request Body:**

```json
{
  "name": "Mean Reversion",
  "description": "Mean reversion strategy for BTC/USD",
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "strategy_type": "mean_reversion",
  "parameters": {
    "lookback_period": 20,
    "entry_threshold": 2.0,
    "exit_threshold": 0.5,
    "stop_loss": 2.0,
    "take_profit": 5.0
  }
}
```

**Response:**

```json
{
  "id": "strategy_123456789",
  "name": "Mean Reversion",
  "description": "Mean reversion strategy for BTC/USD",
  "status": "inactive",
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "parameters": {
    "lookback_period": 20,
    "entry_threshold": 2.0,
    "exit_threshold": 0.5,
    "stop_loss": 2.0,
    "take_profit": 5.0
  }
}
```

#### Update Strategy

```
PUT /strategies/{strategy_id}
```

Update an existing strategy.

**Request Body:**

```json
{
  "name": "Mean Reversion",
  "description": "Updated mean reversion strategy for BTC/USD",
  "parameters": {
    "lookback_period": 30,
    "entry_threshold": 2.5,
    "exit_threshold": 0.7,
    "stop_loss": 2.5,
    "take_profit": 6.0
  }
}
```

**Response:**

```json
{
  "id": "strategy_123456789",
  "name": "Mean Reversion",
  "description": "Updated mean reversion strategy for BTC/USD",
  "status": "inactive",
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T01:00:00Z",
  "parameters": {
    "lookback_period": 30,
    "entry_threshold": 2.5,
    "exit_threshold": 0.7,
    "stop_loss": 2.5,
    "take_profit": 6.0
  }
}
```

#### Delete Strategy

```
DELETE /strategies/{strategy_id}
```

Delete a strategy.

**Response:**

```json
{
  "detail": "Strategy deleted successfully"
}
```

#### Start Strategy

```
POST /strategies/{strategy_id}/start
```

Start a strategy.

**Request Body:**

```json
{
  "capital_allocation": 1000.0,
  "max_positions": 5
}
```

**Response:**

```json
{
  "id": "strategy_123456789",
  "name": "Mean Reversion",
  "status": "active",
  "started_at": "2025-01-01T00:00:00Z",
  "capital_allocation": 1000.0,
  "max_positions": 5
}
```

#### Stop Strategy

```
POST /strategies/{strategy_id}/stop
```

Stop a strategy.

**Request Body:**

```json
### Backtesting

#### Run Backtest

```
POST /backtest
```

Run a backtest for a strategy.

**Request Body:**

```json
{
  "strategy_id": "strategy_123456789",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 10000.0,
  "parameters": {
    "lookback_period": 20,
    "entry_threshold": 2.0,
    "exit_threshold": 0.5,
    "stop_loss": 2.0,
    "take_profit": 5.0
  }
}
```

**Response:**

```json
{
  "backtest_id": "backtest_123456789",
  "strategy_id": "strategy_123456789",
  "status": "running",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 10000.0,
  "estimated_completion_time": "2025-01-01T00:05:00Z"
}
```

#### Get Backtest Status

```
GET /backtest/{backtest_id}
```

Get the status of a backtest.

**Response:**

```json
{
  "backtest_id": "backtest_123456789",
  "strategy_id": "strategy_123456789",
  "status": "completed",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 10000.0,
  "completion_time": "2025-01-01T00:05:00Z",
  "progress": 100
}
```

#### Get Backtest Results

```
GET /backtest/{backtest_id}/results
```

Get the results of a completed backtest.

**Response:**

```json
{
  "backtest_id": "backtest_123456789",
  "strategy_id": "strategy_123456789",
  "status": "completed",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "initial_capital": 10000.0,
  "final_capital": 11550.0,
  "total_return": 15.5,
  "annualized_return": 15.5,
  "sharpe_ratio": 1.2,
  "sortino_ratio": 1.8,
  "max_drawdown": 5.0,
  "win_rate": 65.0,
  "profit_factor": 1.8,
  "trades": 100,
  "winning_trades": 65,
  "losing_trades": 35,
  "average_win": 2.5,
  "average_loss": 1.2,
  "largest_win": 8.0,
  "largest_loss": 2.0,
  "equity_curve": [
    {"timestamp": "2024-01-01T00:00:00Z", "equity": 10000.0},
    {"timestamp": "2024-01-02T00:00:00Z", "equity": 10050.0},
    // ... more data points ...
    {"timestamp": "2024-12-31T23:59:59Z", "equity": 11550.0}
  ],
  "monthly_returns": [
    {"month": "2024-01", "return": 2.5},
    {"month": "2024-02", "return": 1.8},
    // ... more months ...
    {"month": "2024-12", "return": 1.2}
  ],
  "trades_list": [
    {
      "id": "trade_123456789",
      "symbol": "BTC/USD",
      "side": "buy",
      "entry_price": 50000.0,
      "exit_price": 52500.0,
      "entry_time": "2024-01-05T10:00:00Z",
      "exit_time": "2024-01-07T14:00:00Z",
      "quantity": 0.1,
      "profit_loss": 250.0,
      "profit_loss_percent": 5.0,
      "exit_reason": "take_profit"
    },
    // ... more trades ...
  ]
}
```

#### Cancel Backtest

### Market Data

#### Get Market Data

```
GET /data/market/{exchange}/{symbol}
```

Get market data for a symbol.

**Query Parameters:**

- `timeframe` (required): Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
- `start` (optional): Start timestamp (ISO 8601)
- `end` (optional): End timestamp (ISO 8601)
- `limit` (optional): Number of candles to return

**Response:**

```json
{
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timeframe": "1h",
  "data": [
    {
      "timestamp": "2025-01-01T00:00:00Z",
      "open": 50000.0,
      "high": 50500.0,
      "low": 49800.0,
      "close": 50200.0,
      "volume": 100.5
    },
    // ... more candles ...
  ]
}
```

#### Get Order Book

```
GET /data/orderbook/{exchange}/{symbol}
```

Get order book for a symbol.

**Query Parameters:**

- `depth` (optional): Order book depth (default: 10)

**Response:**

```json
{
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timestamp": "2025-01-01T00:00:00Z",
  "bids": [
    [50000.0, 1.5],
    [49900.0, 2.0],
    // ... more bids ...
  ],
  "asks": [
    [50100.0, 1.0],
    [50200.0, 2.5],
    // ... more asks ...
  ]
}
```

#### Get Ticker

```
GET /data/ticker/{exchange}/{symbol}
```

Get ticker for a symbol.

**Response:**

```json
{
### Trade Execution

#### Execute Order

```
POST /trade/execute
```

Execute a trade order.

**Request Body:**

```json
{
  "exchange": "binance",
  "symbol": "BTC/USD",
  "side": "buy",
  "type": "limit",
  "quantity": 0.1,
  "price": 50000.0,
  "time_in_force": "GTC",
  "strategy_id": "strategy_123456789"
}
```

**Response:**

```json
{
  "order_id": "order_123456789",
  "exchange": "binance",
  "symbol": "BTC/USD",
  "side": "buy",
  "type": "limit",
  "quantity": 0.1,
  "price": 50000.0,
  "status": "open",
  "created_at": "2025-01-01T00:00:00Z"
}
```

#### Get Order Status

```
GET /trade/order/{order_id}
```

Get the status of an order.

**Response:**

```json
{
  "order_id": "order_123456789",
  "exchange": "binance",
  "symbol": "BTC/USD",
  "side": "buy",
  "type": "limit",
  "quantity": 0.1,
  "price": 50000.0,
  "status": "filled",
  "filled": 0.1,
  "remaining": 0.0,
  "average_price": 50000.0,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:01:00Z"
}
```

#### Cancel Order

```
DELETE /trade/order/{order_id}
```

Cancel an open order.

**Response:**

```json
{
  "order_id": "order_123456789",
  "status": "canceled",
  "canceled_at": "2025-01-01T00:02:00Z"
}
```

#### List Open Orders

```
GET /trade/orders/open
```

List all open orders.

**Query Parameters:**

- `exchange` (optional): Filter by exchange
- `symbol` (optional): Filter by symbol
- `strategy_id` (optional): Filter by strategy

**Response:**

```json
{
  "data": [
    {
      "order_id": "order_123456789",
      "exchange": "binance",
      "symbol": "BTC/USD",
      "side": "buy",
      "type": "limit",
      "quantity": 0.1,
      "price": 50000.0,
      "status": "open",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 10,
    "pages": 1
  }
}
```

#### List Order History

```
GET /trade/orders/history
```
### Portfolio Management

#### Get Portfolio

```
GET /portfolio
```

Get portfolio information.

**Response:**

```json
{
  "total_value": 15000.0,
  "base_currency": "USD",
  "last_updated": "2025-01-01T00:00:00Z",
  "assets": [
    {
      "asset": "BTC",
      "free": 0.5,
      "used": 0.1,
      "total": 0.6,
      "value_usd": 30000.0
    },
    {
      "asset": "ETH",
      "free": 5.0,
      "used": 0.0,
      "total": 5.0,
      "value_usd": 15000.0
    },
    {
      "asset": "USD",
      "free": 10000.0,
      "used": 0.0,
      "total": 10000.0,
      "value_usd": 10000.0
    }
  ],
  "performance": {
    "daily_change": 2.5,
    "weekly_change": 5.0,
    "monthly_change": 10.0,
    "yearly_change": 25.0
  }
}
```

#### Get Open Positions

```
GET /portfolio/positions
```

Get open positions.

**Response:**

```json
{
  "data": [
    {
      "position_id": "position_123456789",
      "exchange": "binance",
      "symbol": "BTC/USD",
      "side": "long",
      "quantity": 0.1,
      "entry_price": 50000.0,
      "current_price": 52500.0,
      "unrealized_pnl": 250.0,
      "unrealized_pnl_percent": 5.0,
      "strategy_id": "strategy_123456789",
      "opened_at": "2025-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 10,
    "pages": 1
  }
}
```

#### Close Position

```
POST /portfolio/positions/{position_id}/close
```

Close an open position.

**Response:**

```json
{
  "position_id": "position_123456789",
  "status": "closed",
  "close_price": 52500.0,
  "realized_pnl": 250.0,
  "realized_pnl_percent": 5.0,
  "closed_at": "2025-01-01T01:00:00Z"
}
```

### System Status

#### Get System Status

```
GET /system/status
```

Get system status.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 86400,
  "services": {
    "auth": {
      "status": "healthy",
      "uptime": 86400
    },
    "strategy": {
      "status": "healthy",
      "uptime": 86400
    },
    "data": {
      "status": "healthy",
      "uptime": 86400
    },
    "trade": {
      "status": "healthy",
      "uptime": 86400
    },
    "backtest": {
      "status": "healthy",
      "uptime": 86400
    }
  },
  "database": {
    "status": "healthy",
    "connections": 5
  },
  "redis": {
    "status": "healthy",
    "connections": 3
  },
  "exchanges": {
    "binance": {
      "status": "connected",
      "latency": 150
    },
    "kraken": {
      "status": "connected",
      "latency": 200
    }
  }
}
```

#### Get System Metrics

```
GET /system/metrics
```

## Webhooks

Cryptobot can send webhook notifications for various events.

### Configuring Webhooks

Webhooks can be configured through the dashboard or API:

```
POST /webhooks
```

**Request Body:**

```json
{
  "url": "https://example.com/webhook",
  "secret": "your_webhook_secret",
  "events": ["trade.executed", "trade.closed", "strategy.started", "strategy.stopped"]
}
```

### Webhook Payload

Webhook payloads include:

```json
{
  "event": "trade.executed",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    // Event-specific data
  },
  "signature": "hmac_signature"
}
```

### Verifying Webhooks

To verify webhook authenticity, compute the HMAC signature:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    computed_signature = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)
```

## WebSocket API

Cryptobot provides a WebSocket API for real-time updates.

### Connection

Connect to the WebSocket API:

```
ws://localhost:8000/ws
```

### Authentication

To authenticate with the WebSocket API, send an authentication message after connecting:

```json
{
  "action": "authenticate",
  "api_key": "your_api_key_here"
}
```

### Subscribing to Topics

Subscribe to topics to receive real-time updates:

```json
{
  "action": "subscribe",
  "topics": ["market.BTC/USD.ticker", "trades.strategy_123456789"]
}
```

### Available Topics

- `market.{symbol}.ticker`: Real-time ticker updates for a symbol
- `market.{symbol}.trades`: Real-time trade updates for a symbol
- `market.{symbol}.orderbook`: Real-time order book updates for a symbol
- `trades.{strategy_id}`: Real-time trade updates for a strategy
- `positions.{strategy_id}`: Real-time position updates for a strategy
- `system.status`: Real-time system status updates

### Message Format

Messages from the WebSocket API follow this format:

```json
{
  "topic": "market.BTC/USD.ticker",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    // Topic-specific data
  }
}
```

### Example: Ticker Updates

```json
{
  "topic": "market.BTC/USD.ticker",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    "exchange": "binance",
    "symbol": "BTC/USD",
    "bid": 50000.0,
    "ask": 50100.0,
    "last": 50050.0,
    "volume": 1000.5,
    "change": 2.5,
    "change_percent": 0.05
  }
}
```

### Example: Trade Updates

```json
{
  "topic": "trades.strategy_123456789",
  "timestamp": "2025-01-01T00:00:00Z",
  "data": {
    "order_id": "order_123456789",
    "exchange": "binance",
    "symbol": "BTC/USD",
    "side": "buy",
    "type": "limit",
    "quantity": 0.1,
    "price": 50000.0,
    "status": "filled",
    "filled": 0.1,
    "remaining": 0.0,
    "average_price": 50000.0,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:01:00Z"
  }
}
```

### Unsubscribing from Topics

Unsubscribe from topics to stop receiving updates:

```json
{
  "action": "unsubscribe",
  "topics": ["market.BTC/USD.ticker"]
}
```

### Ping/Pong

To keep the connection alive, send ping messages:

```json
{
  "action": "ping",
  "id": 1
}
```

The server will respond with a pong message:

```json
{
  "action": "pong",
  "id": 1
}
```

### Closing the Connection

To close the connection gracefully, send a close message:

```json
{
  "action": "close"
}
```
Get system metrics.

**Response:**

```json
{
  "cpu_usage": 25.0,
  "memory_usage": 512.0,
  "disk_usage": 1024.0,
  "network": {
    "rx_bytes": 1000000,
    "tx_bytes": 500000
  },
  "requests": {
    "total": 10000,
    "success": 9950,
    "error": 50,
    "average_latency": 50
  },
  "trades": {
    "total": 1000,
    "success": 995,
    "error": 5,
    "average_latency": 200
  },
  "strategies": {
    "active": 5,
    "total": 10
  },
  "backtests": {
    "running": 1,
    "completed": 100,
    "failed": 5
  }
}
```

List order history.

**Query Parameters:**

- `exchange` (optional): Filter by exchange
- `symbol` (optional): Filter by symbol
- `strategy_id` (optional): Filter by strategy
- `start` (optional): Start timestamp (ISO 8601)
- `end` (optional): End timestamp (ISO 8601)
- `page` (optional): Page number for pagination
- `limit` (optional): Number of items per page

**Response:**

```json
{
  "data": [
    {
      "order_id": "order_123456789",
      "exchange": "binance",
      "symbol": "BTC/USD",
      "side": "buy",
      "type": "limit",
      "quantity": 0.1,
      "price": 50000.0,
      "status": "filled",
      "filled": 0.1,
      "remaining": 0.0,
      "average_price": 50000.0,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:01:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "page": 1,
    "limit": 10,
    "pages": 1
  }
}
```
  "exchange": "binance",
  "symbol": "BTC/USD",
  "timestamp": "2025-01-01T00:00:00Z",
  "bid": 50000.0,
  "ask": 50100.0,
  "last": 50050.0,
  "volume": 1000.5,
  "change": 2.5,
  "change_percent": 0.05
}
```
```
DELETE /backtest/{backtest_id}
```

Cancel a running backtest.

**Response:**

```json
{
  "detail": "Backtest cancelled successfully"
}
```
{
  "close_positions": true
}
```

**Response:**

```json
{
  "id": "strategy_123456789",
  "name": "Mean Reversion",
  "status": "inactive",
  "stopped_at": "2025-01-01T01:00:00Z",
  "positions_closed": true
}
```

```json
{
  "detail": "API key revoked successfully"
}
```

#### Emergency Revoke API Key

```
POST /api-keys/emergency-revoke
```

Emergency revoke an API key (marks as compromised).

**Request Body:**

```json
{
  "key_id": "key_123456789",
  "details": "Key was leaked in a security breach"
}
```

**Response:**

```json
{
  "detail": "API key marked as compromised and revoked",
  "security_alert": "Security team has been notified"
}
```

#### Validate Token

```
GET /auth/validate
```

Validate a JWT token.

**Response:**

```json
{
  "valid": true,
  "username": "your_username",
  "roles": ["user", "trader"]
}
```
    "page": 2,
    "limit": 10,
    "pages": 10
  }
}