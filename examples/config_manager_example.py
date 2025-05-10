#!/usr/bin/env python
"""
Example script demonstrating how to use the Configuration Management System.

This script shows how to:
1. Initialize the Configuration Manager
2. Load and validate configuration
3. Access and modify configuration values
4. Handle environment-specific configuration
5. Manage secrets
6. Use the configuration UI
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
    logger.info("Starting Configuration Manager Example")
    
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
        
        # Get information about the detected environment
        environment_info = config_manager._environment_handler.get_detected_environment()
        logger.info(f"Detected environment: {environment_info['environment_type']}")
        logger.info(f"Operating system: {environment_info['os']['system']} {environment_info['os']['release']}")
        logger.info(f"Python version: {environment_info['python']['version']}")
        
        # Set environment and profile
        config_manager.set_environment('dev')
        config_manager.set_profile('default')
        logger.info(f"Using environment: {config_manager.get_environment()}")
        logger.info(f"Using profile: {config_manager.get_profile()}")
        
        # Get the merged configuration
        config = config_manager.get_config()
        
        # Validate the configuration
        if 'schema' in config_manager._config_validator._schemas:
            result = config_manager.validate_config(config, 'schema')
            if not result['valid']:
                logger.error(f"Invalid configuration: {result['errors']}")
                return 1
            logger.info("Configuration validated successfully")
        
        # Access configuration values
        database_url = config_manager.get_config_value('database.url')
        logger.info(f"Database URL: {database_url}")
        
        log_level = config_manager.get_config_value('logging.level')
        logger.info(f"Log level: {log_level}")
        
        auth_service_port = config_manager.get_config_value('services.auth.port')
        logger.info(f"Auth service port: {auth_service_port}")
        
        # Modify configuration values
        config_manager.set_user_config_value('logging.level', 'DEBUG')
        logger.info(f"Updated log level to: {config_manager.get_config_value('logging.level')}")
        
        config_manager.set_user_config_value('services.auth.port', 9000)
        logger.info(f"Updated auth service port to: {config_manager.get_config_value('services.auth.port')}")
        
        # Add environment variable mapping
        config_manager.add_environment_variable_mapping('LOG_LEVEL', 'logging.level')
        logger.info("Added environment variable mapping for LOG_LEVEL")
        
        # Store secrets
        config_manager.store_secret('api_key', 'your-api-key-here', 'example')
        logger.info("Stored API key secret")
        
        config_manager.store_secret('database_password', 'your-password-here', 'database')
        logger.info("Stored database password secret")
        
        # Retrieve secrets
        api_key = config_manager.get_secret('api_key', 'example')
        logger.info(f"Retrieved API key: {api_key}")
        
        db_password = config_manager.get_secret('database_password', 'database')
        logger.info(f"Retrieved database password: {db_password}")
        
        # List secrets
        secrets = config_manager._secret_manager.list_secrets()
        logger.info(f"Stored secrets: {[secret['name'] for secret in secrets]}")
        
        # Start the configuration UI
        start_ui = False  # Set to True to start the UI
        if start_ui:
            logger.info("Starting configuration UI...")
            config_manager.start_ui('localhost', 8081)
            
            # Register signal handlers
            def signal_handler(sig, frame):
                logger.info("Shutdown signal received, stopping UI...")
                config_manager.stop_ui()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Keep the main thread running
            try:
                logger.info("Configuration UI running at http://localhost:8081")
                logger.info("Press Ctrl+C to stop.")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                config_manager.stop_ui()
        
        logger.info("Configuration Manager Example completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Error in Configuration Manager: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())