"""
Simple Integration Test

This module contains a simple integration test that can be used to verify
that the integration testing framework is set up correctly.
"""

import pytest
import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.framework.base import IntegrationTestBase


class TestSimpleIntegration(IntegrationTestBase):
    """
    Simple integration test to verify the testing framework.
    
    This test doesn't depend on many external components and can be used
    to verify that the integration testing framework is set up correctly.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up the test class."""
        super().setup_class()
        
        # Create a temporary file for testing
        cls.temp_file_path = os.path.join(os.path.dirname(__file__), "temp_test_file.json")
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
        
        super().teardown_class()
    
    @pytest.mark.integration
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
    
    @pytest.mark.integration
    def test_simple_calculation(self):
        """Test a simple calculation."""
        # Perform a simple calculation
        result = sum(self.test_data["values"])
        
        # Verify result
        assert result == 15
    
    @pytest.mark.integration
    def test_environment_variables(self):
        """Test environment variables."""
        # Get environment variables
        python_path = os.environ.get("PYTHONPATH", "")
        
        # Verify environment
        assert isinstance(python_path, str)
        
        # Get current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Verify current directory
        assert os.path.exists(current_dir)
        assert "integration" in current_dir


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])