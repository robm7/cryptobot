#!/usr/bin/env python3
"""
CryptoBot Distribution Verification Script

This script verifies that the distribution packages for CryptoBot work correctly
on the current platform. It performs a series of tests to ensure that the
executables run correctly and that all required functionality is available.
"""

import os
import sys
import argparse
import platform
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("verify_distribution.log")
    ]
)
logger = logging.getLogger("verify_distribution")

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def find_executable(base_dir, platform_name):
    """Find the executable in the distribution package."""
    if platform_name == "windows":
        executable_path = os.path.join(base_dir, "cryptobot", "cryptobot.exe")
        if os.path.exists(executable_path):
            return executable_path
        
        # Try single-file executable
        executable_path = os.path.join(base_dir, "cryptobot_onefile.exe")
        if os.path.exists(executable_path):
            return executable_path
    elif platform_name == "linux":
        executable_path = os.path.join(base_dir, "cryptobot", "cryptobot")
        if os.path.exists(executable_path):
            return executable_path
        
        # Try single-file executable
        executable_path = os.path.join(base_dir, "cryptobot_onefile")
        if os.path.exists(executable_path):
            return executable_path
    elif platform_name == "macos":
        # Try app bundle
        executable_path = os.path.join(base_dir, "CryptoBot.app", "Contents", "MacOS", "CryptoBot")
        if os.path.exists(executable_path):
            return executable_path
        
        # Try directory-based executable
        executable_path = os.path.join(base_dir, "CryptoBot", "CryptoBot")
        if os.path.exists(executable_path):
            return executable_path
    
    return None

def run_test(executable_path, test_name, args, expected_output=None, expected_return_code=0):
    """Run a test with the executable."""
    logger.info(f"Running test: {test_name}")
    
    cmd = [executable_path] + args
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check return code
        if result.returncode != expected_return_code:
            logger.error(f"Test '{test_name}' failed: Expected return code {expected_return_code}, got {result.returncode}")
            logger.error(f"Stdout: {result.stdout}")
            logger.error(f"Stderr: {result.stderr}")
            return False
        
        # Check output if expected_output is provided
        if expected_output is not None:
            if expected_output not in result.stdout:
                logger.error(f"Test '{test_name}' failed: Expected output '{expected_output}' not found in stdout")
                logger.error(f"Stdout: {result.stdout}")
                logger.error(f"Stderr: {result.stderr}")
                return False
        
        logger.info(f"Test '{test_name}' passed")
        return True
    except Exception as e:
        logger.error(f"Test '{test_name}' failed with exception: {e}")
        return False

def verify_executable(executable_path):
    """Verify that the executable works correctly."""
    if not os.path.exists(executable_path):
        logger.error(f"Executable not found: {executable_path}")
        return False
    
    # Make sure the executable is executable on Unix-like systems
    if platform.system() != "Windows":
        os.chmod(executable_path, 0o755)
    
    # Run a series of tests
    tests = [
        {
            "name": "Version check",
            "args": ["--version"],
            "expected_output": "Cryptobot Trading System v1.0.0",
            "expected_return_code": 0
        },
        {
            "name": "Help check",
            "args": ["--help"],
            "expected_output": "usage:",
            "expected_return_code": 0
        },
        # Add more tests as needed
    ]
    
    success = True
    for test in tests:
        if not run_test(
            executable_path,
            test["name"],
            test["args"],
            test.get("expected_output"),
            test.get("expected_return_code", 0)
        ):
            success = False
    
    return success

def verify_distribution_package(dist_dir, platform_name):
    """Verify that the distribution package works correctly."""
    logger.info(f"Verifying {platform_name} distribution package in {dist_dir}")
    
    # Find the executable
    executable_path = find_executable(dist_dir, platform_name)
    if executable_path is None:
        logger.error(f"Could not find executable in {dist_dir}")
        return False
    
    logger.info(f"Found executable: {executable_path}")
    
    # Verify the executable
    return verify_executable(executable_path)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify CryptoBot distribution packages.")
    parser.add_argument("--platform", choices=["windows", "linux", "macos", "auto"], default="auto",
                        help="Platform to verify (default: auto)")
    parser.add_argument("--dist-dir", default=None,
                        help="Distribution directory (default: dist)")
    
    args = parser.parse_args()
    
    # Determine platform
    platform_name = args.platform
    if platform_name == "auto":
        system = platform.system()
        if system == "Windows":
            platform_name = "windows"
        elif system == "Linux":
            platform_name = "linux"
        elif system == "Darwin":
            platform_name = "macos"
        else:
            logger.error(f"Unsupported platform: {system}")
            return 1
    
    # Determine distribution directory
    dist_dir = args.dist_dir
    if dist_dir is None:
        dist_dir = os.path.join(get_project_root(), "dist")
    
    # Verify the distribution package
    if verify_distribution_package(dist_dir, platform_name):
        logger.info(f"{platform_name.capitalize()} distribution package verification passed")
        return 0
    else:
        logger.error(f"{platform_name.capitalize()} distribution package verification failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())