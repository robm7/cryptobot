#!/bin/bash
# Performance Test Script
# Tests performance of various services and identifies bottlenecks

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Performance Test ====="
echo "Starting performance tests..."

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

# Run performance benchmark tests
echo "Running performance benchmark tests..."
python -m pytest tests/benchmarks/test_performance.py -v

# Get auth token for API tests
echo "Getting auth token for API tests..."
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

# Test auth service performance
echo "Testing auth service performance..."
echo "Running 100 authentication requests..."
START_TIME=$(date +%s.%N)

for i in {1..100}; do
    curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' > /dev/null
done

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
REQUESTS_PER_SECOND=$(echo "100 / $DURATION" | bc -l)

echo "Auth service performance: $REQUESTS_PER_SECOND requests/second"
echo "Average response time: $(echo "$DURATION / 100" | bc -l) seconds"

# Test data service performance
echo "Testing data service performance..."
echo "Running 100 historical data requests..."
START_TIME=$(date +%s.%N)

for i in {1..100}; do
    curl -s -X GET "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -H "Authorization: Bearer $TOKEN" > /dev/null
done

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
REQUESTS_PER_SECOND=$(echo "100 / $DURATION" | bc -l)

echo "Data service performance: $REQUESTS_PER_SECOND requests/second"
echo "Average response time: $(echo "$DURATION / 100" | bc -l) seconds"

# Test strategy service performance
echo "Testing strategy service performance..."
echo "Creating test strategy..."
STRATEGY_DATA='{
    "name": "Performance Test Strategy",
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
fi

echo "Running 50 strategy execution requests..."
START_TIME=$(date +%s.%N)

for i in {1..50}; do
    curl -s -X POST http://localhost:8000/strategy/$STRATEGY_ID/execute -H "Authorization: Bearer $TOKEN" > /dev/null
done

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
REQUESTS_PER_SECOND=$(echo "50 / $DURATION" | bc -l)

echo "Strategy service performance: $REQUESTS_PER_SECOND requests/second"
echo "Average response time: $(echo "$DURATION / 50" | bc -l) seconds"

# Test trade service performance
echo "Testing trade service performance..."
echo "Running 50 trade creation requests..."
START_TIME=$(date +%s.%N)

for i in {1..50}; do
    TRADE_DATA='{
        "symbol": "BTCUSDT",
        "side": "buy",
        "type": "limit",
        "quantity": 0.01,
        "price": 50000.0,
        "strategy_id": '$STRATEGY_ID',
        "exchange": "binance"
    }'
    
    curl -s -X POST http://localhost:8000/trade -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$TRADE_DATA" > /dev/null
done

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
REQUESTS_PER_SECOND=$(echo "50 / $DURATION" | bc -l)

echo "Trade service performance: $REQUESTS_PER_SECOND requests/second"
echo "Average response time: $(echo "$DURATION / 50" | bc -l) seconds"

# Test backtest service performance
echo "Testing backtest service performance..."
echo "Running 10 backtest requests..."
START_TIME=$(date +%s.%N)

for i in {1..10}; do
    BACKTEST_DATA='{
        "strategy_id": '$STRATEGY_ID',
        "start_date": "2025-01-01T00:00:00Z",
        "end_date": "2025-01-31T23:59:59Z",
        "initial_capital": 10000,
        "symbols": ["BTCUSDT"],
        "timeframe": "1h"
    }'
    
    curl -s -X POST http://localhost:8000/backtest -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$BACKTEST_DATA" > /dev/null
done

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)
REQUESTS_PER_SECOND=$(echo "10 / $DURATION" | bc -l)

echo "Backtest service performance: $REQUESTS_PER_SECOND requests/second"
echo "Average response time: $(echo "$DURATION / 10" | bc -l) seconds"

# Test concurrent user load
echo "Testing concurrent user load..."
echo "Simulating 10 concurrent users making requests..."

# Create a function to simulate user activity
simulate_user() {
    local user_id=$1
    local token=$2
    
    # Make a series of requests
    curl -s -X GET "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=10" -H "Authorization: Bearer $token" > /dev/null
    curl -s -X GET "http://localhost:8000/strategy/$STRATEGY_ID" -H "Authorization: Bearer $token" > /dev/null
    curl -s -X GET "http://localhost:8000/trades?limit=10" -H "Authorization: Bearer $token" > /dev/null
    
    echo "User $user_id completed requests"
}

# Start 10 background processes to simulate concurrent users
START_TIME=$(date +%s.%N)

for i in {1..10}; do
    simulate_user $i "$TOKEN" &
done

# Wait for all background processes to complete
wait

END_TIME=$(date +%s.%N)
DURATION=$(echo "$END_TIME - $START_TIME" | bc)

echo "Concurrent user test completed in $DURATION seconds"
echo "Average time per user: $(echo "$DURATION / 10" | bc -l) seconds"

# Test system resource usage
echo "Testing system resource usage..."
echo "CPU usage during load test:"
mpstat 1 5

echo "Memory usage during load test:"
free -m

echo "Disk I/O during load test:"
iostat -x 1 5

# Clean up
echo "Cleaning up..."
curl -s -X DELETE http://localhost:8000/strategy/$STRATEGY_ID -H "Authorization: Bearer $TOKEN"

# Generate performance report
echo "Generating performance report..."
cat > performance_report.md << EOF
# Performance Test Report

## Summary
- Auth Service: $REQUESTS_PER_SECOND requests/second
- Data Service: $REQUESTS_PER_SECOND requests/second
- Strategy Service: $REQUESTS_PER_SECOND requests/second
- Trade Service: $REQUESTS_PER_SECOND requests/second
- Backtest Service: $REQUESTS_PER_SECOND requests/second

## Concurrent User Load
- 10 concurrent users completed in $DURATION seconds
- Average time per user: $(echo "$DURATION / 10" | bc -l) seconds

## Recommendations
- Monitor CPU usage during peak loads
- Consider scaling services with higher response times
- Implement caching for frequently accessed data
- Optimize database queries for better performance
EOF

echo "Performance report generated: performance_report.md"
echo "Performance tests completed."
echo "===== Performance Test Complete ====="