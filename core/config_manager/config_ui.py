"""
Config UI for CryptoBot.

This module provides the ConfigUI class, which provides a web interface for configuration
management, a visual editor for configuration files, configuration templates for common
scenarios, configuration export/import, and configuration history and rollback.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import base64
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query, Path, Body, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import threading

from .config_store import ConfigStore
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)

# Pydantic models for API
class ConfigValue(BaseModel):
    """Configuration value for API requests."""
    value: Any


class ConfigTemplate(BaseModel):
    """Configuration template for API responses."""
    name: str
    description: str
    config: Dict[str, Any]


class ConfigHistoryEntry(BaseModel):
    """Configuration history entry for API responses."""
    timestamp: str
    config: Dict[str, Any]


class ConfigUI:
    """
    User interface for configuration management.
    
    The ConfigUI provides a web interface for configuration management, a visual editor
    for configuration files, configuration templates for common scenarios, configuration
    export/import, and configuration history and rollback.
    """
    
    def __init__(self, config_store: ConfigStore, config_validator: ConfigValidator):
        """
        Initialize the config UI.
        
        Args:
            config_store: Configuration store
            config_validator: Configuration validator
        """
        self._config_store = config_store
        self._config_validator = config_validator
        self._app = None
        self._thread = None
        self._running = False
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._change_handlers: List[Callable[[str, Any], None]] = []
        logger.info("Config UI initialized")
    
    def start(self, host: str = "0.0.0.0", port: int = 8081) -> None:
        """
        Start the config UI server.
        
        Args:
            host: Host address
            port: Port number
        """
        if self._running:
            logger.warning("Config UI is already running")
            return
        
        # Create FastAPI app
        self._app = FastAPI(
            title="CryptoBot Configuration UI",
            description="API for managing CryptoBot configuration",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Create router
        router = APIRouter()
        
        # Configuration endpoints
        @router.get("/config", response_model=Dict[str, Any], tags=["Configuration"])
        async def get_config():
            """Get the current configuration."""
            return self._config_store.get_config()
        
        @router.get("/config/default", response_model=Dict[str, Any], tags=["Configuration"])
        async def get_default_config():
            """Get the default configuration."""
            return self._config_store.get_default_config()
        
        @router.get("/config/user", response_model=Dict[str, Any], tags=["Configuration"])
        async def get_user_config():
            """Get the user configuration."""
            return self._config_store.get_user_config()
        
        @router.get("/config/environment", response_model=Dict[str, Any], tags=["Configuration"])
        async def get_environment_config():
            """Get the environment-specific configuration."""
            return self._config_store.get_environment_config()
        
        @router.get("/config/value/{key}", response_model=ConfigValue, tags=["Configuration"])
        async def get_config_value(key: str = Path(..., description="Configuration key")):
            """Get a configuration value."""
            value = self._config_store.get_config_value(key)
            if value is None:
                raise HTTPException(status_code=404, detail=f"Configuration key '{key}' not found")
            return ConfigValue(value=value)
        
        @router.put("/config/user/value/{key}", response_model=ConfigValue, tags=["Configuration"])
        async def set_user_config_value(
            key: str = Path(..., description="Configuration key"),
            config_value: ConfigValue = Body(..., description="Configuration value")
        ):
            """Set a user configuration value."""
            try:
                self._config_store.set_user_config_value(key, config_value.value)
                
                # Save the configuration
                self._config_store.save_user_config()
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler(key, config_value.value)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return ConfigValue(value=config_value.value)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.put("/config/environment/value/{key}", response_model=ConfigValue, tags=["Configuration"])
        async def set_environment_config_value(
            key: str = Path(..., description="Configuration key"),
            config_value: ConfigValue = Body(..., description="Configuration value")
        ):
            """Set an environment-specific configuration value."""
            try:
                self._config_store.set_environment_config_value(key, config_value.value)
                
                # Save the configuration
                self._config_store.save_environment_config("dev")  # TODO: Get environment from somewhere
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler(key, config_value.value)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return ConfigValue(value=config_value.value)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/config/user/reset", tags=["Configuration"])
        async def reset_user_config():
            """Reset the user configuration."""
            try:
                self._config_store.reset_user_config()
                
                # Save the configuration
                self._config_store.save_user_config()
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler("", None)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return {"message": "User configuration reset"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/config/environment/reset", tags=["Configuration"])
        async def reset_environment_config():
            """Reset the environment-specific configuration."""
            try:
                self._config_store.reset_environment_config()
                
                # Save the configuration
                self._config_store.save_environment_config("dev")  # TODO: Get environment from somewhere
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler("", None)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return {"message": "Environment configuration reset"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Template endpoints
        @router.get("/templates", response_model=List[ConfigTemplate], tags=["Templates"])
        async def get_templates():
            """Get all configuration templates."""
            return [
                ConfigTemplate(name=name, description=template["description"], config=template["config"])
                for name, template in self._templates.items()
            ]
        
        @router.get("/templates/{name}", response_model=ConfigTemplate, tags=["Templates"])
        async def get_template(name: str = Path(..., description="Template name")):
            """Get a configuration template."""
            if name not in self._templates:
                raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
            
            template = self._templates[name]
            return ConfigTemplate(name=name, description=template["description"], config=template["config"])
        
        @router.post("/templates/apply/{name}", response_model=Dict[str, Any], tags=["Templates"])
        async def apply_template(name: str = Path(..., description="Template name")):
            """Apply a configuration template."""
            if name not in self._templates:
                raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
            
            template = self._templates[name]
            
            try:
                # Apply template to user configuration
                for key, value in template["config"].items():
                    self._config_store.set_user_config_value(key, value)
                
                # Save the configuration
                self._config_store.save_user_config()
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler("", None)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return self._config_store.get_config()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # History endpoints
        @router.get("/history/user", response_model=List[ConfigHistoryEntry], tags=["History"])
        async def get_user_config_history(limit: int = Query(10, description="Maximum number of history entries")):
            """Get the user configuration history."""
            history = self._config_store.get_config_history("user", limit)
            return [ConfigHistoryEntry(timestamp=entry["timestamp"], config=entry["config"]) for entry in history]
        
        @router.get("/history/environment", response_model=List[ConfigHistoryEntry], tags=["History"])
        async def get_environment_config_history(limit: int = Query(10, description="Maximum number of history entries")):
            """Get the environment-specific configuration history."""
            history = self._config_store.get_config_history("env_dev", limit)  # TODO: Get environment from somewhere
            return [ConfigHistoryEntry(timestamp=entry["timestamp"], config=entry["config"]) for entry in history]
        
        @router.post("/history/user/restore/{timestamp}", response_model=Dict[str, Any], tags=["History"])
        async def restore_user_config(timestamp: str = Path(..., description="Timestamp of the configuration to restore")):
            """Restore the user configuration from history."""
            try:
                success = self._config_store.restore_config_from_history("user", timestamp)
                if not success:
                    raise HTTPException(status_code=404, detail=f"User configuration at timestamp '{timestamp}' not found")
                
                # Save the configuration
                self._config_store.save_user_config()
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler("", None)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return self._config_store.get_config()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/history/environment/restore/{timestamp}", response_model=Dict[str, Any], tags=["History"])
        async def restore_environment_config(timestamp: str = Path(..., description="Timestamp of the configuration to restore")):
            """Restore the environment-specific configuration from history."""
            try:
                success = self._config_store.restore_config_from_history("env_dev", timestamp)  # TODO: Get environment from somewhere
                if not success:
                    raise HTTPException(status_code=404, detail=f"Environment configuration at timestamp '{timestamp}' not found")
                
                # Save the configuration
                self._config_store.save_environment_config("dev")  # TODO: Get environment from somewhere
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler("", None)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return self._config_store.get_config()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Export/import endpoints
        @router.get("/export", tags=["Export/Import"])
        async def export_config():
            """Export the configuration."""
            try:
                config = self._config_store.get_config()
                
                # Convert to JSON
                config_json = json.dumps(config, indent=2)
                
                # Create a response with the configuration as a downloadable file
                return JSONResponse(
                    content=config,
                    headers={
                        "Content-Disposition": f"attachment; filename=cryptobot_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    }
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/import", response_model=Dict[str, Any], tags=["Export/Import"])
        async def import_config(file: UploadFile = File(...)):
            """Import a configuration."""
            try:
                # Read the file
                content = await file.read()
                
                # Parse the JSON
                config = json.loads(content)
                
                # Validate the configuration
                if "schema" in self._config_validator._schemas:
                    result = self._config_validator.validate_config(config, "schema")
                    if not result.valid:
                        raise HTTPException(status_code=400, detail=f"Invalid configuration: {result.errors}")
                
                # Apply the configuration to user configuration
                for key, value in config.items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            self._config_store.set_user_config_value(f"{key}.{subkey}", subvalue)
                    else:
                        self._config_store.set_user_config_value(key, value)
                
                # Save the configuration
                self._config_store.save_user_config()
                
                # Notify change handlers
                for handler in self._change_handlers:
                    try:
                        handler("", None)
                    except Exception as e:
                        logger.error(f"Error in configuration change handler: {e}")
                
                return self._config_store.get_config()
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON file")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Validation endpoints
        @router.post("/validate", response_model=Dict[str, Any], tags=["Validation"])
        async def validate_config(config: Dict[str, Any] = Body(..., description="Configuration to validate")):
            """Validate a configuration."""
            try:
                if "schema" in self._config_validator._schemas:
                    result = self._config_validator.validate_config(config, "schema")
                    return result.to_dict()
                else:
                    return {"valid": True, "errors": []}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        # Add router to app
        self._app.include_router(router, prefix="/api/v1/config")
        
        # Serve static files for the UI
        static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "config_ui")
        if os.path.exists(static_dir):
            self._app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        
        # Start server in a separate thread
        def run_server():
            uvicorn.run(self._app, host=host, port=port, log_level="info")
        
        self._thread = threading.Thread(target=run_server, daemon=True)
        self._thread.start()
        self._running = True
        
        logger.info(f"Config UI started on {host}:{port}")
    
    def stop(self) -> None:
        """Stop the config UI server."""
        if not self._running:
            logger.warning("Config UI is not running")
            return
        
        # There's no clean way to stop a running uvicorn server in a thread
        # We'll just set the flag and let the thread die when the application exits
        self._running = False
        logger.info("Config UI stopped")
    
    def add_template(self, name: str, description: str, config: Dict[str, Any]) -> None:
        """
        Add a configuration template.
        
        Args:
            name: Template name
            description: Template description
            config: Template configuration
        """
        self._templates[name] = {
            "description": description,
            "config": config
        }
        logger.info(f"Added configuration template '{name}'")
    
    def remove_template(self, name: str) -> None:
        """
        Remove a configuration template.
        
        Args:
            name: Template name
        """
        if name in self._templates:
            del self._templates[name]
            logger.info(f"Removed configuration template '{name}'")
    
    def add_change_handler(self, handler: Callable[[str, Any], None]) -> None:
        """
        Add a configuration change handler.
        
        Args:
            handler: Function that takes a key and a value
        """
        self._change_handlers.append(handler)
    
    def remove_change_handler(self, handler: Callable[[str, Any], None]) -> None:
        """
        Remove a configuration change handler.
        
        Args:
            handler: Handler to remove
        """
        if handler in self._change_handlers:
            self._change_handlers.remove(handler)
    
    def add_common_templates(self) -> None:
        """Add common configuration templates."""
        # Development template
        self.add_template(
            name="development",
            description="Development environment configuration",
            config={
                "services": {
                    "auth": {
                        "host": "localhost",
                        "port": 8000
                    },
                    "strategy": {
                        "host": "localhost",
                        "port": 8001
                    },
                    "data": {
                        "host": "localhost",
                        "port": 8002
                    },
                    "trade": {
                        "host": "localhost",
                        "port": 8003
                    },
                    "backtest": {
                        "host": "localhost",
                        "port": 8004
                    }
                },
                "database": {
                    "url": "sqlite:///cryptobot_dev.db"
                },
                "logging": {
                    "level": "DEBUG"
                },
                "management_api": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 8080
                }
            }
        )
        
        # Production template
        self.add_template(
            name="production",
            description="Production environment configuration",
            config={
                "services": {
                    "auth": {
                        "host": "0.0.0.0",
                        "port": 8000,
                        "workers": 4
                    },
                    "strategy": {
                        "host": "0.0.0.0",
                        "port": 8001,
                        "workers": 4
                    },
                    "data": {
                        "host": "0.0.0.0",
                        "port": 8002,
                        "workers": 4
                    },
                    "trade": {
                        "host": "0.0.0.0",
                        "port": 8003,
                        "workers": 4
                    },
                    "backtest": {
                        "host": "0.0.0.0",
                        "port": 8004,
                        "workers": 4
                    }
                },
                "database": {
                    "url": "sqlite:///cryptobot_prod.db",
                    "pool_size": 10,
                    "max_overflow": 20
                },
                "logging": {
                    "level": "INFO"
                },
                "management_api": {
                    "enabled": True,
                    "host": "0.0.0.0",
                    "port": 8080
                }
            }
        )
        
        # Minimal template
        self.add_template(
            name="minimal",
            description="Minimal configuration with only essential services",
            config={
                "services": {
                    "auth": {
                        "enabled": True,
                        "host": "localhost",
                        "port": 8000
                    },
                    "strategy": {
                        "enabled": False
                    },
                    "data": {
                        "enabled": True,
                        "host": "localhost",
                        "port": 8002
                    },
                    "trade": {
                        "enabled": False
                    },
                    "backtest": {
                        "enabled": False
                    }
                },
                "database": {
                    "url": "sqlite:///cryptobot_minimal.db"
                },
                "logging": {
                    "level": "INFO"
                },
                "management_api": {
                    "enabled": True,
                    "host": "localhost",
                    "port": 8080
                }
            }
        )
        
        logger.info("Added common configuration templates")