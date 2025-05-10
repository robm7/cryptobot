"""
Configuration Manager for CryptoBot.

This module provides the ConfigManager class, which is the central component
responsible for managing configuration in the CryptoBot application.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Callable

from .config_store import ConfigStore
from .environment_handler import EnvironmentHandler
from .secret_manager import SecretManager
from .config_validator import ConfigValidator
from .config_ui import ConfigUI

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manager for CryptoBot configuration.
    
    The ConfigManager is the central component responsible for managing configuration
    in the CryptoBot application. It integrates the Config Store, Environment Handler,
    Secret Manager, Config Validator, and Config UI.
    """
    
    def __init__(self, config_dir: str, app_name: str = "cryptobot"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory for configuration files
            app_name: Application name
        """
        self._config_dir = config_dir
        self._app_name = app_name
        
        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Initialize components
        self._config_store = ConfigStore(config_dir, app_name)
        self._environment_handler = EnvironmentHandler(self._config_store)
        self._secret_manager = SecretManager(config_dir, app_name)
        self._config_validator = ConfigValidator()
        self._config_ui = ConfigUI(self._config_store, self._config_validator)
        
        # Load default configuration
        self._load_default_config()
        
        # Add common environment variable mappings
        self._environment_handler.add_common_environment_variable_mappings()
        
        # Add common configuration templates
        self._config_ui.add_common_templates()
        
        # Add configuration change handler
        self._config_ui.add_change_handler(self._on_config_changed)
        
        logger.info("Configuration Manager initialized")
    
    def initialize(self) -> None:
        """Initialize the configuration manager."""
        # Detect and configure environment
        self._environment_handler.detect_and_configure()
        
        # Load user configuration
        self._config_store.load_user_config()
        
        # Load environment-specific configuration
        environment = self._environment_handler.get_environment()
        self._config_store.load_environment_config(environment)
        
        # Load environment variables
        self._environment_handler.load_environment_variables()
        
        logger.info("Configuration Manager initialized")
    
    def start_ui(self, host: str = "0.0.0.0", port: int = 8081) -> None:
        """
        Start the configuration UI.
        
        Args:
            host: Host address
            port: Port number
        """
        self._config_ui.start(host, port)
    
    def stop_ui(self) -> None:
        """Stop the configuration UI."""
        self._config_ui.stop()
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the merged configuration.
        
        Returns:
            Dict[str, Any]: Merged configuration
        """
        return self._config_store.get_config()
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            default: Default value if key is not found
        
        Returns:
            Any: Configuration value
        """
        return self._config_store.get_config_value(key, default)
    
    def set_user_config_value(self, key: str, value: Any) -> None:
        """
        Set a user configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            value: Configuration value
        """
        self._config_store.set_user_config_value(key, value)
        self._config_store.save_user_config()
    
    def set_environment_config_value(self, key: str, value: Any) -> None:
        """
        Set an environment-specific configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            value: Configuration value
        """
        self._config_store.set_environment_config_value(key, value)
        environment = self._environment_handler.get_environment()
        self._config_store.save_environment_config(environment)
    
    def get_environment(self) -> str:
        """
        Get the current environment.
        
        Returns:
            str: Environment name
        """
        return self._environment_handler.get_environment()
    
    def set_environment(self, environment: str) -> None:
        """
        Set the current environment.
        
        Args:
            environment: Environment name (e.g., "dev", "prod")
        """
        self._environment_handler.set_environment(environment)
    
    def get_profile(self) -> str:
        """
        Get the current profile.
        
        Returns:
            str: Profile name
        """
        return self._environment_handler.get_profile()
    
    def set_profile(self, profile: str) -> None:
        """
        Set the current profile.
        
        Args:
            profile: Profile name (e.g., "default", "docker", "kubernetes")
        """
        self._environment_handler.set_profile(profile)
    
    def get_secret(self, name: str, service: Optional[str] = None) -> Optional[str]:
        """
        Get a secret.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            Optional[str]: Secret value, or None if not found
        """
        return self._secret_manager.get_secret(name, service)
    
    def store_secret(self, name: str, value: str, service: Optional[str] = None,
                    use_keyring: bool = False, expires_in_days: Optional[int] = None) -> None:
        """
        Store a secret.
        
        Args:
            name: Secret name
            value: Secret value
            service: Service that owns the secret
            use_keyring: Whether to use the system keyring
            expires_in_days: Number of days until the secret expires
        """
        self._secret_manager.store_secret(name, value, service, use_keyring, expires_in_days)
    
    def delete_secret(self, name: str, service: Optional[str] = None) -> bool:
        """
        Delete a secret.
        
        Args:
            name: Secret name
            service: Service that owns the secret
        
        Returns:
            bool: True if the secret was deleted, False otherwise
        """
        return self._secret_manager.delete_secret(name, service)
    
    def validate_config(self, config: Dict[str, Any], schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a configuration.
        
        Args:
            config: Configuration to validate
            schema_name: Name of the schema to use, or None to skip schema validation
        
        Returns:
            Dict[str, Any]: Validation result
        """
        result = self._config_validator.validate_config(config, schema_name)
        return result.to_dict()
    
    def add_config_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """
        Add a JSON schema for validation.
        
        Args:
            name: Schema name
            schema: JSON schema
        """
        self._config_validator.add_schema(name, schema)
    
    def add_config_schema_from_file(self, name: str, file_path: str) -> None:
        """
        Add a JSON schema from a file.
        
        Args:
            name: Schema name
            file_path: Path to the schema file
        """
        self._config_validator.add_schema_from_file(name, file_path)
    
    def add_config_template(self, name: str, description: str, config: Dict[str, Any]) -> None:
        """
        Add a configuration template.
        
        Args:
            name: Template name
            description: Template description
            config: Template configuration
        """
        self._config_ui.add_template(name, description, config)
    
    def add_environment_variable_mapping(self, env_var: str, config_key: str) -> None:
        """
        Add a mapping from an environment variable to a configuration key.
        
        Args:
            env_var: Environment variable name
            config_key: Configuration key (dot-separated for nested keys)
        """
        self._environment_handler.add_environment_variable_mapping(env_var, config_key)
    
    def _load_default_config(self) -> None:
        """Load default configuration."""
        default_config_path = os.path.join(self._config_dir, f"{self._app_name}_default_config.json")
        
        if os.path.exists(default_config_path):
            self._config_store.load_default_config(default_config_path)
        else:
            self._config_store.load_default_config()
    
    def _on_config_changed(self, key: str, value: Any) -> None:
        """
        Handle configuration changes.
        
        Args:
            key: Configuration key
            value: New value
        """
        logger.info(f"Configuration changed: {key}")
        
        # Reload configuration
        self._config_store.load_user_config()
        environment = self._environment_handler.get_environment()
        self._config_store.load_environment_config(environment)
    
    @classmethod
    def create_default(cls) -> 'ConfigManager':
        """
        Create a configuration manager with default settings.
        
        Returns:
            ConfigManager: Configuration manager
        """
        # Get default config directory
        config_dir = os.path.join(os.path.expanduser("~"), ".cryptobot", "config")
        
        # Create config manager
        manager = cls(config_dir)
        
        # Initialize
        manager.initialize()
        
        return manager
    
    @classmethod
    def from_config_file(cls, config_path: str) -> 'ConfigManager':
        """
        Create a configuration manager from a configuration file.
        
        Args:
            config_path: Path to the configuration file
        
        Returns:
            ConfigManager: Configuration manager
        
        Raises:
            FileNotFoundError: If the configuration file does not exist
            json.JSONDecodeError: If the configuration file is not valid JSON
        """
        # Check if the file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found")
        
        # Load the configuration
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Get config directory
        config_dir = config.get("config_dir", os.path.join(os.path.expanduser("~"), ".cryptobot", "config"))
        
        # Create config manager
        manager = cls(config_dir)
        
        # Initialize
        manager.initialize()
        
        return manager