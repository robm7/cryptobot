#!/bin/bash
# Auth Service Startup Script

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
export AUTH_HOST=${AUTH_HOST:-"0.0.0.0"}
export AUTH_PORT=${AUTH_PORT:-"8000"}
export AUTH_WORKERS=${AUTH_WORKERS:-"4"}
export AUTH_LOG_LEVEL=${AUTH_LOG_LEVEL:-"info"}
export AUTH_DB_URL=${AUTH_DB_URL:-"sqlite:///./auth.db"}

echo "Starting Auth Service on ${AUTH_HOST}:${AUTH_PORT}"

# Check if database exists and is accessible
if [[ $AUTH_DB_URL == sqlite* ]]; then
    DB_PATH=$(echo $AUTH_DB_URL | sed 's/sqlite:\/\///g')
    if [ ! -f "$DB_PATH" ]; then
        echo "Database file not found. Running migrations..."
        cd auth
        python3 -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"
        cd ..
    fi
fi

# Check if the service is already running
PID_FILE="/tmp/cryptobot_auth.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Auth service is already running with PID $PID"
        exit 0
    else
        echo "Removing stale PID file"
        rm "$PID_FILE"
    fi
fi

# Start the service
cd auth
echo "Starting Auth service..."
nohup uvicorn main:app --host $AUTH_HOST --port $AUTH_PORT --workers $AUTH_WORKERS --log-level $AUTH_LOG_LEVEL > ../logs/auth_service.log 2>&1 &
echo $! > "$PID_FILE"
echo "Auth service started with PID $(cat "$PID_FILE")"
cd ..

# Wait for service to be ready
echo "Waiting for Auth service to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://${AUTH_HOST}:${AUTH_PORT}/health" > /dev/null; then
        echo "Auth service is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for Auth service to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Auth service failed to start within the expected time"
    exit 1
fi

echo "Auth service started successfully"