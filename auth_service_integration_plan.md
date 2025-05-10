# Auth Service Integration Plan

## Integration Approach
1. **Proxy Authentication Requests**:
   - Flask app will forward auth requests to FastAPI service
   - Maintain JWT consistency between services
   - Use HTTP client for service-to-service communication

## Implementation Steps

1. **Service Configuration**:
   - Add FastAPI service URL to Flask config
   - Create HTTP client wrapper for auth service calls

2. **Auth Endpoint Modifications**:
   - Update `/api/login` to proxy to FastAPI
   - Add `/api/refresh` endpoint for token refresh
   - Implement `/api/logout` endpoint

3. **Middleware Integration**:
   - Create custom JWT middleware that validates tokens against both services
   - Add token refresh logic

4. **Error Handling**:
   - Implement consistent error responses
   - Add service health checks

## Code Changes Required

1. **app.py Modifications**:
```python
# Add to config
app.config['AUTH_SERVICE_URL'] = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8000')

# Create auth service client
auth_service = AuthServiceClient(app.config['AUTH_SERVICE_URL'])

# Update login route
@app.route('/api/login', methods=['POST'])
def login():
    return auth_service.login(request.json)
```

2. **New AuthServiceClient Class**:
```python
class AuthServiceClient:
    def __init__(self, base_url):
        self.base_url = base_url
        
    def login(self, credentials):
        response = requests.post(f"{self.base_url}/auth/login", json=credentials)
        return response.json(), response.status_code
        
    def refresh(self, refresh_token):
        response = requests.post(f"{self.base_url}/auth/refresh", json={'refresh_token': refresh_token})
        return response.json(), response.status_code
```

## Testing Plan
1. Unit tests for AuthServiceClient
2. Integration tests for proxied endpoints
3. End-to-end auth flow tests