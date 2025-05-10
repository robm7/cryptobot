<#
.SYNOPSIS
    Alerting setup script for Cryptobot non-Docker installation.
.DESCRIPTION
    This script sets up alerting for the Cryptobot application using Alertmanager and configures alert rules.
    It installs and configures the alerting tools and sets up notification channels.
.NOTES
    File Name      : setup_alerts.ps1
    Prerequisite   : PowerShell 5.1 or later
#>

# Stop on any error
$ErrorActionPreference = "Stop"

# Script variables
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootPath = (Get-Item $ScriptPath).Parent.Parent.FullName
$ConfigPath = Join-Path -Path $RootPath -ChildPath "config\non-docker\monitoring"
$LogPath = Join-Path -Path $RootPath -ChildPath "logs"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = Join-Path -Path $LogPath -ChildPath "alerting_setup_$Timestamp.log"

# Create log directory if it doesn't exist
if (-not (Test-Path -Path $LogPath)) {
    New-Item -Path $LogPath -ItemType Directory -Force | Out-Null
}

# Function to log messages
function Write-Log {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string]$Level = "INFO"
    )
    
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    
    # Write to console
    switch ($Level) {
        "INFO" { Write-Host $LogMessage -ForegroundColor Green }
        "WARNING" { Write-Host $LogMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $LogMessage -ForegroundColor Red }
    }
    
    # Write to log file
    Add-Content -Path $LogFile -Value $LogMessage
}

# Function to check if a command exists
function Test-CommandExists {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    
    $Exists = $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
    return $Exists
}

# Function to download a file
function Download-File {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Url,
        
        [Parameter(Mandatory=$true)]
        [string]$OutputPath
    )
    
    Write-Log "Downloading $Url to $OutputPath"
    
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutputPath
    } catch {
        Write-Log "Failed to download $Url: $_" -Level "ERROR"
        throw
    }
}

# Main alerting setup process
try {
    Write-Log "Starting alerting setup for Cryptobot"
    
    # Create monitoring directory
    $MonitoringDir = Join-Path -Path $RootPath -ChildPath "monitoring"
    if (-not (Test-Path -Path $MonitoringDir)) {
        New-Item -Path $MonitoringDir -ItemType Directory -Force | Out-Null
    }
    
    # Create alerting directory
    $AlertingDir = Join-Path -Path $MonitoringDir -ChildPath "alerting"
    if (-not (Test-Path -Path $AlertingDir)) {
        New-Item -Path $AlertingDir -ItemType Directory -Force | Out-Null
    }
    
    # 1. Check if Alertmanager is installed
    $AlertmanagerInstalled = Test-CommandExists -Command "alertmanager"
    if (-not $AlertmanagerInstalled) {
        Write-Log "Alertmanager not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_alerting"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Alertmanager
        $AlertmanagerUrl = "https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.windows-amd64.zip"
        $AlertmanagerZip = Join-Path -Path $TempDir -ChildPath "alertmanager.zip"
        Download-File -Url $AlertmanagerUrl -OutputPath $AlertmanagerZip
        
        # Extract Alertmanager
        $AlertmanagerDir = Join-Path -Path $AlertingDir -ChildPath "alertmanager"
        if (-not (Test-Path -Path $AlertmanagerDir)) {
            New-Item -Path $AlertmanagerDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Alertmanager to $AlertmanagerDir"
        Expand-Archive -Path $AlertmanagerZip -DestinationPath $AlertmanagerDir -Force
        
        # Move files from the extracted directory to the alertmanager directory
        $ExtractedDir = Get-ChildItem -Path $AlertmanagerDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $AlertmanagerDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Alertmanager to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains($AlertmanagerDir)) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$AlertmanagerDir", "Machine")
            Write-Log "Added Alertmanager to PATH"
        }
    } else {
        Write-Log "Alertmanager is already installed"
    }
    
    # 2. Configure Alertmanager
    Write-Log "Configuring Alertmanager"
    $AlertmanagerConfigPath = Join-Path -Path $AlertingDir -ChildPath "alertmanager\alertmanager.yml"
    
    # Create Alertmanager configuration
    $AlertmanagerConfig = @"
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
"@
    
    Set-Content -Path $AlertmanagerConfigPath -Value $AlertmanagerConfig
    Write-Log "Created Alertmanager configuration at $AlertmanagerConfigPath"
    
    # 3. Create Prometheus alert rules
    Write-Log "Creating Prometheus alert rules"
    $PrometheusRulesDir = Join-Path -Path $MonitoringDir -ChildPath "prometheus\rules"
    if (-not (Test-Path -Path $PrometheusRulesDir)) {
        New-Item -Path $PrometheusRulesDir -ItemType Directory -Force | Out-Null
    }
    
    $AlertRulesPath = Join-Path -Path $PrometheusRulesDir -ChildPath "alert_rules.yml"
    
    # Create alert rules
    $AlertRules = @"
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
"@
    
    Set-Content -Path $AlertRulesPath -Value $AlertRules
    Write-Log "Created Prometheus alert rules at $AlertRulesPath"
    
    # 4. Update Prometheus configuration to include alert rules and Alertmanager
    Write-Log "Updating Prometheus configuration"
    $PrometheusConfigPath = Join-Path -Path $MonitoringDir -ChildPath "prometheus\prometheus.yml"
    
    if (Test-Path -Path $PrometheusConfigPath) {
        $PrometheusConfig = Get-Content -Path $PrometheusConfigPath -Raw
        
        # Check if alerting configuration already exists
        if (-not ($PrometheusConfig -match "alerting:")) {
            $AlertingConfig = @"

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093

# Load rules once and periodically evaluate them
rule_files:
  - "rules/alert_rules.yml"
"@
            
            # Add alerting configuration after global section
            $PrometheusConfig = $PrometheusConfig -replace "(global:.*?(?=\n\w))", "`$1$AlertingConfig"
            
            Set-Content -Path $PrometheusConfigPath -Value $PrometheusConfig
            Write-Log "Updated Prometheus configuration with alerting settings"
        } else {
            Write-Log "Alerting configuration already exists in Prometheus config" -Level "WARNING"
        }
    } else {
        Write-Log "Prometheus configuration not found at $PrometheusConfigPath" -Level "ERROR"
    }
    
    # 5. Set up Alertmanager as a Windows service
    Write-Log "Setting up Alertmanager as a Windows service"
    $AlertmanagerExe = Join-Path -Path $AlertingDir -ChildPath "alertmanager\alertmanager.exe"
    $AlertmanagerServiceName = "CryptobotAlertmanager"
    $AlertmanagerService = Get-Service -Name $AlertmanagerServiceName -ErrorAction SilentlyContinue
    
    if ($AlertmanagerService) {
        Write-Log "Alertmanager service already exists, stopping and removing"
        Stop-Service -Name $AlertmanagerServiceName -Force
        $AlertmanagerService = Get-WmiObject -Class Win32_Service -Filter "Name='$AlertmanagerServiceName'"
        $AlertmanagerService.Delete()
    }
    
    Write-Log "Creating Alertmanager service"
    
    # Use NSSM to create the service
    $NssmPath = Join-Path -Path $RootPath -ChildPath "tools\nssm.exe"
    if (-not (Test-Path -Path $NssmPath)) {
        Write-Log "NSSM not found, downloading"
        $NssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $NssmZip = Join-Path -Path $env:TEMP -ChildPath "nssm.zip"
        Download-File -Url $NssmUrl -OutputPath $NssmZip
        
        $NssmDir = Join-Path -Path $RootPath -ChildPath "tools"
        if (-not (Test-Path -Path $NssmDir)) {
            New-Item -Path $NssmDir -ItemType Directory -Force | Out-Null
        }
        
        Expand-Archive -Path $NssmZip -DestinationPath $env:TEMP -Force
        $NssmExtractedDir = Get-ChildItem -Path $env:TEMP -Directory -Filter "nssm*" | Select-Object -First 1
        if ($NssmExtractedDir) {
            $NssmExe = Get-ChildItem -Path $NssmExtractedDir.FullName -Recurse -Filter "nssm.exe" | Where-Object { $_.DirectoryName -like "*win64*" } | Select-Object -First 1
            if ($NssmExe) {
                Copy-Item -Path $NssmExe.FullName -Destination $NssmPath -Force
            }
        }
    }
    
    if (Test-Path -Path $NssmPath) {
        & $NssmPath install $AlertmanagerServiceName $AlertmanagerExe "--config.file=$AlertmanagerConfigPath"
        & $NssmPath set $AlertmanagerServiceName DisplayName "Cryptobot Alertmanager"
        & $NssmPath set $AlertmanagerServiceName Description "Alertmanager for Cryptobot alerts"
        & $NssmPath set $AlertmanagerServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $AlertmanagerServiceName
        Write-Log "Alertmanager service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Alertmanager service" -Level "ERROR"
    }
    
    # 6. Restart Prometheus to apply new configuration
    Write-Log "Restarting Prometheus to apply new configuration"
    $PrometheusServiceName = "CryptobotPrometheus"
    $PrometheusService = Get-Service -Name $PrometheusServiceName -ErrorAction SilentlyContinue
    
    if ($PrometheusService) {
        Restart-Service -Name $PrometheusServiceName
        Write-Log "Prometheus service restarted"
    } else {
        Write-Log "Prometheus service not found, cannot restart" -Level "WARNING"
    }
    
    Write-Log "Alerting setup completed successfully"
    
} catch {
    $ErrorMessage = $_.Exception.Message
    Write-Log "Alerting setup failed: $ErrorMessage" -Level "ERROR"
    exit 1
}