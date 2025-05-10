#!/bin/bash
# Service Orchestration Script

# Set script to exit immediately if a command exits with a non-zero status
set -e

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to check if a service is running
check_service() {
    local service_name=$1
    local host=$2
    local port=$3
    
    echo "Checking if $service_name is running at $host:$port..."
    if curl -s "http://${host}:${port}/health" > /dev/null 2>&1; then
        echo "$service_name is running."
        return 0
    else
        echo "$service_name is not running."
        return 1
    fi
}

# Function to start a service and wait for it to be ready
start_service() {
    local service_name=$1
    local script_path=$2
    local host=$3
    local port=$4
    
    echo "Starting $service_name..."
    
    # Check if service is already running
    if check_service "$service_name" "$host" "$port"; then
        echo "$service_name is already running."
        return 0
    fi
    
    # Start the service
    bash "$script_path"
    
    # Check if service started successfully
    if check_service "$service_name" "$host" "$port"; then
        echo "$service_name started successfully."
        return 0
    else
        echo "Failed to start $service_name."
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file=$2
    
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null; then
            echo "Stopping $service_name with PID $PID..."
            kill $PID
            sleep 2
            if ps -p $PID > /dev/null; then
                echo "Force stopping $service_name with PID $PID..."
                kill -9 $PID
            fi
            rm "$pid_file"
            echo "$service_name stopped."
        else
            echo "$service_name is not running."
            rm "$pid_file"
        fi
    else
        echo "$service_name is not running."
    fi
}

# Set default values for environment variables if not set
export AUTH_HOST=${AUTH_HOST:-"0.0.0.0"}
export AUTH_PORT=${AUTH_PORT:-"8000"}
export DATA_HOST=${DATA_HOST:-"0.0.0.0"}
export DATA_PORT=${DATA_PORT:-"8001"}
export STRATEGY_HOST=${STRATEGY_HOST:-"0.0.0.0"}
export STRATEGY_PORT=${STRATEGY_PORT:-"8002"}
export BACKTEST_HOST=${BACKTEST_HOST:-"0.0.0.0"}
export BACKTEST_PORT=${BACKTEST_PORT:-"8003"}
export TRADE_HOST=${TRADE_HOST:-"0.0.0.0"}
export TRADE_PORT=${TRADE_PORT:-"8004"}

# Command line arguments
ACTION=${1:-"start"}
SERVICE=${2:-"all"}

case $ACTION in
    start)
        case $SERVICE in
            all)
                echo "Starting all services in the correct order..."
                
                # Start Auth service first
                start_service "Auth" "./scripts/non-docker-setup/start_auth.sh" "$AUTH_HOST" "$AUTH_PORT" || exit 1
                
                # Start Data service next
                start_service "Data" "./scripts/non-docker-setup/start_data.sh" "$DATA_HOST" "$DATA_PORT" || exit 1
                
                # Start Strategy service
                start_service "Strategy" "./scripts/non-docker-setup/start_strategy.sh" "$STRATEGY_HOST" "$STRATEGY_PORT" || exit 1
                
                # Start Backtest service
                start_service "Backtest" "./scripts/non-docker-setup/start_backtest.sh" "$BACKTEST_HOST" "$BACKTEST_PORT" || exit 1
                
                # Start Trade service
                start_service "Trade" "./scripts/non-docker-setup/start_trade.sh" "$TRADE_HOST" "$TRADE_PORT" || exit 1
                
                echo "All services started successfully."
                ;;
            auth)
                start_service "Auth" "./scripts/non-docker-setup/start_auth.sh" "$AUTH_HOST" "$AUTH_PORT" || exit 1
                ;;
            data)
                # Check if Auth service is running
                check_service "Auth" "$AUTH_HOST" "$AUTH_PORT" || { echo "Auth service must be running before starting Data service."; exit 1; }
                
                start_service "Data" "./scripts/non-docker-setup/start_data.sh" "$DATA_HOST" "$DATA_PORT" || exit 1
                ;;
            strategy)
                # Check if Auth service is running
                check_service "Auth" "$AUTH_HOST" "$AUTH_PORT" || { echo "Auth service must be running before starting Strategy service."; exit 1; }
                
                # Check if Data service is running
                check_service "Data" "$DATA_HOST" "$DATA_PORT" || { echo "Data service must be running before starting Strategy service."; exit 1; }
                
                start_service "Strategy" "./scripts/non-docker-setup/start_strategy.sh" "$STRATEGY_HOST" "$STRATEGY_PORT" || exit 1
                ;;
            backtest)
                # Check if Auth service is running
                check_service "Auth" "$AUTH_HOST" "$AUTH_PORT" || { echo "Auth service must be running before starting Backtest service."; exit 1; }
                
                # Check if Data service is running
                check_service "Data" "$DATA_HOST" "$DATA_PORT" || { echo "Data service must be running before starting Backtest service."; exit 1; }
                
                # Check if Strategy service is running
                check_service "Strategy" "$STRATEGY_HOST" "$STRATEGY_PORT" || { echo "Strategy service must be running before starting Backtest service."; exit 1; }
                
                start_service "Backtest" "./scripts/non-docker-setup/start_backtest.sh" "$BACKTEST_HOST" "$BACKTEST_PORT" || exit 1
                ;;
            trade)
                # Check if Auth service is running
                check_service "Auth" "$AUTH_HOST" "$AUTH_PORT" || { echo "Auth service must be running before starting Trade service."; exit 1; }
                
                # Check if Strategy service is running
                check_service "Strategy" "$STRATEGY_HOST" "$STRATEGY_PORT" || { echo "Strategy service must be running before starting Trade service."; exit 1; }
                
                start_service "Trade" "./scripts/non-docker-setup/start_trade.sh" "$TRADE_HOST" "$TRADE_PORT" || exit 1
                ;;
            *)
                echo "Unknown service: $SERVICE"
                echo "Available services: all, auth, data, strategy, backtest, trade"
                exit 1
                ;;
        esac
        ;;
    stop)
        case $SERVICE in
            all)
                echo "Stopping all services in the reverse order..."
                
                # Stop Trade service first
                stop_service "Trade" "/tmp/cryptobot_trade.pid"
                
                # Stop Backtest service
                stop_service "Backtest" "/tmp/cryptobot_backtest.pid"
                
                # Stop Strategy service
                stop_service "Strategy" "/tmp/cryptobot_strategy.pid"
                
                # Stop Data service
                stop_service "Data" "/tmp/cryptobot_data.pid"
                
                # Stop Auth service last
                stop_service "Auth" "/tmp/cryptobot_auth.pid"
                
                echo "All services stopped."
                ;;
            auth)
                stop_service "Auth" "/tmp/cryptobot_auth.pid"
                ;;
            data)
                stop_service "Data" "/tmp/cryptobot_data.pid"
                ;;
            strategy)
                stop_service "Strategy" "/tmp/cryptobot_strategy.pid"
                ;;
            backtest)
                stop_service "Backtest" "/tmp/cryptobot_backtest.pid"
                ;;
            trade)
                stop_service "Trade" "/tmp/cryptobot_trade.pid"
                ;;
            *)
                echo "Unknown service: $SERVICE"
                echo "Available services: all, auth, data, strategy, backtest, trade"
                exit 1
                ;;
        esac
        ;;
    restart)
        case $SERVICE in
            all)
                echo "Restarting all services..."
                $0 stop all
                sleep 2
                $0 start all
                ;;
            *)
                echo "Restarting $SERVICE service..."
                $0 stop $SERVICE
                sleep 2
                $0 start $SERVICE
                ;;
        esac
        ;;
    status)
        echo "Checking status of all services..."
        
        check_service "Auth" "$AUTH_HOST" "$AUTH_PORT"
        check_service "Data" "$DATA_HOST" "$DATA_PORT"
        check_service "Strategy" "$STRATEGY_HOST" "$STRATEGY_PORT"
        check_service "Backtest" "$BACKTEST_HOST" "$BACKTEST_PORT"
        check_service "Trade" "$TRADE_HOST" "$TRADE_PORT"
        ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Available actions: start, stop, restart, status"
        echo "Usage: $0 [action] [service]"
        echo "  action: start, stop, restart, status"
        echo "  service: all, auth, data, strategy, backtest, trade"
        exit 1
        ;;
esac

exit 0