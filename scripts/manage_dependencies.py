#!/usr/bin/env python
"""
Dependency Management Script for Cryptobot

This script helps manage project dependencies by:
1. Updating dependencies to their latest versions
2. Checking for security vulnerabilities
3. Generating requirements.txt with pinned versions
4. Creating a dependency report

Usage:
    python manage_dependencies.py [options]

Options:
    --update        Update dependencies to latest versions
    --check         Check for security vulnerabilities
    --generate      Generate requirements.txt with pinned versions
    --report        Generate dependency report
    --all           Perform all actions
"""

import os
import sys
import subprocess
import argparse
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Set, Optional

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")
DEV_REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements-dev.txt")
REPORT_DIR = os.path.join(PROJECT_ROOT, "reports")
VENV_DIR = os.path.join(PROJECT_ROOT, "venv")

# Ensure reports directory exists
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

def run_command(command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
    """
    Run a command and return the exit code, stdout, and stderr
    
    Args:
        command: Command to run as a list of strings
        capture_output: Whether to capture stdout and stderr
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        if capture_output:
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(command, check=False)
            return result.returncode, "", ""
    except Exception as e:
        return 1, "", str(e)

def get_installed_packages() -> Dict[str, str]:
    """
    Get a dictionary of installed packages and their versions
    
    Returns:
        Dictionary of package names and versions
    """
    code, stdout, stderr = run_command([sys.executable, "-m", "pip", "list", "--format=json"])
    if code != 0:
        print(f"Error getting installed packages: {stderr}")
        return {}
    
    packages = {}
    try:
        for package in json.loads(stdout):
            packages[package["name"].lower()] = package["version"]
    except json.JSONDecodeError:
        print(f"Error parsing pip list output: {stdout}")
    
    return packages

def get_requirements(file_path: str) -> List[Tuple[str, Optional[str]]]:
    """
    Parse a requirements file and return a list of (package, version) tuples
    
    Args:
        file_path: Path to requirements file
        
    Returns:
        List of (package, version) tuples
    """
    if not os.path.exists(file_path):
        return []
    
    requirements = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Handle requirements with version specifiers
            match = re.match(r"([a-zA-Z0-9_\-\.]+)([<>=!~]+.+)?", line)
            if match:
                package = match.group(1).lower()
                version = match.group(2)
                requirements.append((package, version))
            else:
                requirements.append((line.lower(), None))
    
    return requirements

def update_dependencies(requirements_file: str) -> bool:
    """
    Update dependencies to their latest versions
    
    Args:
        requirements_file: Path to requirements file
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Updating dependencies from {requirements_file}...")
    
    # Get current requirements
    requirements = get_requirements(requirements_file)
    
    # Update each package
    success = True
    for package, _ in requirements:
        print(f"Updating {package}...")
        code, stdout, stderr = run_command(
            [sys.executable, "-m", "pip", "install", "--upgrade", package],
            capture_output=False
        )
        if code != 0:
            print(f"Error updating {package}: {stderr}")
            success = False
    
    return success

def check_security_vulnerabilities() -> bool:
    """
    Check for security vulnerabilities using safety
    
    Returns:
        True if no vulnerabilities found, False otherwise
    """
    print("Checking for security vulnerabilities...")
    
    # Install safety if not already installed
    installed_packages = get_installed_packages()
    if "safety" not in installed_packages:
        print("Installing safety...")
        code, stdout, stderr = run_command(
            [sys.executable, "-m", "pip", "install", "safety"],
            capture_output=False
        )
        if code != 0:
            print(f"Error installing safety: {stderr}")
            return False
    
    # Run safety check
    code, stdout, stderr = run_command(["safety", "check", "--json"])
    if code != 0 and "No vulnerable packages found" not in stderr:
        print("Vulnerabilities found!")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_path = os.path.join(REPORT_DIR, f"security_report_{timestamp}.json")
        with open(report_path, "w") as f:
            f.write(stdout)
        
        print(f"Security report saved to {report_path}")
        return False
    
    print("No security vulnerabilities found.")
    return True

def generate_requirements() -> bool:
    """
    Generate requirements.txt with pinned versions
    
    Returns:
        True if successful, False otherwise
    """
    print("Generating requirements files with pinned versions...")
    
    # Install pip-tools if not already installed
    installed_packages = get_installed_packages()
    if "pip-tools" not in installed_packages:
        print("Installing pip-tools...")
        code, stdout, stderr = run_command(
            [sys.executable, "-m", "pip", "install", "pip-tools"],
            capture_output=False
        )
        if code != 0:
            print(f"Error installing pip-tools: {stderr}")
            return False
    
    # Generate requirements.txt
    print("Generating requirements.txt...")
    code, stdout, stderr = run_command([
        sys.executable, "-m", "piptools", "compile",
        "--output-file", REQUIREMENTS_FILE,
        "--no-header", "--no-emit-index-url",
        REQUIREMENTS_FILE
    ])
    if code != 0:
        print(f"Error generating requirements.txt: {stderr}")
        return False
    
    # Generate requirements-dev.txt
    print("Generating requirements-dev.txt...")
    code, stdout, stderr = run_command([
        sys.executable, "-m", "piptools", "compile",
        "--output-file", DEV_REQUIREMENTS_FILE,
        "--no-header", "--no-emit-index-url",
        DEV_REQUIREMENTS_FILE
    ])
    if code != 0:
        print(f"Error generating requirements-dev.txt: {stderr}")
        return False
    
    print("Requirements files generated successfully.")
    return True

def generate_dependency_report() -> bool:
    """
    Generate a dependency report
    
    Returns:
        True if successful, False otherwise
    """
    print("Generating dependency report...")
    
    # Get installed packages
    installed_packages = get_installed_packages()
    
    # Get requirements
    requirements = get_requirements(REQUIREMENTS_FILE)
    dev_requirements = get_requirements(DEV_REQUIREMENTS_FILE)
    
    # Create report
    report = {
        "timestamp": datetime.now().isoformat(),
        "installed_packages": installed_packages,
        "requirements": {package: version for package, version in requirements},
        "dev_requirements": {package: version for package, version in dev_requirements},
        "outdated_packages": {}
    }
    
    # Check for outdated packages
    code, stdout, stderr = run_command([
        sys.executable, "-m", "pip", "list", "--outdated", "--format=json"
    ])
    if code == 0:
        try:
            outdated = json.loads(stdout)
            for package in outdated:
                report["outdated_packages"][package["name"].lower()] = {
                    "current": package["version"],
                    "latest": package["latest_version"]
                }
        except json.JSONDecodeError:
            print(f"Error parsing outdated packages: {stdout}")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_path = os.path.join(REPORT_DIR, f"dependency_report_{timestamp}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Generate human-readable report
    text_report_path = os.path.join(REPORT_DIR, f"dependency_report_{timestamp}.txt")
    with open(text_report_path, "w") as f:
        f.write("Cryptobot Dependency Report\n")
        f.write("==========================\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("Installed Packages\n")
        f.write("-----------------\n")
        for package, version in sorted(installed_packages.items()):
            f.write(f"{package}=={version}\n")
        f.write("\n")
        
        f.write("Outdated Packages\n")
        f.write("----------------\n")
        if report["outdated_packages"]:
            for package, versions in sorted(report["outdated_packages"].items()):
                f.write(f"{package}: {versions['current']} -> {versions['latest']}\n")
        else:
            f.write("No outdated packages found.\n")
        f.write("\n")
        
        f.write("Production Requirements\n")
        f.write("----------------------\n")
        for package, version in sorted(report["requirements"].items()):
            f.write(f"{package}{version or ''}\n")
        f.write("\n")
        
        f.write("Development Requirements\n")
        f.write("-----------------------\n")
        for package, version in sorted(report["dev_requirements"].items()):
            f.write(f"{package}{version or ''}\n")
    
    print(f"Dependency report saved to {report_path}")
    print(f"Human-readable report saved to {text_report_path}")
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Dependency Management Script for Cryptobot")
    parser.add_argument("--update", action="store_true", help="Update dependencies to latest versions")
    parser.add_argument("--check", action="store_true", help="Check for security vulnerabilities")
    parser.add_argument("--generate", action="store_true", help="Generate requirements.txt with pinned versions")
    parser.add_argument("--report", action="store_true", help="Generate dependency report")
    parser.add_argument("--all", action="store_true", help="Perform all actions")
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 0
    
    # Perform actions
    success = True
    
    if args.update or args.all:
        success = update_dependencies(REQUIREMENTS_FILE) and success
        success = update_dependencies(DEV_REQUIREMENTS_FILE) and success
    
    if args.check or args.all:
        success = check_security_vulnerabilities() and success
    
    if args.generate or args.all:
        success = generate_requirements() and success
    
    if args.report or args.all:
        success = generate_dependency_report() and success
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())