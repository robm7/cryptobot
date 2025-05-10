import os
import sys
import unittest
import tempfile
import json
import time
import logging
from datetime import datetime
from unittest import mock

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from token_optimization_system import (
    process_logs, 
    store_in_memory, 
    track_token_usage, 
    preprocess_data,
    analyze_memory_entities, 
    check_token_usage,
    ensure_directories
)
from utils.log_processor import LogProcessor
from utils.token_optimizer import TokenOptimizer
from utils.mcp_wrapper import MCPWrapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Args:
    """Mock arguments class for testing"""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class TokenOptimizationIntegrationTest(unittest.TestCase):
    """
    Integration tests for the Token Optimization System.
    
    These tests verify that all components of the token optimization system
    work together correctly, and that the system consistently stays under
    the token limit of 76,659 tokens.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create temporary directories for tests
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.log_dir = os.path.join(cls.temp_dir.name, "logs")
        cls.output_dir = os.path.join(cls.temp_dir.name, "output")
        cls.storage_dir = os.path.join(cls.temp_dir.name, ".mcp_local_storage")
        
        # Create directories
        os.makedirs(cls.log_dir, exist_ok=True)
        os.makedirs(cls.output_dir, exist_ok=True)
        os.makedirs(cls.storage_dir, exist_ok=True)
        
        # Create test log files of different sizes
        cls.small_log_path = os.path.join(cls.log_dir, "small_test.log")
        cls.medium_log_path = os.path.join(cls.log_dir, "medium_test.log")
        cls.large_log_path = os.path.join(cls.log_dir, "large_test.log")
        
        # Generate test log files
        cls._generate_test_log(cls.small_log_path, size="small")
        cls._generate_test_log(cls.medium_log_path, size="medium")
        cls._generate_test_log(cls.large_log_path, size="large")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.temp_dir.cleanup()
    
    @classmethod
    def _generate_test_log(cls, path, size="small"):
        """
        Generate a test log file of the specified size.
        
        Args:
            path (str): Path to write the test log
            size (str): Size of the log file ("small", "medium", "large")
        """
        line_count = {
            "small": 100,
            "medium": 1000,
            "large": 10000
        }.get(size, a100)
        
        error_count = {
            "small": 5,
            "medium": 50,
            "large": 500
        }.get(size, 5)
        
        with open(path, 'w') as f:
            # Write regular log lines
            for i in range(line_count):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing item {i}\n")
                
                # Add some warnings
                if i % 20 == 0:
                    f.write(f"[WARNING] 2025-05-07 10:00:{i % 60:02d} - Resource usage high: {60 + i % 30}%\n")
                
                # Add some test failures
                if i % (line_count // error_count) == 0:
                    error_type = ["AssertionError", "ValueError", "TypeError", "ConnectionError", "KeyError"][i % 5]
                    test_file = ["test_exchange_clients.py", "test_auth_service.py", "test_data_service.py"][i % 3]
                    test_name = f"test_function_{i % 10}"
                    f.write(f"FAILED {test_file}::{test_name} - {error_type}: Test failed with error message {i}\n")
                    
                    # Add a traceback for some errors
                    if i % 2 == 0:
                        f.write("Traceback (most recent call last):\n")
                        f.write(f'  File "{test_file}", line {i % 100 + 10}, in {test_name}\n')
                        f.write("    result = client.execute_trade(symbol, quantity, price)\n")
                        f.write('  File "exchange/client.py", line 57, in execute_trade\n')
                        f.write("    response = self._send_request('POST', endpoint, data)\n")
                        f.write('  File "exchange/client.py", line 102, in _send_request\n')
                        f.write("    raise ConnectionError(f'Failed to connect to exchange: {err}')\n")
                        f.write(f"{error_type}: Test failed with detailed error message {i}\n\n")
        
        logger.info(f"Generated {size} test log with {line_count} lines at {path}")
    
    def setUp(self):
        """Set up for each test case"""
        # Create standard args for tests
        self.args = Args(
            log_file=self.small_log_path,
            output_dir=self.output_dir,
            max_log_size=5,
            max_logs=10,
            store_memory=False,
            analyze_memory=False,
            memory_query=None,
            token_budget=76659,
            track_usage=False,
            check_usage=False,
            preprocess=False,
            chunk_size=1000
        )
        
        # Patch MCP wrapper to use test storage location
        patcher = mock.patch.object(MCPWrapper, '_initialize_storage')
        self.mock_init_storage = patcher.start()
        self.addCleanup(patcher.stop)
        
        # Force local storage for tests
        patcher2 = mock.patch.object(MCPWrapper, '_check_mcp_availability', return_value=False)
        self.mock_check_mcp = patcher2.start()
        self.addCleanup(patcher2.stop)
        
        # Set up test storage locations
        for wrapper_instance in [MCPWrapper()]:
            wrapper_instance.memory_storage_path = os.path.join(self.storage_dir, "memory_entities.json")
            wrapper_instance.token_usage_path = os.path.join(self.storage_dir, "token_usage.json")
            
            # Initialize storage files
            with open(wrapper_instance.memory_storage_path, 'w') as f:
                json.dump({"entities": [], "relations": []}, f)
            with open(wrapper_instance.token_usage_path, 'w') as f:
                json.dump({
                    "budget": 76659,
                    "current_usage": 0,
                    "usage_history": []
                }, f)
    
    def test_end_to_end_processing_small_log(self):
        """Test complete processing pipeline with a small log file"""
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify basic processing worked
        self.assertIsNotNone(summary)
        self.assertIsNotNone(log_path)
        self.assertTrue(os.path.exists(log_path))
        self.assertGreater(summary["original_size"], 0)
        self.assertGreater(summary["processed_size"], 0)
        self.assertIn("error_types", summary)
        
        # Store in memory
        self.args.store_memory = True
        success = store_in_memory(summary, log_path, self.args)
        self.assertTrue(success)
        
        # Track token usage
        self.args.track_usage = True
        success, under_budget = track_token_usage(log_path, self.args)
        self.assertTrue(success)
        self.assertTrue(under_budget)
        
        # Verify token estimation was performed
        self.assertIn("estimated_tokens", summary)
        self.assertGreater(summary["estimated_tokens"], 0)
        self.assertLess(summary["estimated_tokens"], 76659)  # Should be under token limit
        
        # Check tokens stayed under limit
        self.assertFalse(summary.get("token_limit_reached", False))
    
    def test_processing_with_medium_log(self):
        """Test log processing with a medium sized log file"""
        self.args.log_file = self.medium_log_path
        self.args.token_budget = 76659
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing
        self.assertIsNotNone(summary)
        self.assertIsNotNone(log_path)
        self.assertGreater(summary["compression_ratio"], 0.5)  # Should have good compression
        self.assertLess(summary["estimated_tokens"], 76659)  # Should be under token limit
    
    def test_processing_with_large_log(self):
        """Test log processing with a large log file and token limit enforcement"""
        self.args.log_file = self.large_log_path
        self.args.token_budget = 30000  # Set lower budget to force limit
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Verify processing with token limit
        self.assertIsNotNone(summary)
        self.assertIsNotNone(log_path)
        self.assertLess(summary["estimated_tokens"], 30000)  # Should respect token budget
        self.assertTrue(summary.get("token_limit_reached", False))  # Should have hit limit
    
    def test_memory_server_integration(self):
        """Test integration with Memory Server (fallback implementation)"""
        self.args.store_memory = True
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Store in memory
        success = store_in_memory(summary, log_path, self.args)
        self.assertTrue(success)
        
        # Verify entities were stored
        with open(os.path.join(self.storage_dir, "memory_entities.json"), 'r') as f:
            storage = json.load(f)
            self.assertGreater(len(storage["entities"]), 0)
            self.assertGreater(len(storage["relations"]), 0)
        
        # Analyze stored entities
        self.args.analyze_memory = True
        analyze_memory_entities(self.args)  # Just verify it runs without errors
    
    def test_token_usage_tracking(self):
        """Test token usage tracking and budget enforcement"""
        self.args.track_usage = True
        self.args.token_budget = 50000
        
        # Process logs
        summary, log_path = process_logs(self.args)
        
        # Track token usage
        success, under_budget = track_token_usage(log_path, self.args)
        self.assertTrue(success)
        self.assertTrue(under_budget)
        
        # Verify usage was recorded
        with open(os.path.join(self.storage_dir, "token_usage.json"), 'r') as f:
            usage_data = json.load(f)
            self.assertGreater(usage_data["current_usage"], 0)
            self.assertEqual(usage_data["budget"], 50000)
            self.assertGreater(len(usage_data["usage_history"]), 0)
        
        # Check token usage
        self.args.check_usage = True
        check_token_usage(self.args)  # Just verify it runs without errors
    
    def test_data_preprocessing(self):
        """Test data preprocessing functionality"""
        self.args.preprocess = True
        self.args.chunk_size = 500
        
        # Preprocess data
        processed_data = preprocess_data(self.args)
        
        # Verify preprocessing worked
        self.assertIsNotNone(processed_data)
        self.assertIn("chunks_processed", processed_data)
        self.assertIn("total_lines", processed_data)
        self.assertIn("essential_info", processed_data)
        self.assertGreater(processed_data["chunks_processed"], 0)
        self.assertGreater(processed_data["total_lines"], 0)
    
    def test_benchmark_comparison(self):
        """Benchmark comparison between optimized and unoptimized processing"""
        # First measure unoptimized processing (simulate by reading entire file)
        start_time = time.time()
        with open(self.medium_log_path, 'r') as f:
            unoptimized_content = f.read()
        unoptimized_chars = len(unoptimized_content)
        unoptimized_time = time.time() - start_time
        
        # Now measure optimized processing
        self.args.log_file = self.medium_log_path
        start_time = time.time()
        summary, log_path = process_logs(self.args)
        optimized_time = time.time() - start_time
        
        # Check optimized file size
        with open(log_path, 'r') as f:
            optimized_content = f.read()
        optimized_chars = len(optimized_content)
        
        # Verify optimization metrics
        self.assertLess(optimized_chars, unoptimized_chars)
        compression_ratio = 1 - (optimized_chars / unoptimized_chars)
        logger.info(f"Character compression ratio: {compression_ratio:.2%}")
        logger.info(f"Unoptimized processing time: {unoptimized_time:.4f}s")
        logger.info(f"Optimized processing time: {optimized_time:.4f}s")
        logger.info(f"Time efficiency: {unoptimized_time / optimized_time:.2f}x")
        
        # Token estimates
        unoptimized_tokens = len(unoptimized_content) // 4
        optimized_tokens = summary["estimated_tokens"]
        token_reduction = 1 - (optimized_tokens / unoptimized_tokens)
        logger.info(f"Token reduction: {token_reduction:.2%}")
        
        # Verify substantial improvements
        self.assertGreater(compression_ratio, 0.3)  # At least 30% compression
        self.assertGreater(token_reduction, 0.3)    # At least 30% token reduction
        
        # Store benchmark results for reporting
        benchmark_results = {
            'unoptimized_size': unoptimized_chars,
            'optimized_size': optimized_chars,
            'compression_ratio': compression_ratio,
            'unoptimized_tokens': unoptimized_tokens,
            'optimized_tokens': optimized_tokens,
            'token_reduction': token_reduction,
            'unoptimized_time': unoptimized_time,
            'optimized_time': optimized_time,
            'time_efficiency': unoptimized_time / optimized_time
        }
        
        # Save benchmark results to file for historical tracking
        os.makedirs(os.path.join(self.temp_dir.name, "benchmarks"), exist_ok=True)
        benchmark_file = os.path.join(self.temp_dir.name, "benchmarks", f"benchmark_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
        with open(benchmark_file, 'w') as f:
            json.dump(benchmark_results, f, indent=2)
            
        logger.info(f"Benchmark results saved to {benchmark_file}")
    
    def test_log_rotation(self):
        """Test log rotation functionality"""
        # Set up log processor with small max_logs
        log_processor = LogProcessor(
            log_dir=self.output_dir,
            max_log_size_mb=1,
            max_logs=3
        )
        
        # Create several log files
        for i in range(5):
            # Process the log file
            summary, output_path = log_processor.process_log_file(self.small_log_path)
            self.assertTrue(os.path.exists(output_path))
        
        # Rotate logs
        log_processor.rotate_logs()
        
        # Count log files
        log_files = [f for f in os.listdir(self.output_dir) if f.startswith("processed_log_") and f.endswith(".log")]
        self.assertLessEqual(len(log_files), 3)
    
    def test_ensure_directories(self):
        """Test directory creation functionality"""
        # Delete test directories
        for dir_path in ["./logs", "./processed_data", "./.mcp_local_storage"]:
            full_path = os.path.join(self.temp_dir.name, dir_path.lstrip("./"))
            if os.path.exists(full_path):
                os.rmdir(full_path)
        
        # Call function to recreate them
        with mock.patch('os.path.exists', return_value=False):
            with mock.patch('os.makedirs') as mock_makedirs:
                ensure_directories()
                # Verify directories would be created
                self.assertEqual(mock_makedirs.call_count, 3)

class TokenOptimizationPerformanceTest(unittest.TestCase):
    """
    Performance tests for the Token Optimization System.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create temporary directories for tests
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.log_dir = os.path.join(cls.temp_dir.name, "logs")
        
        # Create directories
        os.makedirs(cls.log_dir, exist_ok=True)
        
        # Single extra large log file for performance testing
        cls.xl_log_path = os.path.join(cls.log_dir, "xl_test.log")
        
        # Only generate the large file if the test will run
        if os.environ.get('RUN_PERFORMANCE_TESTS', '0') == '1':
            logger.info("Generating extra large test log file - this may take a moment...")
            cls._generate_large_test_log(cls.xl_log_path, lines=100000)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.temp_dir.cleanup()
    
    @classmethod
    def _generate_large_test_log(cls, path, lines=100000):
        """Generate a very large test log file"""
        with open(path, 'w') as f:
            # Write regular log lines
            for i in range(lines):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing item {i}\n")
                
                # Add some warnings
                if i % 20 == 0:
                    f.write(f"[WARNING] 2025-05-07 10:00:{i % 60:02d} - Resource usage high: {60 + i % 30}%\n")
                
                # Add some test failures
                if i % 1000 == 0:
                    error_type = ["AssertionError", "ValueError", "TypeError", "ConnectionError", "KeyError"][i % 5]
                    test_file = ["test_exchange_clients.py", "test_auth_service.py", "test_data_service.py"][i % 3]
                    test_name = f"test_function_{i % 10}"
                    f.write(f"FAILED {test_file}::{test_name} - {error_type}: Test failed with error message {i}\n")
                    
                    # Add a traceback for some errors
                    if i % 2 == 0:
                        f.write("Traceback (most recent call last):\n")
                        f.write(f'  File "{test_file}", line {i % 100 + 10}, in {test_name}\n')
                        f.write("    result = client.execute_trade(symbol, quantity, price)\n")
                        f.write('  File "exchange/client.py", line 57, in execute_trade\n')
                        f.write("    response = self._send_request('POST', endpoint, data)\n")
                        f.write('  File "exchange/client.py", line 102, in _send_request\n')
                        f.write("    raise ConnectionError(f'Failed to connect to exchange: {err}')\n")
                        f.write(f"{error_type}: Test failed with detailed error message {i}\n\n")
        
        logger.info(f"Generated extra large test log with {lines} lines at {path}")
    
    @unittest.skipUnless(os.environ.get('RUN_PERFORMANCE_TESTS', '0') == '1',
                         "Performance tests are skipped by default")
    def test_large_file_performance(self):
        """
        Test system performance with a very large log file.
        
        This test is skipped by default and can be enabled by setting 
        the RUN_PERFORMANCE_TESTS=1 environment variable.
        """
        # Set up arguments
        args = Args(
            log_file=self.xl_log_path,
            output_dir=self.log_dir,
            max_log_size=10,
            max_logs=5,
            store_memory=False,
            analyze_memory=False,
            memory_query=None,
            token_budget=76659,
            track_usage=False,
            check_usage=False,
            preprocess=False,
            chunk_size=5000
        )
        
        # Measure memory usage before
        import psutil
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process logs and time it
        start_time = time.time()
        summary, log_path = process_logs(args)
        processing_time = time.time() - start_time
        
        # Measure memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        # Log performance metrics
        logger.info("===== Performance Metrics =====")
        logger.info(f"Log file size: {os.path.getsize(self.xl_log_path) / 1024 / 1024:.2f} MB")
        logger.info(f"Total processing time: {processing_time:.2f} seconds")
        logger.info(f"Lines processed: {summary['original_size']}")
        logger.info(f"Processing rate: {summary['original_size'] / processing_time:.2f} lines/second")
        logger.info(f"Memory increase: {memory_increase:.2f} MB")
        logger.info(f"Compression ratio: {summary['compression_ratio']:.2%}")
        logger.info(f"Estimated tokens: {summary['estimated_tokens']}")
        logger.info(f"Token efficiency: {summary['original_size'] / summary['estimated_tokens']:.2f} lines/token")
        
        # Verify performance metrics
        self.assertLess(processing_time, 60)  # Should process in under 60 seconds
        self.assertLess(memory_increase, 100)  # Should use less than 100MB additional memory
        self.assertLess(summary['estimated_tokens'], 76659)  # Should stay under token limit


    def test_unusual_content_types(self):
        """Test optimization with unusual content types"""
        # Create test files with unusual content
        json_log_path = os.path.join(self.log_dir, "json_test.log")
        xml_log_path = os.path.join(self.log_dir, "xml_test.log")
        mixed_log_path = os.path.join(self.log_dir, "mixed_test.log")
        
        # Generate JSON-like content
        with open(json_log_path, 'w') as f:
            for i in range(100):
                f.write(f'{{"timestamp": "2025-05-07T10:00:{i % 60:02d}", "level": "INFO", "message": "Processing item {i}", "data": {{"id": {i}, "status": "pending"}}}}\n')
                if i % 10 == 0:
                    f.write(f'{{"timestamp": "2025-05-07T10:00:{i % 60:02d}", "level": "ERROR", "message": "Failed to process item {i}", "error": "ConnectionError", "trace": "Simulated error trace for test purposes"}}\n')
        
        # Generate XML-like content
        with open(xml_log_path, 'w') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<logs>\n')
            for i in range(100):
                f.write(f'  <log>\n    <timestamp>2025-05-07T10:00:{i % 60:02d}</timestamp>\n    <level>INFO</level>\n    <message>Processing item {i}</message>\n  </log>\n')
                if i % 10 == 0:
                    f.write(f'  <log>\n    <timestamp>2025-05-07T10:00:{i % 60:02d}</timestamp>\n    <level>ERROR</level>\n    <message>Failed to process item {i}</message>\n    <error>ConnectionError</error>\n    <trace>Simulated error trace for test purposes</trace>\n  </log>\n')
            f.write('</logs>\n')
        
        # Generate mixed content
        with open(mixed_log_path, 'w') as f:
            f.write('=== Mixed Format Log File (Testing Unusual Content) ===\n\n')
            
            # Add some markdown
            f.write('# Test Results Summary\n\n')
            f.write('| Test | Result | Error |\n')
            f.write('|------|--------|-------|\n')
            for i in range(10):
                result = "PASS" if i % 3 != 0 else "FAIL"
                error = "" if i % 3 != 0 else "AssertionError"
                f.write(f'| Test {i} | {result} | {error} |\n')
            
            # Add some code blocks
            f.write('\n```python\n')
            f.write('def process_item(item):\n')
            f.write('    try:\n')
            f.write('        result = item.process()\n')
            f.write('        return result\n')
            f.write('    except Exception as e:\n')
            f.write('        logger.error(f"Error processing {item}: {e}")\n')
            f.write('        return None\n')
            f.write('```\n\n')
            
            # Add some regular logs
            for i in range(20):
                f.write(f'[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing item {i}\n')
                if i % 5 == 0:
                    f.write(f'[ERROR] 2025-05-07 10:00:{i % 60:02d} - Failed to process item {i}\n')
        
        # Test processing each file type
        for log_path, name in [
            (json_log_path, "JSON"),
            (xml_log_path, "XML"),
            (mixed_log_path, "Mixed")
        ]:
            # Set up args for this file
            self.args.log_file = log_path
            self.args.token_budget = 76659
            
            # Process the file
            logger.info(f"Testing {name} content optimization...")
            summary, output_path = process_logs(self.args)
            
            # Verify processing worked properly
            self.assertIsNotNone(summary)
            self.assertIn("estimated_tokens", summary)
            self.assertLess(summary["estimated_tokens"], 76659)
            
            logger.info(f"{name} content optimization: {summary['compression_ratio']:.2%} compression, {summary['estimated_tokens']} tokens")
    
    def test_edge_case_very_large_content(self):
        """Test optimization with extremely large individual entries"""
        # Create test file with some very large entries
        large_entry_path = os.path.join(self.log_dir, "large_entries.log")
        
        with open(large_entry_path, 'w') as f:
            # Write normal log entries
            for i in range(50):
                f.write(f"[INFO] 2025-05-07 10:00:{i % 60:02d} - Processing item {i}\n")
            
            # Write a single extremely large log entry (error trace)
            f.write("\n\nFAILED test_large_transaction.py::test_process_batch - ValueError: Transaction data corrupted\n")
            f.write("Traceback (most recent call last):\n")
            
            # Generate a very deep stack trace
            for i in range(100):
                f.write(f'  File "module{i}.py", line {i+10}, in function_{i}\n')
                f.write(f"    data_{i} = process_level_{i}(data_{i-1})\n")
            
            # Add a large error message with lots of data
            f.write("ValueError: Transaction data corrupted. Details:\n")
            for i in range(100):
                f.write(f"Field {i}: Expected format ABC-123-XYZ but got invalid format. ")
                f.write(f"Raw data: {{'id': {i}, 'timestamp': '2025-05-07T10:00:00', 'value': {i*10.5}, 'status': 'unknown'}}\n")
            
            # Add another normal section after the large entry
            for i in range(50, 100):
                f.write(f"[INFO] 2025-05-07 10:01:{i % 60:02d} - Processing item {i}\n")
        
        # Set up args for this file
        self.args.log_file = large_entry_path
        self.args.token_budget = 76659
        
        # Process the file
        summary, output_path = process_logs(self.args)
        
        # Verify processing handled the large entry properly
        self.assertIsNotNone(summary)
        self.assertIn("estimated_tokens", summary)
        self.assertLess(summary["estimated_tokens"], 76659)
        
        # Check for large entry optimization
        self.assertIn("large_entries_optimized", summary)
        self.assertGreater(summary.get("large_entries_optimized", 0), 0)
        
        # Check for stack trace summarization
        with open(output_path, 'r') as f:
            content = f.read()
            self.assertIn("Stack trace summarized", content)
            self.assertIn("100 frames", content)
    
    def test_predictive_token_usage(self):
        """Test the token usage prediction functionality"""
        # Create a sequence of progressively larger log files
        log_paths = []
        for i, size in enumerate([100, 200, 400, 800, 1600]):
            path = os.path.join(self.log_dir, f"growing_log_{i}.log")
            log_paths.append(path)
            
            # Generate log with specified size
            with open(path, 'w') as f:
                for j in range(size):
                    f.write(f"[INFO] 2025-05-07 10:00:{j % 60:02d} - Processing item {j}\n")
                    if j % 20 == 0:
                        f.write(f"[WARNING] 2025-05-07 10:00:{j % 60:02d} - Resource usage high: {60 + j % 30}%\n")
                    if j % 50 == 0:
                        f.write(f"FAILED test_case_{j}.py - AssertionError: Expected result but got error\n")
        
        # Process logs in sequence to build up historical data
        token_usage_history = []
        for log_path in log_paths:
            self.args.log_file = log_path
            self.args.track_usage = True
            
            # Process log and track token usage
            summary, output_path = process_logs(self.args)
            success, under_budget = track_token_usage(output_path, self.args)
            
            # Store token usage for this file
            token_usage_history.append(summary["estimated_tokens"])
        
        # Get prediction for next log size (should be exponential growth)
        # In a real implementation, the predict_token_usage function would use historical data
        # to make a prediction - we're testing that the prediction is reasonable
        
        # For testing, we'll mock a simple prediction based on the growth pattern
        predicted_tokens = token_usage_history[-1] * 2  # Simple doubling prediction
        
        # Check predictions are being made and stored
        with open(os.path.join(self.storage_dir, "token_usage.json"), 'r') as f:
            usage_data = json.load(f)
            self.assertIn("predictions", usage_data)
            self.assertIn("next_run", usage_data["predictions"])
            
            # Verify prediction is within 50% of our simple model (allowing for different algorithms)
            prediction_error = abs(usage_data["predictions"]["next_run"] - predicted_tokens) / predicted_tokens
            self.assertLess(prediction_error, 0.5)  # Prediction should be within 50% of our simple model
            
            # Verify alert thresholds are calculated
            self.assertIn("alert_threshold", usage_data["predictions"])
            self.assertIn("warning_threshold", usage_data["predictions"])


if __name__ == '__main__':
    unittest.main()