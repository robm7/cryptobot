"""
Integration Test Runner

This module provides utilities for running integration tests with proper
setup and teardown of test environments.
"""

import os
import sys
import logging
import argparse
import importlib
import inspect
import pytest
import time
import json
import traceback
from typing import Dict, Any, Optional, List, Type, Set, Tuple
from pathlib import Path

from tests.integration.framework.base import IntegrationTestBase
from tests.integration.framework.environment import TestEnvironmentManager

logger = logging.getLogger("integration_tests")


class IntegrationTestRunner:
    """
    Runner for integration tests.
    
    Provides utilities for discovering, setting up, and running integration tests.
    """
    
    def __init__(
        self,
        test_dir: str = "tests/integration",
        env_name: str = "test",
        config_file: Optional[str] = None
    ):
        self.test_dir = test_dir
        self.env_name = env_name
        self.config_file = config_file
        self.env_manager = TestEnvironmentManager(env_name)
        self.test_classes: Dict[str, Type[IntegrationTestBase]] = {}
        
        # Set up environment variables
        os.environ["TEST_ENV"] = env_name
        
        logger.info(f"Initialized IntegrationTestRunner for {env_name}")
    
    def discover_tests(self, pattern: str = "test_*.py") -> Dict[str, Type[IntegrationTestBase]]:
        """
        Discover integration test classes.
        
        Args:
            pattern: File pattern for test files
            
        Returns:
            Dictionary of test class names to test classes
        """
        test_dir_path = Path(self.test_dir)
        if not test_dir_path.exists():
            raise FileNotFoundError(f"Test directory not found: {self.test_dir}")
        
        # Find test files
        test_files = list(test_dir_path.glob(pattern))
        logger.info(f"Found {len(test_files)} test files in {self.test_dir}")
        
        # Import test modules and find test classes
        for test_file in test_files:
            # Skip __init__.py and framework files
            if test_file.name == "__init__.py" or "framework" in str(test_file):
                continue
            
            # Convert file path to module path
            rel_path = test_file.relative_to(Path.cwd())
            module_path = str(rel_path).replace(os.path.sep, ".")[:-3]  # Remove .py
            
            try:
                # Import module
                module = importlib.import_module(module_path)
                
                # Find test classes
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj) and 
                        issubclass(obj, IntegrationTestBase) and 
                        obj != IntegrationTestBase
                    ):
                        self.test_classes[name] = obj
                        logger.info(f"Discovered test class: {name}")
            except Exception as e:
                logger.error(f"Error importing {module_path}: {e}")
                traceback.print_exc()
        
        return self.test_classes
    
    def run_tests(
        self, 
        test_names: Optional[List[str]] = None,
        parallel: bool = False,
        junit_xml: Optional[str] = None,
        verbose: bool = False
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Run integration tests.
        
        Args:
            test_names: List of test names to run (None for all)
            parallel: Whether to run tests in parallel
            junit_xml: Path to JUnit XML report
            verbose: Whether to enable verbose output
            
        Returns:
            Tuple of (exit code, test results)
        """
        if not self.test_classes:
            self.discover_tests()
        
        if not self.test_classes:
            logger.error("No test classes found")
            return 1, {}
        
        # Filter tests if names provided
        if test_names:
            filtered_classes = {}
            for name in test_names:
                if name in self.test_classes:
                    filtered_classes[name] = self.test_classes[name]
                else:
                    logger.warning(f"Test class not found: {name}")
            
            self.test_classes = filtered_classes
        
        if not self.test_classes:
            logger.error("No matching test classes found")
            return 1, {}
        
        # Prepare pytest arguments
        pytest_args = ["-v"] if verbose else []
        
        # Add JUnit XML report
        if junit_xml:
            pytest_args.extend(["--junitxml", junit_xml])
        
        # Add parallel execution
        if parallel:
            pytest_args.extend(["-xvs", "--forked"])
        
        # Add test markers
        pytest_args.append("-m")
        pytest_args.append("integration")
        
        # Add test modules
        for test_class in self.test_classes.values():
            module_path = test_class.__module__
            pytest_args.append(module_path)
        
        # Run tests
        logger.info(f"Running integration tests with args: {pytest_args}")
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        end_time = time.time()
        
        # Collect results
        results = {
            "exit_code": exit_code,
            "duration": end_time - start_time,
            "test_count": len(self.test_classes),
            "env_name": self.env_name
        }
        
        logger.info(f"Integration tests completed in {results['duration']:.2f} seconds")
        logger.info(f"Exit code: {exit_code}")
        
        return exit_code, results
    
    def run_specific_test(
        self, 
        test_class: str,
        test_method: Optional[str] = None,
        verbose: bool = False
    ) -> int:
        """
        Run a specific integration test.
        
        Args:
            test_class: Test class name
            test_method: Test method name (None for all methods)
            verbose: Whether to enable verbose output
            
        Returns:
            Exit code
        """
        if not self.test_classes:
            self.discover_tests()
        
        if test_class not in self.test_classes:
            logger.error(f"Test class not found: {test_class}")
            return 1
        
        # Prepare pytest arguments
        pytest_args = ["-v"] if verbose else []
        
        # Add test markers
        pytest_args.append("-m")
        pytest_args.append("integration")
        
        # Add test module and class
        module_path = self.test_classes[test_class].__module__
        class_path = f"{module_path}::{test_class}"
        
        if test_method:
            class_path = f"{class_path}::{test_method}"
        
        pytest_args.append(class_path)
        
        # Run test
        logger.info(f"Running integration test: {class_path}")
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        end_time = time.time()
        
        logger.info(f"Test completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Exit code: {exit_code}")
        
        return exit_code
    
    def generate_test_report(self, results_file: str):
        """
        Generate a test report.
        
        Args:
            results_file: Path to results file
        """
        if not os.path.exists(results_file):
            logger.error(f"Results file not found: {results_file}")
            return
        
        try:
            with open(results_file, "r") as f:
                results = json.load(f)
            
            # Generate report
            report = {
                "summary": {
                    "total": results.get("test_count", 0),
                    "passed": results.get("passed", 0),
                    "failed": results.get("failed", 0),
                    "skipped": results.get("skipped", 0),
                    "duration": results.get("duration", 0)
                },
                "environment": {
                    "name": results.get("env_name", "unknown"),
                    "python_version": sys.version,
                    "platform": sys.platform
                },
                "tests": results.get("tests", [])
            }
            
            # Write report
            report_file = os.path.splitext(results_file)[0] + "_report.json"
            with open(report_file, "w") as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Generated test report: {report_file}")
        except Exception as e:
            logger.error(f"Error generating report: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        self.env_manager.cleanup()


def main():
    """Main entry point for the integration test runner."""
    parser = argparse.ArgumentParser(description="Integration Test Runner")
    parser.add_argument(
        "--env", 
        default="test",
        help="Test environment name"
    )
    parser.add_argument(
        "--config", 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--test-dir", 
        default="tests/integration",
        help="Directory containing integration tests"
    )
    parser.add_argument(
        "--test", 
        action="append",
        help="Specific test class to run"
    )
    parser.add_argument(
        "--method", 
        help="Specific test method to run"
    )
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
        help="Path to results file"
    )
    parser.add_argument(
        "--report", 
        action="store_true",
        help="Generate test report"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create runner
    runner = IntegrationTestRunner(
        test_dir=args.test_dir,
        env_name=args.env,
        config_file=args.config
    )
    
    try:
        # Run tests
        if args.test and args.method:
            # Run specific test method
            exit_code = runner.run_specific_test(
                args.test[0],
                args.method,
                args.verbose
            )
        elif args.test:
            # Run specific test classes
            exit_code, results = runner.run_tests(
                args.test,
                args.parallel,
                args.junit_xml,
                args.verbose
            )
        else:
            # Run all tests
            exit_code, results = runner.run_tests(
                None,
                args.parallel,
                args.junit_xml,
                args.verbose
            )
        
        # Save results
        if args.results:
            with open(args.results, "w") as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Saved test results to {args.results}")
            
            # Generate report
            if args.report:
                runner.generate_test_report(args.results)
        
        return exit_code
    finally:
        runner.cleanup()


if __name__ == "__main__":
    sys.exit(main())