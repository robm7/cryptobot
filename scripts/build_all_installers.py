#!/usr/bin/env python3
"""
CryptoBot Installer Builder

This script builds installers for CryptoBot for Windows, macOS, and Linux platforms.
It provides a unified interface to build installers for all supported platforms.
"""

import os
import sys
import argparse
import platform
import subprocess
import shutil
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def check_prerequisites():
    """Check if the required tools are installed."""
    system = platform.system()
    missing_tools = []
    
    # Common prerequisites
    if shutil.which("python") is None and shutil.which("python3") is None:
        missing_tools.append("Python 3.7+")
    
    if system == "Windows":
        # Windows prerequisites
        if shutil.which("iscc") is None:
            missing_tools.append("Inno Setup")
    elif system == "Darwin":
        # macOS prerequisites
        if shutil.which("create-dmg") is None:
            missing_tools.append("create-dmg")
    elif system == "Linux":
        # Linux prerequisites
        if shutil.which("fpm") is None:
            missing_tools.append("fpm")
    
    return missing_tools

def build_windows_installer(args):
    """Build the Windows installer."""
    print("Building Windows installer...")
    
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", 
           os.path.join(get_project_root(), "scripts", "build_windows_installer.ps1")]
    
    if args.clean:
        cmd.append("-Clean")
    if args.optimize:
        cmd.append("-Optimize")
    if args.test:
        cmd.append("-Test")
    
    try:
        subprocess.run(cmd, check=True)
        print("Windows installer built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building Windows installer: {e}")
        return False

def build_macos_installer(args):
    """Build the macOS installer."""
    print("Building macOS installer...")
    
    # First build the app bundle
    app_cmd = ["bash", os.path.join(get_project_root(), "scripts", "build_macos_app.sh")]
    
    if args.clean:
        app_cmd.append("--clean")
    if args.optimize:
        app_cmd.append("--optimize")
    if args.test:
        app_cmd.append("--test")
    
    try:
        subprocess.run(app_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building macOS app bundle: {e}")
        return False
    
    # Then build the DMG
    dmg_cmd = ["bash", os.path.join(get_project_root(), "scripts", "build_macos_dmg.sh")]
    
    if args.clean:
        dmg_cmd.append("--clean")
    if args.test:
        dmg_cmd.append("--test")
    
    try:
        subprocess.run(dmg_cmd, check=True)
        print("macOS installer built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building macOS DMG: {e}")
        return False

def build_linux_deb_installer(args):
    """Build the Linux DEB installer."""
    print("Building Linux DEB installer...")
    
    cmd = ["bash", os.path.join(get_project_root(), "scripts", "build_linux_deb.sh")]
    
    if args.clean:
        cmd.append("--clean")
    if args.optimize:
        cmd.append("--optimize")
    if args.test:
        cmd.append("--test")
    
    try:
        subprocess.run(cmd, check=True)
        print("Linux DEB installer built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building Linux DEB installer: {e}")
        return False

def build_linux_rpm_installer(args):
    """Build the Linux RPM installer."""
    print("Building Linux RPM installer...")
    
    cmd = ["bash", os.path.join(get_project_root(), "scripts", "build_linux_rpm.sh")]
    
    if args.clean:
        cmd.append("--clean")
    if args.optimize:
        cmd.append("--optimize")
    if args.test:
        cmd.append("--test")
    
    try:
        subprocess.run(cmd, check=True)
        print("Linux RPM installer built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building Linux RPM installer: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build CryptoBot installers for various platforms.")
    parser.add_argument("--platform", choices=["windows", "macos", "linux", "all"], default="all",
                        help="Platform to build installer for (default: all)")
    parser.add_argument("--linux-type", choices=["deb", "rpm", "all"], default="all",
                        help="Type of Linux installer to build (default: all)")
    parser.add_argument("--clean", action="store_true", help="Clean build directories before building")
    parser.add_argument("--optimize", action="store_true", help="Optimize the build for size")
    parser.add_argument("--test", action="store_true", help="Test the installer after building")
    
    args = parser.parse_args()
    
    # Check prerequisites
    missing_tools = check_prerequisites()
    if missing_tools:
        print("The following tools are required but not found:")
        for tool in missing_tools:
            print(f"  - {tool}")
        print("Please install the missing tools and try again.")
        return 1
    
    # Build installers
    success = True
    
    if args.platform in ["windows", "all"] and platform.system() == "Windows":
        if not build_windows_installer(args):
            success = False
    
    if args.platform in ["macos", "all"] and platform.system() == "Darwin":
        if not build_macos_installer(args):
            success = False
    
    if args.platform in ["linux", "all"] and platform.system() == "Linux":
        if args.linux_type in ["deb", "all"]:
            if not build_linux_deb_installer(args):
                success = False
        
        if args.linux_type in ["rpm", "all"]:
            if not build_linux_rpm_installer(args):
                success = False
    
    # Cross-platform building (not implemented yet)
    if args.platform == "windows" and platform.system() != "Windows":
        print("Cross-platform building for Windows is not supported yet.")
    
    if args.platform == "macos" and platform.system() != "Darwin":
        print("Cross-platform building for macOS is not supported yet.")
    
    if args.platform == "linux" and platform.system() != "Linux":
        print("Cross-platform building for Linux is not supported yet.")
    
    if success:
        print("All requested installers built successfully.")
        return 0
    else:
        print("Some installers failed to build. Check the logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())