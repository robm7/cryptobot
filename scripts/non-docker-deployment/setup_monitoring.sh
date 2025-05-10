#!/bin/bash
#
# Monitoring setup script for Cryptobot non-Docker installation.
# This script sets up monitoring for the Cryptobot application using Prometheus and Grafana.
# It installs and configures the monitoring tools and sets up dashboards for system and application monitoring.

# Exit on any error
set -e

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="$ROOT_DIR/config/non-docker/monitoring"
LOG_DIR="$ROOT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/monitoring_setup_$TIMESTAMP.log"

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
    
    cat > "$service_file" << EOF
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

# Main monitoring setup process
{
    log "Starting monitoring setup for Cryptobot"
    
    OS=$(detect_os)
    log "Detected OS: $OS"
    
    # Create monitoring directory
    MONITORING_DIR="$ROOT_DIR/monitoring"
    mkdir -p "$MONITORING_DIR"
    
    # 1. Install Prometheus
    if ! command_exists prometheus; then
        log "Prometheus not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            if ! command_exists brew; then
                log "Homebrew not found, installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install prometheus
        else
            # Linux installation
            PROMETHEUS_VERSION="2.45.0"
            PROMETHEUS_DIR="$MONITORING_DIR/prometheus"
            mkdir -p "$PROMETHEUS_DIR"
            
            ARCH=$(uname -m)
            if [ "$ARCH" == "x86_64" ]; then
                PROMETHEUS_ARCH="amd64"
            elif [ "$ARCH" == "aarch64" ] || [ "$ARCH" == "arm64" ]; then
                PROMETHEUS_ARCH="arm64"
            else
                PROMETHEUS_ARCH="$ARCH"
            fi
            
            PROMETHEUS_URL="https://github.com/prometheus/prometheus/releases/download/v$PROMETHEUS_VERSION/prometheus-$PROMETHEUS_VERSION.linux-$PROMETHEUS_ARCH.tar.gz"
            PROMETHEUS_TAR="/tmp/prometheus.tar.gz"
            
            download_file "$PROMETHEUS_URL" "$PROMETHEUS_TAR"
            
            tar -xzf "$PROMETHEUS_TAR" -C "/tmp"
            PROMETHEUS_EXTRACTED_DIR=$(find /tmp -maxdepth 1 -type d -name "prometheus-*" | head -n 1)
            
            if [ -d "$PROMETHEUS_EXTRACTED_DIR" ]; then
                cp -r "$PROMETHEUS_EXTRACTED_DIR"/* "$PROMETHEUS_DIR/"
                rm -rf "$PROMETHEUS_EXTRACTED_DIR"
                rm "$PROMETHEUS_TAR"
                
                # Create symbolic links to make prometheus available in PATH
                sudo ln -sf "$PROMETHEUS_DIR/prometheus" /usr/local/bin/prometheus
                sudo ln -sf "$PROMETHEUS_DIR/promtool" /usr/local/bin/promtool
            else
                log "Failed to extract Prometheus" "ERROR"
                exit 1
            fi
        fi
        
        log "Prometheus installed successfully"
    else
        log "Prometheus is already installed"
    fi
    
    # 2. Install Grafana
    if ! command_exists grafana-server; then
        log "Grafana not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            brew install grafana
        else
            # Linux installation
            PACKAGE_MANAGER=$(detect_package_manager)
            
            case $PACKAGE_MANAGER in
                apt)
                    sudo apt-get install -y apt-transport-https software-properties-common
                    wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
                    echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
                    sudo apt-get update
                    sudo apt-get install -y grafana
                    ;;
                yum)
                    cat > /etc/yum.repos.d/grafana.repo << EOF
[grafana]
name=grafana
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
                    sudo yum install -y grafana
                    ;;
                dnf)
                    cat > /etc/yum.repos.d/grafana.repo << EOF
[grafana]
name=grafana
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
                    sudo dnf install -y grafana
                    ;;
                *)
                    log "Unsupported package manager for Grafana installation" "ERROR"
                    exit 1
                    ;;
            esac
        fi
        
        log "Grafana installed successfully"
    else
        log "Grafana is already installed"
    fi
    
    # 3. Install Node Exporter
    if ! command_exists node_exporter; then
        log "Node Exporter not found, installing..."
        
        if [ "$OS" == "macOS" ]; then
            brew install node_exporter
        else
            # Linux installation
            NODE_EXPORTER_VERSION="1.6.0"
            NODE_EXPORTER_DIR="$MONITORING_DIR/node_exporter"
            mkdir -p "$NODE_EXPORTER_DIR"
            
            ARCH=$(uname -m)
            if [ "$ARCH" == "x86_64" ]; then
                NODE_EXPORTER_ARCH="amd64"
            elif [ "$ARCH" == "aarch64" ] || [ "$ARCH" == "arm64" ]; then
                NODE_EXPORTER_ARCH="arm64"
            else
                NODE_EXPORTER_ARCH="$ARCH"
            fi
            
            NODE_EXPORTER_URL="https://github.com/prometheus/node_exporter/releases/download/v$NODE_EXPORTER_VERSION/node_exporter-$NODE_EXPORTER_VERSION.linux-$NODE_EXPORTER_ARCH.tar.gz"
            NODE_EXPORTER_TAR="/tmp/node_exporter.tar.gz"
            
            download_file "$NODE_EXPORTER_URL" "$NODE_EXPORTER_TAR"
            
            tar -xzf "$NODE_EXPORTER_TAR" -C "/tmp"
            NODE_EXPORTER_EXTRACTED_DIR=$(find /tmp -maxdepth 1 -type d -name "node_exporter-*" | head -n 1)
            
            if [ -d "$NODE_EXPORTER_EXTRACTED_DIR" ]; then
                cp -r "$NODE_EXPORTER_EXTRACTED_DIR"/* "$NODE_EXPORTER_DIR/"
                rm -rf "$NODE_EXPORTER_EXTRACTED_DIR"
                rm "$NODE_EXPORTER_TAR"
                
                # Create symbolic link to make node_exporter available in PATH
                sudo ln -sf "$NODE_EXPORTER_DIR/node_exporter" /usr/local/bin/node_exporter
            else
                log "Failed to extract Node Exporter" "ERROR"
                exit 1
            fi
        fi
        
        log "Node Exporter installed successfully"
    else
        log "Node Exporter is already installed"
    fi
    
    # 4. Configure Prometheus
    log "Configuring Prometheus"
    PROMETHEUS_CONFIG_SRC="$CONFIG_DIR/prometheus.yml"
    
    if [ "$OS" == "macOS" ]; then
        PROMETHEUS_CONFIG_DST="/usr/local/etc/prometheus.yml"
    else
        PROMETHEUS_CONFIG_DST="$MONITORING_DIR/prometheus/prometheus.yml"
    fi
    
    if [ -f "$PROMETHEUS_CONFIG_SRC" ]; then
        sudo cp "$PROMETHEUS_CONFIG_SRC" "$PROMETHEUS_CONFIG_DST"
        log "Copied Prometheus configuration from $PROMETHEUS_CONFIG_SRC to $PROMETHEUS_CONFIG_DST"
    else
        log "Prometheus configuration not found at $PROMETHEUS_CONFIG_SRC, using default" "WARNING"
    fi
    
    # 5. Configure Grafana
    log "Configuring Grafana"
    GRAFANA_DASHBOARDS_SRC="$CONFIG_DIR/grafana_dashboards"
    
    if [ "$OS" == "macOS" ]; then
        GRAFANA_DASHBOARDS_DST="/usr/local/var/lib/grafana/dashboards"
    else
        if [ -d "/var/lib/grafana" ]; then
            GRAFANA_DASHBOARDS_DST="/var/lib/grafana/dashboards"
        else
            GRAFANA_DASHBOARDS_DST="$MONITORING_DIR/grafana/dashboards"
            mkdir -p "$GRAFANA_DASHBOARDS_DST"
        fi
    fi
    
    if [ -d "$GRAFANA_DASHBOARDS_SRC" ]; then
        sudo mkdir -p "$GRAFANA_DASHBOARDS_DST"
        sudo cp -r "$GRAFANA_DASHBOARDS_SRC"/* "$GRAFANA_DASHBOARDS_DST/"
        log "Copied Grafana dashboards from $GRAFANA_DASHBOARDS_SRC to $GRAFANA_DASHBOARDS_DST"
    else
        log "Grafana dashboards not found at $GRAFANA_DASHBOARDS_SRC, using default" "WARNING"
    fi
    
    # Configure Grafana datasource
    if [ "$OS" == "macOS" ]; then
        GRAFANA_PROVISIONING="/usr/local/var/lib/grafana/provisioning"
    else
        if [ -d "/etc/grafana" ]; then
            GRAFANA_PROVISIONING="/etc/grafana/provisioning"
        else
            GRAFANA_PROVISIONING="$MONITORING_DIR/grafana/provisioning"
            mkdir -p "$GRAFANA_PROVISIONING/datasources"
        fi
    fi
    
    sudo mkdir -p "$GRAFANA_PROVISIONING/datasources"
    
    cat > "/tmp/prometheus_datasource.yml" << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: false
EOF
    
    sudo mv "/tmp/prometheus_datasource.yml" "$GRAFANA_PROVISIONING/datasources/prometheus.yml"
    log "Configured Prometheus datasource for Grafana"
    
    # 6. Set up services
    if [ "$OS" == "macOS" ]; then
        # macOS services using launchd
        log "Setting up services using launchd"
        
        # Prometheus service
        create_launchd_service "com.cryptobot.prometheus" "Prometheus monitoring for Cryptobot" \
            "/usr/local/bin/prometheus" "--config.file=/usr/local/etc/prometheus.yml"
        
        # Grafana service
        create_launchd_service "com.cryptobot.grafana" "Grafana dashboards for Cryptobot" \
            "/usr/local/bin/grafana-server" "--homepath /usr/local/share/grafana --config /usr/local/etc/grafana/grafana.ini"
        
        # Node Exporter service
        create_launchd_service "com.cryptobot.node_exporter" "Prometheus Node Exporter for Cryptobot" \
            "/usr/local/bin/node_exporter" ""
        
    elif command_exists systemctl; then
        # Linux services using systemd
        log "Setting up services using systemd"
        
        # Prometheus service
        if [ -f "$MONITORING_DIR/prometheus/prometheus" ]; then
            create_systemd_service "cryptobot-prometheus" "Prometheus monitoring for Cryptobot" \
                "$MONITORING_DIR/prometheus/prometheus --config.file=$PROMETHEUS_CONFIG_DST --storage.tsdb.path=$MONITORING_DIR/prometheus/data"
        else
            create_systemd_service "cryptobot-prometheus" "Prometheus monitoring for Cryptobot" \
                "/usr/local/bin/prometheus --config.file=$PROMETHEUS_CONFIG_DST"
        fi
        
        # Grafana service (if not already managed by package manager)
        if ! systemctl is-active --quiet grafana-server; then
            create_systemd_service "cryptobot-grafana" "Grafana dashboards for Cryptobot" \
                "/usr/sbin/grafana-server --config=/etc/grafana/grafana.ini"
        else
            log "Grafana service is already managed by the system"
            sudo systemctl enable grafana-server
            sudo systemctl restart grafana-server
        fi
        
        # Node Exporter service
        if [ -f "$MONITORING_DIR/node_exporter/node_exporter" ]; then
            create_systemd_service "cryptobot-node-exporter" "Prometheus Node Exporter for Cryptobot" \
                "$MONITORING_DIR/node_exporter/node_exporter"
        else
            create_systemd_service "cryptobot-node-exporter" "Prometheus Node Exporter for Cryptobot" \
                "/usr/local/bin/node_exporter"
        fi
    else
        log "No service manager found (systemd or launchd), services must be started manually" "WARNING"
    fi
    
    log "Monitoring setup completed successfully"
    
} || {
    error_message="$?"
    log "Monitoring setup failed: $error_message" "ERROR"
    exit 1
}