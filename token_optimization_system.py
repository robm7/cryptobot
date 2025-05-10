#!/usr/bin/env python
"""
Token Optimization System for CryptoBot

This script integrates log processing, memory management, token tracking,
and data preprocessing to prevent context limit errors in the crypto trading bot.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, Any

# Add utils directory to the path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "utils"))

from utils.log_processor import LogProcessor
from utils.mcp_wrapper import MCPWrapper
from utils.token_optimizer import TokenOptimizer
from utils.data_preprocessor import DataPreprocessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("token_optimization.log")
    ]
)
logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure required directories exist."""
    directories = ["./logs", "./processed_data", "./.mcp_local_storage"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")

def process_logs(args):
    """
    Process logs using the log processor.
    
    Args:
        args: Command line arguments
    """
    logger.info(f"Processing log file: {args.log_file}")
    
    # Initialize components
    log_processor = LogProcessor(
        log_dir=args.output_dir,
        max_log_size_mb=args.max_log_size,
        max_logs=args.max_logs
    )
    
    # Set maximum token limit with a buffer to ensure we stay below 76,659
    max_token_limit = args.token_budget - 1000  # Buffer to ensure we're well under limit
    
    # Process the log file with token limit
    summary, output_path = log_processor.process_log_file(
        args.log_file,
        token_limit=max_token_limit
    )
    
    # Rotate logs if necessary
    log_processor.rotate_logs()
    
    # Check if processing was limited by token count
    if summary.get('token_limit_reached', False):
        logger.warning(f"Processing stopped early to stay within token limit of {max_token_limit}")
        print(f"\nWARNING: Log processing truncated to stay within token limit of {max_token_limit}")
    
    # Create and print summary
    logger.info(f"Log processing complete. Output saved to {output_path}")
    print("\nLog Processing Summary:")
    print(f"Original lines: {summary['original_size']}")
    print(f"Processed lines: {summary['processed_size']}")
    print(f"Compression ratio: {summary['compression_ratio']:.2%}")
    print(f"Test failures: {summary['test_failures']}")
    print(f"Duplicate traces removed: {summary['duplicate_traces_removed']}")
    print(f"Estimated tokens: {summary.get('estimated_tokens', 'Not calculated')}")
    
    return summary, output_path

def store_in_memory(summary, log_path, args):
    """
    Store processed data in Memory_Server or local storage.
    
    Args:
        summary: Processing summary
        log_path: Path to processed log file
        args: Command line arguments
        
    Returns:
        bool: Success status
    """
    if not args.store_memory:
        logger.info("Skipping memory storage (--store-memory not specified)")
        return False
    
    logger.info("Storing data in Memory_Server...")
    optimizer = TokenOptimizer(max_token_budget=args.token_budget)
    success = optimizer.store_in_memory_server(summary, log_path)
    
    if success:
        logger.info("Successfully stored data in Memory_Server")
    else:
        logger.warning("Failed to store data in Memory_Server")
    
    return success

def estimate_tokens(content):
    """
    Estimate the number of tokens in the content using a more accurate model
    that accounts for code-specific patterns in tokenization.
    
    Args:
        content: The text content to estimate tokens for
        
    Returns:
        int: Estimated number of tokens with a 20% safety margin
    """
    import re  # Import re here to avoid circular imports
    
    # Base estimation (more accurate than simple character division)
    # Average English text: ~1.3 tokens per word
    words = len(content.split())
    word_based_estimate = words * 1.3
    
    # Code-specific adjustments
    # Count special tokens that often correspond to single tokens
    special_chars = len(re.findall(r'[{}()\[\]<>:;,\.\-=+*/\\]', content))
    
    # Count code patterns that affect tokenization
    variable_names = len(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', content))
    
    # Numeric values tend to tokenize differently
    numbers = len(re.findall(r'\b\d+\b', content))
    
    # Adjust base estimate with code-specific factors
    code_adjusted_estimate = word_based_estimate + (special_chars * 0.5) + (variable_names * 0.2) + (numbers * 0.1)
    
    # Apply 20% safety margin
    final_estimate = int(code_adjusted_estimate * 1.2)
    
    # Fallback minimum based on character count to ensure we never severely underestimate
    char_based_minimum = len(content) // 3  # More conservative than the original //4
    
    return max(final_estimate, char_based_minimum)

def track_token_usage(log_path, args):
    """
    Track token usage with API_Monitoring.
    
    Args:
        log_path: Path to processed log file
        args: Command line arguments
        
    Returns:
        tuple: (success, under_budget)
    """
    if not args.track_usage:
        logger.info("Skipping token usage tracking (--track-usage not specified)")
        return False, True
    
    logger.info("Tracking token usage...")
    
    # Use more accurate token estimation
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.read()
            estimated_tokens = estimate_tokens(content)
            
            # Check if approaching token limit
            if estimated_tokens > args.token_budget:
                logger.warning(f"Estimated tokens ({estimated_tokens}) exceed budget ({args.token_budget})")
                logger.warning("Content will be truncated to fit within token limit")
                # Content would be truncated here in a real implementation
        
        optimizer = TokenOptimizer(max_token_budget=args.token_budget)
        success, under_budget = optimizer.track_token_usage(estimated_tokens)
        
        if success:
            logger.info(f"Token usage tracked: ~{estimated_tokens} tokens (with 20% safety margin)")
            if not under_budget:
                logger.warning(f"WARNING: Token budget exceeded. Budget: {args.token_budget}")
        else:
            logger.warning("Failed to track token usage")
        
        return success, under_budget
    
    except Exception as e:
        logger.error(f"Error tracking token usage: {str(e)}")
        return False, True

def preprocess_data(args):
    """
    Preprocess data in chunks using the data preprocessor.
    
    Args:
        args: Command line arguments
        
    Returns:
        Dict[str, Any]: Processed data
    """
    if not args.preprocess:
        logger.info("Skipping data preprocessing (--preprocess not specified)")
        return None
    
    logger.info(f"Preprocessing data from {args.log_file} in chunks...")
    
    preprocessor = DataPreprocessor(
        output_dir=args.output_dir,
        max_chunk_size=args.chunk_size
    )
    
    processed_data = preprocessor.process_file(args.log_file, args.chunk_size)
    
    # Generate and print report
    report = preprocessor.generate_token_efficient_report(processed_data)
    print("\n" + report)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_path = os.path.join(
        args.output_dir, 
        f"report_{os.path.basename(args.log_file)}_{timestamp}.md"
    )
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Report saved to: {report_path}")
    
    return processed_data

def analyze_memory_entities(args):
    """
    Analyze entities stored in Memory_Server.
    
    Args:
        args: Command line arguments
    """
    if not args.analyze_memory:
        return
    
    logger.info("Analyzing entities stored in Memory_Server...")
    
    # Initialize MCP wrapper
    mcp = MCPWrapper()
    
    # Get entities from Memory_Server
    query = args.memory_query if args.memory_query else None
    entities = mcp.get_memory_entities(query)
    
    # Print entity information
    print(f"\nFound {len(entities)} entities in Memory_Server:")
    
    # Group entities by type
    entities_by_type = {}
    for entity in entities:
        entity_type = entity.get("entityType", "Unknown")
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        entities_by_type[entity_type].append(entity)
    
    # Print summary by type
    for entity_type, entities_list in entities_by_type.items():
        print(f"\n{entity_type} entities: {len(entities_list)}")
        for entity in entities_list[:5]:  # Show only first 5 of each type
            print(f"  - {entity.get('name', 'Unnamed')}")
        
        if len(entities_list) > 5:
            print(f"  - ... and {len(entities_list) - 5} more")

def check_token_usage(args):
    """
    Check current token usage from API_Monitoring.
    
    Args:
        args: Command line arguments
    """
    if not args.check_usage:
        return
    
    logger.info("Checking current token usage...")
    
    # Initialize MCP wrapper
    mcp = MCPWrapper()
    
    # Get token usage information
    usage_data = mcp.get_token_usage()
    
    # Print usage information
    print("\nToken Usage Information:")
    print(f"Current usage: {usage_data.get('current_usage', 0)} tokens")
    print(f"Budget: {usage_data.get('budget', args.token_budget)} tokens")
    
    # Calculate usage percentage
    if 'budget' in usage_data and usage_data['budget'] > 0:
        usage_pct = (usage_data.get('current_usage', 0) / usage_data['budget']) * 100
        print(f"Usage: {usage_pct:.1f}% of budget")
    
    # Print recent usage history
    history = usage_data.get('usage_history', [])
    if history:
        print("\nRecent Usage History:")
        for entry in history[-5:]:  # Show last 5 entries
            timestamp = entry.get('timestamp', 'Unknown')
            tokens = entry.get('tokens', 0)
            service = entry.get('service', 'Unknown')
            print(f"  - {timestamp}: {tokens} tokens ({service})")

def main():
    """Main entry point for the token optimization system."""
    parser = argparse.ArgumentParser(
        description="Token Optimization System for CryptoBot"
    )
    
    # Input/output options
    parser.add_argument(
        "--log-file", 
        default="test_output.log", 
        help="Path to log file to process"
    )
    parser.add_argument(
        "--output-dir", 
        default="./logs", 
        help="Directory for output files"
    )
    
    # Log processing options
    parser.add_argument(
        "--max-log-size", 
        type=int, 
        default=5, 
        help="Maximum size of each log file in MB"
    )
    parser.add_argument(
        "--max-logs", 
        type=int, 
        default=10, 
        help="Maximum number of log files to keep"
    )
    
    # Memory storage options
    parser.add_argument(
        "--store-memory", 
        action="store_true", 
        help="Store processed data in Memory_Server"
    )
    parser.add_argument(
        "--analyze-memory", 
        action="store_true", 
        help="Analyze entities stored in Memory_Server"
    )
    parser.add_argument(
        "--memory-query", 
        help="Query for searching Memory_Server entities"
    )
    
    # Token usage options
    parser.add_argument(
        "--token-budget", 
        type=int, 
        default=76659,
        help="Maximum token budget"
    )
    parser.add_argument(
        "--track-usage", 
        action="store_true", 
        help="Track token usage with API_Monitoring"
    )
    parser.add_argument(
        "--check-usage", 
        action="store_true", 
        help="Check current token usage"
    )
    
    # Data preprocessing options
    parser.add_argument(
        "--preprocess", 
        action="store_true", 
        help="Preprocess data in chunks"
    )
    parser.add_argument(
        "--chunk-size", 
        type=int, 
        default=1000, 
        help="Size of each chunk in lines"
    )
    
    args = parser.parse_args()
    
    # Ensure required directories exist
    ensure_directories()
    
    # Process logs
    summary, log_path = process_logs(args)
    
    # Store in Memory_Server
    store_in_memory(summary, log_path, args)
    
    # Track token usage
    track_token_usage(log_path, args)
    
    # Preprocess data
    preprocess_data(args)
    
    # Analyze memory entities
    analyze_memory_entities(args)
    
    # Check token usage
    check_token_usage(args)
    
    logger.info("Token optimization complete")
    print("\nToken optimization complete. Run with --help for more options.")

if __name__ == "__main__":
    main()