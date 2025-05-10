# Cryptobot Testing Documentation

## Database Connection Testing

### Connection Pooling
- **Configuration**: 
  - Pool size: 10 connections
  - Max overflow: 20 connections  
  - Timeout: 30 seconds
  - Recycle: 3600 seconds (1 hour)
  - Pre-ping: Enabled (validates connections before use)

### Test Coverage
1. **Connection Pooling Tests** (`test_connection_pooling.py`)
   - Connection reuse validation
   - Pool exhaustion scenarios
   - Connection recycling
   - Connection resilience
   - Sync connection testing

2. **CRUD Operations** (`test_database_operations.py`)
   - Trade model operations
   - Strategy model operations  
   - User model operations
   - Async/Sync operation parity

3. **Model Validation** (`test_models.py`)
   - Field validation
   - Relationship integrity
   - Constraint checking

### Running Tests
```bash
# Run all database tests
pytest tests/test_connection_pooling.py tests/test_database_operations.py tests/test_models.py -v

# Run specific test category
pytest tests/test_connection_pooling.py -v
```

### Known Issues
- SQLite doesn't support connection pooling (uses NullPool)
- SQLite has limited concurrent write capabilities
  - Concurrent write tests are skipped for SQLite
  - Use PostgreSQL for production workloads requiring concurrency
- On Windows, database paths must be absolute
- Connection recycling may be delayed under heavy load

### SQLite-Specific Notes
- Use `:memory:` database for testing when possible
- For file-based testing, ensure:
  - Absolute paths are used
  - File permissions allow read/write access
  - No other processes are accessing the file