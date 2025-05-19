#!/usr/bin/env python
"""
Test Coverage Runner

This script runs tests with coverage reporting and generates HTML reports
to track progress toward the coverage goals specified in CRITICAL_TESTING_PLAN.md.
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime

# Critical components with their coverage thresholds
COVERAGE_THRESHOLDS = {
    "order_execution": {
        "path": "services/mcp/order_execution",
        "threshold": 80
    },
    "api_key_management": {
        "path": "auth/key_manager.py",
        "threshold": 80
    },
    "authentication": {
        "path": "auth",
        "threshold": 75
    },
    "default": {
        "threshold": 70
    }
}

def run_tests(test_paths=None, verbose=False):
    """
    Run tests with coverage reporting
    
    Args:
        test_paths: List of test paths to run (default: all tests)
        verbose: Whether to show verbose output
        
    Returns:
        Tuple of (success, coverage_data)
    """
    # Get the project root directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # Set up the command
    cmd = ["pytest"]
    
    # Add verbosity if requested
    if verbose:
        cmd.append("-v")
    
    # Add coverage options
    cmd.extend([
        "--cov=./",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-config=.coveragerc"
    ])
    
    # Add specific test paths if provided
    if test_paths:
        cmd.extend(test_paths)
    else:
        # Default to all tests
        cmd.extend([
            "tests/unit",
            "tests/integration",
            "tests/benchmarks"
        ])
    
    # Set up the python command
    python_cmd = [sys.executable, "-m", "pytest"] + cmd[1:]
    
    # Print the command
    print(f"Running command: {' '.join(python_cmd)}")
    
    # Run the tests using python -m pytest
    result = subprocess.run(python_cmd, cwd=project_root, capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("Errors:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    # Parse coverage data
    coverage_data = parse_coverage_output(result.stdout)
    
    return result.returncode == 0, coverage_data

def parse_coverage_output(output):
    """
    Parse coverage data from pytest-cov output
    
    Args:
        output: pytest-cov output text
        
    Returns:
        Dictionary with coverage data
    """
    coverage_data = {
        "total": 0,
        "components": {}
    }
    
    # Find the coverage report section
    lines = output.split('\n')
    coverage_section = False
    
    for line in lines:
        if line.startswith("---------- coverage:"):
            coverage_section = True
            continue
        
        if coverage_section and line.strip() == "":
            coverage_section = False
            continue
        
        if coverage_section and "%" in line:
            # Parse the line
            parts = line.split()
            if len(parts) >= 4:
                file_path = parts[0]
                statements = int(parts[1])
                missed = int(parts[2])
                coverage_pct = int(parts[3].rstrip('%'))
                
                # Store data
                coverage_data["components"][file_path] = {
                    "statements": statements,
                    "missed": missed,
                    "covered": statements - missed,
                    "coverage": coverage_pct
                }
    
    # Calculate total coverage
    total_statements = sum(comp["statements"] for comp in coverage_data["components"].values())
    total_covered = sum(comp["covered"] for comp in coverage_data["components"].values())
    
    if total_statements > 0:
        coverage_data["total"] = round((total_covered / total_statements) * 100)
    
    return coverage_data

def check_component_coverage(coverage_data):
    """
    Check if components meet their coverage thresholds
    
    Args:
        coverage_data: Coverage data dictionary
        
    Returns:
        Dictionary with component coverage status
    """
    component_status = {}
    
    # Check each critical component
    for component_name, config in COVERAGE_THRESHOLDS.items():
        if component_name == "default":
            continue
            
        path = config["path"]
        threshold = config["threshold"]
        
        # Find all files matching the path
        matching_files = [
            file_path for file_path in coverage_data["components"]
            if file_path.startswith(path)
        ]
        
        if not matching_files:
            component_status[component_name] = {
                "coverage": 0,
                "threshold": threshold,
                "met": False,
                "files": []
            }
            continue
            
        # Calculate component coverage
        total_statements = sum(coverage_data["components"][file]["statements"] for file in matching_files)
        total_covered = sum(coverage_data["components"][file]["covered"] for file in matching_files)
        
        if total_statements > 0:
            component_coverage = round((total_covered / total_statements) * 100)
        else:
            component_coverage = 0
            
        # Check if threshold is met
        threshold_met = component_coverage >= threshold
        
        component_status[component_name] = {
            "coverage": component_coverage,
            "threshold": threshold,
            "met": threshold_met,
            "files": matching_files
        }
    
    # Check overall coverage
    overall_threshold = COVERAGE_THRESHOLDS["default"]["threshold"]
    overall_met = coverage_data["total"] >= overall_threshold
    
    component_status["overall"] = {
        "coverage": coverage_data["total"],
        "threshold": overall_threshold,
        "met": overall_met
    }
    
    return component_status

def generate_report(coverage_data, component_status):
    """
    Generate a report of coverage data
    
    Args:
        coverage_data: Coverage data dictionary
        component_status: Component coverage status
        
    Returns:
        Report text
    """
    report = []
    report.append("=" * 80)
    report.append("TEST COVERAGE REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append(f"Overall Coverage: {coverage_data['total']}% (Threshold: {COVERAGE_THRESHOLDS['default']['threshold']}%)")
    report.append("")
    report.append("Critical Component Coverage:")
    report.append("-" * 80)
    
    # Report on each critical component
    for component_name, status in component_status.items():
        if component_name == "overall":
            continue
            
        icon = "✅" if status["met"] else "❌"
        report.append(f"{icon} {component_name}: {status['coverage']}% (Threshold: {status['threshold']}%)")
    
    report.append("-" * 80)
    report.append("")
    
    # Check if all thresholds are met
    all_met = all(status["met"] for status in component_status.values())
    
    if all_met:
        report.append("🎉 SUCCESS: All coverage thresholds have been met!")
    else:
        report.append("⚠️ WARNING: Some coverage thresholds have not been met.")
        report.append("")
        report.append("Components needing more tests:")
        for component_name, status in component_status.items():
            if not status["met"]:
                report.append(f"  - {component_name}: {status['coverage']}% (need {status['threshold'] - status['coverage']}% more)")
    
    report.append("")
    report.append("HTML coverage report generated in: htmlcov/index.html")
    
    return "\n".join(report)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run tests with coverage reporting")
    parser.add_argument(
        "--tests", 
        nargs="+",
        help="Specific test paths to run (default: all tests)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--save", 
        action="store_true",
        help="Save report to file"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Running tests with coverage reporting")
    print("=" * 80)
    
    success, coverage_data = run_tests(args.tests, args.verbose)
    
    if not success:
        print("Tests failed!")
        return 1
    
    component_status = check_component_coverage(coverage_data)
    report = generate_report(coverage_data, component_status)
    print("\n" + report)
    
    if args.save:
        # Create reports directory if it doesn't exist
        if not os.path.exists("reports"):
            os.makedirs("reports")
        
        # Save text report
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_path = f"reports/coverage_report_{timestamp}.txt"
        
        with open(report_path, "w") as f:
            f.write(report)
        
        # Save JSON data
        json_path = f"reports/coverage_data_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump({
                "coverage": coverage_data,
                "component_status": component_status
            }, f, indent=2)
        
        print(f"Report saved to {report_path}")
        print(f"Coverage data saved to {json_path}")
    
    # Return success based on all thresholds being met
    all_met = all(status["met"] for status in component_status.values())
    return 0 if all_met else 1

if __name__ == "__main__":
    sys.exit(main())