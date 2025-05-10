"""
Test script for the Update Manager.

This script tests the functionality of the Update Manager.
"""

import os
import sys
import json
import logging
import tempfile
import unittest
import shutil
from unittest.mock import patch, MagicMock

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from core.update_manager.manager import UpdateManager
from core.update_manager.config_schema import DEFAULT_UPDATE_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class MockResponse:
    """Mock response for urlopen."""
    
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
    
    def read(self):
        return self.data
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestUpdateManager(unittest.TestCase):
    """Test cases for the Update Manager."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
        # Create a test configuration
        self.config = DEFAULT_UPDATE_CONFIG.copy()
        self.config["update"]["update_url"] = "https://test.example.com/updates"
        
        # Create the update manager
        self.update_manager = UpdateManager(self.config, app_dir=self.test_dir)
        
        # Create version file
        with open(os.path.join(self.test_dir, "version.txt"), "w") as f:
            f.write("1.0.0")
    
    def tearDown(self):
        """Clean up the test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
    
    @patch("core.update_manager.manager.urlopen")
    def test_check_for_updates_no_update(self, mock_urlopen):
        """Test checking for updates when no update is available."""
        # Mock the response
        mock_response = MockResponse(json.dumps({
            "latest_version": "1.0.0",
            "release_notes": "No changes",
            "release_date": "2025-05-10",
            "download_size": "10 MB",
            "critical": False,
            "downloads": {
                "windows-x64": "https://test.example.com/downloads/cryptobot-1.0.0-win-x64.zip",
                "macos-x64": "https://test.example.com/downloads/cryptobot-1.0.0-mac-x64.zip",
                "linux-x64": "https://test.example.com/downloads/cryptobot-1.0.0-linux-x64.tar.gz"
            },
            "checksums": {
                "cryptobot-1.0.0-win-x64.zip": "abcdef1234567890",
                "cryptobot-1.0.0-mac-x64.zip": "abcdef1234567890",
                "cryptobot-1.0.0-linux-x64.tar.gz": "abcdef1234567890"
            }
        }).encode("utf-8"))
        mock_urlopen.return_value = mock_response
        
        # Check for updates
        result = self.update_manager.check_for_updates(force=True)
        
        # Verify the result
        self.assertFalse(result)
        self.assertFalse(self.update_manager._update_available)
        self.assertEqual(self.update_manager._latest_version, "1.0.0")
    
    @patch("core.update_manager.manager.urlopen")
    def test_check_for_updates_with_update(self, mock_urlopen):
        """Test checking for updates when an update is available."""
        # Mock the response
        mock_response = MockResponse(json.dumps({
            "latest_version": "1.1.0",
            "release_notes": "New features and bug fixes",
            "release_date": "2025-05-10",
            "download_size": "10 MB",
            "critical": False,
            "downloads": {
                "windows-x64": "https://test.example.com/downloads/cryptobot-1.1.0-win-x64.zip",
                "macos-x64": "https://test.example.com/downloads/cryptobot-1.1.0-mac-x64.zip",
                "linux-x64": "https://test.example.com/downloads/cryptobot-1.1.0-linux-x64.tar.gz"
            },
            "checksums": {
                "cryptobot-1.1.0-win-x64.zip": "abcdef1234567890",
                "cryptobot-1.1.0-mac-x64.zip": "abcdef1234567890",
                "cryptobot-1.1.0-linux-x64.tar.gz": "abcdef1234567890"
            }
        }).encode("utf-8"))
        mock_urlopen.return_value = mock_response
        
        # Check for updates
        result = self.update_manager.check_for_updates(force=True)
        
        # Verify the result
        self.assertTrue(result)
        self.assertTrue(self.update_manager._update_available)
        self.assertEqual(self.update_manager._latest_version, "1.1.0")
    
    def test_version_comparison(self):
        """Test version comparison logic."""
        # Test cases
        test_cases = [
            # version1, version2, expected result
            ("1.0.0", "1.0.0", False),  # Equal versions
            ("1.0.0", "1.0.1", False),  # Older version
            ("1.0.1", "1.0.0", True),   # Newer version
            ("1.1.0", "1.0.0", True),   # Newer major version
            ("2.0.0", "1.0.0", True),   # Newer major version
            ("1.0.0", "1.1.0", False),  # Older major version
            ("1.0.0", "2.0.0", False),  # Older major version
            ("1.0.0", "0.9.0", True),   # Newer than older version
            ("0.9.0", "1.0.0", False),  # Older than newer version
            ("1.0.0", "1.0", True),     # More specific version
            ("1.0", "1.0.0", False),    # Less specific version
            ("1.0.0.1", "1.0.0", True), # More specific newer version
            ("1.0.0", "1.0.0.1", False) # Less specific older version
        ]
        
        # Run test cases
        for version1, version2, expected in test_cases:
            result = self.update_manager._is_newer_version(version1, version2)
            self.assertEqual(result, expected, f"Failed for {version1} > {version2}")
    
    def test_get_update_info(self):
        """Test getting update information."""
        # Set up test data
        self.update_manager._current_version = "1.0.0"
        self.update_manager._latest_version = "1.1.0"
        self.update_manager._update_available = True
        self.update_manager._update_downloaded = False
        self.update_manager._update_info = {
            "latest_version": "1.1.0",
            "release_notes": "New features and bug fixes",
            "release_date": "2025-05-10",
            "download_size": "10 MB",
            "critical": False
        }
        
        # Get update info
        update_info = self.update_manager.get_update_info()
        
        # Verify the result
        self.assertEqual(update_info["current_version"], "1.0.0")
        self.assertEqual(update_info["latest_version"], "1.1.0")
        self.assertTrue(update_info["update_available"])
        self.assertFalse(update_info["update_downloaded"])
        self.assertEqual(update_info["release_notes"], "New features and bug fixes")
        self.assertEqual(update_info["release_date"], "2025-05-10")
        self.assertEqual(update_info["download_size"], "10 MB")
        self.assertFalse(update_info["critical_update"])


def run_tests():
    """Run the tests."""
    unittest.main()


def simulate_update_server():
    """
    Simulate an update server for manual testing.
    
    This function creates a simple HTTP server that simulates an update server.
    It responds to update check requests with a mock update response.
    """
    import http.server
    import socketserver
    
    class UpdateHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            request_data = json.loads(post_data)
            
            # Get the current version from the request
            current_version = request_data.get("version", "1.0.0")
            
            # Create a response with a newer version
            version_parts = current_version.split(".")
            version_parts[-1] = str(int(version_parts[-1]) + 1)
            new_version = ".".join(version_parts)
            
            response = {
                "latest_version": new_version,
                "release_notes": f"Upgrade from {current_version} to {new_version}\n\nNew features:\n- Feature 1\n- Feature 2\n\nBug fixes:\n- Bug 1\n- Bug 2",
                "release_date": "2025-05-10",
                "download_size": "10 MB",
                "critical": False,
                "downloads": {
                    "windows-x64": f"https://test.example.com/downloads/cryptobot-{new_version}-win-x64.zip",
                    "macos-x64": f"https://test.example.com/downloads/cryptobot-{new_version}-mac-x64.zip",
                    "linux-x64": f"https://test.example.com/downloads/cryptobot-{new_version}-linux-x64.tar.gz"
                },
                "checksums": {
                    f"cryptobot-{new_version}-win-x64.zip": "abcdef1234567890",
                    f"cryptobot-{new_version}-mac-x64.zip": "abcdef1234567890",
                    f"cryptobot-{new_version}-linux-x64.tar.gz": "abcdef1234567890"
                }
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    # Create and start the server
    PORT = 8000
    with socketserver.TCPServer(("", PORT), UpdateHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print(f"Use this URL in your update configuration:")
        print(f"  \"update_url\": \"http://localhost:{PORT}\"")
        httpd.serve_forever()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Update Manager")
    parser.add_argument("--server", action="store_true", help="Run a simulated update server")
    parser.add_argument("--test", action="store_true", help="Run the tests")
    
    args = parser.parse_args()
    
    if args.server:
        simulate_update_server()
    elif args.test:
        run_tests()
    else:
        # If no arguments are provided, run the tests
        run_tests()