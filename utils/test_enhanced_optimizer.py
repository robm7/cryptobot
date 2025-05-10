#!/usr/bin/env python3
"""
Test script for the Enhanced Token Optimizer System.

This script demonstrates the long-term optimizations implemented in the token
optimization system, including:
1. Stream Processing Architecture
2. Token-Aware Data Structures
3. Smarter Memory Integration
4. Adaptive Configuration

Usage:
  python test_enhanced_optimizer.py --log-file path/to/log_file.log [options]

Options:
  --token-budget INT     Maximum token budget (default: 76659)
  --store-memory         Store data in Memory_Server
  --track-usage          Track token usage with API_Monitoring
  --compare-original     Compare with original LogProcessor
  --save-config NAME     Save configuration profile with given name
  --load-config NAME     Load configuration profile with given name
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Add parent directory to path to access utility modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.enhanced_token_optimizer import EnhancedTokenOptimizer
from utils.log_processor import LogProcessor
from utils.token_budget_manager import TokenBudgetManager

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("test_optimizer.log")
        ]
    )

def test_enhanced_optimizer(args):
    """Test the Enhanced Token Optimizer."""
    print("\n==== Testing Enhanced Token Optimizer ====")
    
    # Create Enhanced Token Optimizer
    start_time = time.time()
    optimizer = EnhancedTokenOptimizer(max_token_budget=args.token_budget)
    
    # Load configuration if specified
    if args.load_config:
        optimizer.load_optimal_configuration(args.load_config)
        print(f"Loaded configuration profile: {args.load_config}")
    
    # Process logs
    print(f"\nProcessing log file: {args.log_file}")
    summary, output_path = optimizer.process_logs(args.log_file)
    processing_time = time.time() - start_time
    
    # Save configuration if specified
    if args.save_config:
        optimizer.save_optimal_configuration(args.save_config, summary)
        print(f"Saved optimal configuration as: {args.save_config}")
    
    # Store in Memory_Server if requested
    if args.store_memory:
        print("\nStoring structured data in Memory_Server...")
        success = optimizer.store_in_memory_server(summary, output_path)
        if success:
            print("Successfully stored structured log data in Memory_Server")
        else:
            print("Failed to store data in Memory_Server")
    
    # Track token usage if requested
    if args.track_usage:
        estimated_tokens = summary.get("estimated_tokens", 0)
        print(f"\nTracking token usage: {estimated_tokens} tokens")
        success, under_budget = optimizer.track_token_usage(estimated_tokens)
        if success:
            status = "UNDER BUDGET" if under_budget else "OVER BUDGET"
            print(f"Token usage tracked: ~{estimated_tokens} tokens - {status}")
            if not under_budget:
                print(f"WARNING: Token budget exceeded. Budget: {args.token_budget}")
        else:
            print("Failed to track token usage")
    
    # Print summary
    print("\nLog Processing Summary:")
    print(f"Original lines: {summary['original_size']}")
    print(f"Processed lines: {summary['processed_size']}")
    print(f"Compression ratio: {summary['compression_ratio']:.2%}")
    print(f"Test failures: {summary['test_failures']}")
    print(f"Duplicate traces removed: {summary['duplicate_traces_removed']}")
    print(f"Chunks processed: {summary.get('chunks_processed', 0)}")
    print(f"Estimated tokens: {summary.get('estimated_tokens', 0)}")
    print(f"Processing time: {processing_time:.2f} seconds")
    print(f"Processed log saved to: {output_path}")
    
    return summary, output_path, processing_time

def test_original_processor(args):
    """Test the original Log Processor for comparison."""
    print("\n==== Testing Original Log Processor ====")
    
    # Create original Log Processor
    start_time = time.time()
    log_processor = LogProcessor(log_dir="./logs", max_log_size_mb=5, max_logs=10)
    
    # Process logs
    print(f"\nProcessing log file: {args.log_file}")
    summary, output_path = log_processor.process_log_file(args.log_file, token_limit=args.token_budget)
    processing_time = time.time() - start_time
    
    # Print summary
    print("\nLog Processing Summary:")
    print(f"Original lines: {summary['original_size']}")
    print(f"Processed lines: {summary['processed_size']}")
    print(f"Compression ratio: {summary['compression_ratio']:.2%}")
    print(f"Test failures: {summary['test_failures']}")
    print(f"Duplicate traces removed: {summary['duplicate_traces_removed']}")
    print(f"Estimated tokens: {summary.get('estimated_tokens', 0)}")
    print(f"Processing time: {processing_time:.2f} seconds")
    print(f"Processed log saved to: {output_path}")
    
    return summary, output_path, processing_time

def main():
    parser = argparse.ArgumentParser(
        description="Test the Enhanced Token Optimizer System"
    )
    parser.add_argument("--log-file", required=True, help="Path to log file to process")
    parser.add_argument("--token-budget", type=int, default=76659, help="Maximum token budget")
    parser.add_argument("--store-memory", action="store_true", help="Store data in Memory_Server")
    parser.add_argument("--track-usage", action="store_true", help="Track token usage with API_Monitoring")
    parser.add_argument("--compare-original", action="store_true", help="Compare with original LogProcessor")
    parser.add_argument("--save-config", help="Save configuration profile with given name")
    parser.add_argument("--load-config", help="Load configuration profile with given name")
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Test Enhanced Token Optimizer
    enhanced_summary, enhanced_output, enhanced_time = test_enhanced_optimizer(args)
    
    # Compare with original if requested
    if args.compare_original:
        original_summary, original_output, original_time = test_original_processor(args)
        
        # Compare results
        print("\n==== Comparison Results ====")
        print(f"Processing time: Original: {original_time:.2f}s vs Enhanced: {enhanced_time:.2f}s")
        print(f"Speedup factor: {original_time / enhanced_time:.2f}x")
        
        original_tokens = original_summary.get("estimated_tokens", 0)
        enhanced_tokens = enhanced_summary.get("estimated_tokens", 0)
        
        print(f"Token usage: Original: {original_tokens} vs Enhanced: {enhanced_tokens}")
        if original_tokens > 0:
            print(f"Token reduction: {(original_tokens - enhanced_tokens) / original_tokens:.2%}")
        
        print(f"Compression ratio: Original: {original_summary['compression_ratio']:.2%} vs Enhanced: {enhanced_summary['compression_ratio']:.2%}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()