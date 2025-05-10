#!/bin/bash
# Test Result Reporting Script
# Generates comprehensive test reports from test results

# Set environment variables
export PYTHONPATH=$(pwd)

echo "===== Test Result Report Generation ====="
echo "Generating test reports..."

# Create output directory for reports
REPORT_DIR="test_reports"
mkdir -p $REPORT_DIR

# Get current timestamp for report filenames
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
REPORT_FILE="$REPORT_DIR/test_report_$TIMESTAMP.md"
HTML_REPORT_FILE="$REPORT_DIR/test_report_$TIMESTAMP.html"
JSON_REPORT_FILE="$REPORT_DIR/test_report_$TIMESTAMP.json"

# Function to run tests and capture results
run_tests_and_capture() {
    local service=$1
    local output_file="$REPORT_DIR/${service}_test_output.txt"
    
    echo "Running tests for $service service..."
    ./scripts/non-docker-tests/test_$service.sh > $output_file 2>&1
    
    # Extract test results
    local total_tests=$(grep -c "test" $output_file)
    local passed_tests=$(grep -c "PASSED" $output_file)
    local failed_tests=$(grep -c "FAILED" $output_file)
    local skipped_tests=$(grep -c "SKIPPED" $output_file)
    
    # Calculate success rate
    local success_rate=0
    if [ $total_tests -gt 0 ]; then
        success_rate=$(echo "scale=2; $passed_tests * 100 / $total_tests" | bc)
    fi
    
    # Return results as JSON
    echo "{\"service\":\"$service\",\"total\":$total_tests,\"passed\":$passed_tests,\"failed\":$failed_tests,\"skipped\":$skipped_tests,\"success_rate\":$success_rate}"
}

# Function to run performance tests and capture results
run_performance_tests() {
    local output_file="$REPORT_DIR/performance_test_output.txt"
    
    echo "Running performance tests..."
    ./scripts/non-docker-tests/test_performance.sh > $output_file 2>&1
    
    # Extract performance metrics
    local auth_rps=$(grep "Auth service performance:" $output_file | awk '{print $4}')
    local data_rps=$(grep "Data service performance:" $output_file | awk '{print $4}')
    local strategy_rps=$(grep "Strategy service performance:" $output_file | awk '{print $4}')
    local trade_rps=$(grep "Trade service performance:" $output_file | awk '{print $4}')
    local backtest_rps=$(grep "Backtest service performance:" $output_file | awk '{print $4}')
    
    # Return results as JSON
    echo "{\"auth_rps\":$auth_rps,\"data_rps\":$data_rps,\"strategy_rps\":$strategy_rps,\"trade_rps\":$trade_rps,\"backtest_rps\":$backtest_rps}"
}

# Function to run integration tests and capture results
run_integration_tests() {
    local output_file="$REPORT_DIR/integration_test_output.txt"
    
    echo "Running integration tests..."
    ./scripts/non-docker-tests/test_integration.sh > $output_file 2>&1
    
    # Extract integration test results
    local total_tests=$(grep -c "test" $output_file)
    local passed_tests=$(grep -c "Successfully" $output_file)
    local failed_tests=$(grep -c "Failed" $output_file)
    
    # Calculate success rate
    local success_rate=0
    if [ $total_tests -gt 0 ]; then
        success_rate=$(echo "scale=2; $passed_tests * 100 / $total_tests" | bc)
    fi
    
    # Return results as JSON
    echo "{\"total\":$total_tests,\"passed\":$passed_tests,\"failed\":$failed_tests,\"success_rate\":$success_rate}"
}

# Run all tests and collect results
echo "Running all tests and collecting results..."

# Run individual service tests
AUTH_RESULTS=$(run_tests_and_capture "auth")
STRATEGY_RESULTS=$(run_tests_and_capture "strategy")
BACKTEST_RESULTS=$(run_tests_and_capture "backtest")
TRADE_RESULTS=$(run_tests_and_capture "trade")
DATA_RESULTS=$(run_tests_and_capture "data")

# Run integration tests
INTEGRATION_RESULTS=$(run_integration_tests)

# Run performance tests
PERFORMANCE_RESULTS=$(run_performance_tests)

# Create JSON report
echo "Creating JSON report..."
cat > $JSON_REPORT_FILE << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "individual_services": {
    "auth": $AUTH_RESULTS,
    "strategy": $STRATEGY_RESULTS,
    "backtest": $BACKTEST_RESULTS,
    "trade": $TRADE_RESULTS,
    "data": $DATA_RESULTS
  },
  "integration": $INTEGRATION_RESULTS,
  "performance": $PERFORMANCE_RESULTS
}
EOF

# Extract values for markdown report
AUTH_TOTAL=$(echo $AUTH_RESULTS | jq -r '.total')
AUTH_PASSED=$(echo $AUTH_RESULTS | jq -r '.passed')
AUTH_FAILED=$(echo $AUTH_RESULTS | jq -r '.failed')
AUTH_SUCCESS_RATE=$(echo $AUTH_RESULTS | jq -r '.success_rate')

STRATEGY_TOTAL=$(echo $STRATEGY_RESULTS | jq -r '.total')
STRATEGY_PASSED=$(echo $STRATEGY_RESULTS | jq -r '.passed')
STRATEGY_FAILED=$(echo $STRATEGY_RESULTS | jq -r '.failed')
STRATEGY_SUCCESS_RATE=$(echo $STRATEGY_RESULTS | jq -r '.success_rate')

BACKTEST_TOTAL=$(echo $BACKTEST_RESULTS | jq -r '.total')
BACKTEST_PASSED=$(echo $BACKTEST_RESULTS | jq -r '.passed')
BACKTEST_FAILED=$(echo $BACKTEST_RESULTS | jq -r '.failed')
BACKTEST_SUCCESS_RATE=$(echo $BACKTEST_RESULTS | jq -r '.success_rate')

TRADE_TOTAL=$(echo $TRADE_RESULTS | jq -r '.total')
TRADE_PASSED=$(echo $TRADE_RESULTS | jq -r '.passed')
TRADE_FAILED=$(echo $TRADE_RESULTS | jq -r '.failed')
TRADE_SUCCESS_RATE=$(echo $TRADE_RESULTS | jq -r '.success_rate')

DATA_TOTAL=$(echo $DATA_RESULTS | jq -r '.total')
DATA_PASSED=$(echo $DATA_RESULTS | jq -r '.passed')
DATA_FAILED=$(echo $DATA_RESULTS | jq -r '.failed')
DATA_SUCCESS_RATE=$(echo $DATA_RESULTS | jq -r '.success_rate')

INTEGRATION_TOTAL=$(echo $INTEGRATION_RESULTS | jq -r '.total')
INTEGRATION_PASSED=$(echo $INTEGRATION_RESULTS | jq -r '.passed')
INTEGRATION_FAILED=$(echo $INTEGRATION_RESULTS | jq -r '.failed')
INTEGRATION_SUCCESS_RATE=$(echo $INTEGRATION_RESULTS | jq -r '.success_rate')

AUTH_RPS=$(echo $PERFORMANCE_RESULTS | jq -r '.auth_rps')
DATA_RPS=$(echo $PERFORMANCE_RESULTS | jq -r '.data_rps')
STRATEGY_RPS=$(echo $PERFORMANCE_RESULTS | jq -r '.strategy_rps')
TRADE_RPS=$(echo $PERFORMANCE_RESULTS | jq -r '.trade_rps')
BACKTEST_RPS=$(echo $PERFORMANCE_RESULTS | jq -r '.backtest_rps')

# Create markdown report
echo "Creating markdown report..."
cat > $REPORT_FILE << EOF
# Cryptobot Test Report

**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Summary

| Service | Total Tests | Passed | Failed | Success Rate |
|---------|------------|--------|--------|-------------|
| Auth | $AUTH_TOTAL | $AUTH_PASSED | $AUTH_FAILED | $AUTH_SUCCESS_RATE% |
| Strategy | $STRATEGY_TOTAL | $STRATEGY_PASSED | $STRATEGY_FAILED | $STRATEGY_SUCCESS_RATE% |
| Backtest | $BACKTEST_TOTAL | $BACKTEST_PASSED | $BACKTEST_FAILED | $BACKTEST_SUCCESS_RATE% |
| Trade | $TRADE_TOTAL | $TRADE_PASSED | $TRADE_FAILED | $TRADE_SUCCESS_RATE% |
| Data | $DATA_TOTAL | $DATA_PASSED | $DATA_FAILED | $DATA_SUCCESS_RATE% |
| Integration | $INTEGRATION_TOTAL | $INTEGRATION_PASSED | $INTEGRATION_FAILED | $INTEGRATION_SUCCESS_RATE% |

## Performance Metrics

| Service | Requests/Second |
|---------|----------------|
| Auth | $AUTH_RPS |
| Data | $DATA_RPS |
| Strategy | $STRATEGY_RPS |
| Trade | $TRADE_RPS |
| Backtest | $BACKTEST_RPS |

## Detailed Results

### Auth Service
$(cat $REPORT_DIR/auth_test_output.txt | grep -E "PASSED|FAILED|SKIPPED" | sed 's/^/- /')

### Strategy Service
$(cat $REPORT_DIR/strategy_test_output.txt | grep -E "PASSED|FAILED|SKIPPED" | sed 's/^/- /')

### Backtest Service
$(cat $REPORT_DIR/backtest_test_output.txt | grep -E "PASSED|FAILED|SKIPPED" | sed 's/^/- /')

### Trade Service
$(cat $REPORT_DIR/trade_test_output.txt | grep -E "PASSED|FAILED|SKIPPED" | sed 's/^/- /')

### Data Service
$(cat $REPORT_DIR/data_test_output.txt | grep -E "PASSED|FAILED|SKIPPED" | sed 's/^/- /')

### Integration Tests
$(cat $REPORT_DIR/integration_test_output.txt | grep -E "Successfully|Failed" | sed 's/^/- /')

## Recommendations

$(if [ $(echo "$AUTH_SUCCESS_RATE < 90" | bc -l) -eq 1 ]; then echo "- Auth service needs improvement"; fi)
$(if [ $(echo "$STRATEGY_SUCCESS_RATE < 90" | bc -l) -eq 1 ]; then echo "- Strategy service needs improvement"; fi)
$(if [ $(echo "$BACKTEST_SUCCESS_RATE < 90" | bc -l) -eq 1 ]; then echo "- Backtest service needs improvement"; fi)
$(if [ $(echo "$TRADE_SUCCESS_RATE < 90" | bc -l) -eq 1 ]; then echo "- Trade service needs improvement"; fi)
$(if [ $(echo "$DATA_SUCCESS_RATE < 90" | bc -l) -eq 1 ]; then echo "- Data service needs improvement"; fi)
$(if [ $(echo "$INTEGRATION_SUCCESS_RATE < 90" | bc -l) -eq 1 ]; then echo "- Integration between services needs improvement"; fi)
$(if [ $(echo "$AUTH_RPS < 10" | bc -l) -eq 1 ]; then echo "- Auth service performance needs optimization"; fi)
$(if [ $(echo "$DATA_RPS < 10" | bc -l) -eq 1 ]; then echo "- Data service performance needs optimization"; fi)
$(if [ $(echo "$STRATEGY_RPS < 5" | bc -l) -eq 1 ]; then echo "- Strategy service performance needs optimization"; fi)
$(if [ $(echo "$TRADE_RPS < 5" | bc -l) -eq 1 ]; then echo "- Trade service performance needs optimization"; fi)
$(if [ $(echo "$BACKTEST_RPS < 1" | bc -l) -eq 1 ]; then echo "- Backtest service performance needs optimization"; fi)

EOF

# Convert markdown to HTML
echo "Converting markdown to HTML..."
pandoc -f markdown -t html $REPORT_FILE -o $HTML_REPORT_FILE

echo "Test reports generated:"
echo "- Markdown: $REPORT_FILE"
echo "- HTML: $HTML_REPORT_FILE"
echo "- JSON: $JSON_REPORT_FILE"

echo "===== Test Result Report Generation Complete ====="