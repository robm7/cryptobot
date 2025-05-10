<#
.SYNOPSIS
    Monitoring setup script for Cryptobot non-Docker installation.
.DESCRIPTION
    This script sets up monitoring for the Cryptobot application using Prometheus and Grafana.
    It installs and configures the monitoring tools and sets up dashboards for system and application monitoring.
.NOTES
    File Name      : setup_monitoring.ps1
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
$LogFile = Join-Path -Path $LogPath -ChildPath "monitoring_setup_$Timestamp.log"

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

# Main monitoring setup process
try {
    Write-Log "Starting monitoring setup for Cryptobot"
    
    # 1. Check if Prometheus is installed
    $PrometheusInstalled = Test-CommandExists -Command "prometheus"
    if (-not $PrometheusInstalled) {
        Write-Log "Prometheus not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_monitoring"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Prometheus
        $PrometheusUrl = "https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.windows-amd64.zip"
        $PrometheusZip = Join-Path -Path $TempDir -ChildPath "prometheus.zip"
        Download-File -Url $PrometheusUrl -OutputPath $PrometheusZip
        
        # Extract Prometheus
        $PrometheusDir = Join-Path -Path $RootPath -ChildPath "monitoring\prometheus"
        if (-not (Test-Path -Path $PrometheusDir)) {
            New-Item -Path $PrometheusDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Prometheus to $PrometheusDir"
        Expand-Archive -Path $PrometheusZip -DestinationPath $PrometheusDir -Force
        
        # Move files from the extracted directory to the prometheus directory
        $ExtractedDir = Get-ChildItem -Path $PrometheusDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $PrometheusDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Prometheus to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains($PrometheusDir)) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$PrometheusDir", "Machine")
            Write-Log "Added Prometheus to PATH"
        }
    } else {
        Write-Log "Prometheus is already installed"
    }
    
    # 2. Check if Grafana is installed
    $GrafanaInstalled = Test-CommandExists -Command "grafana-server"
    if (-not $GrafanaInstalled) {
        Write-Log "Grafana not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_monitoring"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Grafana
        $GrafanaUrl = "https://dl.grafana.com/oss/release/grafana-10.0.3.windows-amd64.zip"
        $GrafanaZip = Join-Path -Path $TempDir -ChildPath "grafana.zip"
        Download-File -Url $GrafanaUrl -OutputPath $GrafanaZip
        
        # Extract Grafana
        $GrafanaDir = Join-Path -Path $RootPath -ChildPath "monitoring\grafana"
        if (-not (Test-Path -Path $GrafanaDir)) {
            New-Item -Path $GrafanaDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Grafana to $GrafanaDir"
        Expand-Archive -Path $GrafanaZip -DestinationPath $GrafanaDir -Force
        
        # Move files from the extracted directory to the grafana directory
        $ExtractedDir = Get-ChildItem -Path $GrafanaDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $GrafanaDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Grafana to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains($GrafanaDir)) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$GrafanaDir\bin", "Machine")
            Write-Log "Added Grafana to PATH"
        }
    } else {
        Write-Log "Grafana is already installed"
    }
    
    # 3. Check if Node Exporter is installed
    $NodeExporterInstalled = Test-CommandExists -Command "node_exporter"
    if (-not $NodeExporterInstalled) {
        Write-Log "Node Exporter not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_monitoring"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Node Exporter
        $NodeExporterUrl = "https://github.com/prometheus/node_exporter/releases/download/v1.6.0/node_exporter-1.6.0.windows-amd64.zip"
        $NodeExporterZip = Join-Path -Path $TempDir -ChildPath "node_exporter.zip"
        Download-File -Url $NodeExporterUrl -OutputPath $NodeExporterZip
        
        # Extract Node Exporter
        $NodeExporterDir = Join-Path -Path $RootPath -ChildPath "monitoring\node_exporter"
        if (-not (Test-Path -Path $NodeExporterDir)) {
            New-Item -Path $NodeExporterDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Node Exporter to $NodeExporterDir"
        Expand-Archive -Path $NodeExporterZip -DestinationPath $NodeExporterDir -Force
        
        # Move files from the extracted directory to the node_exporter directory
        $ExtractedDir = Get-ChildItem -Path $NodeExporterDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $NodeExporterDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Node Exporter to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains($NodeExporterDir)) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$NodeExporterDir", "Machine")
            Write-Log "Added Node Exporter to PATH"
        }
    } else {
        Write-Log "Node Exporter is already installed"
    }
    
    # 4. Configure Prometheus
    Write-Log "Configuring Prometheus"
    $PrometheusConfigSrc = Join-Path -Path $ConfigPath -ChildPath "prometheus.yml"
    $PrometheusConfigDst = Join-Path -Path $RootPath -ChildPath "monitoring\prometheus\prometheus.yml"
    
    if (Test-Path -Path $PrometheusConfigSrc) {
        Copy-Item -Path $PrometheusConfigSrc -Destination $PrometheusConfigDst -Force
        Write-Log "Copied Prometheus configuration from $PrometheusConfigSrc to $PrometheusConfigDst"
    } else {
        Write-Log "Prometheus configuration not found at $PrometheusConfigSrc, using default" -Level "WARNING"
    }
    
    # 5. Configure Grafana
    Write-Log "Configuring Grafana"
    $GrafanaDashboardsDir = Join-Path -Path $ConfigPath -ChildPath "grafana_dashboards"
    $GrafanaDashboardsDst = Join-Path -Path $RootPath -ChildPath "monitoring\grafana\conf\provisioning\dashboards"
    
    if (-not (Test-Path -Path $GrafanaDashboardsDst)) {
        New-Item -Path $GrafanaDashboardsDst -ItemType Directory -Force | Out-Null
    }
    
    if (Test-Path -Path $GrafanaDashboardsDir) {
        Copy-Item -Path "$GrafanaDashboardsDir\*" -Destination $GrafanaDashboardsDst -Force -Recurse
        Write-Log "Copied Grafana dashboards from $GrafanaDashboardsDir to $GrafanaDashboardsDst"
    } else {
        Write-Log "Grafana dashboards not found at $GrafanaDashboardsDir, using default" -Level "WARNING"
    }
    
    # 6. Set up Prometheus as a Windows service
    Write-Log "Setting up Prometheus as a Windows service"
    $PrometheusExe = Join-Path -Path $RootPath -ChildPath "monitoring\prometheus\prometheus.exe"
    $PrometheusConfig = Join-Path -Path $RootPath -ChildPath "monitoring\prometheus\prometheus.yml"
    $PrometheusDataDir = Join-Path -Path $RootPath -ChildPath "monitoring\prometheus\data"
    
    if (-not (Test-Path -Path $PrometheusDataDir)) {
        New-Item -Path $PrometheusDataDir -ItemType Directory -Force | Out-Null
    }
    
    $PrometheusServiceName = "CryptobotPrometheus"
    $PrometheusService = Get-Service -Name $PrometheusServiceName -ErrorAction SilentlyContinue
    
    if ($PrometheusService) {
        Write-Log "Prometheus service already exists, stopping and removing"
        Stop-Service -Name $PrometheusServiceName -Force
        $PrometheusService = Get-WmiObject -Class Win32_Service -Filter "Name='$PrometheusServiceName'"
        $PrometheusService.Delete()
    }
    
    Write-Log "Creating Prometheus service"
    $PrometheusArgs = "--config.file=`"$PrometheusConfig`" --storage.tsdb.path=`"$PrometheusDataDir`" --web.console.templates=`"$RootPath\monitoring\prometheus\consoles`" --web.console.libraries=`"$RootPath\monitoring\prometheus\console_libraries`""
    
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
        & $NssmPath install $PrometheusServiceName $PrometheusExe $PrometheusArgs
        & $NssmPath set $PrometheusServiceName DisplayName "Cryptobot Prometheus"
        & $NssmPath set $PrometheusServiceName Description "Prometheus monitoring for Cryptobot"
        & $NssmPath set $PrometheusServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $PrometheusServiceName
        Write-Log "Prometheus service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Prometheus service" -Level "ERROR"
    }
    
    # 7. Set up Grafana as a Windows service
    Write-Log "Setting up Grafana as a Windows service"
    $GrafanaExe = Join-Path -Path $RootPath -ChildPath "monitoring\grafana\bin\grafana-server.exe"
    $GrafanaServiceName = "CryptobotGrafana"
    $GrafanaService = Get-Service -Name $GrafanaServiceName -ErrorAction SilentlyContinue
    
    if ($GrafanaService) {
        Write-Log "Grafana service already exists, stopping and removing"
        Stop-Service -Name $GrafanaServiceName -Force
        $GrafanaService = Get-WmiObject -Class Win32_Service -Filter "Name='$GrafanaServiceName'"
        $GrafanaService.Delete()
    }
    
    Write-Log "Creating Grafana service"
    $GrafanaHomePath = Join-Path -Path $RootPath -ChildPath "monitoring\grafana"
    $GrafanaArgs = "--homepath=`"$GrafanaHomePath`" --config=`"$GrafanaHomePath\conf\defaults.ini`""
    
    if (Test-Path -Path $NssmPath) {
        & $NssmPath install $GrafanaServiceName $GrafanaExe $GrafanaArgs
        & $NssmPath set $GrafanaServiceName DisplayName "Cryptobot Grafana"
        & $NssmPath set $GrafanaServiceName Description "Grafana dashboards for Cryptobot"
        & $NssmPath set $GrafanaServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $GrafanaServiceName
        Write-Log "Grafana service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Grafana service" -Level "ERROR"
    }
    
    # 8. Set up Node Exporter as a Windows service
    Write-Log "Setting up Node Exporter as a Windows service"
    $NodeExporterExe = Join-Path -Path $RootPath -ChildPath "monitoring\node_exporter\node_exporter.exe"
    $NodeExporterServiceName = "CryptobotNodeExporter"
    $NodeExporterService = Get-Service -Name $NodeExporterServiceName -ErrorAction SilentlyContinue
    
    if ($NodeExporterService) {
        Write-Log "Node Exporter service already exists, stopping and removing"
        Stop-Service -Name $NodeExporterServiceName -Force
        $NodeExporterService = Get-WmiObject -Class Win32_Service -Filter "Name='$NodeExporterServiceName'"
        $NodeExporterService.Delete()
    }
    
    Write-Log "Creating Node Exporter service"
    
    if (Test-Path -Path $NssmPath) {
        & $NssmPath install $NodeExporterServiceName $NodeExporterExe
        & $NssmPath set $NodeExporterServiceName DisplayName "Cryptobot Node Exporter"
        & $NssmPath set $NodeExporterServiceName Description "Prometheus Node Exporter for Cryptobot"
        & $NssmPath set $NodeExporterServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $NodeExporterServiceName
        Write-Log "Node Exporter service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Node Exporter service" -Level "ERROR"
    }
    
    Write-Log "Monitoring setup completed successfully"
    
} catch {
    $ErrorMessage = $_.Exception.Message
    Write-Log "Monitoring setup failed: $ErrorMessage" -Level "ERROR"
    exit 1
}