#!/usr/bin/env python
"""
Dependency Management Script for Crypto Trading Bot

This script updates all requirements.txt files from their corresponding requirements.in files
using pip-tools. It ensures consistent dependency management across all services.

Usage:
    python scripts/update_dependencies.py
"""

import os
import subprocess
import sys
from pathlib import Path

# Path to pip-compile executable
PIP_COMPILE = str(Path(sys.executable).parent / "Scripts" / "pip-compile.exe")
if not os.path.exists(PIP_COMPILE):
    # Try user site-packages path
    user_scripts = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "Python" / "Python311" / "Scripts" / "pip-compile.exe"
    if os.path.exists(user_scripts):
        PIP_COMPILE = str(user_scripts)
    else:
        PIP_COMPILE = "pip-compile"  # Fall back to PATH-based pip-compile

# Root directory of the project
ROOT_DIR = Path(__file__).parent.parent

# Services and directories with requirements files
SERVICES = [
    "",  # Root directory
    "auth",
    "backtest",
    "data",
    "strategy",
    "trade",
    "tests/benchmarks",
    "tests/integration",
]


def update_requirements(directory):
    """Update requirements.txt from requirements.in for a specific directory."""
    in_file = os.path.join(directory, "requirements.in")
    out_file = os.path.join(directory, "requirements.txt")
    
    if not os.path.exists(in_file):
        print(f"Skipping {directory}: requirements.in not found")
        return False
    
    print(f"Updating {out_file}...")
    try:
        # Use the full path for pip-compile
        if os.path.exists(PIP_COMPILE):
            cmd = [PIP_COMPILE, in_file, "--output-file", out_file]
        else:
            # If pip-compile is not found, use python -m piptools.scripts.compile
            cmd = [sys.executable, "-m", "piptools.scripts.compile", in_file, "--output-file", out_file]
        
        subprocess.run(
            cmd,
            check=True,
            cwd=ROOT_DIR
        )
        print(f"Successfully updated {out_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating {out_file}: {e}")
        return False


def update_dev_requirements():
    """Update development requirements."""
    in_file = "requirements-dev.in"
    out_file = "requirements-dev.txt"
    
    if not os.path.exists(in_file):
        print(f"Skipping {in_file}: file not found")
        return False
    
    print(f"Updating {out_file}...")
    try:
        # Use the full path for pip-compile
        if os.path.exists(PIP_COMPILE):
            cmd = [PIP_COMPILE, in_file, "--output-file", out_file]
        else:
            # If pip-compile is not found, use python -m piptools.scripts.compile
            cmd = [sys.executable, "-m", "piptools.scripts.compile", in_file, "--output-file", out_file]
        
        subprocess.run(
            cmd,
            check=True,
            cwd=ROOT_DIR
        )
        print(f"Successfully updated {out_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating {out_file}: {e}")
        return False


def main():
    """Main function to update all requirements files."""
    print("Updating requirements files...")
    
    # Update service requirements
    success_count = 0
    total_count = len(SERVICES)
    
    for service in SERVICES:
        if update_requirements(service):
            success_count += 1
    
    # Update development requirements
    if update_dev_requirements():
        success_count += 1
        total_count += 1
    
    print(f"\nCompleted: {success_count}/{total_count} requirements files updated successfully")


if __name__ == "__main__":
    main()