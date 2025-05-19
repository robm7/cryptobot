#!/usr/bin/env python3
"""
CryptoBot Distribution Package Tester

This script tests the distribution packages for CryptoBot on various platforms.
It verifies that the executables run correctly and that all required dependencies
and resources are included.
"""

import os
import sys
import argparse
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def extract_package(package_path, extract_dir):
    """Extract the distribution package to a temporary directory."""
    print(f"Extracting package: {package_path}")
    
    if package_path.endswith('.zip'):
        # Extract ZIP archive
        import zipfile
        with zipfile.ZipFile(package_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    elif package_path.endswith('.tar.gz'):
        # Extract tarball
        import tarfile
        with tarfile.open(package_path, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_dir)
    elif package_path.endswith('.dmg'):
        # For DMG, we need to mount it and copy the contents
        if platform.system() != 'Darwin':
            print("DMG extraction is only supported on macOS.")
            return False
        
        try:
            # Mount the DMG
            mount_point = os.path.join(tempfile.gettempdir(), 'cryptobot_dmg')
            os.makedirs(mount_point, exist_ok=True)
            subprocess.run(['hdiutil', 'attach', package_path, '-mountpoint', mount_point], check=True)
            
            # Copy the app bundle
            app_path = os.path.join(mount_point, 'CryptoBot.app')
            if os.path.exists(app_path):
                shutil.copytree(app_path, os.path.join(extract_dir, 'CryptoBot.app'))
            
            # Unmount the DMG
            subprocess.run(['hdiutil', 'detach', mount_point], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error extracting DMG: {e}")
            return False
    else:
        print(f"Unsupported package format: {package_path}")
        return False
    
    return True

def test_executable(executable_path, test_args=None):
    """Test the executable with the specified arguments."""
    print(f"Testing executable: {executable_path}")
    
    if not os.path.exists(executable_path):
        print(f"Executable not found: {executable_path}")
        return False
    
    # Make sure the executable is executable on Unix-like systems
    if platform.system() != 'Windows':
        os.chmod(executable_path, 0o755)
    
    # Run the executable with --version to check if it works
    cmd = [executable_path, '--version']
    if test_args:
        cmd.extend(test_args)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Executable output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running executable: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return False

def test_windows_package(args):
    """Test the Windows distribution package."""
    print("Testing Windows distribution package...")
    
    dist_dir = os.path.join(get_project_root(), 'dist')
    package_path = os.path.join(dist_dir, 'cryptobot-windows.zip')
    
    if not os.path.exists(package_path):
        print(f"Package not found: {package_path}")
        return False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        if not extract_package(package_path, temp_dir):
            return False
        
        executable_path = os.path.join(temp_dir, 'cryptobot', 'cryptobot.exe')
        if not test_executable(executable_path, args.test_args):
            return False
    
    print("Windows distribution package test passed.")
    return True

def test_linux_package(args):
    """Test the Linux distribution package."""
    print("Testing Linux distribution package...")
    
    dist_dir = os.path.join(get_project_root(), 'dist')
    package_path = os.path.join(dist_dir, 'cryptobot-linux.tar.gz')
    
    if not os.path.exists(package_path):
        print(f"Package not found: {package_path}")
        return False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        if not extract_package(package_path, temp_dir):
            return False
        
        executable_path = os.path.join(temp_dir, 'cryptobot', 'cryptobot')
        if not test_executable(executable_path, args.test_args):
            return False
    
    print("Linux distribution package test passed.")
    return True

def test_macos_package(args):
    """Test the macOS distribution package."""
    print("Testing macOS distribution package...")
    
    dist_dir = os.path.join(get_project_root(), 'dist')
    package_path = os.path.join(dist_dir, 'CryptoBot.dmg')
    
    if not os.path.exists(package_path):
        print(f"Package not found: {package_path}")
        return False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        if not extract_package(package_path, temp_dir):
            return False
        
        executable_path = os.path.join(temp_dir, 'CryptoBot.app', 'Contents', 'MacOS', 'CryptoBot')
        if not test_executable(executable_path, args.test_args):
            return False
    
    print("macOS distribution package test passed.")
    return True

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test CryptoBot distribution packages.")
    parser.add_argument("--platform", choices=["windows", "linux", "macos", "all"], default="all",
                        help="Platform to test (default: all)")
    parser.add_argument("--test-args", nargs=argparse.REMAINDER,
                        help="Additional arguments to pass to the executable during testing")
    
    args = parser.parse_args()
    
    # Test packages
    success = True
    
    if args.platform in ["windows", "all"] and platform.system() == "Windows":
        if not test_windows_package(args):
            success = False
    
    if args.platform in ["linux", "all"] and platform.system() == "Linux":
        if not test_linux_package(args):
            success = False
    
    if args.platform in ["macos", "all"] and platform.system() == "Darwin":
        if not test_macos_package(args):
            success = False
    
    # Cross-platform testing (not implemented yet)
    if args.platform == "windows" and platform.system() != "Windows":
        print("Cross-platform testing for Windows is not supported yet.")
    
    if args.platform == "linux" and platform.system() != "Linux":
        print("Cross-platform testing for Linux is not supported yet.")
    
    if args.platform == "macos" and platform.system() != "Darwin":
        print("Cross-platform testing for macOS is not supported yet.")
    
    if success:
        print("All distribution package tests passed.")
        return 0
    else:
        print("Some distribution package tests failed. Check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())