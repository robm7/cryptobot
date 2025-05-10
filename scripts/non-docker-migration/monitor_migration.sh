#!/bin/bash
# monitor_migration.sh
# Script to monitor the migration process from Docker to non-Docker
# Part of Phase 11: Parallel Operation Strategy

set -e

echo "=== Cryptobot Migration Monitoring Tool ==="
echo "This script monitors the migration process from Docker to non-Docker environments."

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
MONITOR_LOG="$LOG_DIR/migration_monitor.log"
MONITOR_DATA_DIR="$SHARED_DATA_DIR/migration_monitoring"
ALERT_LOG="$MONITOR_DATA_DIR/alerts.log"
STATUS_FILE="$MONITOR_DATA_DIR/migration_status.json"

# Create monitoring directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$MONITOR_DATA_DIR"

# Function to log messages
log_message() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" | tee -a "$MONITOR_LOG"
}

# Function to log alerts
log_alert() {
    local severity=$1
    local message=$2
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$severity] $message" | tee -a "$ALERT_LOG"
    
    # For critical alerts, send notification (implement based on your notification system)
    if [ "$severity" == "CRITICAL" ]; then
        echo "[$timestamp] [$severity] $message" | mail -s "CRITICAL Cryptobot Migration Alert" admin@example.com
    fi
}

# Function to check if a service is running
is_service_running() {
    local host=$1
    local port=$2
    nc -z "$host" "$port" >/dev/null 2>&1
    return $?
}

# Function to check Docker service health
check_docker_service() {
    local service_name=$1
    local port=$2
    
    if is_service_running "localhost" "$port"; then
        log_message "Docker $service_name: RUNNING"
        return 0
    else
        log_message "Docker $service_name: NOT RUNNING"
        return 1
    fi
}

# Function to check non-Docker service health
check_non_docker_service() {
    local service_name=$1
    local port=$2
    
    if is_service_running "localhost" "$port"; then
        log_message "Non-Docker $service_name: RUNNING"
        return 0
    else
        log_message "Non-Docker $service_name: NOT RUNNING"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    log_message "Checking database connectivity..."
    
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
        log_message "Database: CONNECTED"
        return 0
    else
        log_message "Database: NOT CONNECTED"
        log_alert "WARNING" "Database connection failed"
        return 1
    fi
}

# Function to check Redis connectivity
check_redis() {
    log_message "Checking Redis connectivity..."
    
    if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then
        log_message "Redis: CONNECTED"
        return 0
    else
        log_message "Redis: NOT CONNECTED"
        log_alert "WARNING" "Redis connection failed"
        return 1
    fi
}

# Function to check API endpoints
check_api_endpoint() {
    local service_name=$1
    local url=$2
    local expected_status=$3
    
    log_message "Checking $service_name API endpoint: $url"
    
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$status_code" == "$expected_status" ]; then
        log_message "$service_name API: OK (Status: $status_code)"
        return 0
    else
        log_message "$service_name API: FAILED (Status: $status_code, Expected: $expected_status)"
        log_alert "WARNING" "$service_name API endpoint check failed: $url (Status: $status_code, Expected: $expected_status)"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    log_message "Checking disk space..."
    
    local threshold=90  # Alert if disk usage is above 90%
    local disk_usage=$(df -h "$SHARED_DATA_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    
    log_message "Disk usage for $SHARED_DATA_DIR: $disk_usage%"
    
    if [ "$disk_usage" -gt "$threshold" ]; then
        log_alert "WARNING" "Disk usage above threshold: $disk_usage% (Threshold: $threshold%)"
        return 1
    else
        return 0
    fi
}

# Function to check memory usage
check_memory_usage() {
    log_message "Checking memory usage..."
    
    local threshold=90  # Alert if memory usage is above 90%
    local memory_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    
    log_message "Memory usage: $memory_usage%"
    
    if [ "$memory_usage" -gt "$threshold" ]; then
        log_alert "WARNING" "Memory usage above threshold: $memory_usage% (Threshold: $threshold%)"
        return 1
    else
        return 0
    fi
}

# Function to check CPU load
check_cpu_load() {
    log_message "Checking CPU load..."
    
    local threshold=80  # Alert if CPU load is above 80%
    local cpu_load=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    
    log_message "CPU load: $cpu_load%"
    
    if [ "$(echo "$cpu_load > $threshold" | bc)" -eq 1 ]; then
        log_alert "WARNING" "CPU load above threshold: $cpu_load% (Threshold: $threshold%)"
        return 1
    else
        return 0
    fi
}

# Function to check log files for errors
check_logs_for_errors() {
    log_message "Checking logs for errors..."
    
    local error_count=0
    local critical_patterns=("ERROR" "CRITICAL" "FATAL" "Exception" "failed" "crash")
    
    for pattern in "${critical_patterns[@]}"; do
        local count=$(grep -i "$pattern" "$LOG_DIR"/*.log 2>/dev/null | wc -l)
        error_count=$((error_count + count))
        
        if [ "$count" -gt 0 ]; then
            log_message "Found $count occurrences of '$pattern' in logs"
            
            # Log the first 5 occurrences
            grep -i "$pattern" "$LOG_DIR"/*.log 2>/dev/null | head -n 5 | while read -r line; do
                log_message "Log entry: $line"
            done
        fi
    done
    
    if [ "$error_count" -gt 0 ]; then
        log_alert "WARNING" "Found $error_count error patterns in logs"
        return 1
    else
        log_message "No errors found in logs"
        return 0
    fi
}

# Function to compare Docker and non-Docker service response times
compare_response_times() {
    local service_name=$1
    local docker_url=$2
    local non_docker_url=$3
    
    log_message "Comparing response times for $service_name..."
    
    local docker_time=$(curl -s -w "%{time_total}\n" -o /dev/null "$docker_url")
    local non_docker_time=$(curl -s -w "%{time_total}\n" -o /dev/null "$non_docker_url")
    
    log_message "Docker $service_name response time: ${docker_time}s"
    log_message "Non-Docker $service_name response time: ${non_docker_time}s"
    
    # Calculate percentage difference
    local diff=$(echo "scale=2; ($non_docker_time - $docker_time) / $docker_time * 100" | bc)
    
    if [ "$(echo "$diff > 50" | bc)" -eq 1 ]; then
        log_alert "WARNING" "Non-Docker $service_name is significantly slower (${diff}% difference)"
        return 1
    elif [ "$(echo "$diff < -20" | bc)" -eq 1 ]; then
        log_message "Non-Docker $service_name is faster (${diff}% difference)"
    else
        log_message "Response times are comparable (${diff}% difference)"
    fi
    
    return 0
}

# Function to update migration status file
update_status_file() {
    local docker_services_status=$1
    local non_docker_services_status=$2
    local database_status=$3
    local redis_status=$4
    local disk_status=$5
    local memory_status=$6
    local cpu_status=$7
    local logs_status=$8
    
    # Calculate overall status
    local overall_status="GREEN"
    if [ "$docker_services_status" == "RED" ] || [ "$non_docker_services_status" == "RED" ] || [ "$database_status" == "RED" ] || [ "$redis_status" == "RED" ]; then
        overall_status="RED"
    elif [ "$docker_services_status" == "YELLOW" ] || [ "$non_docker_services_status" == "YELLOW" ] || [ "$database_status" == "YELLOW" ] || [ "$redis_status" == "YELLOW" ] || [ "$disk_status" == "YELLOW" ] || [ "$memory_status" == "YELLOW" ] || [ "$cpu_status" == "YELLOW" ] || [ "$logs_status" == "YELLOW" ]; then
        overall_status="YELLOW"
    fi
    
    # Create JSON status file
    cat > "$STATUS_FILE" << EOF
{
  "timestamp": "$(date "+%Y-%m-%d %H:%M:%S")",
  "overall_status": "$overall_status",
  "components": {
    "docker_services": "$docker_services_status",
    "non_docker_services": "$non_docker_services_status",
    "database": "$database_status",
    "redis": "$redis_status",
    "disk_space": "$disk_status",
    "memory_usage": "$memory_status",
    "cpu_load": "$cpu_status",
    "logs": "$logs_status"
  },
  "alert_count": $(wc -l < "$ALERT_LOG"),
  "last_check": "$(date "+%Y-%m-%d %H:%M:%S")"
}
EOF
    
    log_message "Updated status file: $STATUS_FILE"
    
    # If status is RED, send notification
    if [ "$overall_status" == "RED" ]; then
        log_alert "CRITICAL" "Migration monitoring detected RED status"
    fi
}

# Function to run all checks
run_all_checks() {
    log_message "Starting migration monitoring checks..."
    
    # Check Docker services
    local docker_auth_status=$(check_docker_service "auth" "${CRYPTOBOT_DOCKER_AUTH_PORT:-8000}" && echo "GREEN" || echo "RED")
    local docker_strategy_status=$(check_docker_service "strategy" "${CRYPTOBOT_DOCKER_STRATEGY_PORT:-8001}" && echo "GREEN" || echo "RED")
    local docker_backtest_status=$(check_docker_service "backtest" "${CRYPTOBOT_DOCKER_BACKTEST_PORT:-8002}" && echo "GREEN" || echo "RED")
    local docker_trade_status=$(check_docker_service "trade" "${CRYPTOBOT_DOCKER_TRADE_PORT:-8003}" && echo "GREEN" || echo "RED")
    local docker_data_status=$(check_docker_service "data" "${CRYPTOBOT_DOCKER_DATA_PORT:-8004}" && echo "GREEN" || echo "RED")
    
    # Determine overall Docker services status
    local docker_services_status="GREEN"
    if [ "$docker_auth_status" == "RED" ] || [ "$docker_strategy_status" == "RED" ] || [ "$docker_backtest_status" == "RED" ] || [ "$docker_trade_status" == "RED" ] || [ "$docker_data_status" == "RED" ]; then
        docker_services_status="RED"
    fi
    
    # Check non-Docker services
    local non_docker_auth_status=$(check_non_docker_service "auth" "${CRYPTOBOT_NON_DOCKER_AUTH_PORT:-9000}" && echo "GREEN" || echo "RED")
    local non_docker_strategy_status=$(check_non_docker_service "strategy" "${CRYPTOBOT_NON_DOCKER_STRATEGY_PORT:-9001}" && echo "GREEN" || echo "RED")
    local non_docker_backtest_status=$(check_non_docker_service "backtest" "${CRYPTOBOT_NON_DOCKER_BACKTEST_PORT:-9002}" && echo "GREEN" || echo "RED")
    local non_docker_trade_status=$(check_non_docker_service "trade" "${CRYPTOBOT_NON_DOCKER_TRADE_PORT:-9003}" && echo "GREEN" || echo "RED")
    local non_docker_data_status=$(check_non_docker_service "data" "${CRYPTOBOT_NON_DOCKER_DATA_PORT:-9004}" && echo "GREEN" || echo "RED")
    
    # Determine overall non-Docker services status
    local non_docker_services_status="GREEN"
    if [ "$non_docker_auth_status" == "RED" ] || [ "$non_docker_strategy_status" == "RED" ] || [ "$non_docker_backtest_status" == "RED" ] || [ "$non_docker_trade_status" == "RED" ] || [ "$non_docker_data_status" == "RED" ]; then
        non_docker_services_status="RED"
    fi
    
    # Check database and Redis
    local database_status=$(check_database && echo "GREEN" || echo "RED")
    local redis_status=$(check_redis && echo "GREEN" || echo "RED")
    
    # Check system resources
    local disk_status=$(check_disk_space && echo "GREEN" || echo "YELLOW")
    local memory_status=$(check_memory_usage && echo "GREEN" || echo "YELLOW")
    local cpu_status=$(check_cpu_load && echo "GREEN" || echo "YELLOW")
    
    # Check logs
    local logs_status=$(check_logs_for_errors && echo "GREEN" || echo "YELLOW")
    
    # Compare response times if both environments are running
    if [ "$docker_services_status" == "GREEN" ] && [ "$non_docker_services_status" == "GREEN" ]; then
        compare_response_times "auth" "http://localhost:${CRYPTOBOT_DOCKER_AUTH_PORT:-8000}/health" "http://localhost:${CRYPTOBOT_NON_DOCKER_AUTH_PORT:-9000}/health"
        compare_response_times "strategy" "http://localhost:${CRYPTOBOT_DOCKER_STRATEGY_PORT:-8001}/health" "http://localhost:${CRYPTOBOT_NON_DOCKER_STRATEGY_PORT:-9001}/health"
        compare_response_times "backtest" "http://localhost:${CRYPTOBOT_DOCKER_BACKTEST_PORT:-8002}/health" "http://localhost:${CRYPTOBOT_NON_DOCKER_BACKTEST_PORT:-9002}/health"
        compare_response_times "trade" "http://localhost:${CRYPTOBOT_DOCKER_TRADE_PORT:-8003}/health" "http://localhost:${CRYPTOBOT_NON_DOCKER_TRADE_PORT:-9003}/health"
        compare_response_times "data" "http://localhost:${CRYPTOBOT_DOCKER_DATA_PORT:-8004}/health" "http://localhost:${CRYPTOBOT_NON_DOCKER_DATA_PORT:-9004}/health"
    fi
    
    # Update status file
    update_status_file "$docker_services_status" "$non_docker_services_status" "$database_status" "$redis_status" "$disk_status" "$memory_status" "$cpu_status" "$logs_status"
    
    log_message "Migration monitoring checks completed."
}

# Function to display monitoring dashboard
display_dashboard() {
    clear
    echo "=== Cryptobot Migration Monitoring Dashboard ==="
    echo "Time: $(date "+%Y-%m-%d %H:%M:%S")"
    echo ""
    
    if [ -f "$STATUS_FILE" ]; then
        local overall_status=$(grep -o '"overall_status": "[^"]*"' "$STATUS_FILE" | cut -d'"' -f4)
        echo "Overall Status: $overall_status"
        echo ""
        
        echo "Component Status:"
        grep -o '"[^"]*": "[^"]*"' "$STATUS_FILE" | grep -v "timestamp\|overall_status\|last_check\|alert_count" | sed 's/"//g' | sed 's/: /: /' | column -t -s ':'
        echo ""
        
        echo "Recent Alerts:"
        tail -n 5 "$ALERT_LOG" 2>/dev/null || echo "No alerts found."
        echo ""
    else
        echo "Status file not found. Run checks first."
        echo ""
    fi
    
    echo "Commands:"
    echo "  r - Run checks"
    echo "  l - View logs"
    echo "  a - View all alerts"
    echo "  q - Quit"
    echo ""
}

# Function to view logs
view_logs() {
    clear
    echo "=== Cryptobot Migration Monitoring Logs ==="
    echo "Last 20 log entries:"
    echo ""
    
    tail -n 20 "$MONITOR_LOG"
    
    echo ""
    echo "Press Enter to return to dashboard..."
    read -r
}

# Function to view all alerts
view_alerts() {
    clear
    echo "=== Cryptobot Migration Monitoring Alerts ==="
    echo ""
    
    if [ -f "$ALERT_LOG" ]; then
        cat "$ALERT_LOG"
    else
        echo "No alerts found."
    fi
    
    echo ""
    echo "Press Enter to return to dashboard..."
    read -r
}

# Main function for interactive mode
interactive_mode() {
    local running=true
    
    while $running; do
        display_dashboard
        
        read -r -n 1 -p "Enter command: " command
        echo ""
        
        case $command in
            r)
                run_all_checks
                ;;
            l)
                view_logs
                ;;
            a)
                view_alerts
                ;;
            q)
                running=false
                ;;
            *)
                echo "Unknown command. Press Enter to continue..."
                read -r
                ;;
        esac
    done
    
    echo "Exiting migration monitoring tool."
}

# Main function for non-interactive mode
non_interactive_mode() {
    run_all_checks
    
    # Print summary
    if [ -f "$STATUS_FILE" ]; then
        local overall_status=$(grep -o '"overall_status": "[^"]*"' "$STATUS_FILE" | cut -d'"' -f4)
        echo "Overall Status: $overall_status"
        
        echo "Component Status:"
        grep -o '"[^"]*": "[^"]*"' "$STATUS_FILE" | grep -v "timestamp\|overall_status\|last_check\|alert_count" | sed 's/"//g' | sed 's/: /: /' | column -t -s ':'
    else
        echo "Error: Status file not found after running checks."
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --non-interactive)
            non_interactive_mode
            exit 0
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Monitor the migration process from Docker to non-Docker environments."
            echo ""
            echo "Options:"
            echo "  --non-interactive  Run checks once and exit"
            echo "  --help             Display this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
    shift
done

# Run in interactive mode by default
interactive_mode