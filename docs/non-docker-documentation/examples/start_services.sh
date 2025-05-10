#!/bin/bash
# Example script to start Cryptobot services
# This script demonstrates how to start Cryptobot services from the command line

# Set environment variables
export CRYPTOBOT_ENV=development
export CRYPTOBOT_LOG_LEVEL=INFO

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored status messages
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
        "warning")
            echo -e "${YELLOW}[WARNING]${NC} $message"
            ;;
        "error")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "info")
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        *)
            echo "$message"
            ;;
    esac
}

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1
    else
        return 0
    fi
}

# Function to start a service
start_service() {
    local service_name=$1
    local port=$2
    
    print_status "info" "Starting $service_name service on port $port..."
    
    # Check if port is available
    if ! check_port $port; then
        print_status "error" "Port $port is already in use. Cannot start $service_name service."
        return 1
    fi
    
    # Start the service
    cryptobot --service $service_name &
    local pid=$!
    
    # Wait for service to start
    sleep 2
    
    # Check if service is running
    if ps -p $pid > /dev/null; then
        print_status "success" "$service_name service started successfully (PID: $pid)"
        echo $pid > /tmp/cryptobot_${service_name}.pid
        return 0
    else
        print_status "error" "Failed to start $service_name service"
        return 1
    fi
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local port=$2
    
    print_status "info" "Checking health of $service_name service..."
    
    # Try to connect to the service health endpoint
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
    
    if [ "$response" == "200" ]; then
        print_status "success" "$service_name service is healthy"
        return 0
    else
        print_status "warning" "$service_name service health check failed (HTTP $response)"
        return 1
    fi
}

# Main script

# Print banner
echo "========================================"
echo "  Cryptobot Services Startup Script"
echo "========================================"
echo ""

# Check if cryptobot command is available
if ! command -v cryptobot &> /dev/null; then
    print_status "error" "cryptobot command not found. Please make sure Cryptobot is installed correctly."
    exit 1
fi

# Create data directories if they don't exist
mkdir -p data/logs
mkdir -p data/db

print_status "info" "Starting Cryptobot services..."

# Start services
start_service "auth" 8000
auth_status=$?

start_service "strategy" 8001
strategy_status=$?

start_service "data" 8002
data_status=$?

start_service "trade" 8003
trade_status=$?

start_service "backtest" 8004
backtest_status=$?

# Wait for services to initialize
print_status "info" "Waiting for services to initialize..."
sleep 5

# Check service health
if [ $auth_status -eq 0 ]; then
    check_service_health "auth" 8000
fi

if [ $strategy_status -eq 0 ]; then
    check_service_health "strategy" 8001
fi

if [ $data_status -eq 0 ]; then
    check_service_health "data" 8002
fi

if [ $trade_status -eq 0 ]; then
    check_service_health "trade" 8003
fi

if [ $backtest_status -eq 0 ]; then
    check_service_health "backtest" 8004
fi

# Start dashboard
print_status "info" "Starting dashboard..."
if check_port 8080; then
    cryptobot --service dashboard &
    dashboard_pid=$!
    echo $dashboard_pid > /tmp/cryptobot_dashboard.pid
    print_status "success" "Dashboard started successfully (PID: $dashboard_pid)"
    print_status "info" "Dashboard available at: http://localhost:8080"
else
    print_status "error" "Port 8080 is already in use. Cannot start dashboard."
fi

# Summary
echo ""
echo "========================================"
echo "  Cryptobot Services Status Summary"
echo "========================================"

services=("auth:8000" "strategy:8001" "data:8002" "trade:8003" "backtest:8004" "dashboard:8080")

for service_info in "${services[@]}"; do
    service_name="${service_info%%:*}"
    port="${service_info##*:}"
    
    if [ -f "/tmp/cryptobot_${service_name}.pid" ]; then
        pid=$(cat /tmp/cryptobot_${service_name}.pid)
        if ps -p $pid > /dev/null; then
            print_status "success" "$service_name service is running on port $port (PID: $pid)"
        else
            print_status "error" "$service_name service is not running"
        fi
    else
        print_status "error" "$service_name service was not started"
    fi
done

echo ""
print_status "info" "To stop all services, run: ./stop_services.sh"
print_status "info" "To view logs, check the data/logs directory"

exit 0