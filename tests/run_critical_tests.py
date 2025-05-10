#!/usr/bin/env python
"""
Critical Testing Runner

This script runs the critical tests and generates a coverage report
to track progress toward the 70% coverage goal.
"""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime

# Critical components to focus on
CRITICAL_COMPONENTS = [
    "services/mcp/order_execution/reliable_executor.py",
    "services/mcp/order_execution/monitoring.py",
    "auth/key_manager.py",
    "auth/routers/api_keys.py",
    "auth/background_tasks.py",
    "strategy/routers/strategies.py"
]

def run_tests(test_type="all", verbose=False, html_report=False):
    """
    Run the specified tests and generate coverage report
    
    Args:
        test_type: Type of tests to run (unit, integration, api, all)
        verbose: Whether to show verbose output
        html_report: Whether to generate HTML coverage report
        
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
    
    # Add coverage
    cmd.extend([
        "--cov=services.mcp.order_execution",
        "--cov=auth.key_manager",
        "--cov=auth.routers.api_keys",
        "--cov=auth.background_tasks",
        "--cov=strategy.routers.strategies",
        "--cov-report=term"
    ])
    
    # Add HTML report if requested
    if html_report:
        cmd.append("--cov-report=html")
    
    # Determine which tests to run
    if test_type == "unit" or test_type == "all":
        cmd.extend([
            "tests/test_reliable_executor.py",
            "tests/test_key_manager.py"
        ])
    
    if test_type == "integration" or test_type == "all":
        cmd.extend([
            "tests/integration/test_order_execution_integration.py",
            "tests/integration/test_api_key_rotation_integration.py"
        ])
    
    if test_type == "api" or test_type == "all":
        cmd.append("tests/test_api_routes.py")
    
    # Print the command
    print(f"Running command: {' '.join(cmd)}")
    
    # Run the tests
    result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
    
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

def generate_report(coverage_data):
    """
    Generate a report of coverage data
    
    Args:
        coverage_data: Coverage data dictionary
        
    Returns:
        Report text
    """
    report = []
    report.append("=" * 80)
    report.append("CRITICAL TESTING COVERAGE REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append(f"Overall Coverage: {coverage_data['total']}%")
    report.append("")
    report.append("Component Coverage:")
    report.append("-" * 80)
    
    # Sort components by coverage (lowest first)
    sorted_components = sorted(
        coverage_data["components"].items(),
        key=lambda x: x[1]["coverage"]
    )
    
    for file_path, data in sorted_components:
        status = "✅" if data["coverage"] >= 70 else "❌"
        report.append(f"{status} {file_path}: {data['coverage']}% ({data['covered']}/{data['statements']})")
    
    report.append("-" * 80)
    report.append("")
    
    # Check if we've met the goal
    goal_met = coverage_data["total"] >= 70
    critical_components_met = all(
        coverage_data["components"].get(comp, {}).get("coverage", 0) >= 70
        for comp in CRITICAL_COMPONENTS
    )
    
    if goal_met and critical_components_met:
        report.append("🎉 SUCCESS: Coverage goal of 70% has been met for all critical components!")
    else:
        report.append("⚠️ WARNING: Coverage goal of 70% has not been met for all critical components.")
        report.append("")
        report.append("Components needing more tests:")
        for file_path, data in sorted_components:
            if data["coverage"] < 70 and file_path in CRITICAL_COMPONENTS:
                report.append(f"  - {file_path}: {data['coverage']}% (need {70 - data['coverage']}% more)")
    
    return "\n".join(report)

def save_report(report, coverage_data):
    """
    Save the report to a file
    
    Args:
        report: Report text
        coverage_data: Coverage data dictionary
    """
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
        json.dump(coverage_data, f, indent=2)
    
    print(f"Report saved to {report_path}")
    print(f"Coverage data saved to {json_path}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run critical tests and generate coverage report")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "api", "all"], 
        default="all",
        help="Type of tests to run (default: all)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show verbose output"
    )
    parser.add_argument(
        "--html", 
        action="store_true",
        help="Generate HTML coverage report"
    )
    parser.add_argument(
        "--save", 
        action="store_true",
        help="Save report to file"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"Running {args.type} tests for critical components")
    print("=" * 80)
    
    success, coverage_data = run_tests(args.type, args.verbose, args.html)
    
    if not success:
        print("Tests failed!")
        return 1
    
    report = generate_report(coverage_data)
    print("\n" + report)
    
    if args.save:
        save_report(report, coverage_data)
    
    # Return success based on coverage goal
    return 0 if coverage_data["total"] >= 70 else 1

if __name__ == "__main__":
    sys.exit(main())