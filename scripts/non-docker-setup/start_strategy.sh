#!/bin/bash
# Strategy Service Startup Script

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
export STRATEGY_HOST=${STRATEGY_HOST:-"0.0.0.0"}
export STRATEGY_PORT=${STRATEGY_PORT:-"8002"}
export STRATEGY_WORKERS=${STRATEGY_WORKERS:-"2"}
export STRATEGY_LOG_LEVEL=${STRATEGY_LOG_LEVEL:-"info"}
export STRATEGY_DB_URL=${STRATEGY_DB_URL:-"sqlite:///./strategy.db"}
export AUTH_HOST=${AUTH_HOST:-"0.0.0.0"}
export AUTH_PORT=${AUTH_PORT:-"8000"}
export DATA_HOST=${DATA_HOST:-"0.0.0.0"}
export DATA_PORT=${DATA_PORT:-"8001"}

echo "Starting Strategy Service on ${STRATEGY_HOST}:${STRATEGY_PORT}"

# Check if database exists and is accessible
if [[ $STRATEGY_DB_URL == sqlite* ]]; then
    DB_PATH=$(echo $STRATEGY_DB_URL | sed 's/sqlite:\/\///g')
    if [ ! -f "$DB_PATH" ]; then
        echo "Database file not found. Running migrations..."
        cd strategy
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

# Check if Data service is running
echo "Checking Data service connection..."
if ! curl -s "http://${DATA_HOST}:${DATA_PORT}/health" > /dev/null 2>&1; then
    echo "Data service is not running. Please start Data service first."
    exit 1
fi
echo "Data service connection successful."

# Check if the service is already running
PID_FILE="/tmp/cryptobot_strategy.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Strategy service is already running with PID $PID"
        exit 0
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the service
cd strategy
echo "Starting Strategy service..."
nohup uvicorn main:app --host $STRATEGY_HOST --port $STRATEGY_PORT --workers $STRATEGY_WORKERS --log-level $STRATEGY_LOG_LEVEL > ../logs/strategy_service.log 2>&1 &
echo $! > "$PID_FILE"
echo "Strategy service started with PID $(cat "$PID_FILE")"
cd ..

# Wait for service to be ready
echo "Waiting for Strategy service to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://${STRATEGY_HOST}:${STRATEGY_PORT}/health" > /dev/null; then
        echo "Strategy service is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for Strategy service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Strategy service failed to start within the expected time"
    exit 1
fi

echo "Strategy service started successfully"