#!/usr/bin/env python
"""
Test runner for the Order Execution module

This script runs the unit and integration tests for the Order Execution module
and reports the results.
"""

import os
import sys
import subprocess
import argparse
import time

def run_tests(test_type="all", verbose=False):
    """Run the specified tests and return the result"""
    # Get the project root directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    
    # Set up the command
    cmd = ["pytest"]
    
    # Add verbosity if requested
    if verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if "--coverage" in sys.argv:
        cmd.extend(["--cov=services.mcp.order_execution", "--cov-report=term"])
    
    # Determine which tests to run
    if test_type == "unit" or test_type == "all":
        cmd.append("tests/test_reliable_executor.py")
    
    if test_type == "integration" or test_type == "all":
        cmd.append("tests/integration/test_reliable_order_execution.py")
    
    # Print the command
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the tests
    start_time = time.time()
    result = subprocess.run(cmd, cwd=project_root)
    end_time = time.time()
    
    # Print results
    print(f"\nTests completed in {end_time - start_time:.2f} seconds")
    print(f"Return code: {result.returncode}")
    
    return result.returncode

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run Order Execution tests")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"Running {args.type} tests for Order Execution module")
    print("=" * 80)
    
    return run_tests(args.type, args.verbose)

if __name__ == "__main__":
    sys.exit(main())