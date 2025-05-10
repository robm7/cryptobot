"""
Environment Handler for CryptoBot.

This module provides the EnvironmentHandler class, which detects and adapts to different
environments (dev, prod, etc.), loads environment-specific configurations, handles
environment variables, supports profiles for different deployment scenarios, and
provides environment-specific overrides.
"""

import os
import logging
import platform
import socket
from typing import Dict, List, Any, Optional
import json

from .config_store import ConfigStore

logger = logging.getLogger(__name__)

class EnvironmentHandler:
    """
    Handler for environment-specific configuration.
    
    The EnvironmentHandler detects and adapts to different environments (dev, prod, etc.),
    loads environment-specific configurations, handles environment variables, supports
    profiles for different deployment scenarios, and provides environment-specific overrides.
    """
    
    def __init__(self, config_store: ConfigStore):
        """
        Initialize the environment handler.
        
        Args:
            config_store: Configuration store
        """
        self._config_store = config_store
        self._environment = "dev"  # Default environment
        self._profile = "default"  # Default profile
        self._env_vars: Dict[str, str] = {}
        self._env_var_mappings: Dict[str, str] = {}
        self._detected_environment = self._detect_environment()
        logger.info("Environment Handler initialized")
    
    def set_environment(self, environment: str) -> None:
        """
        Set the current environment.
        
        Args:
            environment: Environment name (e.g., "dev", "prod")
        """
        self._environment = environment
        
        # Load environment-specific configuration
        self._config_store.load_environment_config(environment)
        
        logger.info(f"Environment set to {environment}")
    
    def get_environment(self) -> str:
        """
        Get the current environment.
        
        Returns:
            str: Environment name
        """
        return self._environment
    
    def set_profile(self, profile: str) -> None:
        """
        Set the current profile.
        
        Args:
            profile: Profile name (e.g., "default", "docker", "kubernetes")
        """
        self._profile = profile
        
        # Load profile-specific configuration
        profile_config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "config",
            f"profile_{profile}.json"
        )
        
        if os.path.exists(profile_config_path):
            try:
                with open(profile_config_path, "r") as f:
                    profile_config = json.load(f)
                
                # Apply profile configuration to environment configuration
                for key, value in profile_config.items():
                    self._config_store.set_environment_config_value(key, value)
                
                logger.info(f"Loaded profile configuration from {profile_config_path}")
            except Exception as e:
                logger.error(f"Error loading profile configuration from {profile_config_path}: {e}")
        else:
            logger.info(f"No profile configuration found for {profile}")
        
        logger.info(f"Profile set to {profile}")
    
    def get_profile(self) -> str:
        """
        Get the current profile.
        
        Returns:
            str: Profile name
        """
        return self._profile
    
    def load_environment_variables(self) -> None:
        """Load environment variables."""
        # Get all environment variables
        self._env_vars = dict(os.environ)
        
        # Apply environment variable mappings
        for env_var, config_key in self._env_var_mappings.items():
            if env_var in self._env_vars:
                value = self._env_vars[env_var]
                
                # Try to parse as JSON
                try:
                    value = json.loads(value)
                except:
                    # Not JSON, use as is
                    pass
                
                # Set in environment configuration
                self._config_store.set_environment_config_value(config_key, value)
                logger.debug(f"Applied environment variable {env_var} to {config_key}")
        
        logger.info("Loaded environment variables")
    
    def add_environment_variable_mapping(self, env_var: str, config_key: str) -> None:
        """
        Add a mapping from an environment variable to a configuration key.
        
        Args:
            env_var: Environment variable name
            config_key: Configuration key (dot-separated for nested keys)
        """
        self._env_var_mappings[env_var] = config_key
        
        # Apply mapping if environment variable exists
        if env_var in os.environ:
            value = os.environ[env_var]
            
            # Try to parse as JSON
            try:
                value = json.loads(value)
            except:
                # Not JSON, use as is
                pass
            
            # Set in environment configuration
            self._config_store.set_environment_config_value(config_key, value)
            logger.debug(f"Applied environment variable {env_var} to {config_key}")
    
    def remove_environment_variable_mapping(self, env_var: str) -> None:
        """
        Remove a mapping from an environment variable to a configuration key.
        
        Args:
            env_var: Environment variable name
        """
        if env_var in self._env_var_mappings:
            del self._env_var_mappings[env_var]
            logger.debug(f"Removed environment variable mapping for {env_var}")
    
    def get_environment_variable_mappings(self) -> Dict[str, str]:
        """
        Get all environment variable mappings.
        
        Returns:
            Dict[str, str]: Dictionary mapping environment variable names to configuration keys
        """
        return self._env_var_mappings.copy()
    
    def get_environment_variable(self, env_var: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable.
        
        Args:
            env_var: Environment variable name
            default: Default value if environment variable is not set
        
        Returns:
            Optional[str]: Environment variable value, or default if not set
        """
        return os.environ.get(env_var, default)
    
    def get_detected_environment(self) -> Dict[str, Any]:
        """
        Get information about the detected environment.
        
        Returns:
            Dict[str, Any]: Dictionary of environment information
        """
        return self._detected_environment.copy()
    
    def _detect_environment(self) -> Dict[str, Any]:
        """
        Detect the current environment.
        
        Returns:
            Dict[str, Any]: Dictionary of environment information
        """
        env_info = {
            "os": {
                "name": os.name,
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "python": {
                "version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "compiler": platform.python_compiler()
            },
            "network": {
                "hostname": socket.gethostname()
            },
            "environment_variables": {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "HOME": os.environ.get("HOME", ""),
                "USER": os.environ.get("USER", "")
            }
        }
        
        # Detect if running in Docker
        env_info["is_docker"] = os.path.exists("/.dockerenv")
        
        # Detect if running in Kubernetes
        env_info["is_kubernetes"] = "KUBERNETES_SERVICE_HOST" in os.environ
        
        # Detect if running in CI/CD
        env_info["is_ci"] = any(var in os.environ for var in [
            "CI", "TRAVIS", "CIRCLECI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"
        ])
        
        # Try to detect environment type
        if env_info["is_ci"]:
            env_type = "ci"
        elif env_info["is_kubernetes"]:
            env_type = "prod"
        elif env_info["is_docker"]:
            env_type = "dev"
        else:
            # Check for common environment variables
            if os.environ.get("ENV") in ["prod", "production"]:
                env_type = "prod"
            elif os.environ.get("ENV") in ["stage", "staging"]:
                env_type = "stage"
            elif os.environ.get("ENV") in ["test", "testing"]:
                env_type = "test"
            else:
                env_type = "dev"
        
        env_info["environment_type"] = env_type
        
        # Set the environment based on detection
        self._environment = env_type
        
        return env_info
    
    def detect_and_configure(self) -> None:
        """Detect the environment and configure accordingly."""
        # Detect environment
        env_info = self._detect_environment()
        
        # Set environment
        self.set_environment(env_info["environment_type"])
        
        # Set profile based on detection
        if env_info["is_kubernetes"]:
            self.set_profile("kubernetes")
        elif env_info["is_docker"]:
            self.set_profile("docker")
        else:
            self.set_profile("default")
        
        # Load environment variables
        self.load_environment_variables()
        
        logger.info(f"Detected and configured for environment: {self._environment}, profile: {self._profile}")
    
    def add_common_environment_variable_mappings(self) -> None:
        """Add common environment variable mappings."""
        # Database
        self.add_environment_variable_mapping("DATABASE_URL", "database.url")
        self.add_environment_variable_mapping("DATABASE_POOL_SIZE", "database.pool_size")
        self.add_environment_variable_mapping("DATABASE_MAX_OVERFLOW", "database.max_overflow")
        
        # Logging
        self.add_environment_variable_mapping("LOG_LEVEL", "logging.level")
        self.add_environment_variable_mapping("LOG_FILE", "logging.file")
        
        # Security
        self.add_environment_variable_mapping("SECRET_KEY", "security.secret_key")
        self.add_environment_variable_mapping("TOKEN_EXPIRATION", "security.token_expiration")
        
        # Services
        self.add_environment_variable_mapping("AUTH_SERVICE_HOST", "services.auth.host")
        self.add_environment_variable_mapping("AUTH_SERVICE_PORT", "services.auth.port")
        self.add_environment_variable_mapping("STRATEGY_SERVICE_HOST", "services.strategy.host")
        self.add_environment_variable_mapping("STRATEGY_SERVICE_PORT", "services.strategy.port")
        self.add_environment_variable_mapping("DATA_SERVICE_HOST", "services.data.host")
        self.add_environment_variable_mapping("DATA_SERVICE_PORT", "services.data.port")
        self.add_environment_variable_mapping("TRADE_SERVICE_HOST", "services.trade.host")
        self.add_environment_variable_mapping("TRADE_SERVICE_PORT", "services.trade.port")
        self.add_environment_variable_mapping("BACKTEST_SERVICE_HOST", "services.backtest.host")
        self.add_environment_variable_mapping("BACKTEST_SERVICE_PORT", "services.backtest.port")
        
        # Management API
        self.add_environment_variable_mapping("MANAGEMENT_API_ENABLED", "management_api.enabled")
        self.add_environment_variable_mapping("MANAGEMENT_API_HOST", "management_api.host")
        self.add_environment_variable_mapping("MANAGEMENT_API_PORT", "management_api.port")
        
        logger.info("Added common environment variable mappings")