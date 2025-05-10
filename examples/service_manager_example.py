#!/usr/bin/env python
"""
Example script demonstrating how to use the Service Manager and Configuration Management System.

This script shows how to:
1. Initialize the Configuration Manager
2. Load and validate configuration
3. Initialize the Service Manager
4. Register and start services
5. Monitor service health
6. Stop services
"""

import os
import sys
import time
import logging
import signal
import json

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import core components
from core.service_manager.manager import ServiceManager
from core.config_manager.manager import ConfigManager
from core.config_manager.config_validator import ConfigValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("example")

def main():
    """Main function"""
    logger.info("Starting Service Manager Example")
    
    # Initialize Configuration Manager
    try:
        # Use the default configuration directory
        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config'))
        config_manager = ConfigManager(config_dir)
        
        # Load configuration schema
        schema_path = os.path.join(config_dir, 'cryptobot_config_schema.json')
        if os.path.exists(schema_path):
            config_manager.add_config_schema_from_file('schema', schema_path)
            logger.info("Loaded configuration schema")
        
        # Initialize the configuration manager
        config_manager.initialize()
        
        # Set environment and profile
        config_manager.set_environment('dev')
        config_manager.set_profile('default')
        
        # Get the merged configuration
        config = config_manager.get_config()
        
        # Validate the configuration
        if 'schema' in config_manager._config_validator._schemas:
            result = config_manager.validate_config(config, 'schema')
            if not result['valid']:
                logger.error(f"Invalid configuration: {result['errors']}")
                return 1
            logger.info("Configuration validated successfully")
        
        # Store a secret
        config_manager.store_secret('api_key', 'your-api-key-here', 'example')
        logger.info("Stored API key secret")
        
        # Retrieve the secret
        api_key = config_manager.get_secret('api_key', 'example')
        logger.info(f"Retrieved API key: {api_key}")
    except Exception as e:
        logger.error(f"Error initializing Configuration Manager: {e}")
        return 1
    
    # Initialize Service Manager
    try:
        service_manager = ServiceManager(config)
        
        # Register signal handlers
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received, stopping services...")
            service_manager.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the Service Manager
        service_manager.start()
        logger.info("Service Manager started")
        
        # Get components
        registry = service_manager.get_registry()
        lifecycle_controller = service_manager.get_lifecycle_controller()
        health_monitor = service_manager.get_health_monitor()
        resource_manager = service_manager.get_resource_manager()
        
        # Register a custom service
        registry.register_service(
            name="example",
            description="Example service",
            dependencies=set(["auth"]),
            config={
                "enabled": True,
                "host": "localhost",
                "port": 8100
            }
        )
        logger.info("Registered example service")
        
        # Start the auth service (dependency of example service)
        if lifecycle_controller.start_service("auth"):
            logger.info("Auth service started")
        else:
            logger.error("Failed to start auth service")
            service_manager.stop()
            return 1
        
        # Start the example service
        if lifecycle_controller.start_service("example"):
            logger.info("Example service started")
        else:
            logger.error("Failed to start example service")
            service_manager.stop()
            return 1
        
        # Check service health
        time.sleep(2)  # Wait for services to initialize
        
        auth_health = health_monitor.check_service_health("auth")
        logger.info(f"Auth service health: {'Healthy' if auth_health.status else 'Unhealthy'}")
        
        example_health = health_monitor.check_service_health("example")
        logger.info(f"Example service health: {'Healthy' if example_health.status else 'Unhealthy'}")
        
        # Check resource usage
        auth_resources = resource_manager.get_service_resource_usage("auth")
        if auth_resources:
            logger.info(f"Auth service CPU usage: {auth_resources.cpu_percent:.1f}%")
            logger.info(f"Auth service memory usage: {auth_resources.memory_percent:.1f}%")
        
        example_resources = resource_manager.get_service_resource_usage("example")
        if example_resources:
            logger.info(f"Example service CPU usage: {example_resources.cpu_percent:.1f}%")
            logger.info(f"Example service memory usage: {example_resources.memory_percent:.1f}%")
        
        # Run for a while
        logger.info("Services running. Press Ctrl+C to stop.")
        
        # Keep the main thread running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        
        # Stop services
        lifecycle_controller.stop_service("example")
        logger.info("Example service stopped")
        
        lifecycle_controller.stop_service("auth")
        logger.info("Auth service stopped")
        
        # Stop the Service Manager
        service_manager.stop()
        logger.info("Service Manager stopped")
        
        return 0
    except Exception as e:
        logger.error(f"Error in Service Manager: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())