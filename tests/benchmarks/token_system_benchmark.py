#!/usr/bin/env python
"""
Comprehensive Benchmarking Suite for Token Optimization System

This benchmark suite measures:
1. Processing speed improvements
2. Memory usage efficiency
3. Token efficiency gains
4. Visualization of results

Uses pytest-benchmark, memory_profiler, and matplotlib for various metrics.
"""

import os
import sys
import time
import json
import pytest
import random
import logging
import tempfile
import statistics
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from datetime import datetime
from pathlib import Path
from memory_profiler import profile, memory_usage
from functools import wraps, partial
from typing import Dict, List, Tuple, Any, Callable, Optional, Union
import gc
import psutil
import tracemalloc
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import token optimization system components
from utils.token_optimizer import TokenOptimizer
from utils.enhanced_token_optimizer import EnhancedTokenOptimizer
from utils.log_processor import LogProcessor
from utils.data_preprocessor import DataPreprocessor
from utils.stream_log_processor import StreamLogProcessor
from utils.token_budget_manager import TokenBudgetManager
import token_optimization_system as tos

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Benchmark configuration
BENCHMARK_CONFIG = {
    "token_budget": 75000,
    "file_sizes": {
        "small": 1000,    # 1K lines
        "medium": 10000,  # 10K lines
        "large": 50000    # 50K lines
    },
    "repetitions": 5,
    "content_types": ["errors", "logs", "mixed"],
    "report_dir": "benchmark_reports",
    "historical_data_file": "benchmark_history.json",
    "memory_leak_threshold": 5.0,  # Percent increase that indicates potential leak
    "component_breakdown": True,   # Enable detailed component breakdown
}


class BenchmarkUtils:
    """Utility methods for benchmarking token optimization system."""
    
    @staticmethod
    def generate_test_data(size: int, content_type: str = "mixed") -> str:
        """
        Generate synthetic test data for benchmarking.
        
        Args:
            size: Number of lines to generate
            content_type: Type of content (errors, logs, mixed)
            
        Returns:
            Path to generated test file
        """
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.log')
        os.close(fd)
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            # Generate different types of content based on content_type
            if content_type == "errors":
                f.write(BenchmarkUtils._generate_error_content(size))
            elif content_type == "logs":
                f.write(BenchmarkUtils._generate_log_content(size))
            else:  # mixed
                f.write(BenchmarkUtils._generate_mixed_content(size))
        
        return temp_path
    
    @staticmethod
    def generate_realistic_test_data(size: int, sample_logs_path: Optional[str] = None) -> str:
        """
        Generate more realistic test data based on sample logs if available.
        
        Args:
            size: Number of lines to generate
            sample_logs_path: Path to sample real log file to base generation on
            
        Returns:
            Path to generated test file
        """
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(suffix='.log')
        os.close(fd)
        
        # If sample logs are provided, use them as a template
        if sample_logs_path and os.path.exists(sample_logs_path):
            try:
                with open(sample_logs_path, 'r', encoding='utf-8', errors='ignore') as sample:
                    # Read sample lines
                    sample_lines = sample.readlines()
                    
                if not sample_lines:
                    # Fall back to synthetic data if sample is empty
                    return BenchmarkUtils.generate_test_data(size, "mixed")
                
                # Generate based on sample patterns
                with open(temp_path, 'w', encoding='utf-8') as f:
                    # Write random selections from sample file, with some modifications
                    for _ in range(size):
                        line = random.choice(sample_lines).strip()
                        
                        # Maybe modify timestamp
                        if any(time_part in line for time_part in [":", "T", "Z", "-", "/"]):
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                            # Simple attempt to replace timestamp-like portions
                            parts = line.split(" ", 1)
                            if len(parts) > 1:
                                line = f"{timestamp} {parts[1]}"
                        
                        f.write(line + "\n")
                
                return temp_path
            except Exception as e:
                logger.warning(f"Failed to generate realistic test data: {e}. Falling back to synthetic.")
                # Fall back to synthetic on error
                return BenchmarkUtils.generate_test_data(size, "mixed")
        else:
            # Fall back to synthetic if no sample logs
            return BenchmarkUtils.generate_test_data(size, "mixed")
    
    @staticmethod
    def _generate_error_content(size: int) -> str:
        """Generate synthetic error traces and exceptions."""
        error_types = [
            "ValueError", "TypeError", "KeyError", "IndexError", 
            "AttributeError", "ImportError", "RuntimeError", "ZeroDivisionError"
        ]
        
        content = []
        for i in range(size):
            # Randomly decide if this line is an error trace start
            if random.random() < 0.05:  # 5% chance of error
                error_type = random.choice(error_types)
                
                # Add traceback
                content.append("Traceback (most recent call last):")
                content.append(f'  File "test_file.py", line {random.randint(1, 500)}, in test_function')
                content.append('    some_function_call()')
                content.append(f'  File "another_file.py", line {random.randint(1, 500)}, in some_function')
                content.append('    another_function()')
                content.append(f'  File "third_file.py", line {random.randint(1, 500)}, in another_function')
                content.append('    problematic_code()')
                content.append(f'{error_type}: Error message describing the problem')
            else:
                # Add regular log line
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                content.append(f"{timestamp} - test_module - INFO - Regular log message #{i}")
        
        return "\n".join(content)
    
    @staticmethod
    def _generate_log_content(size: int) -> str:
        """Generate synthetic log content with different log levels."""
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        modules = ["auth", "api", "database", "network", "processor", "client"]
        
        content = []
        for i in range(size):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
            level = random.choice(log_levels)
            module = random.choice(modules)
            
            if level == "ERROR" or level == "CRITICAL":
                message = f"An error occurred while processing request #{i}: Connection timed out"
            elif level == "WARNING":
                message = f"Slow database query detected on request #{i}"
            else:
                message = f"Processing request #{i} completed successfully"
            
            content.append(f"{timestamp} - {module} - {level} - {message}")
        
        return "\n".join(content)
    
    @staticmethod
    def _generate_mixed_content(size: int) -> str:
        """Generate mixed content with logs, errors, and test results."""
        content = []
        test_passed = 0
        test_failed = 0
        
        for i in range(size):
            # Randomly decide content type for this line
            content_type = random.choices(
                ["log", "error", "test_result", "blank"],
                weights=[0.7, 0.1, 0.1, 0.1]
            )[0]
            
            if content_type == "log":
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
                level = random.choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
                module = random.choice(["auth", "api", "database", "network", "processor"])
                message = f"Message #{i} for testing token optimization"
                content.append(f"{timestamp} - {module} - {level} - {message}")
            
            elif content_type == "error":
                if random.random() < 0.7:  # 70% chance for traceback
                    content.append("Traceback (most recent call last):")
                    content.append(f'  File "test_file.py", line {random.randint(1, 500)}, in test_function')
                    content.append('    some_function()')
                    content.append(f'{random.choice(["ValueError", "KeyError", "RuntimeError"])}: Error in test')
                else:
                    content.append(f"ERROR: Something went wrong in operation #{i}")
            
            elif content_type == "test_result":
                if random.random() < 0.8:  # 80% pass rate
                    content.append(f"PASSED tests/test_module.py::test_function_{i}")
                    test_passed += 1
                else:
                    content.append(f"FAILED tests/test_module.py::test_function_{i}")
                    content.append(f"AssertionError: Expected result not found")
                    test_failed += 1
            
            else:  # blank line
                content.append("")
        
        # Add a summary section at the end
        content.append("\n=== Test Results Summary ===")
        content.append(f"Tests Passed: {test_passed}")
        content.append(f"Tests Failed: {test_failed}")
        content.append(f"Total Tests: {test_passed + test_failed}")
        
        return "\n".join(content)
    
    @staticmethod
    def measure_execution_time(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
        """
        Measure execution time of a function.
        
        Args:
            func: Function to measure
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            tuple: (function result, execution time in seconds)
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def calculate_token_efficiency(original_content: str, processed_content: str) -> Dict[str, float]:
        """
        Calculate token efficiency metrics.
        
        Args:
            original_content: Original content
            processed_content: Processed content
            
        Returns:
            Dict containing efficiency metrics
        """
        # Simple token estimation (chars / 4)
        original_tokens = len(original_content) // 4
        processed_tokens = len(processed_content) // 4
        
        # Calculate metrics
        token_reduction = original_tokens - processed_tokens
        token_reduction_percentage = (token_reduction / original_tokens) * 100 if original_tokens > 0 else 0
        
        # More accurate token estimation
        original_tokens_accurate = TokenOptimizer._estimate_tokens(original_content) if hasattr(TokenOptimizer, '_estimate_tokens') else tos.estimate_tokens(original_content)
        processed_tokens_accurate = TokenOptimizer._estimate_tokens(processed_content) if hasattr(TokenOptimizer, '_estimate_tokens') else tos.estimate_tokens(processed_content)
        
        token_reduction_accurate = original_tokens_accurate - processed_tokens_accurate
        token_reduction_percentage_accurate = (token_reduction_accurate / original_tokens_accurate) * 100 if original_tokens_accurate > 0 else 0
        
        # Analyze token distribution by content type
        token_distribution = {
            "test_failures": 0,
            "error_traces": 0,
            "regular_logs": 0,
            "metadata": 0
        }
        
        # Estimate distribution based on keywords
        if "FAILED" in processed_content:
            token_distribution["test_failures"] = len("\n".join(line for line in processed_content.split("\n") if "FAILED" in line)) // 4
        
        if "Traceback" in processed_content:
            error_lines = []
            in_traceback = False
            for line in processed_content.split("\n"):
                if "Traceback" in line:
                    in_traceback = True
                    error_lines.append(line)
                elif in_traceback:
                    if any(err in line for err in ["Error", "Exception"]):
                        error_lines.append(line)
                        in_traceback = False
                    else:
                        error_lines.append(line)
            token_distribution["error_traces"] = len("\n".join(error_lines)) // 4
        
        # Regular logs (approximation)
        token_distribution["metadata"] = len("\n".join(line for line in processed_content.split("\n") if line.startswith("==="))) // 4
        token_distribution["regular_logs"] = processed_tokens - sum(token_distribution.values())
        if token_distribution["regular_logs"] < 0:
            token_distribution["regular_logs"] = 0
        
        return {
            "original_tokens": original_tokens,
            "processed_tokens": processed_tokens,
            "token_reduction": token_reduction,
            "token_reduction_percentage": token_reduction_percentage,
            "original_tokens_accurate": original_tokens_accurate,
            "processed_tokens_accurate": processed_tokens_accurate,
            "token_reduction_accurate": token_reduction_accurate,
            "token_reduction_percentage_accurate": token_reduction_percentage_accurate,
            "token_distribution": token_distribution,
            "information_density": processed_tokens_accurate / len(processed_content.split("\n")) if processed_content.split("\n") else 0,
        }
    
    @staticmethod
    def measure_memory_usage(func: Callable, *args, **kwargs) -> Tuple[Any, List[float], Dict[str, Any]]:
        """
        Measure memory usage of a function with enhanced leak detection.
        
        Args:
            func: Function to measure
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            tuple: (function result, list of memory usage samples in MB, memory details dict)
        """
        # Force garbage collection before measurement
        gc.collect()
        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Start tracemalloc for detailed memory tracking
        tracemalloc.start()
        
        # Use memory_usage from memory_profiler
        mem_usage = []
        
        def wrapper():
            return func(*args, **kwargs)
        
        mem_usage = memory_usage(
            (wrapper, (), {}),
            interval=0.1,
            timeout=None,
            max_iterations=None,
            include_children=True,
            multiprocess=True
        )
        
        # Get tracemalloc snapshot
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        # Stop tracemalloc
        tracemalloc.stop()
        
        # Run function and get result
        result = func(*args, **kwargs)
        
        # Force garbage collection after measurement
        gc.collect()
        end_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Check for potential memory leaks
        memory_diff = end_memory - start_memory
        potential_leak = memory_diff > (start_memory * BENCHMARK_CONFIG["memory_leak_threshold"] / 100)
        
        # Detailed memory statistics
        memory_details = {
            "start_memory_mb": start_memory,
            "end_memory_mb": end_memory,
            "memory_diff_mb": memory_diff,
            "potential_leak": potential_leak,
            "top_memory_allocations": [
                {
                    "file": stat.traceback[0].filename,
                    "line": stat.traceback[0].lineno,
                    "size_kb": stat.size / 1024
                }
                for stat in top_stats[:5]  # Top 5 memory allocations
            ]
        }
        
        return result, mem_usage, memory_details
    
    @staticmethod
    def measure_component_times(func: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, float]]:
        """
        Measure execution time of individual components within a function.
        Requires functions to report timing via a specific pattern in log messages.
        
        Args:
            func: Function to measure
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            tuple: (function result, dict of component timings)
        """
        # Create a custom handler to capture log messages with timing information
        class TimingLogHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.timing_logs = []
            
            def emit(self, record):
                if hasattr(record, 'timing'):
                    self.timing_logs.append((record.timing, record.getMessage()))
                elif 'took ' in record.getMessage() and ' seconds' in record.getMessage():
                    # Try to extract timing information from message
                    try:
                        msg = record.getMessage()
                        component = msg.split('took ')[0].strip()
                        seconds = float(msg.split('took ')[1].split(' seconds')[0].strip())
                        self.timing_logs.append((component, seconds))
                    except:
                        pass
        
        # Add handler to root logger
        handler = TimingLogHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        
        # Run function
        start_time = time.time()
        result = func(*args, **kwargs)
        total_time = time.time() - start_time
        
        # Remove handler
        root_logger.removeHandler(handler)
        
        # Process timing logs
        component_times = {}
        for component, seconds in handler.timing_logs:
            if component in component_times:
                component_times[component] += seconds
            else:
                component_times[component] = seconds
        
        # Add total time
        component_times['total'] = total_time
        
        # Calculate unaccounted time
        accounted_time = sum(t for c, t in component_times.items() if c != 'total')
        component_times['unaccounted'] = total_time - accounted_time
        
        return result, component_times
    
    @staticmethod
    def verify_output_quality(original_content: str, processed_content: str) -> Dict[str, Any]:
        """
        Verify that output maintains essential information.
        
        Args:
            original_content: Original content
            processed_content: Processed content
            
        Returns:
            Dict containing quality metrics
        """
        # Extract key information patterns
        def extract_patterns(content):
            patterns = {
                "errors": [],
                "test_failures": [],
                "warnings": [],
                "critical_logs": []
            }
            
            lines = content.split('\n')
            for line in lines:
                if "Error:" in line or "Exception:" in line:
                    patterns["errors"].append(line)
                elif "FAILED" in line and "test" in line:
                    patterns["test_failures"].append(line)
                elif "WARNING" in line:
                    patterns["warnings"].append(line)
                elif "CRITICAL" in line:
                    patterns["critical_logs"].append(line)
            
            return patterns
        
        original_patterns = extract_patterns(original_content)
        processed_patterns = extract_patterns(processed_content)
        
        # Calculate retention metrics
        retention = {}
        for pattern_type in original_patterns:
            if not original_patterns[pattern_type]:
                retention[pattern_type] = 100.0  # Nothing to retain
                continue
                
            # For errors and test failures, we want exact matches
            if pattern_type in ["errors", "test_failures"]:
                # Count how many original patterns are preserved in processed content
                preserved = 0
                for pattern in original_patterns[pattern_type]:
                    if any(pattern in p for p in processed_patterns[pattern_type]):
                        preserved += 1
                
                retention[pattern_type] = (preserved / len(original_patterns[pattern_type])) * 100
            else:
                # For warnings and criticals, we just care about count
                original_count = len(original_patterns[pattern_type])
                processed_count = len(processed_patterns[pattern_type])
                retention[pattern_type] = (min(processed_count, original_count) / original_count) * 100 if original_count > 0 else 100.0
        
        # Overall score: weighted average of retention metrics
        weights = {"errors": 0.4, "test_failures": 0.4, "warnings": 0.1, "critical_logs": 0.1}
        overall_score = sum(retention[k] * weights[k] for k in weights)
        
        return {
            "retention": retention,
            "overall_quality_score": overall_score,
            "original_pattern_counts": {k: len(v) for k, v in original_patterns.items()},
            "processed_pattern_counts": {k: len(v) for k, v in processed_patterns.items()}
        }
    
    @staticmethod
    def ensure_report_dir():
        """Ensure the report directory exists."""
        report_dir = BENCHMARK_CONFIG["report_dir"]
        os.makedirs(report_dir, exist_ok=True)
        return report_dir
    
    @staticmethod
    @contextmanager
    def track_throughput(size):
        """
        Context manager to track throughput (lines/sec or tokens/sec).
        
        Args:
            size: Number of lines being processed
            
        Yields:
            Dict to store timing results
        """
        result = {}
        start_time = time.time()
        yield result
        end_time = time.time()
        
        elapsed = end_time - start_time
        result["elapsed_seconds"] = elapsed
        result["lines_per_second"] = size / elapsed if elapsed > 0 else 0
        # Token throughput will be added by the caller if available


class TokenOptimizationBenchmark:
    """
    Main benchmark class for token optimization system.
    """
    
    def __init__(self):
        self.config = BENCHMARK_CONFIG
        self.utils = BenchmarkUtils
        self.results = {
            "speed": {},
            "memory": {},
            "token_efficiency": {},
            "component_timings": {},
            "throughput": {},
            "quality": {}
        }
        self.report_dir = self.utils.ensure_report_dir()
        self.historical_data = self._load_historical_data()
        
    def _load_historical_data(self):
        """Load historical benchmark data if available."""
        history_path = os.path.join(self.report_dir, self.config["historical_data_file"])
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load historical data: {e}")
        
        # Initialize empty history if file doesn't exist or loading fails
        return {
            "runs": [],
            "trends": {
                "speed": [],
                "memory": [],
                "token_efficiency": []
            }
        }
    
    def _save_historical_data(self):
        """Save historical benchmark data."""
        history_path = os.path.join(self.report_dir, self.config["historical_data_file"])
        
        # Add current run summary to history
        timestamp = datetime.now().isoformat()
        
        # Extract key metrics for historical tracking
        run_summary = {
            "timestamp": timestamp,
            "speed": {},
            "memory": {},
            "token_efficiency": {}
        }
        
        # Speed metrics (medium files, mixed content)
        if "medium" in self.results["speed"] and "mixed" in self.results["speed"]["medium"]:
            run_summary["speed"] = {
                "speedup": self.results["speed"]["medium"]["mixed"].get("speedup", 1.0),
                "original_lps": self.results["speed"]["medium"]["mixed"].get("original_mean", 0),
                "enhanced_lps": self.results["speed"]["medium"]["mixed"].get("enhanced_mean", 0)
            }
        
        # Memory metrics (medium files)
        if "medium" in self.results["memory"]:
            run_summary["memory"] = {
                "reduction_percentage": self.results["memory"]["medium"].get("memory_reduction_percentage", 0),
                "batch_peak_mb": self.results["memory"]["medium"]["batch"].get("peak", 0),
                "stream_peak_mb": self.results["memory"]["medium"]["stream"].get("peak", 0)
            }
        
        # Token efficiency metrics (medium files, mixed content)
        if "medium" in self.results["token_efficiency"] and "mixed" in self.results["token_efficiency"]["medium"]:
            run_summary["token_efficiency"] = {
                "improvement": self.results["token_efficiency"]["medium"]["mixed"].get("improvement", 0),
                "original_reduction": self.results["token_efficiency"]["medium"]["mixed"]["original"].get("token_reduction_percentage_accurate", 0),
                "enhanced_reduction": self.results["token_efficiency"]["medium"]["mixed"]["enhanced"].get("token_reduction_percentage_accurate", 0)
            }
        
        # Add to history and save
        self.historical_data["runs"].append(run_summary)
        
        # Update trends
        self.historical_data["trends"]["speed"].append({
            "timestamp": timestamp,
            "value": run_summary["speed"].get("speedup", 1.0)
        })
        
        self.historical_data["trends"]["memory"].append({
            "timestamp": timestamp,
            "value": run_summary["memory"].get("reduction_percentage", 0)
        })
        
        self.historical_data["trends"]["token_efficiency"].append({
            "timestamp": timestamp,
            "value": run_summary["token_efficiency"].get("improvement", 0)
        })
        
        # Keep only the last 10 runs to avoid file growth
        if len(self.historical_data["runs"]) > 10:
            self.historical_data["runs"] = self.historical_data["runs"][-10:]
        
        # Save to file
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(self.historical_data, f, indent=2, default=self._json_serializer)
        except Exception as e:
            logger.error(f"Failed to save historical data: {e}")
    
    def run_all_benchmarks(self):
        """Run all benchmarks and generate reports."""
        logger.info("Starting comprehensive token optimization benchmark suite")
        
        # Run speed benchmarks
        self.benchmark_processing_speed()
        
        # Run memory usage benchmarks
        self.benchmark_memory_usage()
        
        # Run token efficiency benchmarks
        self.benchmark_token_efficiency()
        
        # Run component timing benchmarks
        self.benchmark_component_timings()
        
        # Run throughput benchmarks
        self.benchmark_throughput()
        
        # Run output quality verification
        self.benchmark_output_quality()
        
        # Update historical data
        self._save_historical_data()
        
        # Generate reports and visualizations
        self.generate_reports()
        
        logger.info("Benchmark suite completed. Reports generated in %s", self.report_dir)
    
    def benchmark_processing_speed(self):
        """Benchmark processing speed of different implementations."""
        logger.info("Benchmarking processing speed")
        
        results = {}
        
        # Benchmark for each file size and content type
        for size_name, size in self.config["file_sizes"].items():
            results[size_name] = {}
            
            for content_type in self.config["content_types"]:
                results[size_name][content_type] = {
                    "original": [],
                    "enhanced": []
                }
                
                # Run benchmarks multiple times for statistical significance
                for _ in range(self.config["repetitions"]):
                    # Generate test data
                    test_file = self.utils.generate_test_data(size, content_type)
                    
                    # Benchmark original implementation
                    optimizer = TokenOptimizer(max_token_budget=self.config["token_budget"])
                    _, orig_time = self.utils.measure_execution_time(
                        optimizer.process_logs, test_file
                    )
                    
                    # Benchmark enhanced implementation
                    enhanced_optimizer = EnhancedTokenOptimizer(max_token_budget=self.config["token_budget"])
                    _, enh_time = self.utils.measure_execution_time(
                        enhanced_optimizer.process_logs, test_file
                    )
                    
                    # Calculate lines per second
                    orig_lps = size / orig_time
                    enh_lps = size / enh_time
                    
                    # Record results
                    results[size_name][content_type]["original"].append(orig_lps)
                    results[size_name][content_type]["enhanced"].append(enh_lps)
                    
                    # Clean up test file
                    os.unlink(test_file)
        
        # Calculate aggregate statistics
        for size_name in results:
            for content_type in results[size_name]:
                orig_mean = statistics.mean(results[size_name][content_type]["original"])
                enh_mean = statistics.mean(results[size_name][content_type]["enhanced"])
                speedup = enh_mean / orig_mean if orig_mean > 0 else float('inf')
                
                # Add aggregate stats
                results[size_name][content_type]["original_mean"] = orig_mean
                results[size_name][content_type]["enhanced_mean"] = enh_mean
                results[size_name][content_type]["speedup"] = speedup
        
        self.results["speed"] = results
        logger.info("Processing speed benchmark completed")
    
    def benchmark_memory_usage(self):
        """Benchmark memory usage of different implementations."""
        logger.info("Benchmarking memory usage")
        
        results = {}
        
        # Benchmark for each file size
        for size_name, size in self.config["file_sizes"].items():
            results[size_name] = {
                "batch": {},
                "stream": {}
            }
            
            # Generate test data
            test_file = self.utils.generate_test_data(size, "mixed")
            
            # Benchmark original implementation (batch processing)
            optimizer = TokenOptimizer(max_token_budget=self.config["token_budget"])
            _, batch_mem_usage, batch_mem_details = self.utils.measure_memory_usage(
                optimizer.process_logs, test_file
            )
            
            # Benchmark enhanced implementation (stream processing)
            enhanced_optimizer = EnhancedTokenOptimizer(max_token_budget=self.config["token_budget"])
            _, stream_mem_usage, stream_mem_details = self.utils.measure_memory_usage(
                enhanced_optimizer.process_logs, test_file
            )
            
            # Calculate memory metrics
            batch_metrics = {
                "peak": max(batch_mem_usage),
                "mean": statistics.mean(batch_mem_usage),
                "samples": batch_mem_usage,
                "details": batch_mem_details
            }
            
            stream_metrics = {
                "peak": max(stream_mem_usage),
                "mean": statistics.mean(stream_mem_usage),
                "samples": stream_mem_usage,
                "details": stream_mem_details
            }
            
            # Calculate memory efficiency
            memory_reduction = batch_metrics["peak"] - stream_metrics["peak"]
            memory_reduction_percentage = (memory_reduction / batch_metrics["peak"]) * 100 if batch_metrics["peak"] > 0 else 0
            
            # Record results
            results[size_name]["batch"] = batch_metrics
            results[size_name]["stream"] = stream_metrics
            results[size_name]["memory_reduction"] = memory_reduction
            results[size_name]["memory_reduction_percentage"] = memory_reduction_percentage
            
            # Check for memory leaks
            results[size_name]["batch_leak_detected"] = batch_metrics["details"]["potential_leak"]
            results[size_name]["stream_leak_detected"] = stream_metrics["details"]["potential_leak"]
            
            # Clean up test file
            os.unlink(test_file)
        
        self.results["memory"] = results
        logger.info("Memory usage benchmark completed")
    
    def benchmark_token_efficiency(self):
        """Benchmark token efficiency gains."""
        logger.info("Benchmarking token efficiency")
        
        results = {}
        
        # Benchmark for each file size and content type
        for size_name, size in self.config["file_sizes"].items():
            results[size_name] = {}
            
            for content_type in self.config["content_types"]:
                # Generate test data
                test_file = self.utils.generate_test_data(size, content_type)
                
                with open(test_file, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # Process with original implementation
                optimizer = TokenOptimizer(max_token_budget=self.config["token_budget"])
                summary, output_path = optimizer.process_logs(test_file)
                
                with open(output_path, 'r', encoding='utf-8') as f:
                    processed_content = f.read()
                
                # Process with enhanced implementation
                enhanced_optimizer = EnhancedTokenOptimizer(max_token_budget=self.config["token_budget"])
                enh_summary, enh_output_path = enhanced_optimizer.process_logs(test_file)
                
                with open(enh_output_path, 'r', encoding='utf-8') as f:
                    enhanced_content = f.read()
                
                # Calculate token efficiency metrics
                original_metrics = self.utils.calculate_token_efficiency(original_content, processed_content)
                enhanced_metrics = self.utils.calculate_token_efficiency(original_content, enhanced_content)
                
                # Record results
                results[size_name][content_type] = {
                    "original": original_metrics,
                    "enhanced": enhanced_metrics,
                    "improvement": enhanced_metrics["token_reduction_percentage_accurate"] - original_metrics["token_reduction_percentage_accurate"]
                }
                
                # Clean up files
                os.unlink(test_file)
                os.unlink(output_path)
                os.unlink(enh_output_path)
        
        self.results["token_efficiency"] = results
        logger.info("Token efficiency benchmark completed")
    
    def benchmark_component_timings(self):
        """Benchmark timing of individual components."""
        logger.info("Benchmarking component timings")
        
        results = {}
        
        # Use a medium-sized mixed content file
        size = self.config["file_sizes"]["medium"]
        test_file = self.utils.generate_test_data(size, "mixed")
        
        # Define components to time
        components = {
            "log_processing": {
                "original": lambda: LogProcessor().process_log_file(test_file)[0],
                "enhanced": lambda: StreamLogProcessor().process_log_file_streaming(test_file)[0]
            },
            "token_estimation": {
                "original": lambda: TokenOptimizer()._estimate_tokens(open(test_file).read()) if hasattr(TokenOptimizer, '_estimate_tokens') else tos.estimate_tokens(open(test_file).read()),
                "enhanced": lambda: TokenBudgetManager().estimate_tokens(open(test_file).read()) if hasattr(TokenBudgetManager, 'estimate_tokens') else tos.estimate_tokens(open(test_file).read())
            },
            "data_preprocessing": {
                "original": lambda: DataPreprocessor().process_file(test_file),
                "enhanced": lambda: EnhancedTokenOptimizer().process_data_streaming(test_file)
            }
        }
        
        # Run timing benchmarks for each component
        for component_name, implementations in components.items():
            results[component_name] = {}
            
            for impl_name, func in implementations.items():
                times = []
                
                # Run multiple times for statistical significance
                for _ in range(self.config["repetitions"]):
                    try:
                        _, exec_time = self.utils.measure_execution_time(func)
                        times.append(exec_time)
                    except Exception as e:
                        logger.error(f"Error timing {component_name} ({impl_name}): {str(e)}")
                        times.append(None)
                
                # Calculate statistics
