#!/bin/bash
# verify_migration.sh
# Script to verify the successful completion of the migration from Docker to non-Docker
# Part of Phase 11: Parallel Operation Strategy

set -e

echo "=== Cryptobot Migration Verification Tool ==="
echo "This script verifies the successful completion of the migration from Docker to non-Docker."

# Check if environment variables are set
if [ -z "$CRYPTOBOT_SHARED_DATA_DIR" ]; then
    # Source environment file if it exists
    if [ -f "/opt/cryptobot/shared_data/config/environment.sh" ]; then
        source /opt/cryptobot/shared_data/config/environment.sh
    else
        echo "Error: CRYPTOBOT_SHARED_DATA_DIR environment variable not set."
        echo "Please run setup_parallel_env.sh first or set the variable manually."
        exit 1
    fi
fi

# Define directories and files
SHARED_DATA_DIR=${CRYPTOBOT_SHARED_DATA_DIR:-"/opt/cryptobot/shared_data"}
DOCKER_ENV_DIR="/opt/cryptobot/docker"
NON_DOCKER_ENV_DIR="/opt/cryptobot/non-docker"
LOG_DIR=${CRYPTOBOT_LOG_DIR:-"/var/log/cryptobot"}
VERIFY_LOG="$LOG_DIR/migration_verification.log"
VERIFY_REPORT="$SHARED_DATA_DIR/migration_verification_report.html"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log_message() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" | tee -a "$VERIFY_LOG"
}

# Function to check if a service is running
is_service_running() {
    local host=$1
    local port=$2
    nc -z "$host" "$port" >/dev/null 2>&1
    return $?
}

# Function to check if Docker is running
is_docker_running() {
    if command -v docker >/dev/null 2>&1; then
        if docker info >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check if Docker containers are running
check_docker_containers() {
    log_message "Checking Docker containers..."
    
    if ! is_docker_running; then
        log_message "Docker is not running."
        return 1
    fi
    
    local containers=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E 'cryptobot|auth|strategy|backtest|trade|data' | wc -l)
    
    if [ "$containers" -gt 0 ]; then
        log_message "Found $containers Docker containers still running."
        log_message "Docker containers should be stopped after successful migration."
        return 1
    else
        log_message "No Docker containers running. Good."
        return 0
    fi
}

# Function to check non-Docker services
check_non_docker_services() {
    log_message "Checking non-Docker services..."
    
    local all_running=true
    local services_status=()
    
    # Check auth service
    if is_service_running "localhost" "${CRYPTOBOT_NON_DOCKER_AUTH_PORT:-9000}"; then
        log_message "Auth service: RUNNING"
        services_status+=("Auth service: ✅ RUNNING")
    else
        log_message "Auth service: NOT RUNNING"
        services_status+=("Auth service: ❌ NOT RUNNING")
        all_running=false
    fi
    
    # Check strategy service
    if is_service_running "localhost" "${CRYPTOBOT_NON_DOCKER_STRATEGY_PORT:-9001}"; then
        log_message "Strategy service: RUNNING"
        services_status+=("Strategy service: ✅ RUNNING")
    else
        log_message "Strategy service: NOT RUNNING"
        services_status+=("Strategy service: ❌ NOT RUNNING")
        all_running=false
    fi
    
    # Check backtest service
    if is_service_running "localhost" "${CRYPTOBOT_NON_DOCKER_BACKTEST_PORT:-9002}"; then
        log_message "Backtest service: RUNNING"
        services_status+=("Backtest service: ✅ RUNNING")
    else
        log_message "Backtest service: NOT RUNNING"
        services_status+=("Backtest service: ❌ NOT RUNNING")
        all_running=false
    fi
    
    # Check trade service
    if is_service_running "localhost" "${CRYPTOBOT_NON_DOCKER_TRADE_PORT:-9003}"; then
        log_message "Trade service: RUNNING"
        services_status+=("Trade service: ✅ RUNNING")
    else
        log_message "Trade service: NOT RUNNING"
        services_status+=("Trade service: ❌ NOT RUNNING")
        all_running=false
    fi
    
    # Check data service
    if is_service_running "localhost" "${CRYPTOBOT_NON_DOCKER_DATA_PORT:-9004}"; then
        log_message "Data service: RUNNING"
        services_status+=("Data service: ✅ RUNNING")
    else
        log_message "Data service: NOT RUNNING"
        services_status+=("Data service: ❌ NOT RUNNING")
        all_running=false
    fi
    
    # Return results
    if $all_running; then
        log_message "All non-Docker services are running."
        SERVICES_STATUS_ARRAY=("${services_status[@]}")
        return 0
    else
        log_message "Some non-Docker services are not running."
        SERVICES_STATUS_ARRAY=("${services_status[@]}")
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    log_message "Checking database connectivity..."
    
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log_message "Database: CONNECTED"
        DATABASE_STATUS="Database: ✅ CONNECTED"
        return 0
    else
        log_message "Database: NOT CONNECTED"
        DATABASE_STATUS="Database: ❌ NOT CONNECTED"
        return 1
    fi
}

# Function to check Redis connectivity
check_redis() {
    log_message "Checking Redis connectivity..."
    
    if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
        log_message "Redis: CONNECTED"
        REDIS_STATUS="Redis: ✅ CONNECTED"
        return 0
    else
        log_message "Redis: NOT CONNECTED"
        REDIS_STATUS="Redis: ❌ NOT CONNECTED"
        return 1
    fi
}

# Function to check API endpoints
check_api_endpoints() {
    log_message "Checking API endpoints..."
    
    local all_endpoints_ok=true
    local endpoints_status=()
    
    # Check auth API
    local auth_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CRYPTOBOT_NON_DOCKER_AUTH_PORT:-9000}/health")
    if [ "$auth_status" == "200" ]; then
        log_message "Auth API: OK (Status: $auth_status)"
        endpoints_status+=("Auth API: ✅ OK (Status: $auth_status)")
    else
        log_message "Auth API: FAILED (Status: $auth_status)"
        endpoints_status+=("Auth API: ❌ FAILED (Status: $auth_status)")
        all_endpoints_ok=false
    fi
    
    # Check strategy API
    local strategy_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CRYPTOBOT_NON_DOCKER_STRATEGY_PORT:-9001}/health")
    if [ "$strategy_status" == "200" ]; then
        log_message "Strategy API: OK (Status: $strategy_status)"
        endpoints_status+=("Strategy API: ✅ OK (Status: $strategy_status)")
    else
        log_message "Strategy API: FAILED (Status: $strategy_status)"
        endpoints_status+=("Strategy API: ❌ FAILED (Status: $strategy_status)")
        all_endpoints_ok=false
    fi
    
    # Check backtest API
    local backtest_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CRYPTOBOT_NON_DOCKER_BACKTEST_PORT:-9002}/health")
    if [ "$backtest_status" == "200" ]; then
        log_message "Backtest API: OK (Status: $backtest_status)"
        endpoints_status+=("Backtest API: ✅ OK (Status: $backtest_status)")
    else
        log_message "Backtest API: FAILED (Status: $backtest_status)"
        endpoints_status+=("Backtest API: ❌ FAILED (Status: $backtest_status)")
        all_endpoints_ok=false
    fi
    
    # Check trade API
    local trade_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CRYPTOBOT_NON_DOCKER_TRADE_PORT:-9003}/health")
    if [ "$trade_status" == "200" ]; then
        log_message "Trade API: OK (Status: $trade_status)"
        endpoints_status+=("Trade API: ✅ OK (Status: $trade_status)")
    else
        log_message "Trade API: FAILED (Status: $trade_status)"
        endpoints_status+=("Trade API: ❌ FAILED (Status: $trade_status)")
        all_endpoints_ok=false
    fi
    
    # Check data API
    local data_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CRYPTOBOT_NON_DOCKER_DATA_PORT:-9004}/health")
    if [ "$data_status" == "200" ]; then
        log_message "Data API: OK (Status: $data_status)"
        endpoints_status+=("Data API: ✅ OK (Status: $data_status)")
    else
        log_message "Data API: FAILED (Status: $data_status)"
        endpoints_status+=("Data API: ❌ FAILED (Status: $data_status)")
        all_endpoints_ok=false
    fi
    
    # Return results
    if $all_endpoints_ok; then
        log_message "All API endpoints are accessible."
        API_STATUS_ARRAY=("${endpoints_status[@]}")
        return 0
    else
        log_message "Some API endpoints are not accessible."
        API_STATUS_ARRAY=("${endpoints_status[@]}")
        return 1
    fi
}

# Function to check data integrity
check_data_integrity() {
    log_message "Checking data integrity..."
    
    local all_data_ok=true
    local data_status=()
    
    # Check database tables
    if psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" >/dev/null 2>&1; then
        local table_count=$(psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        log_message "Database tables: $table_count tables found"
        data_status+=("Database tables: ✅ $table_count tables found")
    else
        log_message "Database tables: FAILED to query"
        data_status+=("Database tables: ❌ FAILED to query")
        all_data_ok=false
    fi
    
    # Check user accounts
    if psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -c "SELECT COUNT(*) FROM users;" >/dev/null 2>&1; then
        local user_count=$(psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -t -c "SELECT COUNT(*) FROM users;")
        log_message "User accounts: $user_count accounts found"
        data_status+=("User accounts: ✅ $user_count accounts found")
    else
        log_message "User accounts: FAILED to query"
        data_status+=("User accounts: ❌ FAILED to query")
        all_data_ok=false
    fi
    
    # Check strategies
    if psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -c "SELECT COUNT(*) FROM strategies;" >/dev/null 2>&1; then
        local strategy_count=$(psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -t -c "SELECT COUNT(*) FROM strategies;")
        log_message "Strategies: $strategy_count strategies found"
        data_status+=("Strategies: ✅ $strategy_count strategies found")
    else
        log_message "Strategies: FAILED to query"
        data_status+=("Strategies: ❌ FAILED to query")
        all_data_ok=false
    fi
    
    # Check historical data files
    if [ -d "$SHARED_DATA_DIR/historical_data" ]; then
        local file_count=$(find "$SHARED_DATA_DIR/historical_data" -type f | wc -l)
        log_message "Historical data files: $file_count files found"
        data_status+=("Historical data files: ✅ $file_count files found")
    else
        log_message "Historical data files: Directory not found"
        data_status+=("Historical data files: ❌ Directory not found")
        all_data_ok=false
    fi
    
    # Check user data files
    if [ -d "$SHARED_DATA_DIR/user_data" ]; then
        local file_count=$(find "$SHARED_DATA_DIR/user_data" -type f | wc -l)
        log_message "User data files: $file_count files found"
        data_status+=("User data files: ✅ $file_count files found")
    else
        log_message "User data files: Directory not found"
        data_status+=("User data files: ❌ Directory not found")
        all_data_ok=false
    fi
    
    # Return results
    if $all_data_ok; then
        log_message "Data integrity check passed."
        DATA_STATUS_ARRAY=("${data_status[@]}")
        return 0
    else
        log_message "Data integrity check failed."
        DATA_STATUS_ARRAY=("${data_status[@]}")
        return 1
    fi
}

# Function to check system performance
check_system_performance() {
    log_message "Checking system performance..."
    
    local all_performance_ok=true
    local performance_status=()
    
    # Check CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    log_message "CPU usage: $cpu_usage%"
    
    if [ "$(echo "$cpu_usage < 80" | bc)" -eq 1 ]; then
        performance_status+=("CPU usage: ✅ $cpu_usage% (Good)")
    else
        performance_status+=("CPU usage: ⚠️ $cpu_usage% (High)")
        all_performance_ok=false
    fi
    
    # Check memory usage
    local memory_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    log_message "Memory usage: $memory_usage%"
    
    if [ "$memory_usage" -lt 80 ]; then
        performance_status+=("Memory usage: ✅ $memory_usage% (Good)")
    else
        performance_status+=("Memory usage: ⚠️ $memory_usage% (High)")
        all_performance_ok=false
    fi
    
    # Check disk usage
    local disk_usage=$(df -h "$SHARED_DATA_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    log_message "Disk usage: $disk_usage%"
    
    if [ "$disk_usage" -lt 80 ]; then
        performance_status+=("Disk usage: ✅ $disk_usage% (Good)")
    else
        performance_status+=("Disk usage: ⚠️ $disk_usage% (High)")
        all_performance_ok=false
    fi
    
    # Check database connections
    local db_connections=$(psql -h localhost -U ${CRYPTOBOT_DB_USER:-"cryptobot"} -d ${CRYPTOBOT_DB_NAME:-"cryptobot"} -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null)
    if [ -n "$db_connections" ]; then
        log_message "Database connections: $db_connections"
        
        if [ "$db_connections" -lt 50 ]; then
            performance_status+=("Database connections: ✅ $db_connections (Good)")
        else
            performance_status+=("Database connections: ⚠️ $db_connections (High)")
            all_performance_ok=false
        fi
    else
        log_message "Database connections: FAILED to query"
        performance_status+=("Database connections: ❌ FAILED to query")
        all_performance_ok=false
    fi
    
    # Check API response times
    local auth_time=$(curl -s -w "%{time_total}\n" -o /dev/null "http://localhost:${CRYPTOBOT_NON_DOCKER_AUTH_PORT:-9000}/health")
    log_message "Auth API response time: ${auth_time}s"
    
    if [ "$(echo "$auth_time < 0.5" | bc)" -eq 1 ]; then
        performance_status+=("Auth API response time: ✅ ${auth_time}s (Good)")
    else
        performance_status+=("Auth API response time: ⚠️ ${auth_time}s (Slow)")
        all_performance_ok=false
    fi
    
    # Return results
    if $all_performance_ok; then
        log_message "System performance check passed."
        PERFORMANCE_STATUS_ARRAY=("${performance_status[@]}")
        return 0
    else
        log_message "System performance check has warnings."
        PERFORMANCE_STATUS_ARRAY=("${performance_status[@]}")
        return 1
    fi
}

# Function to generate HTML report
generate_html_report() {
    local docker_status=$1
    local services_status=$2
    local database_status=$3
    local redis_status=$4
    local api_status=$5
    local data_status=$6
    local performance_status=$7
    local overall_status=$8
    
    log_message "Generating HTML report..."
    
    # Determine status colors
    local overall_color="green"
    if [ "$overall_status" == "FAILED" ]; then
        overall_color="red"
    elif [ "$overall_status" == "WARNING" ]; then
        overall_color="orange"
    fi
    
    local docker_color="green"
    if [ "$docker_status" == "FAILED" ]; then
        docker_color="red"
    fi
    
    local services_color="green"
    if [ "$services_status" == "FAILED" ]; then
        services_color="red"
    fi
    
    local database_color="green"
    if [ "$database_status" == "FAILED" ]; then
        database_color="red"
    fi
    
    local redis_color="green"
    if [ "$redis_status" == "FAILED" ]; then
        redis_color="red"
    fi
    
    local api_color="green"
    if [ "$api_status" == "FAILED" ]; then
        api_color="red"
    fi
    
    local data_color="green"
    if [ "$data_status" == "FAILED" ]; then
        data_color="red"
    fi
    
    local performance_color="green"
    if [ "$performance_status" == "FAILED" ]; then
        performance_color="red"
    elif [ "$performance_status" == "WARNING" ]; then
        performance_color="orange"
    fi
    
    # Create HTML report
    cat > "$VERIFY_REPORT" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cryptobot Migration Verification Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2 {
            color: #2c3e50;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .status {
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            cursor: pointer;
        }
        .status-content {
            display: none;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
        }
        .status-content.active {
            display: block;
        }
        .status-item {
            margin-bottom: 5px;
        }
        .success {
            background-color: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }
        .warning {
            background-color: #fff3cd;
            border-color: #ffeeba;
            color: #856404;
        }
        .danger {
            background-color: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }
        .timestamp {
            font-size: 0.8em;
            color: #6c757d;
            margin-bottom: 20px;
        }
        .overall {
            font-size: 1.2em;
            font-weight: bold;
            text-align: center;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cryptobot Migration Verification Report</h1>
        <div class="timestamp">Generated on: $(date "+%Y-%m-%d %H:%M:%S")</div>
        
        <div class="overall" style="background-color: ${overall_color}; color: white;">
            Overall Status: ${overall_status}
        </div>
        
        <div class="status" style="background-color: ${docker_color}25;">
            <div class="status-header">
                <h2>Docker Status</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>Docker containers should be stopped after successful migration.</p>
                <div class="status-item">
                    Docker containers: ${docker_status}
                </div>
            </div>
        </div>
        
        <div class="status" style="background-color: ${services_color}25;">
            <div class="status-header">
                <h2>Non-Docker Services</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>All non-Docker services should be running.</p>
EOF
    
    # Add services status items
    for item in "${SERVICES_STATUS_ARRAY[@]}"; do
        echo "                <div class=\"status-item\">$item</div>" >> "$VERIFY_REPORT"
    done
    
    cat >> "$VERIFY_REPORT" << EOF
            </div>
        </div>
        
        <div class="status" style="background-color: ${database_color}25;">
            <div class="status-header">
                <h2>Database Status</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>Database should be accessible.</p>
                <div class="status-item">
                    ${DATABASE_STATUS}
                </div>
            </div>
        </div>
        
        <div class="status" style="background-color: ${redis_color}25;">
            <div class="status-header">
                <h2>Redis Status</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>Redis should be accessible.</p>
                <div class="status-item">
                    ${REDIS_STATUS}
                </div>
            </div>
        </div>
        
        <div class="status" style="background-color: ${api_color}25;">
            <div class="status-header">
                <h2>API Endpoints</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>All API endpoints should be accessible.</p>
EOF
    
    # Add API status items
    for item in "${API_STATUS_ARRAY[@]}"; do
        echo "                <div class=\"status-item\">$item</div>" >> "$VERIFY_REPORT"
    done
    
    cat >> "$VERIFY_REPORT" << EOF
            </div>
        </div>
        
        <div class="status" style="background-color: ${data_color}25;">
            <div class="status-header">
                <h2>Data Integrity</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>All data should be intact and accessible.</p>
EOF
    
    # Add data status items
    for item in "${DATA_STATUS_ARRAY[@]}"; do
        echo "                <div class=\"status-item\">$item</div>" >> "$VERIFY_REPORT"
    done
    
    cat >> "$VERIFY_REPORT" << EOF
            </div>
        </div>
        
        <div class="status" style="background-color: ${performance_color}25;">
            <div class="status-header">
                <h2>System Performance</h2>
                <span>▼</span>
            </div>
            <div class="status-content">
                <p>System performance should be within acceptable limits.</p>
EOF
    
    # Add performance status items
    for item in "${PERFORMANCE_STATUS_ARRAY[@]}"; do
        echo "                <div class=\"status-item\">$item</div>" >> "$VERIFY_REPORT"
    done
    
    cat >> "$VERIFY_REPORT" << EOF
            </div>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const headers = document.querySelectorAll('.status-header');
            
            headers.forEach(header => {
                header.addEventListener('click', function() {
                    const content = this.nextElementSibling;
                    content.classList.toggle('active');
                    this.querySelector('span').textContent = content.classList.contains('active') ? '▲' : '▼';
                });
            });
            
            // Open the first section by default
            const firstContent = document.querySelector('.status-content');
            if (firstContent) {
                firstContent.classList.add('active');
                firstContent.previousElementSibling.querySelector('span').textContent = '▲';
            }
        });
    </script>
</body>
</html>
EOF
    
    log_message "HTML report generated: $VERIFY_REPORT"
}

# Main function
main() {
    log_message "Starting migration verification..."
    
    # Check Docker containers
    if check_docker_containers; then
        DOCKER_STATUS="PASSED"
    else
        DOCKER_STATUS="FAILED"
    fi
    
    # Check non-Docker services
    if check_non_docker_services; then
        SERVICES_STATUS="PASSED"
    else
        SERVICES_STATUS="FAILED"
    fi
    
    # Check database
    if check_database; then
        DATABASE_STATUS_RESULT="PASSED"
    else
        DATABASE_STATUS_RESULT="FAILED"
    fi
    
    # Check Redis
    if check_redis; then
        REDIS_STATUS_RESULT="PASSED"
    else
        REDIS_STATUS_RESULT="FAILED"
    fi
    
    # Check API endpoints
    if check_api_endpoints; then
        API_STATUS="PASSED"
    else
        API_STATUS="FAILED"
    fi
    
    # Check data integrity
    if check_data_integrity; then
        DATA_STATUS="PASSED"
    else
        DATA_STATUS="FAILED"
    fi
    
    # Check system performance
    if check_system_performance; then
        PERFORMANCE_STATUS="PASSED"
    else
        PERFORMANCE_STATUS="WARNING"
    fi
    
    # Determine overall status
    if [ "$DOCKER_STATUS" == "FAILED" ] || [ "$SERVICES_STATUS" == "FAILED" ] || [ "$DATABASE_STATUS_RESULT" == "FAILED" ] || [ "$REDIS_STATUS_RESULT" == "FAILED" ] || [ "$API_STATUS" == "FAILED" ] || [ "$DATA_STATUS" == "FAILED" ]; then
        OVERALL_STATUS="FAILED"
    elif [ "$PERFORMANCE_STATUS" == "WARNING" ]; then
        OVERALL_STATUS="WARNING"
    else
        OVERALL_STATUS="PASSED"
    fi
    
    # Generate HTML report
    generate_html_report "$DOCKER_STATUS" "$SERVICES_STATUS" "$DATABASE_STATUS_RESULT" "$REDIS_STATUS_RESULT" "$API_STATUS" "$DATA_STATUS" "$PERFORMANCE_STATUS" "$OVERALL_STATUS"
    
    # Print summary
    echo ""
    echo "=== Migration Verification Summary ==="
    echo "Docker Status: $DOCKER_STATUS"
    echo "Non-Docker Services: $SERVICES_STATUS"
    echo "Database Status: $DATABASE_STATUS_RESULT"
    echo "Redis Status: $REDIS_STATUS_RESULT"
    echo "API Endpoints: $API_STATUS"
    echo "Data Integrity: $DATA_STATUS"
    echo "System Performance: $PERFORMANCE_STATUS"
    echo ""
    echo "Overall Status: $OVERALL_STATUS"
    echo ""
    echo "Detailed report: $VERIFY_REPORT"
    echo "Log file: $VERIFY_LOG"
    
    # Return exit code based on overall status
    if [ "$OVERALL_STATUS" == "PASSED" ]; then
        return 0
    else
        return 1
    fi
}

# Run the main function
main "$@"