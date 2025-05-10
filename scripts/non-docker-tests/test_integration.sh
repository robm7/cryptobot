#!/bin/bash
# Integration Test Script
# Tests integration between different services

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Integration Test ====="
echo "Starting integration tests..."

# Check if all services are running
echo "Checking if all services are running..."
SERVICES_RUNNING=true

if ! pgrep -f "auth/main.py" > /dev/null; then
    echo "Auth service is not running. Starting auth service..."
    ./scripts/non-docker-setup/start_auth.sh
    sleep 5
fi

if ! pgrep -f "strategy/main.py" > /dev/null; then
    echo "Strategy service is not running. Starting strategy service..."
    ./scripts/non-docker-setup/start_strategy.sh
    sleep 5
fi

if ! pgrep -f "backtest/main.py" > /dev/null; then
    echo "Backtest service is not running. Starting backtest service..."
    ./scripts/non-docker-setup/start_backtest.sh
    sleep 5
fi

if ! pgrep -f "trade/main.py" > /dev/null; then
    echo "Trade service is not running. Starting trade service..."
    ./scripts/non-docker-setup/start_trade.sh
    sleep 5
fi

if ! pgrep -f "data/main.py" > /dev/null; then
    echo "Data service is not running. Starting data service..."
    ./scripts/non-docker-setup/start_data.sh
    sleep 5
fi

# Run integration tests
echo "Running integration tests..."
python -m pytest tests/integration/test_auth_integration.py -v
python -m pytest tests/integration/test_service_integration.py -v
python -m pytest tests/integration/test_service_interactions.py -v

# Test end-to-end workflow
echo "Testing end-to-end workflow..."

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

# 1. Create a strategy
echo "1. Creating a strategy..."
STRATEGY_DATA='{
    "name": "Integration Test Strategy",
    "type": "mean_reversion",
    "parameters": {
        "window": 20,
        "deviation_threshold": 2.0,
        "take_profit": 0.05,
        "stop_loss": 0.03
    },
    "symbols": ["BTCUSDT"],
    "timeframe": "1h",
    "status": "active"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/strategy -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$STRATEGY_DATA")
STRATEGY_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -z "$STRATEGY_ID" ]; then
    echo "Failed to create strategy."
    exit 1
else
    echo "Successfully created strategy with ID: $STRATEGY_ID"
fi

# 2. Run a backtest on the strategy
echo "2. Running a backtest on the strategy..."
BACKTEST_DATA='{
    "strategy_id": '$STRATEGY_ID',
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z",
    "initial_capital": 10000,
    "symbols": ["BTCUSDT"],
    "timeframe": "1h"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/backtest -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$BACKTEST_DATA")
BACKTEST_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2)

if [ -z "$BACKTEST_ID" ]; then
    echo "Failed to create backtest."
    exit 1
else
    echo "Successfully created backtest with ID: $BACKTEST_ID"
fi

# Wait for backtest to complete
echo "Waiting for backtest to complete..."
MAX_ATTEMPTS=30
ATTEMPTS=0
COMPLETED=false

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    RESPONSE=$(curl -s -X GET http://localhost:8000/backtest/$BACKTEST_ID/status -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo $RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    if [ "$STATUS" == "completed" ]; then
        COMPLETED=true
        echo "Backtest completed successfully."
        break
    elif [ "$STATUS" == "failed" ]; then
        echo "Backtest failed."
        exit 1
    fi
    
    echo "Backtest status: $STATUS. Waiting..."
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 1
done

if [ "$COMPLETED" != "true" ]; then
    echo "Backtest did not complete within timeout period."
    exit 1
fi

# 3. Get backtest results
echo "3. Getting backtest results..."
RESPONSE=$(curl -s -X GET http://localhost:8000/backtest/$BACKTEST_ID/results -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"total_return"* ]]; then
    echo "Successfully retrieved backtest results."
else
    echo "Failed to retrieve backtest results."
    exit 1
fi

# 4. Execute the strategy
echo "4. Executing the strategy..."
RESPONSE=$(curl -s -X POST http://localhost:8000/strategy/$STRATEGY_ID/execute -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"execution"* ]]; then
    echo "Successfully executed strategy."
else
    echo "Failed to execute strategy."
    exit 1
fi

# 5. Check for generated trades
echo "5. Checking for generated trades..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/trades?strategy_id=$STRATEGY_ID" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"trades"* ]]; then
    echo "Successfully retrieved trades for strategy."
else
    echo "Failed to retrieve trades for strategy."
    exit 1
fi

# 6. Test data flow between services
echo "6. Testing data flow between services..."
# Request historical data
RESPONSE=$(curl -s -X GET "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"data"* ]]; then
    echo "Successfully retrieved historical data."
else
    echo "Failed to retrieve historical data."
    exit 1
fi

# Use the data to create a signal
SIGNAL_DATA='{
    "symbol": "BTCUSDT",
    "side": "buy",
    "price": 50000.0,
    "quantity": 0.01,
    "strategy_id": '$STRATEGY_ID',
    "signal_type": "entry"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/trade/execute -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$SIGNAL_DATA")
if [[ $RESPONSE == *"trade_id"* ]]; then
    echo "Successfully executed trade signal."
    TRADE_ID=$(echo $RESPONSE | grep -o '"trade_id":[0-9]*' | cut -d':' -f2)
else
    echo "Failed to execute trade signal."
    exit 1
fi

# 7. Test cross-service authentication
echo "7. Testing cross-service authentication..."
# Refresh token
REFRESH_TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)

RESPONSE=$(curl -s -X POST http://localhost:8000/auth/refresh -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")
NEW_TOKEN=$(echo $RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$NEW_TOKEN" ]; then
    echo "Failed to refresh token."
    exit 1
else
    echo "Successfully refreshed token."
    
    # Test the new token with a protected endpoint
    RESPONSE=$(curl -s -X GET http://localhost:8000/strategy/$STRATEGY_ID -H "Authorization: Bearer $NEW_TOKEN")
    if [[ $RESPONSE == *"Integration Test Strategy"* ]]; then
        echo "Successfully authenticated with new token."
    else
        echo "Failed to authenticate with new token."
        exit 1
    fi
fi

# 8. Clean up
echo "8. Cleaning up..."
curl -s -X DELETE http://localhost:8000/strategy/$STRATEGY_ID -H "Authorization: Bearer $TOKEN"

echo "Integration tests completed."
echo "===== Integration Test Complete ====="