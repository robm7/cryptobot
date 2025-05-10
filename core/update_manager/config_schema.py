"""
Configuration schema for the Update Manager.

This module defines the JSON schema for the Update Manager configuration.
"""

UPDATE_MANAGER_SCHEMA = {
    "type": "object",
    "properties": {
        "update": {
            "type": "object",
            "properties": {
                "update_url": {
                    "type": "string",
                    "format": "uri",
                    "description": "URL for checking and downloading updates"
                },
                "check_interval": {
                    "type": "integer",
                    "minimum": 3600,  # Minimum 1 hour
                    "description": "Interval in seconds between update checks"
                },
                "auto_check": {
                    "type": "boolean",
                    "description": "Whether to check for updates automatically"
                },
                "auto_download": {
                    "type": "boolean",
                    "description": "Whether to download updates automatically"
                },
                "auto_install": {
                    "type": "boolean",
                    "description": "Whether to install updates automatically"
                },
                "notify_only": {
                    "type": "boolean",
                    "description": "Whether to only notify about updates without downloading or installing"
                },
                "channels": {
                    "type": "object",
                    "properties": {
                        "stable": {
                            "type": "boolean",
                            "description": "Whether to check for stable updates"
                        },
                        "beta": {
                            "type": "boolean",
                            "description": "Whether to check for beta updates"
                        },
                        "alpha": {
                            "type": "boolean",
                            "description": "Whether to check for alpha updates"
                        }
                    }
                },
                "components": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "enabled": {
                                "type": "boolean",
                                "description": "Whether to update this component"
                            },
                            "auto_update": {
                                "type": "boolean",
                                "description": "Whether to update this component automatically"
                            },
                            "version": {
                                "type": "string",
                                "description": "Current version of the component"
                            }
                        }
                    },
                    "description": "Configuration for individual components"
                },
                "proxy": {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether to use a proxy for updates"
                        },
                        "url": {
                            "type": "string",
                            "format": "uri",
                            "description": "Proxy URL"
                        },
                        "username": {
                            "type": "string",
                            "description": "Proxy username"
                        },
                        "password": {
                            "type": "string",
                            "description": "Proxy password"
                        }
                    }
                },
                "backup": {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether to create backups before updating"
                        },
                        "max_backups": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Maximum number of backups to keep"
                        },
                        "backup_dir": {
                            "type": "string",
                            "description": "Directory for storing backups"
                        }
                    }
                }
            },
            "required": ["update_url", "check_interval", "auto_check"],
            "additionalProperties": False
        }
    }
}

DEFAULT_UPDATE_CONFIG = {
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