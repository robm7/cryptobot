#!/bin/bash
#
# Alerting setup script for Cryptobot non-Docker installation.
# This script sets up alerting for the Cryptobot application using Alertmanager and configures alert rules.
# It installs and configures the alerting tools and sets up notification channels.

# Exit on any error
set -e

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$ROOT_DIR/config/non-docker/monitoring"
LOG_DIR="$ROOT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/alerting_setup_$TIMESTAMP.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages
log() {
    local level="INFO"
    if [ $# -eq 2 ]; then
        level="$2"
    fi
    
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    local message="[$timestamp] [$level] $1"
    
    # Write to console
    case "$level" in
        "INFO")
            echo -e "\033[0;32m$message\033[0m"
            ;;
        "WARNING")
            echo -e "\033[0;33m$message\033[0m"
            ;;
        "ERROR")
            echo -e "\033[0;31m$message\033[0m"
            ;;
        *)
            echo "$message"
            ;;
    esac
    
    # Write to log file
    echo "$message" >> "$LOG_FILE"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect the OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
    elif [ "$(uname)" == "Darwin" ]; then
        OS="macOS"
    else
        OS="Unknown"
    fi
    echo $OS
}

# Function to detect the package manager
detect_package_manager() {
    if command_exists apt-get; then
        echo "apt"
    elif command_exists yum; then
        echo "yum"
    elif command_exists dnf; then
        echo "dnf"
    elif command_exists brew; then
        echo "brew"
    else
        echo "unknown"
    fi
}

# Function to install a package
install_package() {
    local package=$1
    local package_manager=$(detect_package_manager)
    
    log "Installing $package using $package_manager"
    
    case $package_manager in
        apt)
            sudo apt-get update
            sudo apt-get install -y $package
            ;;
        yum)
            sudo yum install -y $package
            ;;
        dnf)
            sudo dnf install -y $package
            ;;
        brew)
            brew install $package
            ;;
        *)
            log "Unknown package manager, cannot install $package" "ERROR"
            return 1
            ;;
    esac
}

# Function to download a file
download_file() {
    local url=$1
    local output_path=$2
    
    log "Downloading $url to $output_path"
    
    if command_exists curl; then
        curl -L -o "$output_path" "$url"
    elif command_exists wget; then
        wget -O "$output_path" "$url"
    else
        log "Neither curl nor wget found, cannot download file" "ERROR"
        return 1
    fi
}

# Function to create a systemd service
create_systemd_service() {
    local service_name=$1
    local description=$2
    local exec_start=$3
    local user=${4:-root}
    
    log "Creating systemd service: $service_name"
    
    local service_file="/etc/systemd/system/$service_name.service"
    
    cat > "/tmp/$service_name.service" << EOF
[Unit]
Description=$description
After=network.target

[Service]
Type=simple
User=$user
ExecStart=$exec_start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv "/tmp/$service_name.service" "$service_file"
    sudo systemctl daemon-reload
    sudo systemctl enable "$service_name"
    sudo systemctl start "$service_name"
    
    log "Service $service_name created and started"
}

# Function to create a launchd service (macOS)
create_launchd_service() {
    local service_name=$1
    local description=$2
    local exec_path=$3
    local args=$4
    
    log "Creating launchd service: $service_name"
    
    local plist_file="/Library/LaunchDaemons/$service_name.plist"
    
    cat > "/tmp/$service_name.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$service_name</string>
    <key>ProgramArguments</key>
    <array>
        <string>$exec_path</string>
$(for arg in $args; do echo "        <string>$arg</string>"; done)
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/$service_name.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/$service_name.err</string>
</dict>
</plist>
EOF
    
    sudo mv "/tmp/$service_name.plist" "$plist_file"
    sudo chown root:wheel "$plist_file"
    sudo launchctl load "$plist_file"
    
    log "Service $service_name created and started"
}

# Main alerting setup process
{
    log "Starting alerting setup for Cryptobot"
    
    OS=$(detect_os)
    log "Detected OS: $OS"
    
    # Create monitoring directory
    MONITORING_DIR="$ROOT_DIR/monitoring"
    mkdir -p "$MONITORING_DIR"
    
    # Create alerting directory
    ALERTING_DIR="$MONITORING_DIR/alerting"
    mkdir -p "$ALERTING_DIR"
    
    # 1. Install Alertmanager
    if ! command_exists alertmanager; then
        log "Alertmanager not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            if ! command_exists brew; then
                log "Homebrew not found, installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install alertmanager
        else
            # Linux installation
            ALERTMANAGER_VERSION="0.26.0"
            ALERTMANAGER_DIR="$ALERTING_DIR/alertmanager"
            mkdir -p "$ALERTMANAGER_DIR"
            
            ARCH=$(uname -m)
            if [ "$ARCH" == "x86_64" ]; then
                ALERTMANAGER_ARCH="amd64"
            elif [ "$ARCH" == "aarch64" ] || [ "$ARCH" == "arm64" ]; then
                ALERTMANAGER_ARCH="arm64"
            else
                ALERTMANAGER_ARCH="$ARCH"
            fi
            
            ALERTMANAGER_URL="https://github.com/prometheus/alertmanager/releases/download/v$ALERTMANAGER_VERSION/alertmanager-$ALERTMANAGER_VERSION.linux-$ALERTMANAGER_ARCH.tar.gz"
            ALERTMANAGER_TAR="/tmp/alertmanager.tar.gz"
            
            download_file "$ALERTMANAGER_URL" "$ALERTMANAGER_TAR"
            
            tar -xzf "$ALERTMANAGER_TAR" -C "/tmp"
            ALERTMANAGER_EXTRACTED_DIR=$(find /tmp -maxdepth 1 -type d -name "alertmanager-*" | head -n 1)
            
            if [ -d "$ALERTMANAGER_EXTRACTED_DIR" ]; then
                cp -r "$ALERTMANAGER_EXTRACTED_DIR"/* "$ALERTMANAGER_DIR/"
                rm -rf "$ALERTMANAGER_EXTRACTED_DIR"
                rm "$ALERTMANAGER_TAR"
                
                # Create symbolic links to make alertmanager available in PATH
                sudo ln -sf "$ALERTMANAGER_DIR/alertmanager" /usr/local/bin/alertmanager
                sudo ln -sf "$ALERTMANAGER_DIR/amtool" /usr/local/bin/amtool
            else
                log "Failed to extract Alertmanager" "ERROR"
                exit 1
            fi
        fi
        
        log "Alertmanager installed successfully"
    else
        log "Alertmanager is already installed"
    fi
    
    # 2. Configure Alertmanager
    log "Configuring Alertmanager"
    
    if [ "$OS" == "macOS" ]; then
        ALERTMANAGER_CONFIG="/usr/local/etc/alertmanager/alertmanager.yml"
        mkdir -p "/usr/local/etc/alertmanager"
    else
        ALERTMANAGER_CONFIG="$ALERTING_DIR/alertmanager/alertmanager.yml"
    fi
    
    # Create Alertmanager configuration
    cat > "/tmp/alertmanager.yml" << EOF
global:
  resolve_timeout: 5m
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'
  smtp_auth_username: 'alertmanager'
  smtp_auth_password: 'password'
  smtp_require_tls: true

route:
  group_by: ['alertname', 'job']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'email-notifications'
  routes:
  - match:
      severity: critical
    receiver: 'email-notifications'
    continue: true
  - match:
      severity: warning
    receiver: 'slack-notifications'
    continue: true

receivers:
- name: 'email-notifications'
  email_configs:
  - to: 'admin@example.com'
    send_resolved: true
    
- name: 'slack-notifications'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
    channel: '#alerts'
    send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
EOF
    
    sudo mv "/tmp/alertmanager.yml" "$ALERTMANAGER_CONFIG"
    log "Created Alertmanager configuration at $ALERTMANAGER_CONFIG"
    
    # 3. Create Prometheus alert rules
    log "Creating Prometheus alert rules"
    
    if [ "$OS" == "macOS" ]; then
        PROMETHEUS_RULES_DIR="/usr/local/etc/prometheus/rules"
    else
        PROMETHEUS_RULES_DIR="$MONITORING_DIR/prometheus/rules"
    fi
    
    mkdir -p "$PROMETHEUS_RULES_DIR"
    ALERT_RULES_PATH="$PROMETHEUS_RULES_DIR/alert_rules.yml"
    
    # Create alert rules
    cat > "/tmp/alert_rules.yml" << EOF
groups:
- name: cryptobot_alerts
  rules:
  - alert: InstanceDown
    expr: up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Instance {{ \$labels.instance }} down"
      description: "{{ \$labels.instance }} of job {{ \$labels.job }} has been down for more than 1 minute."

  - alert: HighCpuUsage
    expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage on {{ \$labels.instance }}"
      description: "CPU usage is above 80% for more than 5 minutes on {{ \$labels.instance }}."

  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage on {{ \$labels.instance }}"
      description: "Memory usage is above 80% for more than 5 minutes on {{ \$labels.instance }}."

  - alert: HighDiskUsage
    expr: 100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100) > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High disk usage on {{ \$labels.instance }}"
      description: "Disk usage is above 80% for more than 5 minutes on {{ \$labels.instance }} mount point {{ \$labels.mountpoint }}."

  - alert: HighErrorRate
    expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100 > 5
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High HTTP error rate"
      description: "HTTP error rate is above 5% for more than 5 minutes."

  - alert: SlowResponseTime
    expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Slow response time"
      description: "95th percentile of HTTP response time is above 1 second for more than 5 minutes."

  - alert: TradingServiceDown
    expr: up{job="cryptobot-trade"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Trading service is down"
      description: "The trading service has been down for more than 1 minute."

  - alert: StrategyServiceDown
    expr: up{job="cryptobot-strategy"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Strategy service is down"
      description: "The strategy service has been down for more than 1 minute."

  - alert: DataServiceDown
    expr: up{job="cryptobot-data"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Data service is down"
      description: "The data service has been down for more than 1 minute."

  - alert: AuthServiceDown
    expr: up{job="cryptobot-auth"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Auth service is down"
      description: "The auth service has been down for more than 1 minute."
EOF
    
    sudo mv "/tmp/alert_rules.yml" "$ALERT_RULES_PATH"
    log "Created Prometheus alert rules at $ALERT_RULES_PATH"
    
    # 4. Update Prometheus configuration to include alert rules and Alertmanager
    log "Updating Prometheus configuration"
    
    if [ "$OS" == "macOS" ]; then
        PROMETHEUS_CONFIG="/usr/local/etc/prometheus.yml"
    else
        PROMETHEUS_CONFIG="$MONITORING_DIR/prometheus/prometheus.yml"
    fi
    
    if [ -f "$PROMETHEUS_CONFIG" ]; then
        # Check if alerting configuration already exists
        if ! grep -q "alerting:" "$PROMETHEUS_CONFIG"; then
            # Create a temporary file with the alerting configuration
            cat > "/tmp/alerting_config.yml" << EOF

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093

# Load rules once and periodically evaluate them
rule_files:
  - "rules/alert_rules.yml"
EOF
            
            # Add alerting configuration after global section
            sed -i.bak '/^global:/,/^[a-z]/ {/^[a-z]/!{/^global:/!{/^$/!b}};/^[a-z]/!{/^$/!b};r /tmp/alerting_config.yml
}' "$PROMETHEUS_CONFIG"
            
            rm "/tmp/alerting_config.yml"
            log "Updated Prometheus configuration with alerting settings"
        else
            log "Alerting configuration already exists in Prometheus config" "WARNING"
        fi
    else
        log "Prometheus configuration not found at $PROMETHEUS_CONFIG" "ERROR"
    fi
    
    # 5. Start and enable services
    if [ "$OS" == "macOS" ]; then
        # macOS services using launchd
        log "Setting up services using launchd"
        
        # Alertmanager service
        if ! launchctl list | grep -q "org.alertmanager.alertmanager"; then
            create_launchd_service "org.alertmanager.alertmanager" "Alertmanager for Cryptobot alerts" \
                "/usr/local/bin/alertmanager" "--config.file=$ALERTMANAGER_CONFIG"
        else
            log "Alertmanager service is already running"
        fi
        
        # Restart Prometheus to apply new configuration
        if launchctl list | grep -q "org.prometheus.prometheus"; then
            sudo launchctl unload /Library/LaunchDaemons/org.prometheus.prometheus.plist
            sudo launchctl load /Library/LaunchDaemons/org.prometheus.prometheus.plist
            log "Prometheus service restarted"
        else
            log "Prometheus service not found, cannot restart" "WARNING"
        fi
        
    elif command_exists systemctl; then
        # Linux services using systemd
        log "Setting up services using systemd"
        
        # Alertmanager service
        if [ -f "$ALERTING_DIR/alertmanager/alertmanager" ]; then
            create_systemd_service "cryptobot-alertmanager" "Alertmanager for Cryptobot alerts" \
                "$ALERTING_DIR/alertmanager/alertmanager --config.file=$ALERTMANAGER_CONFIG"
        else
            create_systemd_service "cryptobot-alertmanager" "Alertmanager for Cryptobot alerts" \
                "/usr/local/bin/alertmanager --config.file=$ALERTMANAGER_CONFIG"
        fi
        
        # Restart Prometheus to apply new configuration
        if systemctl is-active --quiet cryptobot-prometheus; then
            sudo systemctl restart cryptobot-prometheus
            log "Prometheus service restarted"
        else
            log "Prometheus service not found, cannot restart" "WARNING"
        fi
    else
        log "No service manager found (systemd or launchd), services must be started manually" "WARNING"
    fi
    
    log "Alerting setup completed successfully"
    
} || {
    error_message="$?"
    log "Alerting setup failed: $error_message" "ERROR"
    exit 1
}