#!/bin/bash
# Service Status Monitoring Script

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

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local pid_file=$4
    
    echo -e "${BLUE}Checking $service_name service...${NC}"
    
    # Check if PID file exists
    if [ -f "$pid_file" ]; then
        PID=$(cat "$pid_file")
        if ps -p $PID > /dev/null; then
            echo -e "  ${GREEN}✓ Process is running with PID $PID${NC}"
            
            # Check if service endpoint is responding
            if curl -s "http://${host}:${port}/health" > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓ Service endpoint is responding at http://${host}:${port}${NC}"
                
                # Get additional service information if available
                local info=$(curl -s "http://${host}:${port}/info" 2>/dev/null)
                if [ $? -eq 0 ] && [ ! -z "$info" ]; then
                    echo -e "  ${BLUE}ℹ Service information:${NC}"
                    echo "$info" | sed 's/^/    /'
                fi
                
                # Get service metrics if available
                local metrics=$(curl -s "http://${host}:${port}/metrics" 2>/dev/null)
                if [ $? -eq 0 ] && [ ! -z "$metrics" ]; then
                    echo -e "  ${BLUE}ℹ Service metrics:${NC}"
                    echo "$metrics" | head -n 5 | sed 's/^/    /'
                    echo "    ..."
                fi
                
                return 0
            else
                echo -e "  ${RED}✗ Process is running but service endpoint is not responding${NC}"
                return 1
            fi
        else
            echo -e "  ${RED}✗ Process with PID $PID is not running${NC}"
            echo -e "  ${YELLOW}! Removing stale PID file${NC}"
            rm "$pid_file"
            return 1
        fi
    else
        echo -e "  ${RED}✗ Service is not running (no PID file)${NC}"
        return 1
    fi
}

# Function to check service logs
check_logs() {
    local service_name=$1
    local log_file=$2
    
    echo -e "${BLUE}Checking $service_name logs...${NC}"
    
    if [ -f "$log_file" ]; then
        echo -e "  ${GREEN}✓ Log file exists: $log_file${NC}"
        
        # Check for errors in logs
        local error_count=$(grep -i "error" "$log_file" | wc -l)
        if [ $error_count -gt 0 ]; then
            echo -e "  ${YELLOW}! Found $error_count error(s) in logs${NC}"
            echo -e "  ${YELLOW}! Last 3 errors:${NC}"
            grep -i "error" "$log_file" | tail -n 3 | sed 's/^/    /'
        else
            echo -e "  ${GREEN}✓ No errors found in logs${NC}"
        fi
        
        # Show last few log entries
        echo -e "  ${BLUE}ℹ Last 3 log entries:${NC}"
        tail -n 3 "$log_file" | sed 's/^/    /'
    else
        echo -e "  ${YELLOW}! Log file not found: $log_file${NC}"
    fi
}

# Display banner
echo "========================================================"
echo "  CryptoBot Services - Status Monitor"
echo "========================================================"
echo ""

# Check if running with sudo/root privileges
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: This script is running with root privileges.${NC}"
    echo ""
fi

# Check all services
echo "Checking service status..."
echo ""

# Check Auth service
check_service "Auth" "$AUTH_HOST" "$AUTH_PORT" "/tmp/cryptobot_auth.pid"
AUTH_STATUS=$?
check_logs "Auth" "./logs/auth_service.log"
echo ""

# Check Data service
check_service "Data" "$DATA_HOST" "$DATA_PORT" "/tmp/cryptobot_data.pid"
DATA_STATUS=$?
check_logs "Data" "./logs/data_service.log"
echo ""

# Check Strategy service
check_service "Strategy" "$STRATEGY_HOST" "$STRATEGY_PORT" "/tmp/cryptobot_strategy.pid"
STRATEGY_STATUS=$?
check_logs "Strategy" "./logs/strategy_service.log"
echo ""

# Check Backtest service
check_service "Backtest" "$BACKTEST_HOST" "$BACKTEST_PORT" "/tmp/cryptobot_backtest.pid"
BACKTEST_STATUS=$?
check_logs "Backtest" "./logs/backtest_service.log"
echo ""

# Check Trade service
check_service "Trade" "$TRADE_HOST" "$TRADE_PORT" "/tmp/cryptobot_trade.pid"
TRADE_STATUS=$?
check_logs "Trade" "./logs/trade_service.log"
echo ""

# Display summary
echo "========================================================"
echo "  Service Status Summary"
echo "========================================================"
echo ""

if [ $AUTH_STATUS -eq 0 ]; then
    echo -e "Auth Service:     ${GREEN}Running${NC}"
else
    echo -e "Auth Service:     ${RED}Not Running${NC}"
fi

if [ $DATA_STATUS -eq 0 ]; then
    echo -e "Data Service:     ${GREEN}Running${NC}"
else
    echo -e "Data Service:     ${RED}Not Running${NC}"
fi

if [ $STRATEGY_STATUS -eq 0 ]; then
    echo -e "Strategy Service: ${GREEN}Running${NC}"
else
    echo -e "Strategy Service: ${RED}Not Running${NC}"
fi

if [ $BACKTEST_STATUS -eq 0 ]; then
    echo -e "Backtest Service: ${GREEN}Running${NC}"
else
    echo -e "Backtest Service: ${RED}Not Running${NC}"
fi

if [ $TRADE_STATUS -eq 0 ]; then
    echo -e "Trade Service:    ${GREEN}Running${NC}"
else
    echo -e "Trade Service:    ${RED}Not Running${NC}"
fi

echo ""
echo "To start all services, run: ./scripts/non-docker-setup/start_all.sh"
echo "To stop all services, run: ./scripts/non-docker-setup/orchestrate_services.sh stop all"
echo ""