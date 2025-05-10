# Auth Service Testing Documentation

## Test Types

### Unit Tests
- Location: `tests/unit/`
- Purpose: Test individual components in isolation
- Coverage: 90%+ required
- Run: `pytest tests/unit --cov`

### Integration Tests
- Location: `tests/integration/`
- Purpose: Test component interactions
- Includes: gRPC endpoint testing
- Run: `pytest tests/integration`

### Security Tests
- Location: `tests/security/`
- Purpose: Validate security controls
- Includes: OWASP checks, fuzz testing
- Run: `pytest tests/security && bandit -r . && safety check`

### Performance Tests
- Location: `tests/performance/`
- Purpose: Benchmark service performance
- Includes: Load testing, latency measurements
- Run: `pytest tests/performance`

## CI/CD Pipeline

The GitHub Actions workflow (`auth-service-tests.yml`) runs:
1. Unit tests with coverage
2. Integration tests
3. Security scans
4. Performance benchmarks

Requirements:
- Minimum 90% code coverage
- No security vulnerabilities
- Performance within SLA thresholds

## Running Tests Locally

1. Start Redis:
```bash
docker run -p 6379:6379 redis
```

2. Install test dependencies:
```bash
pip install -r requirements.txt pytest pytest-cov locust bandit safety
```

3. Run all tests:
```bash
pytest && bandit -r . && safety check
```

## Test Reports

- Coverage: `coverage.xml` (Codecov integration)
- Security: Bandit and Safety reports
- Performance: Console output metrics
- Artifacts: Archived in GitHub Actions