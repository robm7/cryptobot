# Cryptobot Vulnerability Assessment Script for Windows
# This script performs security vulnerability assessments on the Cryptobot application

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
    Log "Warning: This script is not running as Administrator. Some checks may not complete successfully."
}

# Create output directory
New-Item -ItemType Directory -Force -Path "reports\security" | Out-Null
$reportFile = "reports\security\vulnerability_assessment_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
New-Item -ItemType File -Force -Path $reportFile | Out-Null

# Function to write to report file
function Write-Report {
    param (
        [string]$Message
    )
    $Message | Tee-Object -FilePath $reportFile -Append
}

Write-Report "==================================================="
Write-Report "Cryptobot Vulnerability Assessment Report"
Write-Report "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Report "OS: Windows"
Write-Report "==================================================="
Write-Report ""

Log "Starting vulnerability assessment for Cryptobot..."

# Check Python version
Write-Report "## Python Environment Check"
try {
    $pythonVersion = python --version 2>&1
    Write-Report "Python version: $pythonVersion"
    
    # Check if Python version is secure (>=3.7)
    if ($pythonVersion -match "Python 3\.(\d+)") {
        $minorVersion = [int]$Matches[1]
        if ($minorVersion -lt 7) {
            Write-Report "WARNING: Python version is outdated and may have security vulnerabilities. Recommend upgrading to Python 3.7 or newer."
        } else {
            Write-Report "Python version is up-to-date."
        }
    }
} catch {
    Write-Report "ERROR: Python not found. Please install Python 3.7 or newer."
}
Write-Report ""

# Check for vulnerable dependencies
Write-Report "## Dependency Vulnerability Check"
if (Test-Path "requirements.txt") {
    Write-Report "Checking Python dependencies for known vulnerabilities..."
    
    # Try pip-audit if available
    try {
        $pipAuditResult = pip-audit -r requirements.txt 2>&1
        Write-Report $pipAuditResult
    } catch {
        # Try safety if available
        try {
            $safetyResult = safety check -r requirements.txt --json 2>&1
            Write-Report $safetyResult
        } catch {
            Write-Report "WARNING: Neither pip-audit nor safety is installed. Cannot check dependencies for vulnerabilities."
            Write-Report "To install: pip install pip-audit or pip install safety"
            
            # List dependencies anyway
            Write-Report "Dependencies from requirements.txt:"
            Get-Content requirements.txt | Where-Object { $_ -notmatch "^#" -and $_ -match "\S" } | ForEach-Object {
                Write-Report $_
            }
        }
    }
} else {
    Write-Report "WARNING: requirements.txt not found. Cannot check dependencies for vulnerabilities."
}
Write-Report ""

# Check for secrets in code
Write-Report "## Secret Detection"
Write-Report "Checking for hardcoded secrets in code..."

$secretPatterns = @(
    "password\s*=\s*['\"][^'\"]+['\"]",
    "api_key\s*=\s*['\"][^'\"]+['\"]",
    "secret\s*=\s*['\"][^'\"]+['\"]",
    "token\s*=\s*['\"][^'\"]+['\"]",
    "auth\s*=\s*['\"][^'\"]+['\"]",
    "pass\s*=\s*['\"][^'\"]+['\"]",
    "pwd\s*=\s*['\"][^'\"]+['\"]"
)

$secretCount = 0
foreach ($pattern in $secretPatterns) {
    # Exclude test files, documentation, and this script itself
    $foundSecrets = Get-ChildItem -Recurse -Include "*.py", "*.js", "*.json" -Exclude "*test*" | 
                    Where-Object { $_.DirectoryName -notmatch "venv|tests|docs" } | 
                    Select-String -Pattern $pattern -ErrorAction SilentlyContinue
    
    if ($foundSecrets) {
        $secretCount += $foundSecrets.Count
        Write-Report "Potential secrets found matching pattern: $pattern"
        foreach ($secret in $foundSecrets) {
            Write-Report "$($secret.Path):$($secret.LineNumber): $($secret.Line)"
        }
        Write-Report ""
    }
}

if ($secretCount -eq 0) {
    Write-Report "No hardcoded secrets found in code. Good!"
} else {
    Write-Report "WARNING: Found $secretCount potential hardcoded secrets in code. These should be moved to environment variables or a secure vault."
}
Write-Report ""

# Check for insecure configurations
Write-Report "## Configuration Security Check"

# Check .env file permissions
if (Test-Path ".env") {
    $envFile = Get-Item ".env"
    $acl = Get-Acl $envFile.FullName
    $accessRules = $acl.Access
    
    $isSecure = $true
    foreach ($rule in $accessRules) {
        if ($rule.IdentityReference -match "Everyone|BUILTIN\\Users" -and 
            ($rule.FileSystemRights -match "Write|Modify|FullControl")) {
            $isSecure = $false
            Write-Report "WARNING: .env file has insecure permissions. Everyone or Users group has write access."
            break
        }
    }
    
    if ($isSecure) {
        Write-Report ".env file has reasonably secure permissions."
    }
    
    # Check for insecure settings in .env
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "DEBUG=True") {
        Write-Report "WARNING: DEBUG mode is enabled in .env file. This should be disabled in production."
    }
    
    if ($envContent -match "ALLOW_ORIGINS=.*\*") {
        Write-Report "WARNING: CORS is configured to allow all origins (*). This is insecure and should be restricted."
    }
} else {
    Write-Report "INFO: No .env file found."
}

# Check SSL configuration
if (Test-Path "config\ssl") {
    Write-Report "SSL configuration found."
    
    # Check key file permissions
    if (Test-Path "config\ssl\server.key") {
        $keyFile = Get-Item "config\ssl\server.key"
        $acl = Get-Acl $keyFile.FullName
        $accessRules = $acl.Access
        
        $isSecure = $true
        foreach ($rule in $accessRules) {
            if ($rule.IdentityReference -match "Everyone|BUILTIN\\Users" -and 
                ($rule.FileSystemRights -match "Read|Write|Modify|FullControl")) {
                $isSecure = $false
                Write-Report "WARNING: SSL key file has insecure permissions. Everyone or Users group has access."
                break
            }
        }
        
        if ($isSecure) {
            Write-Report "SSL key file has reasonably secure permissions."
        }
    } else {
        Write-Report "WARNING: SSL key file not found."
    }
    
    # Check certificate expiration
    if (Test-Path "config\ssl\server.crt") {
        try {
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 "config\ssl\server.crt"
            $expiryDate = $cert.NotAfter
            $daysRemaining = ($expiryDate - (Get-Date)).Days
            
            Write-Report "SSL certificate expires on: $expiryDate ($daysRemaining days remaining)"
            
            if ($daysRemaining -lt 30) {
                Write-Report "WARNING: SSL certificate will expire soon. Please renew it."
            }
        } catch {
            Write-Report "WARNING: Could not read SSL certificate expiration date."
        }
    } else {
        Write-Report "WARNING: SSL certificate not found."
    }
} else {
    Write-Report "WARNING: No SSL configuration found. HTTPS is recommended for production."
}
Write-Report ""

# Check for open ports
Write-Report "## Network Security Check"
Write-Report "Checking for open ports..."
try {
    $openPorts = netstat -ano | Where-Object { $_ -match "LISTENING" }
    Write-Report "Open ports:"
    foreach ($port in $openPorts) {
        Write-Report $port
    }
} catch {
    Write-Report "WARNING: Cannot check open ports. netstat command failed."
}
Write-Report ""

# Check for database security
Write-Report "## Database Security Check"
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "DB_PASSWORD=(.*)") {
        $dbPwd = $Matches[1].Trim()
        if ([string]::IsNullOrEmpty($dbPwd) -or $dbPwd -eq "changeme" -or $dbPwd.Length -lt 12) {
            Write-Report "WARNING: Database password is weak or default. Please change it to a strong password."
        } else {
            Write-Report "Database password appears to be strong."
        }
        
        # Check if database is exposed
        if ($envContent -match "DB_HOST=(.*)") {
            $dbHost = $Matches[1].Trim()
            if ($dbHost -ne "localhost" -and $dbHost -ne "127.0.0.1") {
                Write-Report "WARNING: Database host is not localhost. Ensure it's properly secured."
            } else {
                Write-Report "Database host is properly set to localhost."
            }
        }
    } else {
        Write-Report "INFO: Database password configuration not found in .env file."
    }
} else {
    Write-Report "INFO: Database configuration not found (.env file missing)."
}
Write-Report ""

# Check for code vulnerabilities
Write-Report "## Code Security Check"
try {
    $banditResult = bandit -r . -x venv,tests,docs 2>&1
    Write-Report "Running Bandit security scanner on Python code..."
    Write-Report $banditResult
} catch {
    Write-Report "WARNING: Bandit security scanner not installed. Cannot check Python code for vulnerabilities."
    Write-Report "To install: pip install bandit"
}

# Check for insecure imports
Write-Report "Checking for insecure imports in Python code..."
$insecureImports = @(
    "import pickle",
    "import marshal",
    "import shelve",
    "from flask import jsonify.*request.args",
    "eval\(",
    "exec\(",
    "os.system\(",
    "subprocess.call\(",
    "subprocess.Popen\(",
    "__import__\("
)

foreach ($pattern in $insecureImports) {
    $foundImports = Get-ChildItem -Recurse -Include "*.py" | 
                    Where-Object { $_.DirectoryName -notmatch "venv|tests|docs" } | 
                    Select-String -Pattern $pattern -ErrorAction SilentlyContinue
    
    if ($foundImports) {
        Write-Report "WARNING: Potentially insecure code pattern found: $pattern"
        foreach ($import in $foundImports) {
            Write-Report "$($import.Path):$($import.LineNumber): $($import.Line)"
        }
        Write-Report ""
    }
}
Write-Report ""

# Check for file permissions
Write-Report "## File Permission Check"
Write-Report "Checking for insecure file permissions..."

# Check for world-writable files
$insecureFiles = @()
Get-ChildItem -Recurse -File | Where-Object { 
    $_.FullName -notmatch "\\venv\\" -and 
    $_.FullName -notmatch "\\.git\\" 
} | ForEach-Object {
    $acl = Get-Acl $_.FullName
    foreach ($access in $acl.Access) {
        if (($access.IdentityReference -match "Everyone|BUILTIN\\Users") -and 
            ($access.FileSystemRights -match "Write|Modify|FullControl")) {
            $insecureFiles += $_.FullName
            break
        }
    }
}

if ($insecureFiles.Count -gt 0) {
    Write-Report "WARNING: Found files with insecure permissions (writable by Everyone or Users group):"
    foreach ($file in $insecureFiles) {
        Write-Report "  - $file"
    }
} else {
    Write-Report "No files with insecure permissions found. Good!"
}
Write-Report ""

# Check for security headers in web application
Write-Report "## Web Security Check"
if (Test-Path "auth\main.py") {
    Write-Report "Checking for security headers in web application..."
    
    # Check for CORS configuration
    $authMainContent = Get-Content "auth\main.py" -Raw
    if ($authMainContent -match "CORSMiddleware") {
        Write-Report "CORS middleware found in auth service."
        
        if ($authMainContent -match "allow_origins=\[""*""\]" -or $authMainContent -match "allow_origins=\[\*\]") {
            Write-Report "WARNING: CORS is configured to allow all origins (*). This is insecure and should be restricted."
        } else {
            Write-Report "CORS appears to be properly configured."
        }
    } else {
        Write-Report "WARNING: No CORS middleware found in auth service."
    }
    
    # Check for security headers
    $securityHeaders = @(
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "Referrer-Policy"
    )
    
    $missingHeaders = @()
    foreach ($header in $securityHeaders) {
        if ($authMainContent -notmatch $header) {
            $missingHeaders += $header
        }
    }
    
    if ($missingHeaders.Count -gt 0) {
        Write-Report "WARNING: Missing security headers in auth service:"
        foreach ($header in $missingHeaders) {
            Write-Report "  - $header"
        }
    } else {
        Write-Report "All recommended security headers appear to be implemented."
    }
} else {
    Write-Report "INFO: Auth service not found or structure is different."
}
Write-Report ""

# Check for logging and monitoring
Write-Report "## Logging and Monitoring Check"
if (Test-Path "logs") {
    Write-Report "Logging directory found."
    
    # Check log file permissions
    $logsDir = Get-Item "logs"
    $acl = Get-Acl $logsDir.FullName
    $accessRules = $acl.Access
    
    $isSecure = $true
    foreach ($rule in $accessRules) {
        if ($rule.IdentityReference -match "Everyone" -and 
            ($rule.FileSystemRights -match "Write|Modify|FullControl")) {
            $isSecure = $false
            Write-Report "WARNING: Logs directory has insecure permissions. Everyone group has write access."
            break
        }
    }
    
    if ($isSecure) {
        Write-Report "Logs directory has reasonably secure permissions."
    }
} else {
    Write-Report "WARNING: No logs directory found. Proper logging is important for security monitoring."
}

# Check for error handling in code
Write-Report "## Error Handling Check"
$tryBlocks = (Get-ChildItem -Recurse -Include "*.py" | 
              Where-Object { $_.DirectoryName -notmatch "venv|tests" } | 
              Select-String -Pattern "try:" -ErrorAction SilentlyContinue).Count

$exceptBlocks = (Get-ChildItem -Recurse -Include "*.py" | 
                 Where-Object { $_.DirectoryName -notmatch "venv|tests" } | 
                 Select-String -Pattern "except " -ErrorAction SilentlyContinue).Count

Write-Report "Found $tryBlocks try blocks and $exceptBlocks except blocks in the codebase."
if ($tryBlocks -lt 10) {
    Write-Report "WARNING: Limited error handling found in the codebase. Proper error handling is important for security."
}
Write-Report ""

# Check for input validation
Write-Report "## Input Validation Check"
$inputValidationCount = (Get-ChildItem -Recurse -Include "*.py" | 
                         Where-Object { $_.DirectoryName -notmatch "venv|tests" } | 
                         Select-String -Pattern "validate|schema|pydantic" -ErrorAction SilentlyContinue).Count

Write-Report "Found approximately $inputValidationCount instances of input validation in the codebase."
if ($inputValidationCount -lt 10) {
    Write-Report "WARNING: Limited input validation found in the codebase. Proper input validation is critical for security."
}
Write-Report ""

# Check Windows-specific security
Write-Report "## Windows-Specific Security Check"

# Check Windows Defender status
try {
    $defenderStatus = Get-MpComputerStatus
    Write-Report "Windows Defender Status:"
    Write-Report "  - Real-time protection enabled: $($defenderStatus.RealTimeProtectionEnabled)"
    Write-Report "  - Anti-virus enabled: $($defenderStatus.AntivirusEnabled)"
    Write-Report "  - Anti-spyware enabled: $($defenderStatus.AntispywareEnabled)"
    Write-Report "  - Last scan time: $($defenderStatus.LastFullScanTime)"
    
    if (-not $defenderStatus.RealTimeProtectionEnabled) {
        Write-Report "WARNING: Windows Defender real-time protection is disabled."
    }
    
    if ($defenderStatus.LastFullScanTime -lt (Get-Date).AddDays(-7)) {
        Write-Report "WARNING: Windows Defender full scan has not been run in the last 7 days."
    }
} catch {
    Write-Report "INFO: Could not retrieve Windows Defender status."
}

# Check Windows Firewall status
try {
    $firewallProfiles = Get-NetFirewallProfile
    Write-Report "Windows Firewall Status:"
    foreach ($profile in $firewallProfiles) {
        Write-Report "  - $($profile.Name) profile enabled: $($profile.Enabled)"
        
        if (-not $profile.Enabled) {
            Write-Report "WARNING: Windows Firewall $($profile.Name) profile is disabled."
        }
    }
} catch {
    Write-Report "INFO: Could not retrieve Windows Firewall status."
}

# Summary
Write-Report "==================================================="
Write-Report "Vulnerability Assessment Summary"
Write-Report "==================================================="
Write-Report "The vulnerability assessment has completed. Please review the report for security issues."
Write-Report "Report saved to: $reportFile"
Write-Report ""
Write-Report "Recommended actions:"
Write-Report "1. Address any WARNING items identified in the report"
Write-Report "2. Implement regular security scanning as part of your CI/CD pipeline"
Write-Report "3. Keep all dependencies up-to-date"
Write-Report "4. Implement proper logging and monitoring"
Write-Report "5. Conduct regular security reviews"
Write-Report "6. Ensure Windows security features are properly configured"
Write-Report ""

Log "Vulnerability assessment completed. Report saved to: $reportFile"
exit 0