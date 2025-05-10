"""
Test Environment Manager for Integration Tests

This module provides utilities for setting up and tearing down test environments
for integration testing, including database, Redis, and service mocks.
"""

import os
import logging
import asyncio
import subprocess
import time
import signal
import atexit
from typing import Dict, Any, Optional, List, Callable, Tuple
import tempfile
import json
import shutil
import sqlite3
import redis
from contextlib import contextmanager

logger = logging.getLogger("integration_tests")


class TestEnvironmentManager:
    """
    Manager for setting up and tearing down test environments.
    
    Provides utilities for managing databases, Redis, and other services
    required for integration testing.
    """
    
    def __init__(self, env_name: str = "test"):
        self.env_name = env_name
        self.temp_dir = tempfile.mkdtemp(prefix=f"cryptobot_test_{env_name}_")
        self.processes: List[subprocess.Popen] = []
        self.db_path: Optional[str] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # Register cleanup handler
        atexit.register(self.cleanup)
        
        logger.info(f"Initialized TestEnvironmentManager for {env_name}")
        logger.info(f"Temporary directory: {self.temp_dir}")
    
    def setup_database(self, db_name: str = "test_db") -> str:
        """
        Set up a SQLite database for testing.
        
        Args:
            db_name: Database name
            
        Returns:
            Database URL
        """
        self.db_path = os.path.join(self.temp_dir, f"{db_name}.db")
        db_url = f"sqlite:///{self.db_path}"
        
        # Initialize empty database
        conn = sqlite3.connect(self.db_path)
        conn.close()
        
        logger.info(f"Set up SQLite database at {self.db_path}")
        return db_url
    
    def setup_redis(
        self, 
        port: int = 6379, 
        db: int = 10
    ) -> redis.Redis:
        """
        Set up Redis connection for testing.
        
        Args:
            port: Redis port
            db: Redis database number
            
        Returns:
            Redis client
        """
        self.redis_client = redis.Redis(
            host="localhost",
            port=port,
            db=db,
            decode_responses=True
        )
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"Connected to Redis on port {port}, db {db}")
        except redis.ConnectionError:
            logger.warning(f"Could not connect to Redis on port {port}")
            self.redis_client = None
        
        return self.redis_client
    
    def start_service(
        self, 
        command: List[str], 
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        wait_for_output: Optional[str] = None,
        timeout: int = 30
    ) -> subprocess.Popen:
        """
        Start a service process.
        
        Args:
            command: Command to run
            env: Environment variables
            cwd: Working directory
            wait_for_output: String to wait for in stdout
            timeout: Timeout in seconds
            
        Returns:
            Process object
            
        Raises:
            TimeoutError: If service does not start within timeout
        """
        # Prepare environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        # Start process
        process = subprocess.Popen(
            command,
            env=process_env,
            cwd=cwd or self.temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        self.processes.append(process)
        
        logger.info(f"Started service: {' '.join(command)}")
        
        # Wait for output if specified
        if wait_for_output:
            start_time = time.time()
            while time.time() - start_time < timeout:
                output = process.stdout.readline()
                if wait_for_output in output:
                    logger.info(f"Service ready: {' '.join(command)}")
                    break
                
                # Check if process is still running
                if process.poll() is not None:
                    stderr = process.stderr.read()
                    raise RuntimeError(
                        f"Service failed to start: {stderr}"
                    )
                
                time.sleep(0.1)
            else:
                raise TimeoutError(
                    f"Timeout waiting for service to start: {' '.join(command)}"
                )
        
        return process
    
    def setup_docker_services(
        self, 
        compose_file: str,
        services: Optional[List[str]] = None,
        env_file: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> None:
        """
        Set up services using Docker Compose.
        
        Args:
            compose_file: Path to docker-compose.yml
            services: List of services to start (None for all)
            env_file: Path to .env file
            project_name: Docker Compose project name
        """
        # Build command
        command = ["docker-compose", "-f", compose_file]
        
        if project_name:
            command.extend(["-p", project_name])
        
        if env_file:
            command.extend(["--env-file", env_file])
        
        command.append("up")
        command.append("-d")  # Detached mode
        
        if services:
            command.extend(services)
        
        # Start services
        logger.info(f"Starting Docker services: {' '.join(command)}")
        subprocess.run(command, check=True)
        
        # Register cleanup
        project_arg = ["-p", project_name] if project_name else []
        cleanup_command = [
            "docker-compose", "-f", compose_file, *project_arg, "down", "-v"
        ]
        
        def cleanup_docker():
            logger.info("Stopping Docker services")
            subprocess.run(cleanup_command, check=False)
        
        atexit.register(cleanup_docker)
    
    def create_test_data_file(
        self, 
        filename: str, 
        data: Any
    ) -> str:
        """
        Create a test data file.
        
        Args:
            filename: File name
            data: Data to write
            
        Returns:
            Path to the file
        """
        file_path = os.path.join(self.temp_dir, filename)
        
        with open(file_path, "w") as f:
            if filename.endswith(".json"):
                json.dump(data, f, indent=2)
            else:
                f.write(str(data))
        
        logger.info(f"Created test data file: {file_path}")
        return file_path
    
    def cleanup(self):
        """Clean up resources."""
        # Stop processes
        for process in self.processes:
            if process.poll() is None:  # Process is still running
                logger.info(f"Stopping process {process.pid}")
                try:
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {process.pid} did not terminate, killing")
                    process.kill()
        
        # Close Redis connection
        if self.redis_client:
            self.redis_client.close()
        
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            logger.info(f"Removing temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @contextmanager
    def temporary_config(self, config_data: Dict[str, Any]) -> str:
        """
        Create a temporary configuration file.
        
        Args:
            config_data: Configuration data
            
        Yields:
            Path to the configuration file
        """
        config_path = os.path.join(self.temp_dir, "test_config.json")
        
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        
        try:
            yield config_path
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


class DockerServiceManager:
    """
    Manager for Docker-based services in integration tests.
    
    Provides utilities for starting and stopping Docker containers
    for integration testing.
    """
    
    def __init__(self, project_name: str = "cryptobot_test"):
        self.project_name = project_name
        self.compose_files: List[str] = []
        self.services_started: List[str] = []
        
        logger.info(f"Initialized DockerServiceManager for {project_name}")
    
    def add_compose_file(self, compose_file: str):
        """
        Add a Docker Compose file.
        
        Args:
            compose_file: Path to docker-compose.yml
        """
        if not os.path.exists(compose_file):
            raise FileNotFoundError(f"Compose file not found: {compose_file}")
        
        self.compose_files.append(compose_file)
        logger.info(f"Added compose file: {compose_file}")
    
    def start_services(
        self, 
        services: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None,
        wait_timeout: int = 60
    ):
        """
        Start Docker services.
        
        Args:
            services: List of services to start (None for all)
            env_vars: Environment variables for Docker Compose
            wait_timeout: Timeout for waiting for services in seconds
        """
        if not self.compose_files:
            raise ValueError("No compose files added")
        
        # Build command
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name])
        command.append("up")
        command.append("-d")  # Detached mode
        
        if services:
            command.extend(services)
            self.services_started.extend(services)
        
        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        # Start services
        logger.info(f"Starting Docker services: {' '.join(command)}")
        subprocess.run(command, env=env, check=True)
        
        # Wait for services to be ready
        self._wait_for_services(wait_timeout)
    
    def _wait_for_services(self, timeout: int = 60):
        """
        Wait for services to be ready.
        
        Args:
            timeout: Timeout in seconds
        """
        # Build command to check service status
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name, "ps", "--services", "--filter", "status=running"])
        
        # Wait for services
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            running_services = result.stdout.strip().split("\n")
            running_services = [s for s in running_services if s]
            
            if not self.services_started or all(s in running_services for s in self.services_started):
                logger.info("All services are running")
                return
            
            logger.info(f"Waiting for services: {', '.join(set(self.services_started) - set(running_services))}")
            time.sleep(2)
        
        # If we get here, timeout occurred
        raise TimeoutError(f"Timeout waiting for services: {', '.join(set(self.services_started) - set(running_services))}")
    
    def stop_services(self):
        """Stop Docker services."""
        if not self.compose_files:
            return
        
        # Build command
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name, "down", "-v"])
        
        # Stop services
        logger.info(f"Stopping Docker services: {' '.join(command)}")
        subprocess.run(command, check=False)
        
        self.services_started = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_services()