#!/usr/bin/env python
"""
Run Standalone Integration Test

This script runs the standalone integration test without using the project's
conftest.py file. It can be used to verify that the integration testing
framework is set up correctly.
"""

import os
import sys
import subprocess

def main():
    """Run the standalone integration test."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the standalone test
    test_file = os.path.join(script_dir, "test_standalone.py")
    
    # Check if the test file exists
    if not os.path.exists(test_file):
        print(f"Error: Test file {test_file} not found")
        return 1
    
    # Build the pytest command with -xvs flags and --no-header
    # The -p no:conftest flag tells pytest not to load conftest.py files
    cmd = [
        sys.executable, 
        "-m", 
        "pytest", 
        "-xvs", 
        "--no-header",
        "-p", 
        "no:conftest", 
        test_file
    ]
    
    # Run the test
    print(f"Running standalone integration test: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\nStandalone integration test passed successfully!")
        print("\nYour integration testing framework is set up correctly.")
        print("You can now run the other integration tests.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\nError running standalone integration test: {e}")
        print("\nPlease check the error message and fix any issues.")
        print("You may need to install additional dependencies or fix configuration issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())