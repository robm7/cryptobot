#!/bin/bash
# Auth Service Test Script
# Tests authentication service functionality

# Set environment variables
export PYTHONPATH=$(pwd)
export TEST_MODE=true

echo "===== Auth Service Test ====="
echo "Starting auth service tests..."

# Check if auth service is running
echo "Checking if auth service is running..."
if pgrep -f "auth/main.py" > /dev/null; then
    echo "Auth service is running."
else
    echo "Auth service is not running. Starting auth service..."
    # Start auth service if not running
    ./scripts/non-docker-setup/start_auth.sh
    sleep 5  # Wait for service to start
fi

# Run unit tests for auth service
echo "Running auth service unit tests..."
python -m pytest tests/test_auth_service.py -v

# Test API endpoints
echo "Testing auth API endpoints..."
python -m pytest tests/test_auth_decorators.py -v

# Test token management
echo "Testing token management..."
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"password123"}' > /tmp/auth_response.json
TOKEN=$(cat /tmp/auth_response.json | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "Failed to get access token."
    exit 1
else
    echo "Successfully obtained access token."
    # Test protected endpoint
    RESPONSE=$(curl -s -X GET http://localhost:8000/auth/protected -H "Authorization: Bearer $TOKEN")
    if [[ $RESPONSE == *"authenticated"* ]]; then
        echo "Successfully accessed protected endpoint."
    else
        echo "Failed to access protected endpoint."
        exit 1
    fi
fi

# Test token refresh
echo "Testing token refresh..."
REFRESH_TOKEN=$(cat /tmp/auth_response.json | grep -o '"refresh_token":"[^"]*' | cut -d'"' -f4)
if [ -z "$REFRESH_TOKEN" ]; then
    echo "Failed to get refresh token."
    exit 1
else
    echo "Successfully obtained refresh token."
    # Test refresh endpoint
    RESPONSE=$(curl -s -X POST http://localhost:8000/auth/refresh -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH_TOKEN\"}")
    if [[ $RESPONSE == *"access_token"* ]]; then
        echo "Successfully refreshed access token."
    else
        echo "Failed to refresh access token."
        exit 1
    fi
fi

# Test user registration
echo "Testing user registration..."
RANDOM_USER="testuser_$(date +%s)"
RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d "{\"username\":\"$RANDOM_USER\",\"password\":\"Password123!\",\"email\":\"$RANDOM_USER@example.com\"}")
if [[ $RESPONSE == *"success"* ]]; then
    echo "Successfully registered new user."
else
    echo "Failed to register new user."
    exit 1
fi

# Test rate limiting
echo "Testing rate limiting..."
for i in {1..15}; do
    RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"username":"test_user","password":"wrong_password"}')
    if [[ $RESPONSE == *"Too many requests"* ]]; then
        echo "Rate limiting working correctly."
        break
    fi
    if [ $i -eq 15 ]; then
        echo "Rate limiting not working correctly."
    fi
done

# Clean up
rm -f /tmp/auth_response.json

echo "Auth service tests completed."
echo "===== Auth Service Test Complete ====="