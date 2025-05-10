"""
Configuration schema for CryptoBot.

This module defines the JSON schema for the CryptoBot configuration.
"""

import os
import json
from typing import Dict, Any

from ..update_manager.config_schema import UPDATE_MANAGER_SCHEMA

# Base schema for the CryptoBot configuration
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "version": {
            "type": "string",
            "description": "CryptoBot version"
        },
        "environment": {
            "type": "string",
            "enum": ["dev", "test", "stage", "prod"],
            "description": "Environment (dev, test, stage, prod)"
        },
        "profile": {
            "type": "string",
            "enum": ["default", "docker", "kubernetes"],
            "description": "Profile (default, docker, kubernetes)"
        },
        "log_level": {
            "type": "string",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "description": "Log level"
        },
        "log_file": {
            "type": "string",
            "description": "Log file path"
        },
        "data_dir": {
            "type": "string",
            "description": "Data directory path"
        },
        "config_dir": {
            "type": "string",
            "description": "Configuration directory path"
        },
        "database": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["sqlite", "postgresql", "mysql"],
                    "description": "Database type"
                },
                "connection_string": {
                    "type": "string",
                    "description": "Database connection string"
                },
                "pool_size": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Database connection pool size"
                },
                "max_overflow": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Maximum number of connections to overflow"
                },
                "pool_recycle": {
                    "type": "integer",
                    "minimum": -1,
                    "description": "Number of seconds after which a connection is recycled"
                },
                "pool_timeout": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of seconds to wait before giving up on getting a connection from the pool"
                }
            },
            "required": ["type", "connection_string"],
            "additionalProperties": False
        },
        "services": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether the service is enabled"
                    },
                    "description": {
                        "type": "string",
                        "description": "Service description"
                    },
                    "dependencies": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Service dependencies"
                    },
                    "optional_dependencies": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional service dependencies"
                    },
                    "host": {
                        "type": "string",
                        "description": "Service host"
                    },
                    "port": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 65535,
                        "description": "Service port"
                    },
                    "resource_limits": {
                        "type": "object",
                        "properties": {
                            "cpu_percent": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                                "description": "Maximum CPU usage percentage"
                            },
                            "memory_percent": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                                "description": "Maximum memory usage percentage"
                            },
                            "memory_bytes": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "Maximum memory usage in bytes"
                            },
                            "num_threads": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "Maximum number of threads"
                            },
                            "num_connections": {
                                "type": "integer",
                                "minimum": 0,
                                "description": "Maximum number of connections"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "additionalProperties": True
            },
            "description": "Service configuration"
        },
        "management_api": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Whether the management API is enabled"
                },
                "host": {
                    "type": "string",
                    "description": "Management API host"
                },
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535,
                    "description": "Management API port"
                },
                "auth": {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether authentication is enabled"
                        },
                        "username": {
                            "type": "string",
                            "description": "Authentication username"
                        },
                        "password": {
                            "type": "string",
                            "description": "Authentication password"
                        }
                    },
                    "required": ["enabled"],
                    "additionalProperties": False
                }
            },
            "required": ["enabled"],
            "additionalProperties": False
        },
        "auto_start": {
            "type": "boolean",
            "description": "Whether to automatically start services"
        }
    },
    "required": ["version", "environment", "profile"],
    "additionalProperties": True
}

# Merge the update manager schema into the main schema
CONFIG_SCHEMA["properties"].update(UPDATE_MANAGER_SCHEMA["properties"])

# Default configuration
DEFAULT_CONFIG = {
    "version": "1.0.0",
    "environment": "dev",
    "profile": "default",
    "log_level": "INFO",
    "log_file": "cryptobot.log",
    "data_dir": "data",
    "config_dir": "config",
    "database": {
        "type": "sqlite",
        "connection_string": "sqlite:///cryptobot.db",
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 3600,
        "pool_timeout": 30
    },
    "services": {
        "auth": {
            "enabled": True,
            "description": "Authentication Service",
            "dependencies": [],
            "host": "0.0.0.0",
            "port": 8000
        },
        "strategy": {
            "enabled": True,
            "description": "Strategy Service",
            "dependencies": ["auth"],
            "host": "0.0.0.0",
            "port": 8001
        },
        "data": {
            "enabled": True,
            "description": "Data Service",
            "dependencies": ["auth"],
            "host": "0.0.0.0",
            "port": 8002
        },
        "trade": {
            "enabled": True,
            "description": "Trade Service",
            "dependencies": ["auth", "strategy", "data"],
            "host": "0.0.0.0",
            "port": 8003
        },
        "backtest": {
            "enabled": True,
            "description": "Backtest Service",
            "dependencies": ["auth", "strategy", "data"],
            "host": "0.0.0.0",
            "port": 8004
        },
        "dashboard": {
            "enabled": True,
            "description": "Dashboard",
            "dependencies": ["auth", "strategy", "data", "trade"],
            "host": "0.0.0.0",
            "port": 8080
        }
    },
    "management_api": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8081,
        "auth": {
            "enabled": True,
            "username": "admin",
            "password": "admin"
        }
    },
    "auto_start": True,
    "update": {
        "update_url": "https://api.cryptobot.com/updates",
        "check_interval": 86400,  # Once per day
        "auto_check": True,
        "auto_download": False,
        "auto_install": False,
        "notify_only": False,
        "channels": {
            "stable": True,
            "beta": False,
            "alpha": False
        },
        "components": {
            "core": {
                "enabled": True,
                "auto_update": True,
                "version": "1.0.0"
            }
        },
        "proxy": {
            "enabled": False,
            "url": "",
            "username": "",
            "password": ""
        },
        "backup": {
            "enabled": True,
            "max_backups": 5,
            "backup_dir": ""
        }
    }
}


def load_schema_from_file(file_path: str) -> Dict[str, Any]:
    """
    Load a JSON schema from a file.
    
    Args:
        file_path: Path to the schema file
    
    Returns:
        Dict[str, Any]: JSON schema
    
    Raises:
        FileNotFoundError: If the schema file does not exist
        json.JSONDecodeError: If the schema file is not valid JSON
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Schema file '{file_path}' not found")
    
    with open(file_path, "r") as f:
        schema = json.load(f)
    
    return schema


def save_schema_to_file(schema: Dict[str, Any], file_path: str) -> None:
    """
    Save a JSON schema to a file.
    
    Args:
        schema: JSON schema
        file_path: Path to save the schema to
    """
    with open(file_path, "w") as f:
        json.dump(schema, f, indent=2)