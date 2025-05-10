#!/bin/bash
# Master Startup Script for CryptoBot Services

# Set script to exit immediately if a command exits with a non-zero status
set -e

# Display banner
echo "========================================================"
echo "  CryptoBot Services - Master Startup Script"
echo "========================================================"
echo ""

# Check if running with sudo/root privileges
if [ "$EUID" -eq 0 ]; then
    echo "Warning: This script is running with root privileges."
    echo "It's recommended to run this script as a regular user."
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting."
        exit 1
    fi
fi

# Check for required dependencies
echo "Checking dependencies..."
command -v python3 >/dev/null 2>&1 || { echo "Python3 is required but not installed. Aborting."; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "Pip3 is required but not installed. Aborting."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "Curl is required but not installed. Aborting."; exit 1; }

# Create logs directory if it doesn't exist
mkdir -p logs

# Load environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found. Using default environment variables."
fi

# Make orchestration script executable
chmod +x ./scripts/non-docker-setup/orchestrate_services.sh

# Start all services using the orchestration script
echo "Starting all services..."
./scripts/non-docker-setup/orchestrate_services.sh start all

# Check if all services started successfully
echo "Checking if all services are running..."
./scripts/non-docker-setup/orchestrate_services.sh status

echo ""
echo "========================================================"
echo "  CryptoBot Services - Startup Complete"
echo "========================================================"
echo ""
echo "Services are now running with the following endpoints:"
echo "- Auth Service:     http://${AUTH_HOST:-0.0.0.0}:${AUTH_PORT:-8000}"
echo "- Data Service:     http://${DATA_HOST:-0.0.0.0}:${DATA_PORT:-8001}"
echo "- Strategy Service: http://${STRATEGY_HOST:-0.0.0.0}:${STRATEGY_PORT:-8002}"
echo "- Backtest Service: http://${BACKTEST_HOST:-0.0.0.0}:${BACKTEST_PORT:-8003}"
echo "- Trade Service:    http://${TRADE_HOST:-0.0.0.0}:${TRADE_PORT:-8004}"
echo ""
echo "To stop all services, run: ./scripts/non-docker-setup/orchestrate_services.sh stop all"
echo "To check service status, run: ./scripts/non-docker-setup/orchestrate_services.sh status"
echo ""