#!/bin/bash
# Cryptobot Vulnerability Assessment Script for Linux/macOS
# This script performs security vulnerability assessments on the Cryptobot application

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    log "Detected Linux operating system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    log "Detected macOS operating system"
else
    log "Error: Unsupported operating system. This script is for Linux and macOS only."
    exit 1
fi

# Create output directory
mkdir -p reports/security
REPORT_FILE="reports/security/vulnerability_assessment_$(date '+%Y%m%d_%H%M%S').txt"
touch $REPORT_FILE

# Function to write to report file
write_report() {
    echo "$1" | tee -a $REPORT_FILE
}

write_report "==================================================="
write_report "Cryptobot Vulnerability Assessment Report"
write_report "Date: $(date '+%Y-%m-%d %H:%M:%S')"
write_report "OS: $OS"
write_report "==================================================="
write_report ""

log "Starting vulnerability assessment for Cryptobot..."

# Check Python version
write_report "## Python Environment Check"
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    write_report "Python version: $PYTHON_VERSION"
    
    # Check if Python version is secure (>=3.7)
    if [[ $PYTHON_VERSION =~ Python\ 3\.([0-9]+) ]]; then
        MINOR_VERSION=${BASH_REMATCH[1]}
        if [ $MINOR_VERSION -lt 7 ]; then
            write_report "WARNING: Python version is outdated and may have security vulnerabilities. Recommend upgrading to Python 3.7 or newer."
        else
            write_report "Python version is up-to-date."
        fi
    fi
else
    write_report "ERROR: Python 3 not found. Please install Python 3.7 or newer."
fi
write_report ""

# Check for vulnerable dependencies
write_report "## Dependency Vulnerability Check"
if [ -f "requirements.txt" ]; then
    write_report "Checking Python dependencies for known vulnerabilities..."
    
    if command_exists pip-audit; then
        # Use pip-audit if available
        PIP_AUDIT_RESULT=$(pip-audit -r requirements.txt 2>&1)
        write_report "$PIP_AUDIT_RESULT"
    elif command_exists safety; then
        # Use safety if available
        SAFETY_RESULT=$(safety check -r requirements.txt --json 2>&1)
        write_report "$SAFETY_RESULT"
    else
        write_report "WARNING: Neither pip-audit nor safety is installed. Cannot check dependencies for vulnerabilities."
        write_report "To install: pip install pip-audit or pip install safety"
        
        # List dependencies anyway
        write_report "Dependencies from requirements.txt:"
        cat requirements.txt | grep -v "^#" | grep -v "^$" | tee -a $REPORT_FILE
    fi
else
    write_report "WARNING: requirements.txt not found. Cannot check dependencies for vulnerabilities."
fi
write_report ""

# Check for secrets in code
write_report "## Secret Detection"
write_report "Checking for hardcoded secrets in code..."

SECRET_PATTERNS=(
    "password\s*=\s*['\"][^'\"]+['\"]"
    "api_key\s*=\s*['\"][^'\"]+['\"]"
    "secret\s*=\s*['\"][^'\"]+['\"]"
    "token\s*=\s*['\"][^'\"]+['\"]"
    "auth\s*=\s*['\"][^'\"]+['\"]"
    "pass\s*=\s*['\"][^'\"]+['\"]"
    "pwd\s*=\s*['\"][^'\"]+['\"]"
)

SECRET_COUNT=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    # Exclude test files, documentation, and this script itself
    FOUND_SECRETS=$(grep -r -E "$pattern" --include="*.py" --include="*.js" --include="*.json" --exclude-dir="venv" --exclude-dir="tests" --exclude-dir="docs" --exclude="*test*" . 2>/dev/null || true)
    if [ ! -z "$FOUND_SECRETS" ]; then
        SECRET_COUNT=$((SECRET_COUNT + $(echo "$FOUND_SECRETS" | wc -l)))
        write_report "Potential secrets found matching pattern: $pattern"
        write_report "$FOUND_SECRETS"
        write_report ""
    fi
done

if [ $SECRET_COUNT -eq 0 ]; then
    write_report "No hardcoded secrets found in code. Good!"
else
    write_report "WARNING: Found $SECRET_COUNT potential hardcoded secrets in code. These should be moved to environment variables or a secure vault."
fi
write_report ""

# Check for insecure configurations
write_report "## Configuration Security Check"

# Check .env file permissions
if [ -f ".env" ]; then
    ENV_PERMS=$(stat -c "%a" .env 2>/dev/null || stat -f "%Lp" .env 2>/dev/null)
    if [ "$ENV_PERMS" != "600" ]; then
        write_report "WARNING: .env file has insecure permissions: $ENV_PERMS. Should be 600 (user read/write only)."
    else
        write_report ".env file has secure permissions."
    fi
    
    # Check for insecure settings in .env
    if grep -q "DEBUG=True" .env; then
        write_report "WARNING: DEBUG mode is enabled in .env file. This should be disabled in production."
    fi
    
    if grep -q "ALLOW_ORIGINS=.*\*" .env; then
        write_report "WARNING: CORS is configured to allow all origins (*). This is insecure and should be restricted."
    fi
else
    write_report "INFO: No .env file found."
fi

# Check SSL configuration
if [ -d "config/ssl" ]; then
    write_report "SSL configuration found."
    
    # Check key file permissions
    if [ -f "config/ssl/server.key" ]; then
        KEY_PERMS=$(stat -c "%a" config/ssl/server.key 2>/dev/null || stat -f "%Lp" config/ssl/server.key 2>/dev/null)
        if [ "$KEY_PERMS" != "600" ]; then
            write_report "WARNING: SSL key file has insecure permissions: $KEY_PERMS. Should be 600 (user read/write only)."
        else
            write_report "SSL key file has secure permissions."
        fi
    else
        write_report "WARNING: SSL key file not found."
    fi
    
    # Check certificate expiration
    if [ -f "config/ssl/server.crt" ] && command_exists openssl; then
        CERT_EXPIRY=$(openssl x509 -enddate -noout -in config/ssl/server.crt | cut -d= -f2)
        CERT_EXPIRY_SECONDS=$(date -d "$CERT_EXPIRY" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$CERT_EXPIRY" +%s 2>/dev/null)
        CURRENT_SECONDS=$(date +%s)
        SECONDS_REMAINING=$((CERT_EXPIRY_SECONDS - CURRENT_SECONDS))
        DAYS_REMAINING=$((SECONDS_REMAINING / 86400))
        
        write_report "SSL certificate expires on: $CERT_EXPIRY ($DAYS_REMAINING days remaining)"
        
        if [ $DAYS_REMAINING -lt 30 ]; then
            write_report "WARNING: SSL certificate will expire soon. Please renew it."
        fi
    else
        write_report "WARNING: SSL certificate not found or openssl not available."
    fi
else
    write_report "WARNING: No SSL configuration found. HTTPS is recommended for production."
fi
write_report ""

# Check for open ports
write_report "## Network Security Check"
if command_exists netstat; then
    write_report "Checking for open ports..."
    OPEN_PORTS=$(netstat -tuln 2>/dev/null | grep LISTEN)
    write_report "Open ports:"
    write_report "$OPEN_PORTS"
elif command_exists ss; then
    write_report "Checking for open ports..."
    OPEN_PORTS=$(ss -tuln 2>/dev/null | grep LISTEN)
    write_report "Open ports:"
    write_report "$OPEN_PORTS"
else
    write_report "WARNING: Cannot check open ports. netstat or ss command not found."
fi
write_report ""

# Check for database security
write_report "## Database Security Check"
if [ -f ".env" ] && grep -q "DB_PASSWORD" .env; then
    DB_PWD=$(grep "DB_PASSWORD" .env | cut -d= -f2)
    if [ -z "$DB_PWD" ] || [ "$DB_PWD" == "changeme" ] || [ ${#DB_PWD} -lt 12 ]; then
        write_report "WARNING: Database password is weak or default. Please change it to a strong password."
    else
        write_report "Database password appears to be strong."
    fi
    
    # Check if database is exposed
    DB_HOST=$(grep "DB_HOST" .env | cut -d= -f2)
    if [ "$DB_HOST" != "localhost" ] && [ "$DB_HOST" != "127.0.0.1" ]; then
        write_report "WARNING: Database host is not localhost. Ensure it's properly secured."
    else
        write_report "Database host is properly set to localhost."
    fi
else
    write_report "INFO: Database configuration not found in .env file."
fi
write_report ""

# Check for code vulnerabilities
write_report "## Code Security Check"
if command_exists bandit; then
    write_report "Running Bandit security scanner on Python code..."
    BANDIT_RESULT=$(bandit -r . -x venv,tests,docs 2>&1 || true)
    write_report "$BANDIT_RESULT"
else
    write_report "WARNING: Bandit security scanner not installed. Cannot check Python code for vulnerabilities."
    write_report "To install: pip install bandit"
fi

# Check for insecure imports
write_report "Checking for insecure imports in Python code..."
INSECURE_IMPORTS=(
    "import pickle"
    "import marshal"
    "import shelve"
    "from flask import jsonify.*request.args"
    "eval\("
    "exec\("
    "os.system\("
    "subprocess.call\("
    "subprocess.Popen\("
    "__import__\("
)

for pattern in "${INSECURE_IMPORTS[@]}"; do
    FOUND_IMPORTS=$(grep -r -E "$pattern" --include="*.py" --exclude-dir="venv" --exclude-dir="tests" --exclude-dir="docs" . 2>/dev/null || true)
    if [ ! -z "$FOUND_IMPORTS" ]; then
        write_report "WARNING: Potentially insecure code pattern found: $pattern"
        write_report "$FOUND_IMPORTS"
        write_report ""
    fi
done
write_report ""

# Check for file permissions
write_report "## File Permission Check"
write_report "Checking for insecure file permissions..."

# Check script permissions
WORLD_WRITABLE_FILES=$(find . -type f -perm -002 -not -path "*/\.*" -not -path "*/venv/*" 2>/dev/null || true)
if [ ! -z "$WORLD_WRITABLE_FILES" ]; then
    write_report "WARNING: Found world-writable files. These should be restricted:"
    write_report "$WORLD_WRITABLE_FILES"
else
    write_report "No world-writable files found. Good!"
fi
write_report ""

# Check for security headers in web application
write_report "## Web Security Check"
if [ -d "auth" ] && [ -f "auth/main.py" ]; then
    write_report "Checking for security headers in web application..."
    
    # Check for CORS configuration
    if grep -q "CORSMiddleware" auth/main.py; then
        write_report "CORS middleware found in auth service."
        
        if grep -q "allow_origins=\[\"*\"\]" auth/main.py || grep -q "allow_origins=\[\*\]" auth/main.py; then
            write_report "WARNING: CORS is configured to allow all origins (*). This is insecure and should be restricted."
        else
            write_report "CORS appears to be properly configured."
        fi
    else
        write_report "WARNING: No CORS middleware found in auth service."
    fi
    
    # Check for security headers
    SECURITY_HEADERS=(
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
        "Strict-Transport-Security"
        "Content-Security-Policy"
        "Referrer-Policy"
    )
    
    MISSING_HEADERS=()
    for header in "${SECURITY_HEADERS[@]}"; do
        if ! grep -q "$header" auth/main.py; then
            MISSING_HEADERS+=("$header")
        fi
    done
    
    if [ ${#MISSING_HEADERS[@]} -gt 0 ]; then
        write_report "WARNING: Missing security headers in auth service:"
        for header in "${MISSING_HEADERS[@]}"; do
            write_report "  - $header"
        done
    else
        write_report "All recommended security headers appear to be implemented."
    fi
else
    write_report "INFO: Auth service not found or structure is different."
fi
write_report ""

# Check for logging and monitoring
write_report "## Logging and Monitoring Check"
if [ -d "logs" ]; then
    write_report "Logging directory found."
    
    # Check log file permissions
    LOG_PERMS=$(stat -c "%a" logs 2>/dev/null || stat -f "%Lp" logs 2>/dev/null)
    if [ "$LOG_PERMS" = "777" ] || [ "$LOG_PERMS" = "766" ] || [ "$LOG_PERMS" = "755" ]; then
        write_report "WARNING: Logs directory has insecure permissions: $LOG_PERMS. Should be more restrictive."
    else
        write_report "Logs directory has reasonable permissions."
    fi
else
    write_report "WARNING: No logs directory found. Proper logging is important for security monitoring."
fi

# Check for error handling in code
write_report "## Error Handling Check"
ERROR_HANDLING_COUNT=$(grep -r "try:" --include="*.py" --exclude-dir="venv" --exclude-dir="tests" . | wc -l)
EXCEPT_COUNT=$(grep -r "except " --include="*.py" --exclude-dir="venv" --exclude-dir="tests" . | wc -l)

write_report "Found $ERROR_HANDLING_COUNT try blocks and $EXCEPT_COUNT except blocks in the codebase."
if [ $ERROR_HANDLING_COUNT -lt 10 ]; then
    write_report "WARNING: Limited error handling found in the codebase. Proper error handling is important for security."
fi
write_report ""

# Check for input validation
write_report "## Input Validation Check"
INPUT_VALIDATION_COUNT=$(grep -r -E "validate|schema|pydantic" --include="*.py" --exclude-dir="venv" --exclude-dir="tests" . | wc -l)

write_report "Found approximately $INPUT_VALIDATION_COUNT instances of input validation in the codebase."
if [ $INPUT_VALIDATION_COUNT -lt 10 ]; then
    write_report "WARNING: Limited input validation found in the codebase. Proper input validation is critical for security."
fi
write_report ""

# Summary
write_report "==================================================="
write_report "Vulnerability Assessment Summary"
write_report "==================================================="
write_report "The vulnerability assessment has completed. Please review the report for security issues."
write_report "Report saved to: $REPORT_FILE"
write_report ""
write_report "Recommended actions:"
write_report "1. Address any WARNING items identified in the report"
write_report "2. Implement regular security scanning as part of your CI/CD pipeline"
write_report "3. Keep all dependencies up-to-date"
write_report "4. Implement proper logging and monitoring"
write_report "5. Conduct regular security reviews"
write_report ""

log "Vulnerability assessment completed. Report saved to: $REPORT_FILE"
exit 0