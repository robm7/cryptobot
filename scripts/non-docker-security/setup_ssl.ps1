# Cryptobot SSL/TLS Configuration Script for Windows
# This script sets up SSL/TLS certificates and configures the application to use HTTPS

# Function to display messages
function Log {
    param (
        [string]$Message
    )
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Log "Error: This script must be run as Administrator. Please restart PowerShell as Administrator and try again."
    exit 1
}

Log "Starting SSL/TLS configuration for Cryptobot..."

# Load environment variables from .env file if it exists
if (Test-Path ".env") {
    Log "Loading environment variables from .env file..."
    $envContent = Get-Content ".env" -Raw
    $envLines = $envContent -split "`n" | Where-Object { $_ -match '^\s*[^#]' }
    $envVars = @{}
    foreach ($line in $envLines) {
        if ($line -match '^\s*([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $envVars[$key] = $value
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
} else {
    Log "Warning: .env file not found. Using default values."
    # Set default values
    $envVars = @{
        "AUTH_SERVICE_PORT" = "8000"
        "STRATEGY_SERVICE_PORT" = "8010"
        "BACKTEST_SERVICE_PORT" = "8020"
        "TRADE_SERVICE_PORT" = "8030"
        "DATA_SERVICE_PORT" = "8001"
    }
}

# Check if OpenSSL is installed
$openSSLPath = $null
$openSSLPaths = @(
    "C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
    "C:\Program Files (x86)\OpenSSL-Win32\bin\openssl.exe",
    "C:\OpenSSL-Win64\bin\openssl.exe",
    "C:\OpenSSL-Win32\bin\openssl.exe"
)

foreach ($path in $openSSLPaths) {
    if (Test-Path $path) {
        $openSSLPath = $path
        break
    }
}

if (-not $openSSLPath) {
    # Try to find OpenSSL in PATH
    try {
        $openSSLPath = (Get-Command "openssl.exe" -ErrorAction Stop).Source
    } catch {
        Log "Error: OpenSSL is not installed or not in PATH. Please install OpenSSL and try again."
        Log "You can download OpenSSL from https://slproweb.com/products/Win32OpenSSL.html"
        exit 1
    }
}

Log "Using OpenSSL from: $openSSLPath"

# Create SSL directory if it doesn't exist
New-Item -ItemType Directory -Force -Path "config\ssl" | Out-Null
Set-Location "config\ssl"

# Generate SSL configuration file
Log "Generating SSL configuration file..."
$opensslConfig = @"
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C = US
ST = State
L = City
O = Cryptobot
OU = Security
CN = localhost

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
"@

Set-Content -Path "openssl.cnf" -Value $opensslConfig

# Generate CA key and certificate
Log "Generating CA key and certificate..."
& $openSSLPath genrsa -out ca.key 4096
& $openSSLPath req -new -x509 -key ca.key -out ca.crt -days 3650 -subj "/C=US/ST=State/L=City/O=Cryptobot/OU=Security/CN=Cryptobot CA"

# Generate server key and certificate signing request
Log "Generating server key and certificate signing request..."
& $openSSLPath genrsa -out server.key 2048
& $openSSLPath req -new -key server.key -out server.csr -config openssl.cnf

# Sign the server certificate with the CA
Log "Signing server certificate with CA..."
& $openSSLPath x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -extensions v3_req -extfile openssl.cnf

# Generate Diffie-Hellman parameters for perfect forward secrecy
Log "Generating Diffie-Hellman parameters (this may take a while)..."
& $openSSLPath dhparam -out dhparam.pem 2048

# Clean up
Remove-Item -Path "server.csr" -Force -ErrorAction SilentlyContinue
Remove-Item -Path "ca.srl" -Force -ErrorAction SilentlyContinue

# Set proper permissions
Log "Setting proper permissions for SSL files..."
$acl = Get-Acl "server.key"
$acl.SetAccessRuleProtection($true, $false)
$administratorsRule = New-Object System.Security.AccessControl.FileSystemAccessRule("Administrators", "FullControl", "Allow")
$systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule("SYSTEM", "FullControl", "Allow")
$currentUserRule = New-Object System.Security.AccessControl.FileSystemAccessRule([System.Security.Principal.WindowsIdentity]::GetCurrent().Name, "FullControl", "Allow")
$acl.AddAccessRule($administratorsRule)
$acl.AddAccessRule($systemRule)
$acl.AddAccessRule($currentUserRule)
Set-Acl "server.key" $acl
Set-Acl "ca.key" $acl

# Return to the original directory
Set-Location -Path (Split-Path -Parent (Split-Path -Parent $PWD.Path))

# Update environment configuration to use HTTPS
Log "Updating environment configuration to use HTTPS..."
$envContent = if (Test-Path ".env") { Get-Content ".env" -Raw } else { "" }
$envLines = $envContent -split "`n"
$updatedEnvLines = @()
$useHttpsAdded = $false
$sslCertPathAdded = $false
$sslKeyPathAdded = $false
$sslCaPathAdded = $false
$sslDhParamsPathAdded = $false

foreach ($line in $envLines) {
    if ($line -match '^USE_HTTPS=') {
        $updatedEnvLines += "USE_HTTPS=true"
        $useHttpsAdded = $true
    } elseif ($line -match '^SSL_CERT_PATH=') {
        $updatedEnvLines += "SSL_CERT_PATH=config/ssl/server.crt"
        $sslCertPathAdded = $true
    } elseif ($line -match '^SSL_KEY_PATH=') {
        $updatedEnvLines += "SSL_KEY_PATH=config/ssl/server.key"
        $sslKeyPathAdded = $true
    } elseif ($line -match '^SSL_CA_PATH=') {
        $updatedEnvLines += "SSL_CA_PATH=config/ssl/ca.crt"
        $sslCaPathAdded = $true
    } elseif ($line -match '^SSL_DH_PARAMS_PATH=') {
        $updatedEnvLines += "SSL_DH_PARAMS_PATH=config/ssl/dhparam.pem"
        $sslDhParamsPathAdded = $true
    } else {
        $updatedEnvLines += $line
    }
}

if (-not $useHttpsAdded) {
    $updatedEnvLines += "USE_HTTPS=true"
}

if (-not $sslCertPathAdded) {
    $updatedEnvLines += "SSL_CERT_PATH=config/ssl/server.crt"
}

if (-not $sslKeyPathAdded) {
    $updatedEnvLines += "SSL_KEY_PATH=config/ssl/server.key"
}

if (-not $sslCaPathAdded) {
    $updatedEnvLines += "SSL_CA_PATH=config/ssl/ca.crt"
}

if (-not $sslDhParamsPathAdded) {
    $updatedEnvLines += "SSL_DH_PARAMS_PATH=config/ssl/dhparam.pem"
}

# Save updated .env file
$updatedEnvContent = $updatedEnvLines -join "`n"
Set-Content -Path ".env" -Value $updatedEnvContent

# Create HTTPS configuration for services
Log "Creating HTTPS configuration for services..."

# Create SSL configuration file for services
$sslConfig = @{
    ssl = @{
        enabled = $true
        cert_path = "config/ssl/server.crt"
        key_path = "config/ssl/server.key"
        ca_path = "config/ssl/ca.crt"
        dh_params_path = "config/ssl/dhparam.pem"
        protocols = @("TLSv1.2", "TLSv1.3")
        ciphers = "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384"
        prefer_server_ciphers = $true
        session_timeout = 3600
        session_cache = "shared:SSL:10m"
        stapling = $true
        stapling_verify = $true
        headers = @{
            "Strict-Transport-Security" = "max-age=63072000; includeSubDomains; preload"
            "X-Frame-Options" = "SAMEORIGIN"
            "X-Content-Type-Options" = "nosniff"
            "X-XSS-Protection" = "1; mode=block"
            "Referrer-Policy" = "strict-origin-when-cross-origin"
        }
    }
}

$sslConfigJson = $sslConfig | ConvertTo-Json -Depth 5
Set-Content -Path "config\ssl\ssl_config.json" -Value $sslConfigJson

# Create Python SSL configuration module
New-Item -ItemType Directory -Force -Path "utils\ssl" | Out-Null
$sslModuleContent = @"
# SSL/TLS Configuration Module
import os
import json
import ssl

def load_ssl_config():
    """Load SSL configuration from config file"""
    config_path = os.path.join(os.getcwd(), 'config', 'ssl', 'ssl_config.json')
    
    if not os.path.exists(config_path):
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config.get('ssl', {})

def create_ssl_context():
    """Create an SSL context for HTTPS servers"""
    ssl_config = load_ssl_config()
    
    if not ssl_config or not ssl_config.get('enabled', False):
        return None
    
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # Load certificate and private key
    cert_path = os.path.join(os.getcwd(), ssl_config.get('cert_path', ''))
    key_path = os.path.join(os.getcwd(), ssl_config.get('key_path', ''))
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    else:
        return None
    
    # Set SSL/TLS protocol versions
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    
    # Set cipher suite
    if ssl_config.get('ciphers'):
        context.set_ciphers(ssl_config.get('ciphers'))
    
    # Enable OCSP stapling if available
    if hasattr(ssl, 'OPENSSL_VERSION_NUMBER') and ssl.OPENSSL_VERSION_NUMBER >= 0x10002000:
        if ssl_config.get('stapling', False):
            context.options |= 0x4000  # SSL_OP_NO_TICKET
            context.options |= 0x2000000  # SSL_OP_SINGLE_DH_USE
            context.options |= 0x100000  # SSL_OP_SINGLE_ECDH_USE
    
    return context
"@

Set-Content -Path "utils\ssl\__init__.py" -Value $sslModuleContent

# Update service startup scripts to use HTTPS
Log "Updating service startup scripts to use HTTPS..."

# Update auth service
if (Test-Path "auth\main.py") {
    $authMainContent = Get-Content "auth\main.py" -Raw
    
    # Check if SSL import already exists
    if (-not ($authMainContent -match "from utils.ssl import create_ssl_context")) {
        # Add SSL import
        $authMainContent = $authMainContent -replace "import uvicorn", "import uvicorn`nfrom utils.ssl import create_ssl_context"
        
        # Update uvicorn.run to use SSL
        $authMainContent = $authMainContent -replace "uvicorn\.run\(\s*`"main:app`",\s*host=`"0\.0\.0\.0`",\s*port=8000,\s*reload=True\s*\)", "uvicorn.run(`"main:app`", host=`"0.0.0.0`", port=8000, reload=True, ssl_keyfile=`"config/ssl/server.key`", ssl_certfile=`"config/ssl/server.crt`")"
        
        # Save updated file
        Set-Content -Path "auth\main.py" -Value $authMainContent
    }
}

Log "SSL/TLS configuration completed successfully!"
Log "Note: You may need to restart services for the changes to take effect."
Log "Important: The generated certificates are self-signed and intended for development/testing."
Log "For production, please obtain certificates from a trusted certificate authority."
exit 0