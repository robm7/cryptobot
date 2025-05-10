#!/bin/bash
# Backtest Service Test Script
# Tests backtest service functionality

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Backtest Service Test ====="
echo "Starting backtest service tests..."

# Check if backtest service is running
echo "Checking if backtest service is running..."
if pgrep -f "backtest/main.py" > /dev/null; then
    echo "Backtest service is running."
else
    echo "Backtest service is not running. Starting backtest service..."
    # Start backtest service if not running
    ./scripts/non-docker-setup/start_backtest.sh
    sleep 5  # Wait for service to start
fi

# Run unit tests for backtest service
echo "Running backtest service unit tests..."
python -m pytest tests/test_backtest.py -v

# Test backtest API endpoints
echo "Testing backtest API endpoints..."
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

# Create a test strategy for backtesting
STRATEGY_DATA='{
    "name": "Test Breakout Strategy",
    "type": "breakout",
    "parameters": {
        "breakout_period": 20,
        "atr_period": 14,
        "atr_multiplier": 2.0,
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
    echo "Failed to create strategy for backtest."
    exit 1
else
    echo "Successfully created strategy with ID: $STRATEGY_ID"
fi

# Test backtest creation
echo "Testing backtest creation..."
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

# Test backtest status retrieval
echo "Testing backtest status retrieval..."
# Wait for backtest to complete (or timeout after 30 seconds)
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

# Test backtest results retrieval
echo "Testing backtest results retrieval..."
RESPONSE=$(curl -s -X GET http://localhost:8000/backtest/$BACKTEST_ID/results -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"total_return"* ]]; then
    echo "Successfully retrieved backtest results."
else
    echo "Failed to retrieve backtest results."
    exit 1
fi

# Test backtest comparison
echo "Testing backtest comparison..."
# Create another backtest with different parameters
STRATEGY_DATA='{
    "name": "Test Breakout Strategy 2",
    "type": "breakout",
    "parameters": {
        "breakout_period": 30,
        "atr_period": 10,
        "atr_multiplier": 1.5,
        "take_profit": 0.06,
        "stop_loss": 0.02
    },
    "symbols": ["BTCUSDT"],
    "timeframe": "1h",
    "status": "active"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/strategy -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$STRATEGY_DATA")
STRATEGY_ID_2=$(echo $RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2)

BACKTEST_DATA='{
    "strategy_id": '$STRATEGY_ID_2',
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z",
    "initial_capital": 10000,
    "symbols": ["BTCUSDT"],
    "timeframe": "1h"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/backtest -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$BACKTEST_DATA")
BACKTEST_ID_2=$(echo $RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2)

# Wait for second backtest to complete
ATTEMPTS=0
COMPLETED=false

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    RESPONSE=$(curl -s -X GET http://localhost:8000/backtest/$BACKTEST_ID_2/status -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo $RESPONSE | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    
    if [ "$STATUS" == "completed" ]; then
        COMPLETED=true
        echo "Second backtest completed successfully."
        break
    elif [ "$STATUS" == "failed" ]; then
        echo "Second backtest failed."
        exit 1
    fi
    
    echo "Second backtest status: $STATUS. Waiting..."
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 1
done

if [ "$COMPLETED" != "true" ]; then
    echo "Second backtest did not complete within timeout period."
    exit 1
fi

# Compare backtests
COMPARE_DATA='{
    "backtest_ids": ['$BACKTEST_ID', '$BACKTEST_ID_2']
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/backtest/compare -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$COMPARE_DATA")
if [[ $RESPONSE == *"comparison"* ]]; then
    echo "Successfully compared backtests."
else
    echo "Failed to compare backtests."
    exit 1
fi

# Clean up
echo "Cleaning up test data..."
curl -s -X DELETE http://localhost:8000/strategy/$STRATEGY_ID -H "Authorization: Bearer $TOKEN"
curl -s -X DELETE http://localhost:8000/strategy/$STRATEGY_ID_2 -H "Authorization: Bearer $TOKEN"

echo "Backtest service tests completed."
echo "===== Backtest Service Test Complete ====="