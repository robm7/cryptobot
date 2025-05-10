<#
.SYNOPSIS
    Log aggregation setup script for Cryptobot non-Docker installation.
.DESCRIPTION
    This script sets up log aggregation for the Cryptobot application using Filebeat and Elasticsearch.
    It installs and configures the logging tools and sets up dashboards for log visualization.
.NOTES
    File Name      : setup_logging.ps1
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
$LogFile = Join-Path -Path $LogPath -ChildPath "logging_setup_$Timestamp.log"

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

# Main logging setup process
try {
    Write-Log "Starting logging setup for Cryptobot"
    
    # Create monitoring directory
    $MonitoringDir = Join-Path -Path $RootPath -ChildPath "monitoring"
    if (-not (Test-Path -Path $MonitoringDir)) {
        New-Item -Path $MonitoringDir -ItemType Directory -Force | Out-Null
    }
    
    # Create logging directory
    $LoggingDir = Join-Path -Path $MonitoringDir -ChildPath "logging"
    if (-not (Test-Path -Path $LoggingDir)) {
        New-Item -Path $LoggingDir -ItemType Directory -Force | Out-Null
    }
    
    # 1. Check if Filebeat is installed
    $FilebeatInstalled = Test-CommandExists -Command "filebeat"
    if (-not $FilebeatInstalled) {
        Write-Log "Filebeat not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_logging"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Filebeat
        $FilebeatUrl = "https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.10.4-windows-x86_64.zip"
        $FilebeatZip = Join-Path -Path $TempDir -ChildPath "filebeat.zip"
        Download-File -Url $FilebeatUrl -OutputPath $FilebeatZip
        
        # Extract Filebeat
        $FilebeatDir = Join-Path -Path $LoggingDir -ChildPath "filebeat"
        if (-not (Test-Path -Path $FilebeatDir)) {
            New-Item -Path $FilebeatDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Filebeat to $FilebeatDir"
        Expand-Archive -Path $FilebeatZip -DestinationPath $FilebeatDir -Force
        
        # Move files from the extracted directory to the filebeat directory
        $ExtractedDir = Get-ChildItem -Path $FilebeatDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $FilebeatDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Filebeat to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains($FilebeatDir)) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$FilebeatDir", "Machine")
            Write-Log "Added Filebeat to PATH"
        }
    } else {
        Write-Log "Filebeat is already installed"
    }
    
    # 2. Configure Filebeat
    Write-Log "Configuring Filebeat"
    $FilebeatConfigPath = Join-Path -Path $LoggingDir -ChildPath "filebeat\filebeat.yml"
    
    # Create Filebeat configuration
    $FilebeatConfig = @"
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - $LogPath\*.log
    - $LogPath\auth\*.log
    - $LogPath\strategy\*.log
    - $LogPath\backtest\*.log
    - $LogPath\trade\*.log
    - $LogPath\data\*.log
    - $LogPath\mcp\*.log
  fields:
    application: cryptobot
  fields_under_root: true
  multiline:
    pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}'
    negate: true
    match: after

filebeat.config.modules:
  path: `${path.config}/modules.d/*.yml
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
"@
    
    Set-Content -Path $FilebeatConfigPath -Value $FilebeatConfig
    Write-Log "Created Filebeat configuration at $FilebeatConfigPath"
    
    # 3. Check if Elasticsearch is installed
    $ElasticsearchInstalled = Test-CommandExists -Command "elasticsearch"
    if (-not $ElasticsearchInstalled) {
        Write-Log "Elasticsearch not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_logging"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Elasticsearch
        $ElasticsearchUrl = "https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.10.4-windows-x86_64.zip"
        $ElasticsearchZip = Join-Path -Path $TempDir -ChildPath "elasticsearch.zip"
        Download-File -Url $ElasticsearchUrl -OutputPath $ElasticsearchZip
        
        # Extract Elasticsearch
        $ElasticsearchDir = Join-Path -Path $LoggingDir -ChildPath "elasticsearch"
        if (-not (Test-Path -Path $ElasticsearchDir)) {
            New-Item -Path $ElasticsearchDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Elasticsearch to $ElasticsearchDir"
        Expand-Archive -Path $ElasticsearchZip -DestinationPath $ElasticsearchDir -Force
        
        # Move files from the extracted directory to the elasticsearch directory
        $ExtractedDir = Get-ChildItem -Path $ElasticsearchDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $ElasticsearchDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Elasticsearch to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains("$ElasticsearchDir\bin")) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$ElasticsearchDir\bin", "Machine")
            Write-Log "Added Elasticsearch to PATH"
        }
    } else {
        Write-Log "Elasticsearch is already installed"
    }
    
    # 4. Check if Kibana is installed
    $KibanaInstalled = Test-CommandExists -Command "kibana"
    if (-not $KibanaInstalled) {
        Write-Log "Kibana not found, installing..."
        
        # Create temporary directory for downloads
        $TempDir = Join-Path -Path $env:TEMP -ChildPath "cryptobot_logging"
        if (-not (Test-Path -Path $TempDir)) {
            New-Item -Path $TempDir -ItemType Directory -Force | Out-Null
        }
        
        # Download Kibana
        $KibanaUrl = "https://artifacts.elastic.co/downloads/kibana/kibana-8.10.4-windows-x86_64.zip"
        $KibanaZip = Join-Path -Path $TempDir -ChildPath "kibana.zip"
        Download-File -Url $KibanaUrl -OutputPath $KibanaZip
        
        # Extract Kibana
        $KibanaDir = Join-Path -Path $LoggingDir -ChildPath "kibana"
        if (-not (Test-Path -Path $KibanaDir)) {
            New-Item -Path $KibanaDir -ItemType Directory -Force | Out-Null
        }
        
        Write-Log "Extracting Kibana to $KibanaDir"
        Expand-Archive -Path $KibanaZip -DestinationPath $KibanaDir -Force
        
        # Move files from the extracted directory to the kibana directory
        $ExtractedDir = Get-ChildItem -Path $KibanaDir -Directory | Select-Object -First 1
        if ($ExtractedDir) {
            Get-ChildItem -Path $ExtractedDir.FullName | Move-Item -Destination $KibanaDir -Force
            Remove-Item -Path $ExtractedDir.FullName -Force -Recurse
        }
        
        # Add Kibana to PATH
        $EnvPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
        if (-not $EnvPath.Contains("$KibanaDir\bin")) {
            [Environment]::SetEnvironmentVariable("PATH", "$EnvPath;$KibanaDir\bin", "Machine")
            Write-Log "Added Kibana to PATH"
        }
    } else {
        Write-Log "Kibana is already installed"
    }
    
    # 5. Set up Elasticsearch as a Windows service
    Write-Log "Setting up Elasticsearch as a Windows service"
    $ElasticsearchExe = Join-Path -Path $LoggingDir -ChildPath "elasticsearch\bin\elasticsearch.bat"
    $ElasticsearchServiceName = "CryptobotElasticsearch"
    $ElasticsearchService = Get-Service -Name $ElasticsearchServiceName -ErrorAction SilentlyContinue
    
    if ($ElasticsearchService) {
        Write-Log "Elasticsearch service already exists, stopping and removing"
        Stop-Service -Name $ElasticsearchServiceName -Force
        $ElasticsearchService = Get-WmiObject -Class Win32_Service -Filter "Name='$ElasticsearchServiceName'"
        $ElasticsearchService.Delete()
    }
    
    Write-Log "Creating Elasticsearch service"
    
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
        & $NssmPath install $ElasticsearchServiceName $ElasticsearchExe
        & $NssmPath set $ElasticsearchServiceName DisplayName "Cryptobot Elasticsearch"
        & $NssmPath set $ElasticsearchServiceName Description "Elasticsearch for Cryptobot log aggregation"
        & $NssmPath set $ElasticsearchServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $ElasticsearchServiceName
        Write-Log "Elasticsearch service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Elasticsearch service" -Level "ERROR"
    }
    
    # 6. Set up Kibana as a Windows service
    Write-Log "Setting up Kibana as a Windows service"
    $KibanaExe = Join-Path -Path $LoggingDir -ChildPath "kibana\bin\kibana.bat"
    $KibanaServiceName = "CryptobotKibana"
    $KibanaService = Get-Service -Name $KibanaServiceName -ErrorAction SilentlyContinue
    
    if ($KibanaService) {
        Write-Log "Kibana service already exists, stopping and removing"
        Stop-Service -Name $KibanaServiceName -Force
        $KibanaService = Get-WmiObject -Class Win32_Service -Filter "Name='$KibanaServiceName'"
        $KibanaService.Delete()
    }
    
    Write-Log "Creating Kibana service"
    
    if (Test-Path -Path $NssmPath) {
        & $NssmPath install $KibanaServiceName $KibanaExe
        & $NssmPath set $KibanaServiceName DisplayName "Cryptobot Kibana"
        & $NssmPath set $KibanaServiceName Description "Kibana for Cryptobot log visualization"
        & $NssmPath set $KibanaServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $KibanaServiceName
        Write-Log "Kibana service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Kibana service" -Level "ERROR"
    }
    
    # 7. Set up Filebeat as a Windows service
    Write-Log "Setting up Filebeat as a Windows service"
    $FilebeatExe = Join-Path -Path $LoggingDir -ChildPath "filebeat\filebeat.exe"
    $FilebeatServiceName = "CryptobotFilebeat"
    $FilebeatService = Get-Service -Name $FilebeatServiceName -ErrorAction SilentlyContinue
    
    if ($FilebeatService) {
        Write-Log "Filebeat service already exists, stopping and removing"
        Stop-Service -Name $FilebeatServiceName -Force
        $FilebeatService = Get-WmiObject -Class Win32_Service -Filter "Name='$FilebeatServiceName'"
        $FilebeatService.Delete()
    }
    
    Write-Log "Creating Filebeat service"
    
    if (Test-Path -Path $NssmPath) {
        & $NssmPath install $FilebeatServiceName $FilebeatExe "-c $FilebeatConfigPath -e"
        & $NssmPath set $FilebeatServiceName DisplayName "Cryptobot Filebeat"
        & $NssmPath set $FilebeatServiceName Description "Filebeat for Cryptobot log collection"
        & $NssmPath set $FilebeatServiceName Start SERVICE_AUTO_START
        
        Start-Service -Name $FilebeatServiceName
        Write-Log "Filebeat service created and started"
    } else {
        Write-Log "NSSM not found, cannot create Filebeat service" -Level "ERROR"
    }
    
    # 8. Wait for Elasticsearch and Kibana to start
    Write-Log "Waiting for Elasticsearch and Kibana to start..."
    Start-Sleep -Seconds 30
    
    # 9. Set up Filebeat dashboards
    Write-Log "Setting up Filebeat dashboards"
    $FilebeatSetupCmd = Join-Path -Path $LoggingDir -ChildPath "filebeat\filebeat.exe"
    & $FilebeatSetupCmd setup --dashboards -c "$FilebeatConfigPath"
    
    Write-Log "Logging setup completed successfully"
    
} catch {
    $ErrorMessage = $_.Exception.Message
    Write-Log "Logging setup failed: $ErrorMessage" -Level "ERROR"
    exit 1
}