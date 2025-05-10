# Authentication Testing Guide for Strategy Service

This document outlines how to test the authentication and authorization mechanisms implemented in the Strategy Service.

## Overview of Changes

The authentication system now supports:

1. **Token-based Authentication**: JWT tokens for secure API access
2. **Role-based Authorization**: Different permissions for admin, trader, and viewer roles
3. **Resilient Authentication**: Fallback authentication when auth service is unavailable
4. **Comprehensive Error Handling**: Clear error messages and proper HTTP status codes

## Testing the Authentication System

### Automated Tests

We have two test scripts for validating the authentication system:

1. **Basic Authentication Test**
   ```
   python test_auth.py
   ```
   This tests the core authentication components, including token validation and fallback mechanisms.

2. **Protected Endpoints Test**
   ```
   python test_protected_endpoints.py
   ```
   This tests the full API with different roles to ensure authorization is enforced correctly.

### Manual Testing Steps

You can also manually test the authentication system using tools like curl or Postman:

#### 1. Test Authentication Requirement

Try accessing a protected endpoint without authentication:
```
curl http://localhost:8000/api/strategies/
```
Expected: 401 Unauthorized

#### 2. Test with Authentication

Get a token from the auth service (or create a test token), then:
```
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/strategies/
```
Expected: 200 OK with strategy list

#### 3. Test Role-Based Authorization

Test with different user roles:

##### As Admin:
```
# Admin can create, update, and delete strategies
curl -X POST -H "Authorization: Bearer ADMIN_TOKEN" -H "Content-Type: application/json" -d '{"name":"Test Strategy", "description":"Test", "parameters":{}}' http://localhost:8000/api/strategies/
```
Expected: 201 Created

##### As Trader:
```
# Trader can create and update, but not delete
curl -X POST -H "Authorization: Bearer TRADER_TOKEN" -H "Content-Type: application/json" -d '{"name":"Trader Strategy", "description":"Test", "parameters":{}}' http://localhost:8000/api/strategies/
```
Expected: 201 Created

```
# Trader cannot delete
curl -X DELETE -H "Authorization: Bearer TRADER_TOKEN" http://localhost:8000/api/strategies/1
```
Expected: 403 Forbidden

##### As Viewer:
```
# Viewer can only view, not modify
curl -X POST -H "Authorization: Bearer VIEWER_TOKEN" -H "Content-Type: application/json" -d '{"name":"Viewer Strategy", "description":"Test", "parameters":{}}' http://localhost:8000/api/strategies/
```
Expected: 403 Forbidden

#### 4. Test Fallback Authentication

To test the fallback authentication:

1. Stop the auth service
2. Create a token using the local secret key:
   ```python
   import jwt
   from datetime import datetime, timedelta
   
   payload = {
       "sub": "test_user",
       "roles": ["admin"],
       "exp": datetime.utcnow() + timedelta(minutes=30)
   }
   token = jwt.encode(payload, "test_secret_key_for_local_testing", algorithm="HS256")
   print(token)
   ```
3. Use this token in your requests:
   ```
   curl -H "Authorization: Bearer YOUR_LOCAL_TOKEN" http://localhost:8000/api/strategies/
   ```
   Expected: 200 OK with strategy list

## Troubleshooting

If authentication is not working as expected:

1. Check the logs for error messages
2. Verify the token format and content
3. Ensure the SECRET_KEY is consistent between token generation and validation
4. Confirm that the auth_middleware is properly configured in main.py
5. Check if the role required by the endpoint matches the role in the token

## Security Considerations

The fallback authentication mechanism is less secure than the auth service because:

1. It validates tokens locally without checking against a central authority
2. It doesn't check for token revocation
3. It has limited validation capabilities

This fallback should only be used during auth service outages and should not be relied upon for long-term security.