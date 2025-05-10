"""
Config Store for CryptoBot.

This module provides the ConfigStore class, which is responsible for hierarchical
configuration storage, merging configurations from multiple sources, supporting default,
user, and environment-specific configs, file-based storage with SQLite backup, and
handling configuration versioning.
"""

import os
import json
import logging
import sqlite3
import copy
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)

class ConfigStore:
    """
    Store for configuration data.
    
    The ConfigStore is responsible for hierarchical configuration storage, merging
    configurations from multiple sources, supporting default, user, and environment-specific
    configs, file-based storage with SQLite backup, and handling configuration versioning.
    """
    
    def __init__(self, config_dir: str, app_name: str = "cryptobot"):
        """
        Initialize the config store.
        
        Args:
            config_dir: Directory for configuration files
            app_name: Application name
        """
        self._config_dir = config_dir
        self._app_name = app_name
        self._default_config: Dict[str, Any] = {}
        self._user_config: Dict[str, Any] = {}
        self._env_config: Dict[str, Any] = {}
        self._merged_config: Dict[str, Any] = {}
        self._db_path = os.path.join(config_dir, f"{app_name}_config.db")
        self._config_version = 1
        
        # Create config directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        logger.info("Config Store initialized")
    
    def load_default_config(self, config_path: Optional[str] = None) -> None:
        """
        Load default configuration.
        
        Args:
            config_path: Path to default configuration file, or None to use built-in defaults
        """
        if config_path and os.path.exists(config_path):
            # Load from file
            try:
                with open(config_path, "r") as f:
                    self._default_config = json.load(f)
                logger.info(f"Loaded default configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading default configuration from {config_path}: {e}")
                self._default_config = self._get_builtin_defaults()
        else:
            # Use built-in defaults
            self._default_config = self._get_builtin_defaults()
            logger.info("Using built-in default configuration")
        
        # Update merged config
        self._update_merged_config()
    
    def load_user_config(self, config_path: Optional[str] = None) -> None:
        """
        Load user configuration.
        
        Args:
            config_path: Path to user configuration file, or None to use default path
        """
        if config_path is None:
            config_path = os.path.join(self._config_dir, f"{self._app_name}_user_config.json")
        
        if os.path.exists(config_path):
            # Load from file
            try:
                with open(config_path, "r") as f:
                    self._user_config = json.load(f)
                logger.info(f"Loaded user configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading user configuration from {config_path}: {e}")
                self._user_config = {}
        else:
            # No user config
            self._user_config = {}
            logger.info("No user configuration found")
        
        # Update merged config
        self._update_merged_config()
    
    def load_environment_config(self, environment: str, config_path: Optional[str] = None) -> None:
        """
        Load environment-specific configuration.
        
        Args:
            environment: Environment name (e.g., "dev", "prod")
            config_path: Path to environment configuration file, or None to use default path
        """
        if config_path is None:
            config_path = os.path.join(self._config_dir, f"{self._app_name}_{environment}_config.json")
        
        if os.path.exists(config_path):
            # Load from file
            try:
                with open(config_path, "r") as f:
                    self._env_config = json.load(f)
                logger.info(f"Loaded {environment} configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading {environment} configuration from {config_path}: {e}")
                self._env_config = {}
        else:
            # No environment config
            self._env_config = {}
            logger.info(f"No {environment} configuration found")
        
        # Update merged config
        self._update_merged_config()
    
    def save_user_config(self, config_path: Optional[str] = None) -> None:
        """
        Save user configuration.
        
        Args:
            config_path: Path to user configuration file, or None to use default path
        """
        if config_path is None:
            config_path = os.path.join(self._config_dir, f"{self._app_name}_user_config.json")
        
        # Create backup
        if os.path.exists(config_path):
            backup_path = f"{config_path}.bak"
            try:
                shutil.copy2(config_path, backup_path)
                logger.info(f"Created backup of user configuration at {backup_path}")
            except Exception as e:
                logger.error(f"Error creating backup of user configuration: {e}")
        
        # Save to file
        try:
            with open(config_path, "w") as f:
                json.dump(self._user_config, f, indent=2)
            logger.info(f"Saved user configuration to {config_path}")
            
            # Save to database
            self._save_config_to_db("user", self._user_config)
        except Exception as e:
            logger.error(f"Error saving user configuration to {config_path}: {e}")
    
    def save_environment_config(self, environment: str, config_path: Optional[str] = None) -> None:
        """
        Save environment-specific configuration.
        
        Args:
            environment: Environment name (e.g., "dev", "prod")
            config_path: Path to environment configuration file, or None to use default path
        """
        if config_path is None:
            config_path = os.path.join(self._config_dir, f"{self._app_name}_{environment}_config.json")
        
        # Create backup
        if os.path.exists(config_path):
            backup_path = f"{config_path}.bak"
            try:
                shutil.copy2(config_path, backup_path)
                logger.info(f"Created backup of {environment} configuration at {backup_path}")
            except Exception as e:
                logger.error(f"Error creating backup of {environment} configuration: {e}")
        
        # Save to file
        try:
            with open(config_path, "w") as f:
                json.dump(self._env_config, f, indent=2)
            logger.info(f"Saved {environment} configuration to {config_path}")
            
            # Save to database
            self._save_config_to_db(f"env_{environment}", self._env_config)
        except Exception as e:
            logger.error(f"Error saving {environment} configuration to {config_path}: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the merged configuration.
        
        Returns:
            Dict[str, Any]: Merged configuration
        """
        return copy.deepcopy(self._merged_config)
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get the default configuration.
        
        Returns:
            Dict[str, Any]: Default configuration
        """
        return copy.deepcopy(self._default_config)
    
    def get_user_config(self) -> Dict[str, Any]:
        """
        Get the user configuration.
        
        Returns:
            Dict[str, Any]: User configuration
        """
        return copy.deepcopy(self._user_config)
    
    def get_environment_config(self) -> Dict[str, Any]:
        """
        Get the environment-specific configuration.
        
        Returns:
            Dict[str, Any]: Environment-specific configuration
        """
        return copy.deepcopy(self._env_config)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            default: Default value if key is not found
        
        Returns:
            Any: Configuration value
        """
        # Split key into parts
        parts = key.split(".")
        
        # Navigate through the config
        config = self._merged_config
        for part in parts:
            if isinstance(config, dict) and part in config:
                config = config[part]
            else:
                return default
        
        return config
    
    def set_user_config_value(self, key: str, value: Any) -> None:
        """
        Set a user configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            value: Configuration value
        """
        # Split key into parts
        parts = key.split(".")
        
        # Navigate through the config
        config = self._user_config
        for i, part in enumerate(parts[:-1]):
            if part not in config or not isinstance(config[part], dict):
                config[part] = {}
            config = config[part]
        
        # Set the value
        config[parts[-1]] = value
        
        # Update merged config
        self._update_merged_config()
    
    def set_environment_config_value(self, key: str, value: Any) -> None:
        """
        Set an environment-specific configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            value: Configuration value
        """
        # Split key into parts
        parts = key.split(".")
        
        # Navigate through the config
        config = self._env_config
        for i, part in enumerate(parts[:-1]):
            if part not in config or not isinstance(config[part], dict):
                config[part] = {}
            config = config[part]
        
        # Set the value
        config[parts[-1]] = value
        
        # Update merged config
        self._update_merged_config()
    
    def reset_user_config(self) -> None:
        """Reset the user configuration to an empty dictionary."""
        self._user_config = {}
        self._update_merged_config()
        logger.info("User configuration reset")
    
    def reset_environment_config(self) -> None:
        """Reset the environment-specific configuration to an empty dictionary."""
        self._env_config = {}
        self._update_merged_config()
        logger.info("Environment configuration reset")
    
    def get_config_history(self, config_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the configuration history.
        
        Args:
            config_type: Configuration type ("default", "user", or "env_*")
            limit: Maximum number of history entries to return
        
        Returns:
            List[Dict[str, Any]]: List of history entries
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT timestamp, config FROM config_history WHERE type = ? ORDER BY timestamp DESC LIMIT ?",
                (config_type, limit)
            )
            
            result = []
            for timestamp, config_json in cursor.fetchall():
                result.append({
                    "timestamp": timestamp,
                    "config": json.loads(config_json)
                })
            
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error getting configuration history: {e}")
            return []
    
    def restore_config_from_history(self, config_type: str, timestamp: str) -> bool:
        """
        Restore configuration from history.
        
        Args:
            config_type: Configuration type ("default", "user", or "env_*")
            timestamp: Timestamp of the configuration to restore
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT config FROM config_history WHERE type = ? AND timestamp = ?",
                (config_type, timestamp)
            )
            
            row = cursor.fetchone()
            conn.close()
            
            if row is None:
                logger.error(f"No configuration found for type {config_type} at timestamp {timestamp}")
                return False
            
            config_json = row[0]
            config = json.loads(config_json)
            
            if config_type == "user":
                self._user_config = config
            elif config_type.startswith("env_"):
                self._env_config = config
            else:
                logger.error(f"Cannot restore configuration of type {config_type}")
                return False
            
            # Update merged config
            self._update_merged_config()
            
            logger.info(f"Restored {config_type} configuration from {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Error restoring configuration from history: {e}")
            return False
    
    def _update_merged_config(self) -> None:
        """Update the merged configuration."""
        # Start with default config
        self._merged_config = copy.deepcopy(self._default_config)
        
        # Merge user config
        self._deep_merge(self._merged_config, self._user_config)
        
        # Merge environment config
        self._deep_merge(self._merged_config, self._env_config)
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Deep merge two dictionaries.
        
        Args:
            target: Target dictionary
            source: Source dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # Recursively merge dictionaries
                self._deep_merge(target[key], value)
            else:
                # Replace or add value
                target[key] = copy.deepcopy(value)
    
    def _init_db(self) -> None:
        """Initialize the database."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    config TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            
            # Set version if not exists
            cursor.execute("SELECT value FROM config_metadata WHERE key = 'version'")
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "INSERT INTO config_metadata (key, value) VALUES (?, ?)",
                    ("version", str(self._config_version))
                )
            
            conn.commit()
            conn.close()
            
            logger.info("Config database initialized")
        except Exception as e:
            logger.error(f"Error initializing config database: {e}")
    
    def _save_config_to_db(self, config_type: str, config: Dict[str, Any]) -> None:
        """
        Save configuration to database.
        
        Args:
            config_type: Configuration type ("default", "user", or "env_*")
            config: Configuration dictionary
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            
            # Save to history
            timestamp = datetime.now().isoformat()
            config_json = json.dumps(config)
            
            cursor.execute(
                "INSERT INTO config_history (type, timestamp, config) VALUES (?, ?, ?)",
                (config_type, timestamp, config_json)
            )
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Saved {config_type} configuration to database")
        except Exception as e:
            logger.error(f"Error saving configuration to database: {e}")
    
    def _get_builtin_defaults(self) -> Dict[str, Any]:
        """
        Get built-in default configuration.
        
        Returns:
            Dict[str, Any]: Default configuration
        """
        return {
            "services": {
                "auth": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8000,
                    "workers": 1,
                    "description": "Authentication service",
                    "dependencies": []
                },
                "strategy": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8001,
                    "workers": 1,
                    "description": "Strategy management service",
                    "dependencies": ["auth"]
                },
                "data": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8002,
                    "workers": 1,
                    "description": "Market data service",
                    "dependencies": ["auth"]
                },
                "trade": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8003,
                    "workers": 1,
                    "description": "Trade execution service",
                    "dependencies": ["auth", "strategy", "data"]
                },
                "backtest": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8004,
                    "workers": 1,
                    "description": "Backtesting service",
                    "dependencies": ["auth", "strategy", "data"]
                }
            },
            "database": {
                "url": "sqlite:///cryptobot.db",
                "pool_size": 5,
                "max_overflow": 10,
                "echo": False
            },
            "logging": {
                "level": "INFO",
                "file": "cryptobot.log",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "security": {
                "secret_key": "",
                "token_expiration": 3600,
                "password_hash_algorithm": "argon2",
                "argon2_time_cost": 3,
                "argon2_memory_cost": 65536,
                "argon2_parallelism": 4
            },
            "management_api": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8080
            },
            "auto_start": True,
            "health_check": {
                "interval": 30,
                "auto_restart": True,
                "max_restart_attempts": 3,
                "restart_cooldown": 300
            },
            "resource_limits": {
                "enabled": True,
                "check_interval": 30
            }
        }