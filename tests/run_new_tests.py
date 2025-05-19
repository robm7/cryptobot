"""
Simple test runner for the new test files.
This script runs the tests directly without using pytest's discovery mechanism,
which would try to load conftest.py and other files that might have dependencies.
"""

import unittest
import sys
import importlib.util
import os

def load_module_from_file(file_path, module_name):
    """Load a module from a file path"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def run_tests_from_file(file_path):
    """Run tests from a file"""
    # Extract module name from file path
    module_name = os.path.basename(file_path).replace('.py', '')
    
    # Load the module
    try:
        module = load_module_from_file(file_path, module_name)
        
        # Create a test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        # Run the tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
    except Exception as e:
        print(f"Error loading module {module_name}: {e}")
        return False

if __name__ == "__main__":
    # List of test files to run
    test_files = [
        "test_performance_metrics_validation.py",
        "test_position_sizing_scenarios.py",
        "test_exchange_integration_advanced.py",
        "test_error_handling_verification.py"
    ]
    
    # Run each test file
    success = True
    for file in test_files:
        print(f"\n\n{'='*80}\nRunning tests from {file}\n{'='*80}")
        if not run_tests_from_file(file):
            success = False
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)