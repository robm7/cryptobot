#!/bin/bash
#
# Log aggregation setup script for Cryptobot non-Docker installation.
# This script sets up log aggregation for the Cryptobot application using Filebeat and Elasticsearch.
# It installs and configures the logging tools and sets up dashboards for log visualization.

# Exit on any error
set -e

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$ROOT_DIR/config/non-docker/monitoring"
LOG_DIR="$ROOT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/logging_setup_$TIMESTAMP.log"

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

# Main logging setup process
{
    log "Starting logging setup for Cryptobot"
    
    OS=$(detect_os)
    log "Detected OS: $OS"
    
    # Create monitoring directory
    MONITORING_DIR="$ROOT_DIR/monitoring"
    mkdir -p "$MONITORING_DIR"
    
    # Create logging directory
    LOGGING_DIR="$MONITORING_DIR/logging"
    mkdir -p "$LOGGING_DIR"
    
    # 1. Install Elasticsearch
    if ! command_exists elasticsearch; then
        log "Elasticsearch not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            if ! command_exists brew; then
                log "Homebrew not found, installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew tap elastic/tap
            brew install elastic/tap/elasticsearch
        else
            # Linux installation
            PACKAGE_MANAGER=$(detect_package_manager)
            
            case $PACKAGE_MANAGER in
                apt)
                    # Install dependencies
                    sudo apt-get update
                    sudo apt-get install -y apt-transport-https gnupg
                    
                    # Add Elasticsearch repository
                    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
                    echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
                    
                    # Install Elasticsearch
                    sudo apt-get update
                    sudo apt-get install -y elasticsearch
                    ;;
                yum|dnf)
                    # Add Elasticsearch repository
                    cat > /tmp/elasticsearch.repo << EOF
[elasticsearch]
name=Elasticsearch repository for 8.x packages
baseurl=https://artifacts.elastic.co/packages/8.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF
                    sudo mv /tmp/elasticsearch.repo /etc/yum.repos.d/elasticsearch.repo
                    
                    # Install Elasticsearch
                    if [ "$PACKAGE_MANAGER" == "yum" ]; then
                        sudo yum install -y elasticsearch
                    else
                        sudo dnf install -y elasticsearch
                    fi
                    ;;
                *)
                    log "Unsupported package manager for Elasticsearch installation" "ERROR"
                    exit 1
                    ;;
            esac
        fi
        
        log "Elasticsearch installed successfully"
    else
        log "Elasticsearch is already installed"
    fi
    
    # 2. Install Kibana
    if ! command_exists kibana; then
        log "Kibana not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            brew install elastic/tap/kibana
        else
            # Linux installation
            PACKAGE_MANAGER=$(detect_package_manager)
            
            case $PACKAGE_MANAGER in
                apt)
                    # Elasticsearch repository should already be added
                    sudo apt-get update
                    sudo apt-get install -y kibana
                    ;;
                yum|dnf)
                    # Elasticsearch repository should already be added
                    if [ "$PACKAGE_MANAGER" == "yum" ]; then
                        sudo yum install -y kibana
                    else
                        sudo dnf install -y kibana
                    fi
                    ;;
                *)
                    log "Unsupported package manager for Kibana installation" "ERROR"
                    exit 1
                    ;;
            esac
        fi
        
        log "Kibana installed successfully"
    else
        log "Kibana is already installed"
    fi
    
    # 3. Install Filebeat
    if ! command_exists filebeat; then
        log "Filebeat not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            brew install elastic/tap/filebeat
        else
            # Linux installation
            PACKAGE_MANAGER=$(detect_package_manager)
            
            case $PACKAGE_MANAGER in
                apt)
                    # Elasticsearch repository should already be added
                    sudo apt-get update
                    sudo apt-get install -y filebeat
                    ;;
                yum|dnf)
                    # Elasticsearch repository should already be added
                    if [ "$PACKAGE_MANAGER" == "yum" ]; then
                        sudo yum install -y filebeat
                    else
                        sudo dnf install -y filebeat
                    fi
                    ;;
                *)
                    log "Unsupported package manager for Filebeat installation" "ERROR"
                    exit 1
                    ;;
            esac
        fi
        
        log "Filebeat installed successfully"
    else
        log "Filebeat is already installed"
    fi
    
    # 4. Configure Filebeat
    log "Configuring Filebeat"
    
    if [ "$OS" == "macOS" ]; then
        FILEBEAT_CONFIG="/usr/local/etc/filebeat/filebeat.yml"
    else
        FILEBEAT_CONFIG="/etc/filebeat/filebeat.yml"
    fi
    
    # Create Filebeat configuration
    cat > "/tmp/filebeat.yml" << EOF
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - $LOG_DIR/*.log
    - $LOG_DIR/auth/*.log
    - $LOG_DIR/strategy/*.log
    - $LOG_DIR/backtest/*.log
    - $LOG_DIR/trade/*.log
    - $LOG_DIR/data/*.log
    - $LOG_DIR/mcp/*.log
  fields:
    application: cryptobot
  fields_under_root: true
  multiline:
    pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
    negate: true
    match: after

filebeat.config.modules:
  path: \${path.config}/modules.d/*.yml
  reload.enabled: false

setup.template.settings:
  index.number_of_shards: 1

setup.kibana:
  host: "localhost:5601"

output.elasticsearch:
  hosts: ["localhost:9200"]
  indices:
    - index: "cryptobot-logs-%{+yyyy.MM.dd}"
      when.contains:
        application: "cryptobot"

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_cloud_metadata: ~
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~
EOF
    
    sudo mv "/tmp/filebeat.yml" "$FILEBEAT_CONFIG"
    log "Created Filebeat configuration at $FILEBEAT_CONFIG"
    
    # 5. Start and enable services
    if [ "$OS" == "macOS" ]; then
        # macOS services using launchd
        log "Setting up services using launchd"
        
        # Elasticsearch service
        if ! launchctl list | grep -q "org.elasticsearch.elasticsearch"; then
            create_launchd_service "org.elasticsearch.elasticsearch" "Elasticsearch for Cryptobot log aggregation" \
                "/usr/local/bin/elasticsearch" ""
        else
            log "Elasticsearch service is already running"
        fi
        
        # Kibana service
        if ! launchctl list | grep -q "org.kibana.kibana"; then
            create_launchd_service "org.kibana.kibana" "Kibana for Cryptobot log visualization" \
                "/usr/local/bin/kibana" ""
        else
            log "Kibana service is already running"
        fi
        
        # Filebeat service
        if ! launchctl list | grep -q "org.filebeat.filebeat"; then
            create_launchd_service "org.filebeat.filebeat" "Filebeat for Cryptobot log collection" \
                "/usr/local/bin/filebeat" "-c /usr/local/etc/filebeat/filebeat.yml -e"
        else
            log "Filebeat service is already running"
        fi
        
    elif command_exists systemctl; then
        # Linux services using systemd
        log "Setting up services using systemd"
        
        # Elasticsearch service
        sudo systemctl enable elasticsearch
        sudo systemctl restart elasticsearch
        log "Elasticsearch service enabled and started"
        
        # Kibana service
        sudo systemctl enable kibana
        sudo systemctl restart kibana
        log "Kibana service enabled and started"
        
        # Filebeat service
        sudo systemctl enable filebeat
        sudo systemctl restart filebeat
        log "Filebeat service enabled and started"
    else
        log "No service manager found (systemd or launchd), services must be started manually" "WARNING"
    fi
    
    # 6. Wait for Elasticsearch and Kibana to start
    log "Waiting for Elasticsearch and Kibana to start..."
    sleep 30
    
    # 7. Set up Filebeat dashboards
    log "Setting up Filebeat dashboards"
    sudo filebeat setup --dashboards
    
    log "Logging setup completed successfully"
    
} || {
    error_message="$?"
    log "Logging setup failed: $error_message" "ERROR"
    exit 1
}