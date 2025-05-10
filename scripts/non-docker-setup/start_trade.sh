#!/bin/bash
# Trade Service Startup Script

# Set script to exit immediately if a command exits with a non-zero status
set -e

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Check for required dependencies
command -v python3 >/dev/null 2>&1 || { echo "Python3 is required but not installed. Aborting."; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "Pip3 is required but not installed. Aborting."; exit 1; }

# Set default values for environment variables if not set
export TRADE_HOST=${TRADE_HOST:-"0.0.0.0"}
export TRADE_PORT=${TRADE_PORT:-"8004"}
export TRADE_WORKERS=${TRADE_WORKERS:-"2"}
export TRADE_LOG_LEVEL=${TRADE_LOG_LEVEL:-"info"}
export TRADE_DB_URL=${TRADE_DB_URL:-"sqlite:///./trade.db"}
export AUTH_HOST=${AUTH_HOST:-"0.0.0.0"}
export AUTH_PORT=${AUTH_PORT:-"8000"}
export STRATEGY_HOST=${STRATEGY_HOST:-"0.0.0.0"}
export STRATEGY_PORT=${STRATEGY_PORT:-"8002"}

# Check for required API keys
if [ -z "$EXCHANGE_API_KEY" ]; then
    echo "EXCHANGE_API_KEY environment variable is not set. Please set it before starting the Trade service."
    exit 1
fi

if [ -z "$EXCHANGE_API_SECRET" ]; then
    echo "EXCHANGE_API_SECRET environment variable is not set. Please set it before starting the Trade service."
    exit 1
fi

echo "Starting Trade Service on ${TRADE_HOST}:${TRADE_PORT}"

# Check if database exists and is accessible
if [[ $TRADE_DB_URL == sqlite* ]]; then
    DB_PATH=$(echo $TRADE_DB_URL | sed 's/sqlite:\/\///g')
    if [ ! -f "$DB_PATH" ]; then
        echo "Database file not found. Running migrations..."
        cd trade
        python3 -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
        cd ..
    fi
fi

# Check if Auth service is running
echo "Checking Auth service connection..."
if ! curl -s "http://${AUTH_HOST}:${AUTH_PORT}/health" > /dev/null 2>&1; then
    echo "Auth service is not running. Please start Auth service first."
    exit 1
fi
echo "Auth service connection successful."

# Check if Strategy service is running
echo "Checking Strategy service connection..."
if ! curl -s "http://${STRATEGY_HOST}:${STRATEGY_PORT}/health" > /dev/null 2>&1; then
    echo "Strategy service is not running. Please start Strategy service first."
    exit 1
fi
echo "Strategy service connection successful."

# Check if the service is already running
PID_FILE="/tmp/cryptobot_trade.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Trade service is already running with PID $PID"
        exit 0
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the service
cd trade
echo "Starting Trade service..."
nohup uvicorn main:app --host $TRADE_HOST --port $TRADE_PORT --workers $TRADE_WORKERS --log-level $TRADE_LOG_LEVEL > ../logs/trade_service.log 2>&1 &
echo $! > "$PID_FILE"
echo "Trade service started with PID $(cat "$PID_FILE")"
cd ..

# Wait for service to be ready
echo "Waiting for Trade service to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://${TRADE_HOST}:${TRADE_PORT}/health" > /dev/null; then
        echo "Trade service is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for Trade service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Trade service failed to start within the expected time"
    exit 1
fi

echo "Trade service started successfully"