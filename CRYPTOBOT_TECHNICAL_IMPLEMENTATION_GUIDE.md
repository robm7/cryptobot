# Cryptobot Technical Implementation Guide

This document provides detailed technical guidance for implementing key components of the Cryptobot project. It's intended to be used alongside the `CRYPTOBOT_COMPLETION_PLAN.md` to provide more specific implementation details.

## Table of Contents

1. [Core Functionality Implementation](#core-functionality-implementation)
2. [Testing Strategy](#testing-strategy)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Microservice Migration](#microservice-migration)
5. [Security Implementation](#security-implementation)
6. [Distribution & Packaging](#distribution--packaging)
7. [Technical Standards](#technical-standards)

## Core Functionality Implementation

### ReliableOrderExecutor Completion

The `ReliableOrderExecutor` class in `services/mcp/order_execution/reliable_executor.py` needs to be completed with the following enhancements:

1. **Monitoring Integration**
   ```python
   # Example implementation for Prometheus metrics integration
   from prometheus_client import Counter, Histogram, Gauge
   
   ORDER_EXECUTION_COUNT = Counter(
       'order_execution_total', 
       'Order execution count',
       ['exchange', 'symbol', 'side', 'status']
   )
   
   ORDER_EXECUTION_LATENCY = Histogram(
       'order_execution_seconds', 
       'Order execution latency',
       ['exchange', 'symbol']
   )
   
   CIRCUIT_BREAKER_STATE = Gauge(
       'circuit_breaker_state',
       'Circuit breaker state (0=closed, 1=half-open, 2=open)',
       ['exchange']
   )
   ```

2. **Reconciliation Job**
   ```python
   async def reconcile_orders(self, time_period: str = "daily") -> Dict[str, Any]:
       """
       Daily batch reconciliation process to verify all orders
       are properly accounted for
       
       1. Get all orders from local database for the period
       2. Get all orders from exchange for the period
       3. Compare and identify discrepancies
       4. Generate alerts for mismatches > 0.1%
       """
       # Implementation details...
   ```

3. **Circuit Breaker Pattern**
   - Ensure the circuit breaker state machine transitions correctly
   - Implement proper error tracking with time window
   - Add metrics for circuit breaker state changes

### Risk Management Integration

1. **Position Sizing**
   - Implement Kelly Criterion for optimal position sizing
   - Add volatility-based position sizing
   - Implement maximum drawdown limits

2. **Strategy Backtesting**
   - Complete walk-forward testing capability
   - Add parameter optimization
   - Implement Monte Carlo simulation for risk assessment

## Testing Strategy

### Test Coverage Setup

1. **Coverage Configuration**
   ```python
   # pytest.ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   addopts = --cov=. --cov-report=xml --cov-report=term
   ```

2. **CI Integration**
   ```yaml
   # .github/workflows/test.yml
   - name: Run tests with coverage
     run: |
       pytest --cov=. --cov-report=xml
   
   - name: Upload coverage to Codecov
     uses: codecov/codecov-action@v1
     with:
       file: ./coverage.xml
   ```

### Unit Testing Approach

1. **Auth Service Tests**
   - Test JWT token generation and validation
   - Test user authentication flows
   - Test permission checks

2. **Trading Strategy Tests**
   - Test signal generation with mock market data
   - Test strategy parameter validation
   - Test risk management rule application

3. **API Route Tests**
   - Test request validation
   - Test response formatting
   - Test error handling

### Integration Testing

1. **Database Interaction Tests**
   - Use test database with migrations
   - Test transaction rollback
   - Test concurrent access patterns

2. **Exchange Communication Tests**
   - Mock exchange API responses
   - Test rate limiting handling
   - Test error recovery

## Infrastructure Setup

### Kubernetes Configuration

1. **Service Manifests**
   ```yaml
   # Example service manifest
   apiVersion: v1
   kind: Service
   metadata:
     name: auth-service
     labels:
       app: auth-service
   spec:
     selector:
       app: auth-service
     ports:
     - port: 8080
       targetPort: 8080
     type: ClusterIP
   ```

2. **Deployment Manifests**
   ```yaml
   # Example deployment manifest
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: auth-service
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: auth-service
     template:
       metadata:
         labels:
           app: auth-service
       spec:
         containers:
         - name: auth-service
           image: cryptobot/auth-service:latest
           ports:
           - containerPort: 8080
           resources:
             limits:
               cpu: "500m"
               memory: "512Mi"
             requests:
               cpu: "100m"
               memory: "256Mi"
   ```

3. **Horizontal Pod Autoscaling**
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: auth-service-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: auth-service
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

### TimescaleDB Setup

1. **Schema Design**
   ```sql
   -- OHLCV data table with TimescaleDB hypertable
   CREATE TABLE ohlcv (
     time TIMESTAMPTZ NOT NULL,
     symbol TEXT NOT NULL,
     exchange TEXT NOT NULL,
     open DECIMAL NOT NULL,
     high DECIMAL NOT NULL,
     low DECIMAL NOT NULL,
     close DECIMAL NOT NULL,
     volume DECIMAL NOT NULL
   );
   
   -- Create hypertable
   SELECT create_hypertable('ohlcv', 'time');
   
   -- Create indexes
   CREATE INDEX idx_ohlcv_symbol ON ohlcv (symbol, time DESC);
   ```

2. **Continuous Aggregates**
   ```sql
   -- Create continuous aggregate for 1-hour candles
   CREATE MATERIALIZED VIEW ohlcv_1h WITH (timescaledb.continuous) AS
   SELECT
     time_bucket('1 hour', time) AS bucket,
     symbol,
     exchange,
     first(open, time) AS open,
     max(high) AS high,
     min(low) AS low,
     last(close, time) AS close,
     sum(volume) AS volume
   FROM ohlcv
   GROUP BY bucket, symbol, exchange;
   ```

3. **Retention Policy**
   ```sql
   -- Set retention policy to keep raw data for 30 days
   SELECT add_retention_policy('ohlcv', INTERVAL '30 days');
   
   -- Keep aggregated data longer
   SELECT add_retention_policy('ohlcv_1h', INTERVAL '1 year');
   ```

### Redis Configuration

1. **Caching Setup**
   ```python
   # Example Redis cache configuration
   REDIS_CONFIG = {
       'host': 'redis-master',
       'port': 6379,
       'db': 0,
       'socket_timeout': 5,
       'retry_on_timeout': True,
       'decode_responses': True
   }
   
   # Cache implementation
   class RedisCache:
       def __init__(self, config=None):
           self.config = config or REDIS_CONFIG
           self.client = redis.Redis(**self.config)
           
       def get(self, key, default=None):
           value = self.client.get(key)
           return value if value is not None else default
           
       def set(self, key, value, ttl=None):
           return self.client.set(key, value, ex=ttl)
   ```

2. **Rate Limiting**
   ```python
   # Rate limiting with Redis
   class RedisRateLimiter:
       def __init__(self, redis_client, limit=100, window=60):
           self.redis = redis_client
           self.limit = limit
           self.window = window
           
       async def is_rate_limited(self, key):
           current = await self.redis.get(key)
           if current is None:
               await self.redis.set(key, 1, ex=self.window)
               return False
           if int(current) >= self.limit:
               return True
           await self.redis.incr(key)
           return False
   ```

## Microservice Migration

### Auth Service Extraction

1. **Service Interface**
   ```python
   # auth_service/interfaces.py
   from abc import ABC, abstractmethod
   from typing import Dict, Optional
   
   class AuthServiceInterface(ABC):
       @abstractmethod
       async def authenticate(self, username: str, password: str) -> Optional[Dict]:
           """Authenticate user and return token"""
           pass
           
       @abstractmethod
       async def validate_token(self, token: str) -> Optional[Dict]:
           """Validate token and return user info"""
           pass
           
       @abstractmethod
       async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
           """Refresh access token"""
           pass
   ```

2. **JWT Implementation**
   ```python
   # auth_service/jwt_service.py
   import jwt
   from datetime import datetime, timedelta
   
   class JWTService:
       def __init__(self, secret_key, algorithm='HS256'):
           self.secret_key = secret_key
           self.algorithm = algorithm
           
       def generate_token(self, user_id, expires_delta=None):
           expires = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
           payload = {
               'sub': str(user_id),
               'exp': expires,
               'iat': datetime.utcnow()
           }
           return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
           
       def validate_token(self, token):
           try:
               payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
               return payload
           except jwt.PyJWTError:
               return None
   ```

3. **API Gateway Integration**
   ```python
   # Example Kong configuration
   {
       "name": "jwt-auth",
       "config": {
           "secret_is_base64": false,
           "key_claim_name": "kid",
           "claims_to_verify": ["exp"]
       }
   }
   ```

### Data Service Decoupling

1. **WebSocket Implementation**
   ```python
   # data_service/websocket.py
   import asyncio
   import websockets
   import json
   
   class MarketDataWebSocket:
       def __init__(self, host='0.0.0.0', port=8765):
           self.host = host
           self.port = port
           self.clients = set()
           
       async def register(self, websocket):
           self.clients.add(websocket)
           
       async def unregister(self, websocket):
           self.clients.remove(websocket)
           
       async def broadcast(self, message):
           if not self.clients:
               return
           await asyncio.gather(
               *[client.send(json.dumps(message)) for client in self.clients]
           )
           
       async def handler(self, websocket, path):
           await self.register(websocket)
           try:
               async for message in websocket:
                   # Process incoming messages if needed
                   pass
           finally:
               await self.unregister(websocket)
               
       async def start_server(self):
           return await websockets.serve(self.handler, self.host, self.port)
   ```

2. **Historical Data API**
   ```python
   # data_service/api.py
   from fastapi import FastAPI, Query, Path, Depends
   from typing import List, Optional
   
   app = FastAPI()
   
   @app.get("/api/v1/ohlcv/{symbol}")
   async def get_ohlcv(
       symbol: str = Path(..., description="Trading pair symbol"),
       exchange: str = Query("binance", description="Exchange name"),
       interval: str = Query("1h", description="Candle interval"),
       start: Optional[int] = Query(None, description="Start timestamp"),
       end: Optional[int] = Query(None, description="End timestamp"),
       limit: int = Query(100, description="Number of candles")
   ):
       # Implementation to fetch data from TimescaleDB
       pass
   ```

## Security Implementation

### API Key Rotation

1. **Redis Storage**
   ```python
   # key_manager/storage.py
   import redis
   import json
   
   class RedisKeyStorage:
       def __init__(self, redis_client):
           self.redis = redis_client
           self.key_prefix = "api_key:"
           
       async def store_key(self, user_id, exchange, key_data, ttl=None):
           key = f"{self.key_prefix}{user_id}:{exchange}"
           await self.redis.set(key, json.dumps(key_data), ex=ttl)
           
       async def get_key(self, user_id, exchange):
           key = f"{self.key_prefix}{user_id}:{exchange}"
           data = await self.redis.get(key)
           return json.loads(data) if data else None
           
       async def delete_key(self, user_id, exchange):
           key = f"{self.key_prefix}{user_id}:{exchange}"
           await self.redis.delete(key)
   ```

2. **Scheduled Rotation**
   ```python
   # key_manager/rotation.py
   import asyncio
   from datetime import datetime, timedelta
   
   class KeyRotationScheduler:
       def __init__(self, key_storage, exchange_service, notification_service):
           self.key_storage = key_storage
           self.exchange_service = exchange_service
           self.notification_service = notification_service
           
       async def rotate_key(self, user_id, exchange):
           # Get current key
           current_key = await self.key_storage.get_key(user_id, exchange)
           
           # Generate new key on exchange
           new_key = await self.exchange_service.create_api_key(
               exchange, user_id, current_key.get('permissions', [])
           )
           
           # Store new key
           await self.key_storage.store_key(
               user_id, exchange, new_key, ttl=timedelta(days=30).total_seconds()
           )
           
           # Notify user
           await self.notification_service.notify(
               user_id, 
               f"API key for {exchange} has been rotated"
           )
           
           # Delete old key on exchange
           await self.exchange_service.delete_api_key(
               exchange, user_id, current_key['key_id']
           )
           
       async def schedule_rotations(self):
           while True:
               # Find keys nearing expiration (e.g., 3 days before)
               # Rotate those keys
               # Sleep until next check
               await asyncio.sleep(3600)  # Check hourly
   ```

### Rate Limiting

1. **API Endpoint Rate Limiting**
   ```python
   # middleware/rate_limit.py
   from fastapi import Request, HTTPException
   from starlette.middleware.base import BaseHTTPMiddleware
   
   class RateLimitMiddleware(BaseHTTPMiddleware):
       def __init__(self, app, rate_limiter):
           super().__init__(app)
           self.rate_limiter = rate_limiter
           
       async def dispatch(self, request: Request, call_next):
           # Get client identifier (IP, user ID, etc.)
           client_id = self._get_client_id(request)
           
           # Check rate limit
           key = f"ratelimit:{request.url.path}:{client_id}"
           if await self.rate_limiter.is_rate_limited(key):
               raise HTTPException(status_code=429, detail="Rate limit exceeded")
               
           # Process request
           response = await call_next(request)
           return response
           
       def _get_client_id(self, request: Request):
           # Get user ID from token if authenticated
           # Otherwise use IP address
           return request.client.host
   ```

## Distribution & Packaging

### PyInstaller Configuration

1. **Spec File**
   ```python
   # cryptobot.spec
   block_cipher = None
   
   a = Analysis(
       ['main.py'],
       pathex=['.'],
       binaries=[],
       datas=[
           ('static', 'static'),
           ('templates', 'templates'),
           ('config', 'config')
       ],
       hiddenimports=[
           'uvicorn.logging',
           'uvicorn.protocols',
           'strategies'
       ],
       hookspath=[],
       runtime_hooks=[],
       excludes=[],
       win_no_prefer_redirects=False,
       win_private_assemblies=False,
       cipher=block_cipher,
       noarchive=False
   )
   
   pyz = PYZ(
       a.pure, 
       a.zipped_data,
       cipher=block_cipher
   )
   
   exe = EXE(
       pyz,
       a.scripts,
       a.binaries,
       a.zipfiles,
       a.datas,
       [],
       name='cryptobot',
       debug=False,
       bootloader_ignore_signals=False,
       strip=False,
       upx=True,
       upx_exclude=[],
       runtime_tmpdir=None,
       console=True,
       icon='static/images/icon.ico'
   )
   ```

2. **Build Script**
   ```powershell
   # build_windows.ps1
   $env:PYTHONOPTIMIZE = 1
   pyinstaller --clean --noconfirm cryptobot.spec
   
   # Copy additional files
   Copy-Item -Path "LICENSE" -Destination "dist\"
   Copy-Item -Path "README.md" -Destination "dist\"
   
   # Create version file
   $version = (Get-Date -Format "yyyy.MM.dd.HHmm")
   Set-Content -Path "dist\version.txt" -Value $version
   
   # Create zip archive
   Compress-Archive -Path "dist\*" -DestinationPath "dist\cryptobot-$version.zip"
   ```

### Installer Creation

1. **InnoSetup Script**
   ```inno
   ; windows_installer.iss
   #define MyAppName "Cryptobot"
   #define MyAppVersion "1.0.0"
   #define MyAppPublisher "Cryptobot Team"
   #define MyAppURL "https://cryptobot.example.com"
   #define MyAppExeName "cryptobot.exe"
   
   [Setup]
   AppId={{CRYPTOBOT-TRADING-APP}}
   AppName={#MyAppName}
   AppVersion={#MyAppVersion}
   AppPublisher={#MyAppPublisher}
   AppPublisherURL={#MyAppURL}
   AppSupportURL={#MyAppURL}
   AppUpdatesURL={#MyAppURL}
   DefaultDirName={autopf}\{#MyAppName}
   DefaultGroupName={#MyAppName}
   OutputBaseFilename=cryptobot-setup
   Compression=lzma
   SolidCompression=yes
   WizardStyle=modern
   
   [Languages]
   Name: "english"; MessagesFile: "compiler:Default.isl"
   
   [Tasks]
   Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
   
   [Files]
   Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
   Source: "dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
   
   [Icons]
   Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
   Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
   
   [Run]
   Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
   ```

## Technical Standards

### Code Style

1. **Python Style Guide**
   - Follow PEP 8 for Python code style
   - Use type hints for all function parameters and return values
   - Document all classes and functions with docstrings
   - Maximum line length: 100 characters

2. **JavaScript Style Guide**
   - Follow Airbnb JavaScript Style Guide
   - Use ESLint for static analysis
   - Use Prettier for code formatting

### Commit Standards

1. **Commit Message Format**
   ```
   <type>(<scope>): <subject>
   
   <body>
   
   <footer>
   ```

2. **Types**
   - feat: A new feature
   - fix: A bug fix
   - docs: Documentation changes
   - style: Code style changes (formatting, etc.)
   - refactor: Code changes that neither fix bugs nor add features
   - perf: Performance improvements
   - test: Adding or modifying tests
   - chore: Changes to the build process or auxiliary tools

### Pull Request Process

1. Create a feature branch from `develop`
2. Make changes and commit following commit standards
3. Push branch and create pull request to `develop`
4. Ensure CI passes (tests, linting, etc.)
5. Request review from at least one team member
6. Address review comments
7. Merge when approved

### Versioning

Follow Semantic Versioning (SemVer):
- MAJOR version for incompatible API changes
- MINOR version for backward-compatible functionality additions
- PATCH version for backward-compatible bug fixes