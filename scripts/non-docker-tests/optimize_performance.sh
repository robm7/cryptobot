#!/bin/bash
# Performance Optimization Script
# Analyzes system performance and suggests optimizations

# Set environment variables
export PYTHONPATH=$(pwd)

echo "===== Performance Optimization ====="
echo "Analyzing system performance and suggesting optimizations..."

# Create output directory for reports
REPORT_DIR="optimization_reports"
mkdir -p $REPORT_DIR

# Get current timestamp for report filenames
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
REPORT_FILE="$REPORT_DIR/optimization_report_$TIMESTAMP.md"
HTML_REPORT_FILE="$REPORT_DIR/optimization_report_$TIMESTAMP.html"

# Function to check system resources
check_system_resources() {
    echo "Checking system resources..."
    
    # CPU info
    CPU_INFO=$(lscpu | grep "Model name" | sed 's/Model name: *//')
    CPU_CORES=$(nproc)
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    
    # Memory info
    TOTAL_MEM=$(free -m | awk '/Mem:/ {print $2}')
    USED_MEM=$(free -m | awk '/Mem:/ {print $3}')
    MEM_USAGE=$(free | awk '/Mem:/ {print $3/$2 * 100.0}')
    
    # Disk info
    DISK_USAGE=$(df -h | grep -v "tmpfs" | grep -v "udev" | awk '{print $5}' | grep -v "Use%" | sort -nr | head -1 | sed 's/%//')
    
    # Network info
    NETWORK_CONNECTIONS=$(netstat -an | grep ESTABLISHED | wc -l)
    
    echo "CPU: $CPU_INFO ($CPU_CORES cores, $CPU_USAGE% usage)"
    echo "Memory: $USED_MEM MB / $TOTAL_MEM MB ($MEM_USAGE% usage)"
    echo "Disk: $DISK_USAGE% usage"
    echo "Network: $NETWORK_CONNECTIONS established connections"
    
    # Return results as JSON
    cat << EOF
{
  "cpu": {
    "model": "$CPU_INFO",
    "cores": $CPU_CORES,
    "usage": $CPU_USAGE
  },
  "memory": {
    "total": $TOTAL_MEM,
    "used": $USED_MEM,
    "usage": $MEM_USAGE
  },
  "disk": {
    "usage": $DISK_USAGE
  },
  "network": {
    "connections": $NETWORK_CONNECTIONS
  }
}
EOF
}

# Function to check database performance
check_database_performance() {
    echo "Checking database performance..."
    
    # Run database performance tests
    python -c "
import time
import sqlite3
from database.session import get_session
from sqlalchemy import text

# Test SQLAlchemy ORM performance
start_time = time.time()
session = get_session()
result = session.execute(text('SELECT 1'))
session.close()
orm_time = time.time() - start_time

# Test raw SQLite performance
start_time = time.time()
conn = sqlite3.connect('instance/cryptobot.db')
cursor = conn.cursor()
cursor.execute('SELECT 1')
conn.close()
raw_time = time.time() - start_time

# Print results
print(f'ORM query time: {orm_time:.6f} seconds')
print(f'Raw query time: {raw_time:.6f} seconds')
print(f'ORM overhead: {(orm_time/raw_time):.2f}x')
" > $REPORT_DIR/db_performance.txt
    
    # Extract results
    ORM_TIME=$(grep "ORM query time:" $REPORT_DIR/db_performance.txt | awk '{print $4}')
    RAW_TIME=$(grep "Raw query time:" $REPORT_DIR/db_performance.txt | awk '{print $4}')
    ORM_OVERHEAD=$(grep "ORM overhead:" $REPORT_DIR/db_performance.txt | awk '{print $3}')
    
    echo "ORM query time: $ORM_TIME seconds"
    echo "Raw query time: $RAW_TIME seconds"
    echo "ORM overhead: $ORM_OVERHEAD"
    
    # Return results as JSON
    cat << EOF
{
  "orm_time": $ORM_TIME,
  "raw_time": $RAW_TIME,
  "orm_overhead": $ORM_OVERHEAD
}
EOF
}

# Function to check API endpoint performance
check_api_performance() {
    echo "Checking API endpoint performance..."
    
    # Get auth token
    TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$TOKEN" ]; then
        echo "Failed to get access token."
        return 1
    fi
    
    # Test endpoints
    ENDPOINTS=(
        "auth/protected"
        "strategy"
        "backtest"
        "trade"
        "data/historical?symbol=BTCUSDT&timeframe=1h&limit=10"
    )
    
    echo "Testing API endpoint performance..."
    echo "Endpoint,Response Time (ms)" > $REPORT_DIR/api_performance.csv
    
    for ENDPOINT in "${ENDPOINTS[@]}"; do
        echo "Testing $ENDPOINT..."
        START_TIME=$(date +%s.%N)
        curl -s -X GET "http://localhost:8000/$ENDPOINT" -H "Authorization: Bearer $TOKEN" > /dev/null
        END_TIME=$(date +%s.%N)
        DURATION=$(echo "($END_TIME - $START_TIME) * 1000" | bc)
        echo "$ENDPOINT,$DURATION" >> $REPORT_DIR/api_performance.csv
        echo "$ENDPOINT: $DURATION ms"
    done
    
    # Calculate average response time
    AVERAGE_TIME=$(awk -F',' 'NR>1 {sum+=$2; count++} END {print sum/count}' $REPORT_DIR/api_performance.csv)
    echo "Average response time: $AVERAGE_TIME ms"
    
    # Find slowest endpoint
    SLOWEST_ENDPOINT=$(awk -F',' 'NR>1 {if(max<$2){max=$2; endpoint=$1}} END {print endpoint}' $REPORT_DIR/api_performance.csv)
    SLOWEST_TIME=$(awk -F',' 'NR>1 {if(max<$2){max=$2}} END {print max}' $REPORT_DIR/api_performance.csv)
    echo "Slowest endpoint: $SLOWEST_ENDPOINT ($SLOWEST_TIME ms)"
    
    # Return results as JSON
    cat << EOF
{
  "average_time": $AVERAGE_TIME,
  "slowest_endpoint": "$SLOWEST_ENDPOINT",
  "slowest_time": $SLOWEST_TIME,
  "endpoints": [
$(awk -F',' 'NR>1 {print "    {\"endpoint\": \""$1"\", \"time\": "$2"},"} END {print "    {\"endpoint\": \"dummy\", \"time\": 0}"}' $REPORT_DIR/api_performance.csv | sed '$s/,$//')
  ]
}
EOF
}

# Function to check service resource usage
check_service_resource_usage() {
    echo "Checking service resource usage..."
    
    # Get process IDs for each service
    AUTH_PID=$(pgrep -f "auth/main.py" | head -1)
    STRATEGY_PID=$(pgrep -f "strategy/main.py" | head -1)
    BACKTEST_PID=$(pgrep -f "backtest/main.py" | head -1)
    TRADE_PID=$(pgrep -f "trade/main.py" | head -1)
    DATA_PID=$(pgrep -f "data/main.py" | head -1)
    
    # Check CPU and memory usage for each service
    echo "Service,PID,CPU %,Memory %" > $REPORT_DIR/service_resource_usage.csv
    
    if [ ! -z "$AUTH_PID" ]; then
        AUTH_CPU=$(ps -p $AUTH_PID -o %cpu | tail -1 | tr -d ' ')
        AUTH_MEM=$(ps -p $AUTH_PID -o %mem | tail -1 | tr -d ' ')
        echo "Auth,$AUTH_PID,$AUTH_CPU,$AUTH_MEM" >> $REPORT_DIR/service_resource_usage.csv
        echo "Auth service: $AUTH_CPU% CPU, $AUTH_MEM% memory"
    fi
    
    if [ ! -z "$STRATEGY_PID" ]; then
        STRATEGY_CPU=$(ps -p $STRATEGY_PID -o %cpu | tail -1 | tr -d ' ')
        STRATEGY_MEM=$(ps -p $STRATEGY_PID -o %mem | tail -1 | tr -d ' ')
        echo "Strategy,$STRATEGY_PID,$STRATEGY_CPU,$STRATEGY_MEM" >> $REPORT_DIR/service_resource_usage.csv
        echo "Strategy service: $STRATEGY_CPU% CPU, $STRATEGY_MEM% memory"
    fi
    
    if [ ! -z "$BACKTEST_PID" ]; then
        BACKTEST_CPU=$(ps -p $BACKTEST_PID -o %cpu | tail -1 | tr -d ' ')
        BACKTEST_MEM=$(ps -p $BACKTEST_PID -o %mem | tail -1 | tr -d ' ')
        echo "Backtest,$BACKTEST_PID,$BACKTEST_CPU,$BACKTEST_MEM" >> $REPORT_DIR/service_resource_usage.csv
        echo "Backtest service: $BACKTEST_CPU% CPU, $BACKTEST_MEM% memory"
    fi
    
    if [ ! -z "$TRADE_PID" ]; then
        TRADE_CPU=$(ps -p $TRADE_PID -o %cpu | tail -1 | tr -d ' ')
        TRADE_MEM=$(ps -p $TRADE_PID -o %mem | tail -1 | tr -d ' ')
        echo "Trade,$TRADE_PID,$TRADE_CPU,$TRADE_MEM" >> $REPORT_DIR/service_resource_usage.csv
        echo "Trade service: $TRADE_CPU% CPU, $TRADE_MEM% memory"
    fi
    
    if [ ! -z "$DATA_PID" ]; then
        DATA_CPU=$(ps -p $DATA_PID -o %cpu | tail -1 | tr -d ' ')
        DATA_MEM=$(ps -p $DATA_PID -o %mem | tail -1 | tr -d ' ')
        echo "Data,$DATA_PID,$DATA_CPU,$DATA_MEM" >> $REPORT_DIR/service_resource_usage.csv
        echo "Data service: $DATA_CPU% CPU, $DATA_MEM% memory"
    fi
    
    # Find service with highest CPU and memory usage
    HIGHEST_CPU_SERVICE=$(awk -F',' 'NR>1 {if(max<$3){max=$3; service=$1}} END {print service}' $REPORT_DIR/service_resource_usage.csv)
    HIGHEST_CPU=$(awk -F',' 'NR>1 {if(max<$3){max=$3}} END {print max}' $REPORT_DIR/service_resource_usage.csv)
    
    HIGHEST_MEM_SERVICE=$(awk -F',' 'NR>1 {if(max<$4){max=$4; service=$1}} END {print service}' $REPORT_DIR/service_resource_usage.csv)
    HIGHEST_MEM=$(awk -F',' 'NR>1 {if(max<$4){max=$4}} END {print max}' $REPORT_DIR/service_resource_usage.csv)
    
    echo "Service with highest CPU usage: $HIGHEST_CPU_SERVICE ($HIGHEST_CPU%)"
    echo "Service with highest memory usage: $HIGHEST_MEM_SERVICE ($HIGHEST_MEM%)"
    
    # Return results as JSON
    cat << EOF
{
  "highest_cpu": {
    "service": "$HIGHEST_CPU_SERVICE",
    "usage": $HIGHEST_CPU
  },
  "highest_memory": {
    "service": "$HIGHEST_MEM_SERVICE",
    "usage": $HIGHEST_MEM
  },
  "services": [
$(awk -F',' 'NR>1 {print "    {\"service\": \""$1"\", \"pid\": "$2", \"cpu\": "$3", \"memory\": "$4"},"} END {print "    {\"service\": \"dummy\", \"pid\": 0, \"cpu\": 0, \"memory\": 0}"}' $REPORT_DIR/service_resource_usage.csv | sed '$s/,$//')
  ]
}
EOF
}

# Function to generate optimization recommendations
generate_recommendations() {
    echo "Generating optimization recommendations..."
    
    # System resources
    CPU_USAGE=$(echo $SYSTEM_RESOURCES | jq -r '.cpu.usage')
    MEM_USAGE=$(echo $SYSTEM_RESOURCES | jq -r '.memory.usage')
    DISK_USAGE=$(echo $SYSTEM_RESOURCES | jq -r '.disk.usage')
    
    # Database performance
    ORM_OVERHEAD=$(echo $DB_PERFORMANCE | jq -r '.orm_overhead')
    
    # API performance
    SLOWEST_ENDPOINT=$(echo $API_PERFORMANCE | jq -r '.slowest_endpoint')
    SLOWEST_TIME=$(echo $API_PERFORMANCE | jq -r '.slowest_time')
    
    # Service resource usage
    HIGHEST_CPU_SERVICE=$(echo $SERVICE_USAGE | jq -r '.highest_cpu.service')
    HIGHEST_CPU=$(echo $SERVICE_USAGE | jq -r '.highest_cpu.usage')
    HIGHEST_MEM_SERVICE=$(echo $SERVICE_USAGE | jq -r '.highest_memory.service')
    HIGHEST_MEM=$(echo $SERVICE_USAGE | jq -r '.highest_memory.usage')
    
    # Generate recommendations
    RECOMMENDATIONS=()
    
    # System resource recommendations
    if [ $(echo "$CPU_USAGE > 80" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **High CPU Usage**: Consider upgrading CPU or optimizing CPU-intensive operations.")
    fi
    
    if [ $(echo "$MEM_USAGE > 80" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **High Memory Usage**: Consider adding more RAM or optimizing memory-intensive operations.")
    fi
    
    if [ $(echo "$DISK_USAGE > 80" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **High Disk Usage**: Consider adding more storage or cleaning up unnecessary files.")
    fi
    
    # Database recommendations
    if [ $(echo "$ORM_OVERHEAD > 2" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **High ORM Overhead**: Consider using raw SQL queries for performance-critical operations.")
    fi
    
    # API recommendations
    if [ $(echo "$SLOWEST_TIME > 500" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **Slow API Endpoint**: Optimize the '$SLOWEST_ENDPOINT' endpoint ($SLOWEST_TIME ms).")
    fi
    
    # Service recommendations
    if [ $(echo "$HIGHEST_CPU > 50" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **High CPU Service**: Optimize the $HIGHEST_CPU_SERVICE service ($HIGHEST_CPU% CPU).")
    fi
    
    if [ $(echo "$HIGHEST_MEM > 50" | bc -l) -eq 1 ]; then
        RECOMMENDATIONS+=("- **High Memory Service**: Optimize the $HIGHEST_MEM_SERVICE service ($HIGHEST_MEM% memory).")
    fi
    
    # General recommendations
    RECOMMENDATIONS+=(
        "- **Database Indexing**: Ensure proper indexes are created for frequently queried fields."
        "- **Connection Pooling**: Implement connection pooling for database connections."
        "- **Caching**: Implement caching for frequently accessed data."
        "- **Asynchronous Processing**: Use asynchronous processing for non-critical operations."
        "- **Load Balancing**: Consider implementing load balancing for high-traffic services."
    )
    
    # Return recommendations
    for REC in "${RECOMMENDATIONS[@]}"; do
        echo "$REC"
    done
}

# Run all checks and collect results
echo "Running all checks and collecting results..."

# Check system resources
echo "Checking system resources..."
SYSTEM_RESOURCES=$(check_system_resources)

# Check database performance
echo "Checking database performance..."
DB_PERFORMANCE=$(check_database_performance)

# Check API performance
echo "Checking API performance..."
API_PERFORMANCE=$(check_api_performance)

# Check service resource usage
echo "Checking service resource usage..."
SERVICE_USAGE=$(check_service_resource_usage)

# Generate recommendations
echo "Generating recommendations..."
RECOMMENDATIONS=$(generate_recommendations)

# Create optimization report
echo "Creating optimization report..."
cat > $REPORT_FILE << EOF
# Cryptobot Performance Optimization Report

**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## System Resources

- **CPU:** $(echo $SYSTEM_RESOURCES | jq -r '.cpu.model') ($(echo $SYSTEM_RESOURCES | jq -r '.cpu.cores') cores)
- **CPU Usage:** $(echo $SYSTEM_RESOURCES | jq -r '.cpu.usage')%
- **Memory:** $(echo $SYSTEM_RESOURCES | jq -r '.memory.used') MB / $(echo $SYSTEM_RESOURCES | jq -r '.memory.total') MB
- **Memory Usage:** $(echo $SYSTEM_RESOURCES | jq -r '.memory.usage')%
- **Disk Usage:** $(echo $SYSTEM_RESOURCES | jq -r '.disk.usage')%
- **Network Connections:** $(echo $SYSTEM_RESOURCES | jq -r '.network.connections')

## Database Performance

- **ORM Query Time:** $(echo $DB_PERFORMANCE | jq -r '.orm_time') seconds
- **Raw Query Time:** $(echo $DB_PERFORMANCE | jq -r '.raw_time') seconds
- **ORM Overhead:** $(echo $DB_PERFORMANCE | jq -r '.orm_overhead')x

## API Performance

- **Average Response Time:** $(echo $API_PERFORMANCE | jq -r '.average_time') ms
- **Slowest Endpoint:** $(echo $API_PERFORMANCE | jq -r '.slowest_endpoint') ($(echo $API_PERFORMANCE | jq -r '.slowest_time') ms)

### Endpoint Response Times

| Endpoint | Response Time (ms) |
|----------|-------------------|
$(echo $API_PERFORMANCE | jq -r '.endpoints[] | "| " + .endpoint + " | " + (.time | tostring) + " |"')

## Service Resource Usage

| Service | CPU % | Memory % |
|---------|-------|----------|
$(echo $SERVICE_USAGE | jq -r '.services[] | "| " + .service + " | " + (.cpu | tostring) + " | " + (.memory | tostring) + " |"')

- **Highest CPU Usage:** $(echo $SERVICE_USAGE | jq -r '.highest_cpu.service') ($(echo $SERVICE_USAGE | jq -r '.highest_cpu.usage')%)
- **Highest Memory Usage:** $(echo $SERVICE_USAGE | jq -r '.highest_memory.service') ($(echo $SERVICE_USAGE | jq -r '.highest_memory.usage')%)

## Optimization Recommendations

$RECOMMENDATIONS

## Implementation Plan

1. **Short-term Optimizations:**
   - Implement caching for frequently accessed data
   - Add database indexes for common queries
   - Optimize the slowest API endpoint

2. **Medium-term Optimizations:**
   - Implement connection pooling
   - Optimize high CPU/memory services
   - Add asynchronous processing for non-critical operations

3. **Long-term Optimizations:**
   - Consider scaling horizontally with load balancing
   - Evaluate database sharding for improved performance
   - Implement microservices architecture for better scalability
EOF

# Convert markdown to HTML
echo "Converting markdown to HTML..."
pandoc -f markdown -t html $REPORT_FILE -o $HTML_REPORT_FILE

echo "Optimization reports generated:"
echo "- Markdown: $REPORT_FILE"
echo "- HTML: $HTML_REPORT_FILE"

echo "===== Performance Optimization Complete ====="