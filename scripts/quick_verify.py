#!/usr/bin/env python3
"""
Quick Verification Script for CryptoBot Executable

This script performs a quick verification of the CryptoBot executable
to ensure it runs correctly and responds to basic commands.
"""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def find_executable():
    """Find the executable in the distribution directory."""
    dist_dir = os.path.join(get_project_root(), "dist")
    
    if platform.system() == "Windows":
        # Try directory-based executable first
        exe_path = os.path.join(dist_dir, "cryptobot", "cryptobot.exe")
        if os.path.exists(exe_path):
            return exe_path
        
        # Try single-file executable
        exe_path = os.path.join(dist_dir, "cryptobot_onefile.exe")
        if os.path.exists(exe_path):
            return exe_path
    elif platform.system() == "Linux":
        # Try directory-based executable first
        exe_path = os.path.join(dist_dir, "cryptobot", "cryptobot")
        if os.path.exists(exe_path):
            return exe_path
        
        # Try single-file executable
        exe_path = os.path.join(dist_dir, "cryptobot_onefile")
        if os.path.exists(exe_path):
            return exe_path
    elif platform.system() == "Darwin":  # macOS
        # Try app bundle
        exe_path = os.path.join(dist_dir, "CryptoBot.app", "Contents", "MacOS", "CryptoBot")
        if os.path.exists(exe_path):
            return exe_path
    
    return None

def run_test(executable, args, expected_output=None, expected_return_code=0):
    """Run a test with the executable."""
    print(f"Running test with args: {args}")
    
    cmd = [executable] + args
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check return code
        if result.returncode != expected_return_code:
            print(f"❌ Test failed: Expected return code {expected_return_code}, got {result.returncode}")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
        
        # Check output if expected_output is provided
        if expected_output is not None and expected_output not in result.stdout:
            print(f"❌ Test failed: Expected output '{expected_output}' not found in stdout")
            print(f"Stdout: {result.stdout}")
            print(f"Stderr: {result.stderr}")
            return False
        
        print(f"✅ Test passed")
        return True
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Quick verification of CryptoBot executable")
    parser.add_argument("--executable", help="Path to the executable to test")
    
    args = parser.parse_args()
    
    # Find the executable
    executable = args.executable
    if executable is None:
        executable = find_executable()
    
    if executable is None:
        print("❌ Could not find CryptoBot executable. Make sure it has been built.")
        return 1
    
    print(f"Found executable: {executable}")
    
    # Make sure the executable is executable on Unix-like systems
    if platform.system() != "Windows":
        os.chmod(executable, 0o755)
    
    # Run tests
    tests = [
        {
            "args": ["--version"],
            "expected_output": "Cryptobot Trading System"
        },
        {
            "args": ["--help"],
            "expected_output": "usage:"
        }
    ]
    
    success = True
    for test in tests:
        if not run_test(
            executable,
            test["args"],
            test.get("expected_output"),
            test.get("expected_return_code", 0)
        ):
            success = False
    
    if success:
        print("\n✅ All tests passed! The executable is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())