#!/bin/bash
# Master Test Script
# Runs all test scripts and generates a comprehensive report

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Master Test Script ====="
echo "Running all tests and generating reports..."

# Create output directory for logs
LOG_DIR="test_logs"
mkdir -p $LOG_DIR

# Get current timestamp for log filenames
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
MASTER_LOG="$LOG_DIR/master_test_log_$TIMESTAMP.txt"

# Function to run a test script and log results
run_test_script() {
    local script=$1
    local name=$2
    local log_file="$LOG_DIR/${name}_test_log_$TIMESTAMP.txt"
    
    echo "Running $name tests..."
    echo "===============================================" >> $MASTER_LOG
    echo "Running $name tests at $(date)" >> $MASTER_LOG
    echo "===============================================" >> $MASTER_LOG
    
    # Run the test script and capture output
    ./scripts/non-docker-tests/$script > $log_file 2>&1
    local exit_code=$?
    
    # Append log to master log
    cat $log_file >> $MASTER_LOG
    
    # Check if test passed or failed
    if [ $exit_code -eq 0 ]; then
        echo "✅ $name tests completed successfully."
        echo "✅ $name tests completed successfully." >> $MASTER_LOG
    else
        echo "❌ $name tests failed with exit code $exit_code."
        echo "❌ $name tests failed with exit code $exit_code." >> $MASTER_LOG
    fi
    
    echo "" >> $MASTER_LOG
    return $exit_code
}

# Initialize counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Start the master log
echo "===== Cryptobot Test Suite =====" > $MASTER_LOG
echo "Started at: $(date)" >> $MASTER_LOG
echo "Environment: $(uname -a)" >> $MASTER_LOG
echo "" >> $MASTER_LOG

# Check if all services are running
echo "Checking if all services are running..."
echo "Checking if all services are running..." >> $MASTER_LOG

SERVICES_RUNNING=true

if ! pgrep -f "auth/main.py" > /dev/null; then
    echo "Auth service is not running. Starting auth service..."
    echo "Auth service is not running. Starting auth service..." >> $MASTER_LOG
    ./scripts/non-docker-setup/start_auth.sh
    sleep 5
fi

if ! pgrep -f "strategy/main.py" > /dev/null; then
    echo "Strategy service is not running. Starting strategy service..."
    echo "Strategy service is not running. Starting strategy service..." >> $MASTER_LOG
    ./scripts/non-docker-setup/start_strategy.sh
    sleep 5
fi

if ! pgrep -f "backtest/main.py" > /dev/null; then
    echo "Backtest service is not running. Starting backtest service..."
    echo "Backtest service is not running. Starting backtest service..." >> $MASTER_LOG
    ./scripts/non-docker-setup/start_backtest.sh
    sleep 5
fi

if ! pgrep -f "trade/main.py" > /dev/null; then
    echo "Trade service is not running. Starting trade service..."
    echo "Trade service is not running. Starting trade service..." >> $MASTER_LOG
    ./scripts/non-docker-setup/start_trade.sh
    sleep 5
fi

if ! pgrep -f "data/main.py" > /dev/null; then
    echo "Data service is not running. Starting data service..."
    echo "Data service is not running. Starting data service..." >> $MASTER_LOG
    ./scripts/non-docker-setup/start_data.sh
    sleep 5
fi

echo "All services are running."
echo "All services are running." >> $MASTER_LOG
echo "" >> $MASTER_LOG

# Run individual service tests
echo "Running individual service tests..."
echo "Running individual service tests..." >> $MASTER_LOG

# Auth service tests
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_auth.sh" "auth"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Strategy service tests
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_strategy.sh" "strategy"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Backtest service tests
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_backtest.sh" "backtest"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Trade service tests
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_trade.sh" "trade"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Data service tests
TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_data.sh" "data"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Run integration tests
echo "Running integration tests..."
echo "Running integration tests..." >> $MASTER_LOG

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_integration.sh" "integration"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Run performance tests
echo "Running performance tests..."
echo "Running performance tests..." >> $MASTER_LOG

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "test_performance.sh" "performance"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Generate test report
echo "Generating test report..."
echo "Generating test report..." >> $MASTER_LOG

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "generate_test_report.sh" "report"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Run performance optimization
echo "Running performance optimization..."
echo "Running performance optimization..." >> $MASTER_LOG

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if run_test_script "optimize_performance.sh" "optimization"; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Calculate success rate
SUCCESS_RATE=$(echo "scale=2; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)

# Print summary
echo ""
echo "===== Test Summary ====="
echo "Total tests: $TOTAL_TESTS"
echo "Passed tests: $PASSED_TESTS"
echo "Failed tests: $FAILED_TESTS"
echo "Success rate: $SUCCESS_RATE%"

# Add summary to master log
echo "" >> $MASTER_LOG
echo "===== Test Summary =====" >> $MASTER_LOG
echo "Total tests: $TOTAL_TESTS" >> $MASTER_LOG
echo "Passed tests: $PASSED_TESTS" >> $MASTER_LOG
echo "Failed tests: $FAILED_TESTS" >> $MASTER_LOG
echo "Success rate: $SUCCESS_RATE%" >> $MASTER_LOG
echo "Completed at: $(date)" >> $MASTER_LOG

echo "Master log file: $MASTER_LOG"
echo "All tests completed."
echo "===== Master Test Script Complete ====="