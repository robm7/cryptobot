#!/bin/bash
# Data Service Test Script
# Tests data service functionality

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Data Service Test ====="
echo "Starting data service tests..."

# Check if data service is running
echo "Checking if data service is running..."
if pgrep -f "data/main.py" > /dev/null; then
    echo "Data service is running."
else
    echo "Data service is not running. Starting data service..."
    # Start data service if not running
    ./scripts/non-docker-setup/start_data.sh
    sleep 5  # Wait for service to start
fi

# Run unit tests for data service
echo "Running data service unit tests..."
python -m pytest tests/test_data_service.py -v

# Test data API endpoints
echo "Testing data API endpoints..."
# Get auth token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
fi

# Test historical data retrieval
echo "Testing historical data retrieval..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/data/historical?symbol=BTCUSDT&timeframe=1h&limit=100" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"data"* ]]; then
    echo "Successfully retrieved historical data."
else
    echo "Failed to retrieve historical data."
    exit 1
fi

# Test OHLCV data retrieval
echo "Testing OHLCV data retrieval..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/data/ohlcv?symbol=BTCUSDT&timeframe=1h&limit=100" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"open"* ]]; then
    echo "Successfully retrieved OHLCV data."
else
    echo "Failed to retrieve OHLCV data."
    exit 1
fi

# Test ticker data retrieval
echo "Testing ticker data retrieval..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/data/ticker?symbol=BTCUSDT" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"price"* ]]; then
    echo "Successfully retrieved ticker data."
else
    echo "Failed to retrieve ticker data."
    exit 1
fi

# Test order book data retrieval
echo "Testing order book data retrieval..."
RESPONSE=$(curl -s -X GET "http://localhost:8000/data/orderbook?symbol=BTCUSDT&limit=10" -H "Authorization: Bearer $TOKEN")
if [[ $RESPONSE == *"bids"* ]] && [[ $RESPONSE == *"asks"* ]]; then
    echo "Successfully retrieved order book data."
else
    echo "Failed to retrieve order book data."
    exit 1
fi

# Test data import
echo "Testing data import..."
# Create a test CSV file with OHLCV data
cat > /tmp/test_ohlcv.csv << EOF
timestamp,open,high,low,close,volume
2025-01-01T00:00:00Z,50000.0,51000.0,49500.0,50500.0,100.5
2025-01-01T01:00:00Z,50500.0,51500.0,50000.0,51000.0,120.3
2025-01-01T02:00:00Z,51000.0,52000.0,50800.0,51800.0,150.7
EOF

IMPORT_DATA='{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "source": "file",
    "format": "csv"
}'

RESPONSE=$(curl -s -X POST "http://localhost:8000/data/import" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -F "data=@/tmp/test_ohlcv.csv" -F "metadata=$IMPORT_DATA")
if [[ $RESPONSE == *"imported"* ]]; then
    echo "Successfully imported data."
else
    echo "Failed to import data."
    exit 1
fi

# Test data export
echo "Testing data export..."
EXPORT_DATA='{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-01T03:00:00Z",
    "format": "csv"
}'

RESPONSE=$(curl -s -X POST "http://localhost:8000/data/export" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$EXPORT_DATA" -o /tmp/exported_data.csv)
if [ -s /tmp/exported_data.csv ]; then
    echo "Successfully exported data."
else
    echo "Failed to export data."
    exit 1
fi

# Test data aggregation
echo "Testing data aggregation..."
AGGREGATION_DATA='{
    "symbol": "BTCUSDT",
    "source_timeframe": "1h",
    "target_timeframe": "4h",
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z"
}'

RESPONSE=$(curl -s -X POST "http://localhost:8000/data/aggregate" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$AGGREGATION_DATA")
if [[ $RESPONSE == *"aggregated"* ]]; then
    echo "Successfully aggregated data."
else
    echo "Failed to aggregate data."
    exit 1
fi

# Test data synchronization
echo "Testing data synchronization..."
SYNC_DATA='{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "exchange": "binance",
    "start_time": "2025-01-01T00:00:00Z",
    "end_time": "2025-01-02T00:00:00Z"
}'

RESPONSE=$(curl -s -X POST "http://localhost:8000/data/sync" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d "$SYNC_DATA")
if [[ $RESPONSE == *"sync"* ]]; then
    echo "Successfully initiated data synchronization."
else
    echo "Failed to initiate data synchronization."
    exit 1
fi

# Test data streaming
echo "Testing data streaming..."
# Start a background process to listen for streaming data
curl -s -N -X GET "http://localhost:8000/data/stream?symbol=BTCUSDT" -H "Authorization: Bearer $TOKEN" > /tmp/stream_output &
STREAM_PID=$!

# Wait a few seconds to collect some data
sleep 5

# Kill the streaming process
kill $STREAM_PID

# Check if we received any data
if [ -s /tmp/stream_output ]; then
    echo "Successfully received streaming data."
else
    echo "Failed to receive streaming data."
    exit 1
fi

# Clean up
rm -f /tmp/test_ohlcv.csv /tmp/exported_data.csv /tmp/stream_output

echo "Data service tests completed."
echo "===== Data Service Test Complete ====="