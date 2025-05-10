#!/bin/bash
# Data Service Startup Script

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
command -v redis-cli >/dev/null 2>&1 || { echo "Redis CLI is required but not installed. Aborting."; exit 1; }

# Set default values for environment variables if not set
export DATA_HOST=${DATA_HOST:-"0.0.0.0"}
export DATA_PORT=${DATA_PORT:-"8001"}
export DATA_WORKERS=${DATA_WORKERS:-"2"}
export DATA_LOG_LEVEL=${DATA_LOG_LEVEL:-"info"}
export REDIS_HOST=${REDIS_HOST:-"localhost"}
export REDIS_PORT=${REDIS_PORT:-"6379"}
export REDIS_DB=${REDIS_DB:-"0"}
export AUTH_HOST=${AUTH_HOST:-"0.0.0.0"}
export AUTH_PORT=${AUTH_PORT:-"8000"}

echo "Starting Data Service on ${DATA_HOST}:${DATA_PORT}"

# Check if Redis is running
echo "Checking Redis connection..."
if ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; then
    echo "Redis is not running. Please start Redis first."
    exit 1
fi
echo "Redis connection successful."

# Check if Auth service is running
echo "Checking Auth service connection..."
if ! curl -s "http://${AUTH_HOST}:${AUTH_PORT}/health" > /dev/null 2>&1; then
    echo "Auth service is not running. Please start Auth service first."
    exit 1
fi
echo "Auth service connection successful."

# Check if the service is already running
PID_FILE="/tmp/cryptobot_data.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Data service is already running with PID $PID"
        exit 0
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start the service
cd data
echo "Starting Data service..."
nohup uvicorn main:app --host $DATA_HOST --port $DATA_PORT --workers $DATA_WORKERS --log-level $DATA_LOG_LEVEL > ../logs/data_service.log 2>&1 &
echo $! > "$PID_FILE"
echo "Data service started with PID $(cat "$PID_FILE")"
cd ..

# Wait for service to be ready
echo "Waiting for Data service to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://${DATA_HOST}:${DATA_PORT}/health" > /dev/null; then
        echo "Data service is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for Data service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Data service failed to start within the expected time"
    exit 1
fi

echo "Data service started successfully"