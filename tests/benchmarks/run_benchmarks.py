#!/usr/bin/env python
"""
Benchmark Runner Script for Token Optimization System

This script provides a simple interface to run the comprehensive benchmark suite
with various configurations and output options.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the benchmark suite
from token_system_benchmark import TokenOptimizationBenchmark, BENCHMARK_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Parse arguments and run benchmarks."""
    parser = argparse.ArgumentParser(
        description="Run token optimization system benchmarks"
    )
    
    # Benchmark configuration options
    parser.add_argument(
        "--token-budget", 
        type=int, 
        default=BENCHMARK_CONFIG["token_budget"],
        help="Token budget to use for benchmarks"
    )
    
    parser.add_argument(
        "--repetitions", 
        type=int, 
        default=BENCHMARK_CONFIG["repetitions"],
        help="Number of repetitions for each benchmark"
    )
    
    parser.add_argument(
        "--report-dir", 
        default=BENCHMARK_CONFIG["report_dir"],
        help="Directory to store benchmark reports and visualizations"
    )
    
    # File size options
    parser.add_argument(
        "--small-size", 
        type=int, 
        default=BENCHMARK_CONFIG["file_sizes"]["small"],
        help="Size of small test files in lines"
    )
    
    parser.add_argument(
        "--medium-size", 
        type=int, 
        default=BENCHMARK_CONFIG["file_sizes"]["medium"],
        help="Size of medium test files in lines"
    )
    
    parser.add_argument(
        "--large-size", 
        type=int, 
        default=BENCHMARK_CONFIG["file_sizes"]["large"],
        help="Size of large test files in lines"
    )
    
    # Benchmark selection
    parser.add_argument(
        "--skip-speed",
        action="store_true",
        help="Skip processing speed benchmarks"
    )
    
    parser.add_argument(
        "--skip-memory",
        action="store_true",
        help="Skip memory usage benchmarks"
    )
    
    parser.add_argument(
        "--skip-token-efficiency",
        action="store_true",
        help="Skip token efficiency benchmarks"
    )
    
    parser.add_argument(
        "--skip-component-timings",
        action="store_true",
        help="Skip component timing benchmarks"
    )
    
    # Output options
    parser.add_argument(
        "--report-format",
        choices=["md", "json", "both"],
        default="both",
        help="Format for benchmark reports"
    )
    
    parser.add_argument(
        "--skip-visualizations",
        action="store_true",
        help="Skip generating visualization charts"
    )
    
    args = parser.parse_args()
    
    # Update benchmark configuration
    BENCHMARK_CONFIG["token_budget"] = args.token_budget
    BENCHMARK_CONFIG["repetitions"] = args.repetitions
    BENCHMARK_CONFIG["report_dir"] = args.report_dir
    BENCHMARK_CONFIG["file_sizes"]["small"] = args.small_size
    BENCHMARK_CONFIG["file_sizes"]["medium"] = args.medium_size
    BENCHMARK_CONFIG["file_sizes"]["large"] = args.large_size
    
    # Create benchmark instance
    benchmark = TokenOptimizationBenchmark()
    benchmark.config = BENCHMARK_CONFIG
    
    # Create timestamp for this benchmark run
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    logger.info(f"Starting benchmark run at {datetime.now().isoformat()}")
    logger.info(f"Configuration: token_budget={args.token_budget}, repetitions={args.repetitions}")
    logger.info(f"File sizes: small={args.small_size}, medium={args.medium_size}, large={args.large_size}")
    
    # Run selected benchmarks
    if not args.skip_speed:
        logger.info("Running processing speed benchmarks...")
        benchmark.benchmark_processing_speed()
    
    if not args.skip_memory:
        logger.info("Running memory usage benchmarks...")
        benchmark.benchmark_memory_usage()
    
    if not args.skip_token_efficiency:
        logger.info("Running token efficiency benchmarks...")
        benchmark.benchmark_token_efficiency()
    
    if not args.skip_component_timings:
        logger.info("Running component timing benchmarks...")
        benchmark.benchmark_component_timings()
    
    # Generate reports and visualizations
    if args.report_format in ["md", "both"]:
        logger.info("Generating Markdown report...")
        benchmark._generate_summary_report(timestamp)
    
    if not args.skip_visualizations:
        logger.info("Generating visualizations...")
        benchmark._generate_speed_visualizations(timestamp)
        benchmark._generate_memory_visualizations(timestamp)
        benchmark._generate_token_efficiency_visualizations(timestamp)
        benchmark._generate_component_timing_visualizations(timestamp)
    
    # Save raw results to JSON
    if args.report_format in ["json", "both"]:
        logger.info("Saving raw results to JSON...")
        results_path = os.path.join(benchmark.report_dir, f"benchmark_results_{timestamp}.json")
        import json
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(benchmark.results, f, indent=2, default=benchmark._json_serializer)
    
    logger.info(f"Benchmark run completed. Reports saved to {benchmark.report_dir}")
    
    # Print summary to console
    print(f"\nBenchmark Summary ({timestamp}):")
    
    if "speed" in benchmark.results and benchmark.results["speed"]:
        size = "medium"
        content = "mixed"
        if size in benchmark.results["speed"] and content in benchmark.results["speed"][size]:
            speedup = benchmark.results["speed"][size][content].get("speedup", "N/A")
            print(f"- Processing Speed Improvement: {speedup}x faster")
    
    if "memory" in benchmark.results and benchmark.results["memory"]:
        size = "medium"
        if size in benchmark.results["memory"]:
            reduction = benchmark.results["memory"][size].get("memory_reduction_percentage", "N/A")
            print(f"- Memory Usage Reduction: {reduction}% less memory")
    
    if "token_efficiency" in benchmark.results and benchmark.results["token_efficiency"]:
        size = "medium"
        content = "mixed"
        if size in benchmark.results["token_efficiency"] and content in benchmark.results["token_efficiency"][size]:
            improvement = benchmark.results["token_efficiency"][size][content].get("improvement", "N/A")
            print(f"- Token Efficiency Improvement: {improvement}% better compression")
            
    print(f"\nFull reports available in: {benchmark.report_dir}")


if __name__ == "__main__":
    main()