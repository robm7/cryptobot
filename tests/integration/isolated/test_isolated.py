"""
Isolated Integration Test

This module contains an isolated integration test that doesn't depend on
any project files. It can be used to verify that the integration testing
framework is set up correctly.
"""

import pytest
import os
import sys
import json
import tempfile
from datetime import datetime

def test_simple_calculation():
    """Test a simple calculation."""
    # Perform a simple calculation
    values = [1, 2, 3, 4, 5]
    result = sum(values)
    
    # Verify result
    assert result == 15

def test_file_operations():
    """Test simple file operations."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file_path = temp_file.name
        
        # Create test data
        test_data = {
            "name": "Test Data",
            "timestamp": datetime.now().isoformat(),
            "values": [1, 2, 3, 4, 5]
        }
        
        # Write test data to file
        json.dump(test_data, temp_file)
    
    try:
        # Verify file exists
        assert os.path.exists(temp_file_path)
        
        # Read file
        with open(temp_file_path, "r") as f:
            data = json.load(f)
        
        # Verify data
        assert data["name"] == "Test Data"
        assert "timestamp" in data
        assert data["values"] == [1, 2, 3, 4, 5]
    finally:
        # Remove temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def test_environment():
    """Test environment."""
    # Get current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Verify current directory
    assert os.path.exists(current_dir)
    assert "isolated" in current_dir

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])