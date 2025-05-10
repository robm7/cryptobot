"""
Docker Compose Integration for Integration Tests

This module provides utilities for running integration tests with Docker Compose,
allowing tests to be run against containerized services.
"""

import os
import logging
import subprocess
import time
import yaml
import tempfile
import shutil
from typing import Dict, Any, Optional, List, Set, Tuple
from contextlib import contextmanager

logger = logging.getLogger("integration_tests")


class DockerComposeManager:
    """
    Manager for Docker Compose in integration tests.
    
    Provides utilities for creating, starting, and stopping Docker Compose
    environments for integration testing.
    """
    
    def __init__(
        self, 
        project_name: str = "cryptobot_test",
        compose_files: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ):
        self.project_name = project_name
        self.compose_files = compose_files or []
        self.env_vars = env_vars or {}
        self.temp_dir = tempfile.mkdtemp(prefix=f"docker_compose_{project_name}_")
        self.services_started: Set[str] = set()
        
        # Add default environment variables
        self.env_vars.update({
            "COMPOSE_PROJECT_NAME": project_name,
            "TEST_ENV": "test"
        })
        
        logger.info(f"Initialized DockerComposeManager for {project_name}")
    
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
    
    def create_compose_file(
        self, 
        services: Dict[str, Any],
        networks: Optional[Dict[str, Any]] = None,
        volumes: Optional[Dict[str, Any]] = None,
        version: str = "3.8"
    ) -> str:
        """
        Create a Docker Compose file.
        
        Args:
            services: Services configuration
            networks: Networks configuration
            volumes: Volumes configuration
            version: Compose file version
            
        Returns:
            Path to the created compose file
        """
        compose_data = {
            "version": version,
            "services": services
        }
        
        if networks:
            compose_data["networks"] = networks
        
        if volumes:
            compose_data["volumes"] = volumes
        
        # Create compose file
        compose_file = os.path.join(self.temp_dir, "docker-compose.yml")
        
        with open(compose_file, "w") as f:
            yaml.dump(compose_data, f, default_flow_style=False)
        
        self.compose_files.append(compose_file)
        logger.info(f"Created compose file: {compose_file}")
        
        return compose_file
    
    def start_services(
        self, 
        services: Optional[List[str]] = None,
        wait_timeout: int = 60,
        build: bool = False
    ):
        """
        Start Docker Compose services.
        
        Args:
            services: List of services to start (None for all)
            wait_timeout: Timeout for waiting for services in seconds
            build: Whether to build services before starting
        """
        if not self.compose_files:
            raise ValueError("No compose files added")
        
        # Build command
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name])
        
        # Build services if requested
        if build:
            build_command = command.copy()
            build_command.append("build")
            
            if services:
                build_command.extend(services)
            
            logger.info(f"Building Docker services: {' '.join(build_command)}")
            subprocess.run(
                build_command, 
                env={**os.environ, **self.env_vars}, 
                check=True
            )
        
        # Start services
        up_command = command.copy()
        up_command.extend(["up", "-d"])
        
        if services:
            up_command.extend(services)
            self.services_started.update(services)
        
        logger.info(f"Starting Docker services: {' '.join(up_command)}")
        subprocess.run(
            up_command, 
            env={**os.environ, **self.env_vars}, 
            check=True
        )
        
        # Wait for services to be ready
        self._wait_for_services(command, wait_timeout)
    
    def _wait_for_services(self, base_command: List[str], timeout: int = 60):
        """
        Wait for services to be ready.
        
        Args:
            base_command: Base Docker Compose command
            timeout: Timeout in seconds
        """
        # Build command to check service status
        ps_command = base_command.copy()
        ps_command.extend(["ps", "--services", "--filter", "status=running"])
        
        # Wait for services
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = subprocess.run(
                ps_command, 
                env={**os.environ, **self.env_vars},
                capture_output=True, 
                text=True, 
                check=False
            )
            
            running_services = result.stdout.strip().split("\n")
            running_services = [s for s in running_services if s]
            
            if not self.services_started or all(s in running_services for s in self.services_started):
                logger.info("All services are running")
                return
            
            missing_services = self.services_started - set(running_services)
            logger.info(f"Waiting for services: {', '.join(missing_services)}")
            time.sleep(2)
        
        # If we get here, timeout occurred
        missing_services = self.services_started - set(running_services)
        raise TimeoutError(f"Timeout waiting for services: {', '.join(missing_services)}")
    
    def stop_services(self):
        """Stop Docker Compose services."""
        if not self.compose_files:
            return
        
        # Build command
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name, "down", "-v"])
        
        # Stop services
        logger.info(f"Stopping Docker services: {' '.join(command)}")
        subprocess.run(
            command, 
            env={**os.environ, **self.env_vars}, 
            check=False
        )
        
        self.services_started.clear()
    
    def get_service_logs(self, service: str, tail: Optional[int] = None) -> str:
        """
        Get logs for a service.
        
        Args:
            service: Service name
            tail: Number of lines to tail
            
        Returns:
            Service logs
        """
        if not self.compose_files:
            raise ValueError("No compose files added")
        
        # Build command
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name, "logs"])
        
        if tail:
            command.extend(["--tail", str(tail)])
        
        command.append(service)
        
        # Get logs
        result = subprocess.run(
            command, 
            env={**os.environ, **self.env_vars},
            capture_output=True, 
            text=True, 
            check=True
        )
        
        return result.stdout
    
    def get_service_host_port(self, service: str, container_port: int) -> Optional[int]:
        """
        Get the host port for a service.
        
        Args:
            service: Service name
            container_port: Container port
            
        Returns:
            Host port or None if not found
        """
        if not self.compose_files:
            raise ValueError("No compose files added")
        
        # Build command
        command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            command.extend(["-f", compose_file])
        
        command.extend(["-p", self.project_name, "port", service, str(container_port)])
        
        # Get port
        result = subprocess.run(
            command, 
            env={**os.environ, **self.env_vars},
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode != 0:
            logger.warning(f"Failed to get port for {service}:{container_port}")
            return None
        
        # Parse port
        port_mapping = result.stdout.strip()
        if not port_mapping:
            return None
        
        # Format is typically "0.0.0.0:12345"
        try:
            host, port = port_mapping.split(":")
            return int(port)
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse port mapping: {port_mapping}")
            return None
    
    def exec_command(
        self, 
        service: str, 
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """
        Execute a command in a service container.
        
        Args:
            service: Service name
            command: Command to execute
            env: Environment variables
            workdir: Working directory
            
        Returns:
            Tuple of (exit code, stdout, stderr)
        """
        if not self.compose_files:
            raise ValueError("No compose files added")
        
        # Build command
        docker_command = ["docker-compose"]
        
        for compose_file in self.compose_files:
            docker_command.extend(["-f", compose_file])
        
        docker_command.extend(["-p", self.project_name, "exec"])
        
        # Add environment variables
        if env:
            for key, value in env.items():
                docker_command.extend(["-e", f"{key}={value}"])
        
        # Add working directory
        if workdir:
            docker_command.extend(["--workdir", workdir])
        
        # Add service and command
        docker_command.append(service)
        docker_command.extend(command)
        
        # Execute command
        logger.info(f"Executing command in {service}: {' '.join(command)}")
        result = subprocess.run(
            docker_command, 
            env={**os.environ, **self.env_vars},
            capture_output=True, 
            text=True, 
            check=False
        )
        
        return result.returncode, result.stdout, result.stderr
    
    def cleanup(self):
        """Clean up resources."""
        # Stop services
        self.stop_services()
        
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            logger.info(f"Removing temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @contextmanager
    def service_environment(
        self, 
        services: Optional[List[str]] = None,
        wait_timeout: int = 60,
        build: bool = False
    ):
        """
        Context manager for Docker Compose environment.
        
        Args:
            services: List of services to start (None for all)
            wait_timeout: Timeout for waiting for services in seconds
            build: Whether to build services before starting
            
        Yields:
            DockerComposeManager instance
        """
        try:
            self.start_services(services, wait_timeout, build)
            yield self
        finally:
            self.stop_services()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_test_compose_file(
    services: Dict[str, Dict[str, Any]],
    output_path: Optional[str] = None
) -> str:
    """
    Create a Docker Compose file for testing.
    
    Args:
        services: Dictionary of service configurations
        output_path: Output path (None for temporary file)
        
    Returns:
        Path to the created compose file
    """
    compose_data = {
        "version": "3.8",
        "services": services,
        "networks": {
            "test_network": {
                "driver": "bridge"
            }
        }
    }
    
    # Create output path if not provided
    if not output_path:
        temp_dir = tempfile.mkdtemp(prefix="docker_compose_test_")
        output_path = os.path.join(temp_dir, "docker-compose.yml")
    
    # Create compose file
    with open(output_path, "w") as f:
        yaml.dump(compose_data, f, default_flow_style=False)
    
    logger.info(f"Created test compose file: {output_path}")
    return output_path