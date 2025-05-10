# Exchange Gateway MCP Server Documentation

## Overview
Provides unified interface for multiple cryptocurrency exchanges with:
- Standardized API endpoints
- Consistent error handling
- Exchange client management

## API Endpoints

### Health Check
`GET /health`
- Returns service status

### Exchange Operations
`GET /api/exchanges/ticker/{exchange}/{pair}`
- Get current price for trading pair

`POST /api/exchanges/order`
- Place new order
- Body: 
```json
{
  "exchange": "string",
  "pair": "string",
  "type": "limit|market",
  "side": "buy|sell",
  "amount": "number",
  "price": "number" (for limit orders)
}
```

`DELETE /api/exchanges/order/{exchange}/{order_id}`
- Cancel existing order

`GET /api/exchanges/balance/{exchange}/{asset}`
- Get balance for specific asset

## Configuration
Environment variables:
- `EXCHANGE_API_KEY`: API key for exchanges
- `EXCHANGE_API_SECRET`: API secret for exchanges

## Deployment
```bash
docker-compose up -d exchange-gateway
```

## Testing
Run integration tests:
```bash
pytest services/mcp/exchange-gateway/test_endpoints.py