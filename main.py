#!/usr/bin/env python
"""
Cryptobot Main Entry Point

This is the main entry point for the Cryptobot application.
It handles command-line arguments, service startup, and shutdown.
"""

import os
import sys
import argparse
import logging
import json
import signal
from typing import Dict, List, Optional, Any
import multiprocessing

# Import core components
from core.service_manager.manager import ServiceManager
from core.config_manager.manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("cryptobot.log")
    ]
)
logger = logging.getLogger("cryptobot")

def main():
    """Main function"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Cryptobot Trading System")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--dashboard", action="store_true", help="Run the dashboard")
    parser.add_argument("--cli", action="store_true", help="Run the command-line interface")
    parser.add_argument("--service", choices=["auth", "strategy", "data", "trade", "backtest"], 
                        help="Run a specific service")
    parser.add_argument("--all", action="store_true", help="Run all services")
    parser.add_argument("--config-ui", action="store_true", help="Run the configuration UI")
    parser.add_argument("--environment", choices=["dev", "test", "stage", "prod"], 
                        help="Set the environment")
    parser.add_argument("--profile", choices=["default", "docker", "kubernetes"], 
                        help="Set the profile")
    parser.add_argument("--version", action="store_true", help="Show version information")
    
    args = parser.parse_args()
    
    # Show version information
    if args.version:
        print("Cryptobot Trading System v1.0.0")
        return 0
    
    # Initialize Configuration Manager
    try:
        if args.config:
            config_manager = ConfigManager.from_config_file(args.config)
        else:
            config_manager = ConfigManager.create_default()
        
        # Set environment if specified
        if args.environment:
            config_manager.set_environment(args.environment)
        
        # Set profile if specified
        if args.profile:
            config_manager.set_profile(args.profile)
        
        # Get the merged configuration
        config = config_manager.get_config()
        
        # Configure logging
        log_level = getattr(logging, config["logging"]["level"].upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
        
        logger.info(f"Using environment: {config_manager.get_environment()}")
        logger.info(f"Using profile: {config_manager.get_profile()}")
    except Exception as e:
        logger.error(f"Error initializing Configuration Manager: {e}")
        return 1
    
    # Run the configuration UI if requested
    if args.config_ui:
        try:
            host = config.get("config_ui", {}).get("host", "0.0.0.0")
            port = config.get("config_ui", {}).get("port", 8081)
            config_manager.start_ui(host, port)
            logger.info(f"Configuration UI started on {host}:{port}")
            
            # Keep the main thread running
            try:
                signal.pause()
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received, shutting down...")
                config_manager.stop_ui()
            
            return 0
        except Exception as e:
            logger.error(f"Error starting Configuration UI: {e}")
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
    except Exception as e:
        logger.error(f"Error initializing Service Manager: {e}")
        return 1
    
    # Run the appropriate component
    if args.dashboard:
        try:
            # Start the Service Manager
            service_manager.start()
            
            # Run the dashboard
            from dashboard.main import app as dashboard_app
            
            # Configure Uvicorn
            host = config.get("dashboard", {}).get("host", "0.0.0.0")
            port = config.get("dashboard", {}).get("port", 8080)
            
            # Run the dashboard
            import uvicorn
            uvicorn.run(
                dashboard_app,
                host=host,
                port=port,
                log_level="info"
            )
            
            return 0
        except ImportError:
            logger.error("Dashboard module not found")
            return 1
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}")
            return 1
    elif args.cli:
        try:
            # Start the Service Manager
            service_manager.start()
            
            # Run the CLI
            from cli.main import run_cli as start_cli
            
            # Run the CLI
            start_cli(config, service_manager)
            
            return 0
        except ImportError:
            logger.error("CLI module not found")
            return 1
        except Exception as e:
            logger.error(f"Error starting CLI: {e}")
            return 1
    elif args.service:
        try:
            # Start the Service Manager
            service_manager.start()
            
            # Get the lifecycle controller
            lifecycle_controller = service_manager.get_lifecycle_controller()
            
            # Start the specified service
            if lifecycle_controller.start_service(args.service):
                logger.info(f"Service '{args.service}' started successfully")
                
                # Keep the main thread running
                try:
                    signal.pause()
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, shutting down...")
                    lifecycle_controller.stop_service(args.service)
                    service_manager.stop()
                
                return 0
            else:
                logger.error(f"Failed to start service '{args.service}'")
                service_manager.stop()
                return 1
        except Exception as e:
            logger.error(f"Error starting service '{args.service}': {e}")
            return 1
    elif args.all:
        try:
            # Start the Service Manager
            service_manager.start()
            
            # Get the lifecycle controller
            lifecycle_controller = service_manager.get_lifecycle_controller()
            
            # Start all services
            if lifecycle_controller.start_all_services():
                logger.info("All services started successfully")
                
                # Keep the main thread running
                try:
                    signal.pause()
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received, shutting down...")
                    service_manager.stop()
                
                return 0
            else:
                logger.error("Failed to start all services")
                service_manager.stop()
                return 1
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            return 1
    else:
        # No arguments provided, show help
        parser.print_help()
        return 0

if __name__ == "__main__":
    multiprocessing.freeze_support()  # Required for PyInstaller
    sys.exit(main())