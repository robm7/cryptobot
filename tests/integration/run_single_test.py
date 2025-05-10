#!/usr/bin/env python
"""
Script to run a single integration test.

This script allows running a specific integration test file or test case.
"""

import os
import sys
import argparse
import subprocess
import importlib.util

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a single integration test")
    parser.add_argument("test_file", help="Test file to run (e.g., test_backtest_integration.py)")
    parser.add_argument("--test-case", help="Specific test case to run (e.g., TestBacktestIntegration.test_mean_reversion_backtest)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser.parse_args()

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import pytest
        return True
    except ImportError:
        print("Error: pytest is not installed. Please run setup_integration_tests.py first.")
        return False

def run_test(test_file, test_case=None, verbose=False):
    """Run a specific test file or test case."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Full path to the test file
    test_file_path = os.path.join(script_dir, test_file)
    
    # Check if the test file exists
    if not os.path.exists(test_file_path):
        print(f"Error: Test file {test_file_path} not found")
        return False
    
    # Build the pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add verbose flag if requested
    if verbose:
        cmd.append("-v")
    
    # Add test file path
    cmd.append(test_file_path)
    
    # Add test case if specified
    if test_case:
        cmd[-1] = f"{cmd[-1]}::{test_case}"
    
    # Run the test
    print(f"Running test: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running test: {e}")
        return False

def main():
    """Main function."""
    args = parse_args()
    
    if not check_dependencies():
        return 1
    
    if not run_test(args.test_file, args.test_case, args.verbose):
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())