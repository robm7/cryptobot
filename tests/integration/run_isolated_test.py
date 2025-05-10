#!/usr/bin/env python
"""
Run Isolated Integration Test

This script runs the isolated integration test without using any project files.
It can be used to verify that the integration testing framework is set up correctly.
"""

import os
import sys
import subprocess

def main():
    """Run the isolated integration test."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the isolated test
    test_file = os.path.join(script_dir, "isolated", "test_isolated.py")
    
    # Check if the test file exists
    if not os.path.exists(test_file):
        print(f"Error: Test file {test_file} not found")
        return 1
    
    # Create a temporary PYTHONPATH that excludes the project root
    # This ensures that pytest doesn't try to load any project modules
    env = os.environ.copy()
    
    # Get the isolated directory path
    isolated_dir = os.path.dirname(test_file)
    
    # Set PYTHONPATH to only include the isolated directory
    env["PYTHONPATH"] = isolated_dir
    
    # Build the pytest command with -xvs flags and --no-header
    # The -p no:conftest flag tells pytest not to load conftest.py files
    # The --rootdir flag tells pytest to use the isolated directory as the root
    cmd = [
        sys.executable, 
        "-m", 
        "pytest", 
        "-xvs", 
        "--no-header",
        "-p", 
        "no:conftest", 
        "--rootdir=" + isolated_dir,
        test_file
    ]
    
    # Run the test
    print(f"Running isolated integration test: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd, env=env)
        print("\nIsolated integration test passed successfully!")
        print("\nYour integration testing framework is set up correctly.")
        print("You can now run the other integration tests.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\nError running isolated integration test: {e}")
        print("\nPlease check the error message and fix any issues.")
        print("You may need to install additional dependencies or fix configuration issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())