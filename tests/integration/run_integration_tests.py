#!/usr/bin/env python
"""
Integration Test Runner Script

This script runs integration tests for the cryptobot project.
It provides options for running specific tests, using Docker Compose,
and generating test reports.
"""

import os
import sys
import argparse
import logging
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.integration.framework.runner import IntegrationTestRunner
from tests.integration.framework.docker import DockerComposeManager
from tests.integration.framework.utils import setup_test_logging, Timer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run integration tests")
    
    # Test selection
    parser.add_argument(
        "--test", "-t",
        action="append",
        help="Specific test class to run (can be specified multiple times)"
    )
    parser.add_argument(
        "--method", "-m",
        help="Specific test method to run"
    )
    parser.add_argument(
        "--pattern", "-p",
        default="test_*.py",
        help="File pattern for test discovery"
    )
    
    # Environment options
    parser.add_argument(
        "--env", "-e",
        default="test",
        help="Test environment name"
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    
    # Docker options
    parser.add_argument(
        "--docker", "-d",
        action="store_true",
        help="Use Docker Compose for services"
    )
    parser.add_argument(
        "--compose-file",
        default="tests/integration/docker-compose.yml",
        help="Path to Docker Compose file"
    )
    parser.add_argument(
        "--services", "-s",
        action="append",
        help="Specific services to start (can be specified multiple times)"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--junit-xml",
        help="Path to JUnit XML report"
    )
    parser.add_argument(
        "--results",
        default="tests/integration/results.json",
        help="Path to results file"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate test report"
    )
    
    # Logging options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_test_logging(
        level=log_level,
        log_file=args.log_file,
        console=True
    )
    
    # Start timer
    timer = Timer("integration_tests")
    timer.start()
    
    # Create Docker Compose manager if requested
    docker_manager = None
    if args.docker:
        logger.info("Using Docker Compose for services")
        docker_manager = DockerComposeManager(
            project_name=f"cryptobot_test_{args.env}",
            compose_files=[args.compose_file]
        )
        
        # Start services
        try:
            docker_manager.start_services(
                services=args.services,
                wait_timeout=60,
                build=True
            )
        except Exception as e:
            logger.error(f"Failed to start Docker services: {e}")
            return 1
    
    try:
        # Create test runner
        runner = IntegrationTestRunner(
            test_dir="tests/integration",
            env_name=args.env,
            config_file=args.config
        )
        
        # Discover tests
        runner.discover_tests(pattern=args.pattern)
        
        # Run tests
        if args.test and args.method:
            # Run specific test method
            exit_code = runner.run_specific_test(
                args.test[0],
                args.method,
                args.verbose
            )
        else:
            # Run test classes
            exit_code, results = runner.run_tests(
                args.test,
                args.parallel,
                args.junit_xml,
                args.verbose
            )
            
            # Save results
            if args.results:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(args.results), exist_ok=True)
                
                with open(args.results, "w") as f:
                    json.dump(results, f, indent=2)
                
                logger.info(f"Saved test results to {args.results}")
                
                # Generate report
                if args.report:
                    runner.generate_test_report(args.results)
        
        # Stop timer
        elapsed = timer.stop()
        logger.info(f"Integration tests completed in {elapsed:.2f} seconds")
        
        return exit_code
    
    finally:
        # Clean up Docker services
        if docker_manager:
            logger.info("Stopping Docker services")
            docker_manager.stop_services()


if __name__ == "__main__":
    sys.exit(main())