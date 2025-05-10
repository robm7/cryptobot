#!/bin/bash
# Trade Service Test Script
# Tests trade service functionality

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Trade Service Test ====="
echo "Starting trade service tests..."

# Check if trade service is running
echo "Checking if trade service is running..."
if pgrep -f "trade/main.py" > /dev/null; then
    echo "Trade service is running."
else
    echo "Trade service is not running. Starting trade service..."
    # Start trade service if not running
    ./scripts/non-docker-setup/start_trade.sh
    sleep 5  # Wait for service to start
fi

# Run unit tests for trade service
echo "Running trade service unit tests..."
python -m pytest tests/test_trades.py -v
python -m pytest tests/test_trade_execution.py -v

# Test trade API endpoints
echo "Testing trade API endpoints..."
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

# Test trade creation
echo "Testing trade creation..."
TRADE_DATA='{
    "symbol": "BTCUSDT",
    "side": "buy",
    "type": "limit",
    "quantity": 0.01,
    "price": 50000.0,
    "strategy_id": 1,
    "exchange": "binance"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/trade -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$TRADE_DATA")
TRADE_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -z "$TRADE_ID" ]; then
    echo "Failed to create trade."
    exit 1
else
    echo "Successfully created trade with ID: $TRADE_ID"
fi

# Test trade retrieval
echo "Testing trade retrieval..."
RESPONSE=$(curl -s -X GET http://localhost:8000/trade/$TRADE_ID -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"BTCUSDT"* ]]; then
    echo "Successfully retrieved trade."
else
    echo "Failed to retrieve trade."
    exit 1
fi

# Test trade update
echo "Testing trade update..."
UPDATE_DATA='{
    "status": "filled",
    "filled_quantity": 0.01,
    "filled_price": 50005.0,
    "fill_time": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
}'

RESPONSE=$(curl -s -X PUT http://localhost:8000/trade/$TRADE_ID -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$UPDATE_DATA")
if [[ $RESPONSE == *"updated"* ]]; then
    echo "Successfully updated trade."
else
    echo "Failed to update trade."
    exit 1
fi

# Test trade cancellation
echo "Testing trade cancellation..."
CANCEL_DATA='{
    "reason": "test_cancellation"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/trade/$TRADE_ID/cancel -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$CANCEL_DATA")
if [[ $RESPONSE == *"cancelled"* ]]; then
    echo "Successfully cancelled trade."
else
    echo "Failed to cancel trade."
    exit 1
fi

# Test trade list retrieval
echo "Testing trade list retrieval..."
RESPONSE=$(curl -s -X GET http://localhost:8000/trades -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"trades"* ]]; then
    echo "Successfully retrieved trade list."
else
    echo "Failed to retrieve trade list."
    exit 1
fi

# Test trade filtering
echo "Testing trade filtering..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/trades?symbol=BTCUSDT&side=buy" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"trades"* ]]; then
    echo "Successfully filtered trades."
else
    echo "Failed to filter trades."
    exit 1
fi

# Test trade statistics
echo "Testing trade statistics..."
RESPONSE=$(curl -s -X GET http://localhost:8000/trades/stats -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"total_trades"* ]]; then
    echo "Successfully retrieved trade statistics."
else
    echo "Failed to retrieve trade statistics."
    exit 1
fi

# Test trade execution reliability
echo "Testing trade execution reliability..."
# Create multiple trades in rapid succession
for i in {1..5}; do
    TRADE_DATA='{
        "symbol": "BTCUSDT",
        "side": "buy",
        "type": "limit",
        "quantity": 0.01,
        "price": 50000.0,
        "strategy_id": 1,
        "exchange": "binance"
    }'
    
    curl -s -X POST http://localhost:8000/trade -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$TRADE_DATA" > /dev/null
done

# Check if all trades were created
RESPONSE=$(curl -s -X GET "http://localhost:8000/trades?limit=10" -H "Authorization: Bearer $TOKEN")
TRADE_COUNT=$(echo $RESPONSE | grep -o '"id"' | wc -l)

if [ $TRADE_COUNT -ge 5 ]; then
    echo "Successfully created multiple trades."
else
    echo "Failed to create multiple trades."
    exit 1
fi

# Test trade execution service
echo "Testing trade execution service..."
SIGNAL_DATA='{
    "symbol": "BTCUSDT",
    "side": "buy",
    "price": 50000.0,
    "quantity": 0.01,
    "strategy_id": 1,
    "signal_type": "entry"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/trade/execute -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$SIGNAL_DATA")
if [[ $RESPONSE == *"trade_id"* ]]; then
    echo "Successfully executed trade signal."
else
    echo "Failed to execute trade signal."
    exit 1
fi

echo "Trade service tests completed."
echo "===== Trade Service Test Complete ====="