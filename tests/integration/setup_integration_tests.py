#!/usr/bin/env python
"""
Setup script for integration tests.

This script installs the required dependencies for running the integration tests.
"""

import os
import sys
import subprocess
import argparse

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Setup integration tests")
    parser.add_argument("--venv", action="store_true", help="Create a virtual environment")
    parser.add_argument("--venv-path", default="venv", help="Path to virtual environment")
    return parser.parse_args()

def install_dependencies(venv_path=None):
    """Install dependencies from requirements.txt."""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to requirements.txt
    requirements_path = os.path.join(script_dir, "requirements.txt")
    
    # Check if requirements.txt exists
    if not os.path.exists(requirements_path):
        print(f"Error: {requirements_path} not found")
        return False
    
    # Command to install dependencies
    if venv_path:
        # Use pip from virtual environment
        if sys.platform == "win32":
            pip_path = os.path.join(venv_path, "Scripts", "pip")
        else:
            pip_path = os.path.join(venv_path, "bin", "pip")
        
        cmd = [pip_path, "install", "-r", requirements_path]
    else:
        # Use system pip
        cmd = [sys.executable, "-m", "pip", "install", "-r", requirements_path]
    
    # Install dependencies
    print(f"Installing dependencies from {requirements_path}...")
    try:
        subprocess.check_call(cmd)
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False

def create_venv(venv_path):
    """Create a virtual environment."""
    if os.path.exists(venv_path):
        print(f"Virtual environment already exists at {venv_path}")
        return True
    
    print(f"Creating virtual environment at {venv_path}...")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", venv_path])
        print(f"Virtual environment created at {venv_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating virtual environment: {e}")
        return False

def main():
    """Main function."""
    args = parse_args()
    
    if args.venv:
        if not create_venv(args.venv_path):
            return 1
        
        if not install_dependencies(args.venv_path):
            return 1
    else:
        if not install_dependencies():
            return 1
    
    print("\nSetup complete. You can now run the integration tests with:")
    if args.venv:
        if sys.platform == "win32":
            python_path = os.path.join(args.venv_path, "Scripts", "python")
        else:
            python_path = os.path.join(args.venv_path, "bin", "python")
        
        print(f"  {python_path} tests/integration/run_integration_tests.py")
    else:
        print("  python tests/integration/run_integration_tests.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())