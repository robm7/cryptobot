"""
Standalone Integration Test

This module contains a standalone integration test that doesn't depend on
the project's conftest.py file. It can be used to verify that the integration
testing framework is set up correctly.
"""

import pytest
import os
import sys
import json
import tempfile
from datetime import datetime

class TestStandalone:
    """
    Standalone integration test that doesn't depend on the project's conftest.py.
    
    This test can be used to verify that the integration testing framework
    is set up correctly without being affected by issues in the main project's
    test configuration.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        # Create a temporary file for testing
        cls.temp_dir = tempfile.mkdtemp()
        cls.temp_file_path = os.path.join(cls.temp_dir, "test_data.json")
        cls.test_data = {
            "name": "Test Data",
            "timestamp": datetime.now().isoformat(),
            "values": [1, 2, 3, 4, 5]
        }
        
        # Write test data to file
        with open(cls.temp_file_path, "w") as f:
            json.dump(cls.test_data, f, indent=2)
    
    @classmethod
    def teardown_class(cls):
        """Tear down the test class."""
        # Remove temporary file
        if os.path.exists(cls.temp_file_path):
            os.remove(cls.temp_file_path)
        
        # Remove temporary directory
        if os.path.exists(cls.temp_dir):
            os.rmdir(cls.temp_dir)
    
    def test_file_operations(self):
        """Test simple file operations."""
        # Verify file exists
        assert os.path.exists(self.temp_file_path)
        
        # Read file
        with open(self.temp_file_path, "r") as f:
            data = json.load(f)
        
        # Verify data
        assert data["name"] == "Test Data"
        assert "timestamp" in data
        assert data["values"] == [1, 2, 3, 4, 5]
    
    def test_simple_calculation(self):
        """Test a simple calculation."""
        # Perform a simple calculation
        result = sum(self.test_data["values"])
        
        # Verify result
        assert result == 15
    
    def test_environment(self):
        """Test environment."""
        # Get current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Verify current directory
        assert os.path.exists(current_dir)
        assert "integration" in current_dir


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])