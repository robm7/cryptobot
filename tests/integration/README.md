# Cryptobot Integration Tests

This directory contains integration tests for the Cryptobot system. These tests verify that different components of the system work together correctly.

## Overview

The integration tests cover the following critical workflows:

1. **Backtesting Workflow** (`test_backtest_integration.py`)
   - Tests the full backtesting pipeline from historical data to strategy execution to performance analysis
   - Includes tests for different strategies (Mean Reversion, Breakout Reset)
   - Covers multi-symbol backtesting and parameter optimization

2. **Risk Management Workflow** (`test_risk_management_integration.py`)
   - Tests integration between trade execution and risk management services
   - Verifies position size limits, concentration limits, and drawdown limits
   - Includes risk-adjusted position sizing and end-to-end risk workflow

3. **Authentication & Authorization** (`test_auth_integration.py`)
   - Tests user authentication, JWT token management, and API key rotation
   - Verifies permission checks for different user roles
   - Covers the complete auth workflow from login to API operations

4. **Strategy Execution Workflow** (`test_strategy_execution_integration.py`)
   - Tests the full lifecycle from strategy creation to execution to performance tracking
   - Verifies signal generation, processing, and trade execution
   - Includes performance metrics calculation and tracking

5. **Data Pipeline** (`test_data_pipeline.py`)
   - Tests the data collection, processing, and storage pipeline
   - Verifies OHLCV data processing and historical data loading

6. **Order Execution** (`test_order_execution_integration.py`)
   - Tests the reliable order execution system
   - Verifies retry logic, circuit breaker functionality, and error handling

7. **Service Interactions** (`test_service_integration.py`)
   - Tests interactions between different services
   - Verifies data flow between services and error handling

## Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Install the required dependencies:

```bash
# Option 1: Install directly
python tests/integration/setup_integration_tests.py

# Option 2: Create a virtual environment and install dependencies
python tests/integration/setup_integration_tests.py --venv
```

## Running the Tests

### Verifying Setup with Isolated Test

Before running the full integration tests, you can verify that your testing environment is set up correctly by running the isolated test:

```bash
python tests/integration/run_isolated_test.py
```

This test is completely isolated from the project's code and doesn't depend on any project files, so it's the most reliable way to check that your testing framework is working correctly.

### Verifying Setup with Standalone Test

If the isolated test passes, you can try running the standalone test:

```bash
python tests/integration/run_standalone_test.py
```

This test doesn't depend on the project's conftest.py file but may still require some project modules.

### Running a Simple Integration Test

Once the standalone test passes, you can try running the simple integration test:

```bash
python tests/integration/run_simple_test.py
```

This test is more integrated with the framework but still has minimal dependencies.

### Running a Single Test

To run a specific test file:

```bash
python tests/integration/run_single_test.py test_backtest_integration.py -v
```

To run a specific test case:

```bash
python tests/integration/run_single_test.py test_backtest_integration.py --test-case TestBacktestIntegration.test_mean_reversion_backtest -v
```

### Running All Integration Tests

To run all integration tests:

```bash
python tests/integration/run_integration_tests.py
```

### Using pytest Directly

You can also use pytest directly:

```bash
# Run a specific test file
python -m pytest tests/integration/test_backtest_integration.py -v

# Run a specific test case
python -m pytest tests/integration/test_backtest_integration.py::TestBacktestIntegration::test_mean_reversion_backtest -v

# Skip loading conftest.py files (useful for troubleshooting)
python -m pytest -p no:conftest tests/integration/test_standalone.py -v

# Run isolated test with custom PYTHONPATH
PYTHONPATH=tests/integration/isolated python -m pytest tests/integration/isolated/test_isolated.py -v
```

### Running with Docker

To run tests with Docker services:

```bash
python tests/integration/run_integration_tests.py --docker
```

## Test Framework

The integration tests use a custom framework that provides:

- Base classes for integration tests
- Mock services for testing
- Docker integration for realistic environments
- Utilities for common testing tasks

### Key Components

- `IntegrationTestBase`: Base class for all integration tests
- `ServiceContainer`: Dependency injection container for managing services
- `MockExchangeService`, `MockDatabaseService`, etc.: Mock implementations of services
- `DockerComposeManager`: Manager for Docker Compose environments

## Writing New Tests

To write a new integration test:

1. Create a new test file in the `tests/integration` directory
2. Inherit from `IntegrationTestBase`
3. Use the provided mock services or create new ones as needed
4. Follow the existing test patterns for setup and teardown

Example:

```python
import pytest
from tests.integration.framework.base import IntegrationTestBase

class TestMyFeature(IntegrationTestBase):
    
    @classmethod
    def setup_class(cls):
        """Set up test class environment"""
        super().setup_class()
        # Additional setup
    
    @classmethod
    def teardown_class(cls):
        """Tear down test class environment"""
        # Additional teardown
        super().teardown_class()
    
    @pytest.mark.integration
    def test_my_feature(self):
        """Test my feature"""
        # Test implementation
        assert True
```

## Best Practices

1. **Isolation**: Each test should be isolated and not depend on the state of other tests
2. **Cleanup**: Always clean up resources after tests
3. **Realistic Data**: Use realistic test data that represents production scenarios
4. **Error Handling**: Test error conditions and verify proper error handling
5. **Service Boundaries**: Focus on testing interactions across service boundaries
6. **Logging**: Use logging to debug test failures
7. **CI/CD Integration**: Run integration tests in CI/CD pipelines

## Troubleshooting

### Common Issues

1. **Missing Dependencies**:
   - Run `python tests/integration/setup_integration_tests.py` to install required dependencies
   - If specific dependencies are missing, install them manually: `pip install python-dotenv redis docker aioredis flask-sqlalchemy`

2. **Port Conflicts**:
   - If you encounter port conflicts, check if any services are already running on the required ports
   - You can modify the port mappings in `docker-compose.yml`

3. **Docker Issues**:
   - Ensure Docker and Docker Compose are installed and running
   - Check Docker logs for any errors

4. **Authentication Errors**:
   - Verify that the auth service is properly configured
   - Check that the JWT secret key is set correctly

5. **Import Errors**:
   - If you encounter import errors, make sure all required modules are installed
   - Check that the Python path includes the project root directory

6. **Conftest.py Issues**:
   - If you encounter issues with the project's conftest.py file, you can skip loading it with `-p no:conftest`
   - Use the isolated test to verify your testing environment: `python tests/integration/run_isolated_test.py`
   - Use the standalone test to verify your testing environment: `python tests/integration/run_standalone_test.py`

7. **pytest.ini Issues**:
   - If you encounter issues with duplicate entries in pytest.ini, check for duplicate configuration options
   - You can use `--no-header` to suppress pytest header output

8. **PYTHONPATH Issues**:
   - If you encounter issues with the PYTHONPATH, you can set it explicitly:
     ```bash
     PYTHONPATH=tests/integration/isolated python -m pytest tests/integration/isolated/test_isolated.py -v
     ```
   - On Windows, you can set it with:
     ```bash
     set PYTHONPATH=tests\integration\isolated
     python -m pytest tests\integration\isolated\test_isolated.py -v
     ```

### Getting Help

If you encounter any issues with the integration tests, please:

1. Check the logs for error messages
2. Review the test code to understand what it's trying to do
3. Consult the documentation for the specific components being tested
4. Reach out to the development team for assistance