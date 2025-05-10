#!/bin/bash
# Strategy Service Test Script
# Tests strategy service functionality

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Strategy Service Test ====="
echo "Starting strategy service tests..."

# Check if strategy service is running
echo "Checking if strategy service is running..."
if pgrep -f "strategy/main.py" > /dev/null; then
    echo "Strategy service is running."
else
    echo "Strategy service is not running. Starting strategy service..."
    # Start strategy service if not running
    ./scripts/non-docker-setup/start_strategy.sh
    sleep 5  # Wait for service to start
fi

# Run unit tests for strategy service
echo "Running strategy service unit tests..."
python -m pytest tests/test_base_strategy.py -v
python -m pytest tests/test_strategy_endpoints.py -v
python -m pytest tests/test_strategy_execution.py -v

# Test strategy creation
echo "Testing strategy creation..."
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

# Create a test strategy
STRATEGY_DATA='{
    "name": "Test Mean Reversion",
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

# Test strategy retrieval
echo "Testing strategy retrieval..."
RESPONSE=$(curl -s -X GET http://localhost:8000/strategy/$STRATEGY_ID -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"Test Mean Reversion"* ]]; then
    echo "Successfully retrieved strategy."
else
    echo "Failed to retrieve strategy."
    exit 1
fi

# Test strategy update
echo "Testing strategy update..."
UPDATE_DATA='{
    "parameters": {
        "window": 25,
        "deviation_threshold": 2.5,
        "take_profit": 0.06,
        "stop_loss": 0.04
    },
    "status": "paused"
}'

RESPONSE=$(curl -s -X PUT http://localhost:8000/strategy/$STRATEGY_ID -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$UPDATE_DATA")
if [[ $RESPONSE == *"updated"* ]]; then
    echo "Successfully updated strategy."
else
    echo "Failed to update strategy."
    exit 1
fi

# Test strategy execution
echo "Testing strategy execution..."
RESPONSE=$(curl -s -X POST http://localhost:8000/strategy/$STRATEGY_ID/execute -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"execution"* ]]; then
    echo "Successfully executed strategy."
else
    echo "Failed to execute strategy."
    exit 1
fi

# Test strategy backtest
echo "Testing strategy backtest..."
BACKTEST_DATA='{
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": "2025-01-31T23:59:59Z",
    "initial_capital": 10000,
    "symbols": ["BTCUSDT"],
    "timeframe": "1h"
}'

RESPONSE=$(curl -s -X POST http://localhost:8000/strategy/$STRATEGY_ID/backtest -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$BACKTEST_DATA")
if [[ $RESPONSE == *"backtest_id"* ]]; then
    echo "Successfully started backtest."
else
    echo "Failed to start backtest."
    exit 1
fi

# Test strategy deletion
echo "Testing strategy deletion..."
RESPONSE=$(curl -s -X DELETE http://localhost:8000/strategy/$STRATEGY_ID -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"deleted"* ]]; then
    echo "Successfully deleted strategy."
else
    echo "Failed to delete strategy."
    exit 1
fi

echo "Strategy service tests completed."
echo "===== Strategy Service Test Complete ====="