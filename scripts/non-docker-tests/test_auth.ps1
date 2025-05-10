# Auth Service Test Script (PowerShell)
# Tests authentication service functionality

# Set environment variables
$env:PYTHONPATH = (Get-Location).Path
$env:TEST_MODE = "true"

Write-Host "===== Auth Service Test =====" -ForegroundColor Cyan
Write-Host "Starting auth service tests..." -ForegroundColor Cyan

# Check if auth service is running
Write-Host "Checking if auth service is running..." -ForegroundColor Cyan
$authProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*auth/main.py*" }
if ($authProcess) {
    Write-Host "Auth service is running." -ForegroundColor Green
} else {
    Write-Host "Auth service is not running. Starting auth service..." -ForegroundColor Yellow
    # Start auth service if not running
    & "$PSScriptRoot\..\non-docker-setup\start_auth.ps1"
    Start-Sleep -Seconds 5  # Wait for service to start
}

# Run unit tests for auth service
Write-Host "Running auth service unit tests..." -ForegroundColor Cyan
python -m pytest tests/test_auth_service.py -v

# Test API endpoints
Write-Host "Testing auth API endpoints..." -ForegroundColor Cyan
python -m pytest tests/test_auth_decorators.py -v

# Test token management
Write-Host "Testing token management..." -ForegroundColor Cyan
$loginBody = @{
    username = "test_user"
    password = "password123"
} | ConvertTo-Json

$authResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -ErrorAction SilentlyContinue
if (-not $authResponse.access_token) {
    Write-Host "Failed to get access token." -ForegroundColor Red
    exit 1
} else {
    Write-Host "Successfully obtained access token." -ForegroundColor Green
    # Test protected endpoint
    try {
        $protectedResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/protected" -Method Get -Headers @{Authorization = "Bearer $($authResponse.access_token)"} -ErrorAction Stop
        Write-Host "Successfully accessed protected endpoint." -ForegroundColor Green
    } catch {
        Write-Host "Failed to access protected endpoint." -ForegroundColor Red
        exit 1
    }
}

# Test token refresh
Write-Host "Testing token refresh..." -ForegroundColor Cyan
if (-not $authResponse.refresh_token) {
    Write-Host "Failed to get refresh token." -ForegroundColor Red
    exit 1
} else {
    Write-Host "Successfully obtained refresh token." -ForegroundColor Green
    # Test refresh endpoint
    $refreshBody = @{
        refresh_token = $authResponse.refresh_token
    } | ConvertTo-Json
    
    try {
        $refreshResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/refresh" -Method Post -ContentType "application/json" -Body $refreshBody -ErrorAction Stop
        if ($refreshResponse.access_token) {
            Write-Host "Successfully refreshed access token." -ForegroundColor Green
        } else {
            Write-Host "Failed to refresh access token." -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "Failed to refresh access token: $_" -ForegroundColor Red
        exit 1
    }
}

# Test user registration
Write-Host "Testing user registration..." -ForegroundColor Cyan
$randomUser = "testuser_" + (Get-Date).Ticks
$registerBody = @{
    username = $randomUser
    password = "Password123!"
    email = "$randomUser@example.com"
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "http://localhost:8000/auth/register" -Method Post -ContentType "application/json" -Body $registerBody -ErrorAction Stop
    Write-Host "Successfully registered new user." -ForegroundColor Green
} catch {
    Write-Host "Failed to register new user: $_" -ForegroundColor Red
    exit 1
}

# Test rate limiting
Write-Host "Testing rate limiting..." -ForegroundColor Cyan
$rateLimitDetected = $false
$wrongLoginBody = @{
    username = "test_user"
    password = "wrong_password"
} | ConvertTo-Json

for ($i = 1; $i -le 15; $i++) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body $wrongLoginBody -ErrorAction SilentlyContinue
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 429) {
            Write-Host "Rate limiting working correctly." -ForegroundColor Green
            $rateLimitDetected = $true
            break
        }
    }
}

if (-not $rateLimitDetected) {
    Write-Host "Rate limiting not working correctly." -ForegroundColor Yellow
}

Write-Host "Auth service tests completed." -ForegroundColor Cyan
Write-Host "===== Auth Service Test Complete =====" -ForegroundColor Cyan