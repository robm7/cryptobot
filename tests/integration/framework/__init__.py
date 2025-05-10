"""
Integration Testing Framework

This package provides a comprehensive framework for integration testing
in the cryptobot project. It includes utilities for setting up test environments,
managing service dependencies, mocking services, and running integration tests.

Key components:
- Base classes for integration tests
- Service container for managing dependencies
- Environment manager for test setup and teardown
- Docker Compose integration for containerized services
- Mock services for testing in isolation
- Utilities and helpers for common testing tasks
- Test runner for executing integration tests
"""

import logging
from .base import IntegrationTestBase, ServiceMock
from .container import ServiceContainer, MockServiceFactory
from .environment import TestEnvironmentManager, DockerServiceManager
from .docker import DockerComposeManager, create_test_compose_file
from .mocks import (
    MockService, MockExchangeService, MockDatabaseService, 
    MockRedisService, MockServiceFactory as MockFactory
)
from .runner import IntegrationTestRunner
from .utils import (
    find_free_port, generate_random_string, wait_for_port,
    wait_for_http, wait_for_async_condition, retry, retry_async,
    load_test_data, save_test_data, import_module_from_path,
    get_service_url, run_command, temp_env_vars, get_test_data_dir,
    get_project_root, get_test_config, Timer, setup_test_logging
)

# Configure logging
logger = logging.getLogger("integration_tests")
if not logger.handlers:
    # Set up default logging if not already configured
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Version
__version__ = "1.0.0"