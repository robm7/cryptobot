#!/usr/bin/env python
"""
Run Simple Integration Test

This script runs the simple integration test to verify that the integration
testing framework is set up correctly.
"""

import os
import sys
import subprocess

def main():
    """Run the simple integration test."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the simple integration test
    test_file = os.path.join(script_dir, "test_simple_integration.py")
    
    # Check if the test file exists
    if not os.path.exists(test_file):
        print(f"Error: Test file {test_file} not found")
        return 1
    
    # Build the pytest command
    cmd = [sys.executable, "-m", "pytest", "-v", test_file]
    
    # Run the test
    print(f"Running simple integration test: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\nSimple integration test passed successfully!")
        print("\nYour integration testing framework is set up correctly.")
        print("You can now run the other integration tests.")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\nError running simple integration test: {e}")
        print("\nPlease check the error message and fix any issues.")
        print("You may need to install additional dependencies or fix configuration issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())