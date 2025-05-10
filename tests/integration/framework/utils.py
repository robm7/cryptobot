"""
Utilities and Helpers for Integration Tests

This module provides utility functions and helpers for integration testing.
"""

import os
import sys
import logging
import json
import time
import asyncio
import inspect
import importlib
import random
import string
import socket
import requests
import subprocess
from typing import Dict, Any, Optional, List, Callable, Type, Union, Tuple
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger("integration_tests")


def find_free_port() -> int:
    """
    Find a free port on the local machine.
    
    Returns:
        Free port number
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def generate_random_string(length: int = 10) -> str:
    """
    Generate a random string.
    
    Args:
        length: String length
        
    Returns:
        Random string
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def wait_for_port(
    host: str, 
    port: int, 
    timeout: int = 30,
    interval: float = 0.5
) -> bool:
    """
    Wait for a port to be open.
    
    Args:
        host: Host
        port: Port
        timeout: Timeout in seconds
        interval: Check interval in seconds
        
    Returns:
        True if port is open, False if timeout occurred
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                logger.info(f"Port {port} is open on {host}")
                return True
        except (socket.timeout, ConnectionRefusedError):
            pass
        
        time.sleep(interval)
    
    logger.warning(f"Timeout waiting for port {port} on {host}")
    return False


def wait_for_http(
    url: str, 
    timeout: int = 30,
    interval: float = 0.5,
    expected_status: Optional[int] = 200,
    headers: Optional[Dict[str, str]] = None
) -> bool:
    """
    Wait for an HTTP endpoint to be available.
    
    Args:
        url: URL
        timeout: Timeout in seconds
        interval: Check interval in seconds
        expected_status: Expected HTTP status code
        headers: HTTP headers
        
    Returns:
        True if endpoint is available, False if timeout occurred
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, headers=headers, timeout=1)
            
            if expected_status is None or response.status_code == expected_status:
                logger.info(f"HTTP endpoint {url} is available")
                return True
        except (requests.RequestException, ConnectionError):
            pass
        
        time.sleep(interval)
    
    logger.warning(f"Timeout waiting for HTTP endpoint {url}")
    return False


async def wait_for_async_condition(
    condition_func: Callable[[], bool],
    timeout: int = 30,
    interval: float = 0.5,
    description: str = "condition"
) -> bool:
    """
    Wait for an async condition to be true.
    
    Args:
        condition_func: Condition function
        timeout: Timeout in seconds
        interval: Check interval in seconds
        description: Condition description
        
    Returns:
        True if condition is true, False if timeout occurred
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            if condition_func():
                logger.info(f"Condition '{description}' is true")
                return True
        except Exception as e:
            logger.debug(f"Error checking condition '{description}': {e}")
        
        await asyncio.sleep(interval)
    
    logger.warning(f"Timeout waiting for condition '{description}'")
    return False


def retry(
    func: Callable,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry a function.
    
    Args:
        func: Function to retry
        retries: Number of retries
        delay: Initial delay in seconds
        backoff: Backoff factor
        exceptions: Exceptions to catch
        
    Returns:
        Function result
    """
    def wrapper(*args, **kwargs):
        current_delay = delay
        last_exception = None
        
        for i in range(retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if i < retries:
                    logger.warning(f"Retry {i+1}/{retries} after error: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        raise last_exception
    
    return wrapper


async def retry_async(
    func: Callable,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry an async function.
    
    Args:
        func: Async function to retry
        retries: Number of retries
        delay: Initial delay in seconds
        backoff: Backoff factor
        exceptions: Exceptions to catch
        
    Returns:
        Function result
    """
    current_delay = delay
    last_exception = None
    
    for i in range(retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            
            if i < retries:
                logger.warning(f"Retry {i+1}/{retries} after error: {e}")
                await asyncio.sleep(current_delay)
                current_delay *= backoff
    
    raise last_exception


def load_test_data(file_path: str) -> Any:
    """
    Load test data from a file.
    
    Args:
        file_path: File path
        
    Returns:
        Test data
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Test data file not found: {file_path}")
    
    with open(file_path, "r") as f:
        if file_path.endswith(".json"):
            return json.load(f)
        else:
            return f.read()


def save_test_data(file_path: str, data: Any):
    """
    Save test data to a file.
    
    Args:
        file_path: File path
        data: Test data
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        if file_path.endswith(".json"):
            json.dump(data, f, indent=2)
        else:
            f.write(str(data))


def import_module_from_path(module_path: str) -> Any:
    """
    Import a module from a file path.
    
    Args:
        module_path: Module path
        
    Returns:
        Imported module
    """
    module_name = os.path.basename(module_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_service_url(
    service_name: str,
    port: int,
    protocol: str = "http",
    host: str = "localhost",
    path: str = ""
) -> str:
    """
    Get a service URL.
    
    Args:
        service_name: Service name
        port: Port
        protocol: Protocol
        host: Host
        path: Path
        
    Returns:
        Service URL
    """
    url = f"{protocol}://{host}:{port}"
    
    if path:
        if not path.startswith("/"):
            path = f"/{path}"
        url = f"{url}{path}"
    
    return url


def run_command(
    command: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[int] = None,
    check: bool = True
) -> Tuple[int, str, str]:
    """
    Run a command.
    
    Args:
        command: Command
        cwd: Working directory
        env: Environment variables
        timeout: Timeout in seconds
        check: Whether to check the return code
        
    Returns:
        Tuple of (return code, stdout, stderr)
    """
    logger.info(f"Running command: {' '.join(command)}")
    
    # Prepare environment
    if env:
        env = {**os.environ, **env}
    
    # Run command
    process = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        timeout=timeout,
        check=check,
        capture_output=True,
        text=True
    )
    
    return process.returncode, process.stdout, process.stderr


@contextmanager
def temp_env_vars(env_vars: Dict[str, str]):
    """
    Temporarily set environment variables.
    
    Args:
        env_vars: Environment variables
    """
    original_env = {}
    
    try:
        # Save original environment variables
        for key, value in env_vars.items():
            if key in os.environ:
                original_env[key] = os.environ[key]
            
            # Set new value
            os.environ[key] = value
        
        yield
    finally:
        # Restore original environment variables
        for key in env_vars:
            if key in original_env:
                os.environ[key] = original_env[key]
            else:
                del os.environ[key]


def get_test_data_dir() -> str:
    """
    Get the test data directory.
    
    Returns:
        Test data directory
    """
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up to the tests directory
    tests_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # Create test data directory if it doesn't exist
    test_data_dir = os.path.join(tests_dir, "data")
    os.makedirs(test_data_dir, exist_ok=True)
    
    return test_data_dir


def get_project_root() -> str:
    """
    Get the project root directory.
    
    Returns:
        Project root directory
    """
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up to the project root
    return os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))


def get_test_config() -> Dict[str, Any]:
    """
    Get the test configuration.
    
    Returns:
        Test configuration
    """
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up to the tests directory
    tests_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # Load test configuration
    config_path = os.path.join(tests_dir, "integration", "config.py")
    
    # Import config module
    sys.path.insert(0, tests_dir)
    config_module = importlib.import_module("integration.config")
    sys.path.pop(0)
    
    # Get configuration
    config = {}
    
    for key in dir(config_module):
        if key.isupper():
            config[key] = getattr(config_module, key)
    
    return config


class Timer:
    """
    Timer for measuring execution time.
    """
    
    def __init__(self, name: str = "timer"):
        self.name = name
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        self.end_time = None
        logger.debug(f"Started timer: {self.name}")
    
    def stop(self) -> float:
        """
        Stop the timer.
        
        Returns:
            Elapsed time in seconds
        """
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        logger.debug(f"Stopped timer: {self.name}, elapsed: {elapsed:.6f}s")
        
        return elapsed
    
    def elapsed(self) -> float:
        """
        Get the elapsed time.
        
        Returns:
            Elapsed time in seconds
        """
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        if self.end_time is None:
            return time.time() - self.start_time
        else:
            return self.end_time - self.start_time
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def setup_test_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True
):
    """
    Set up logging for tests.
    
    Args:
        level: Logging level
        log_file: Log file path
        console: Whether to log to console
    """
    # Create logger
    logger = logging.getLogger("integration_tests")
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Add console handler
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler
    if log_file:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger