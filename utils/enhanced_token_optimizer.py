import os
import sys
import json
import logging
import argparse
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from stream_log_processor import StreamLogProcessor
from token_budget_manager import TokenBudgetManager
from mcp_wrapper import MCPWrapper

logger = logging.getLogger(__name__)

class EnhancedTokenOptimizer:
    """
    Enhanced token optimization system that implements longer-term optimizations:
    
    1. Stream Processing Architecture:
       - Processes files line-by-line rather than loading entire files at once
       - Implements processing in smaller chunks with token budget allocation
       - Supports streaming rather than batch processing
    
    2. Token-Aware Data Structures:
       - Uses TokenBudgetManager to track and allocate tokens across components
       - Implements prioritization logic to preserve critical information
       - Dynamically adjusts verbosity based on available token budget
    
    3. Smarter Memory Integration:
       - Stores only error type summaries rather than full traces in Memory_Server
       - Implements a reference system to reuse common error patterns
       - Adds deduplication logic that works across processing sessions
    
    4. Adaptive Configuration:
       - Implements automatic parameter tuning based on input file size
       - Adds configuration profiles for different types of logs
       - Creates a mechanism to save and load optimal configurations
    """
    
    def __init__(self, max_token_budget=76659, log_dir="./logs"):
        """
        Initialize the enhanced token optimizer with a maximum token budget.
        
        Args:
            max_token_budget (int): Maximum number of tokens allowed for API usage
            log_dir (str): Directory to store processed logs and configurations
        """
        self.max_token_budget = max_token_budget
        self.log_dir = log_dir
        
        # Create token budget manager
        self.token_manager = TokenBudgetManager(max_token_budget=max_token_budget)
        
        # Create stream log processor
        self.log_processor = StreamLogProcessor(
            log_dir=log_dir, 
            max_log_size_mb=5, 
            max_logs=10,
            token_budget=max_token_budget,
            chunk_size=500,
            profile="test_logs"
        )
        
        # Initialize MCPWrapper for integrations
        self.mcp = MCPWrapper()
        
        # Error reference system
        self.error_references = {}
        self.reference_counter = 0
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("token_optimizer.log")
            ]
        )
        
        # Initialize error reference system
        self._initialize_error_reference_system()
    
    def _initialize_error_reference_system(self):
        """Initialize error reference system for reusing common error patterns."""
        reference_file = os.path.join(self.log_dir, "error_references.json")
        
        if os.path.exists(reference_file):
            try:
                with open(reference_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.error_references = data.get("references", {})
                    self.reference_counter = data.get("counter", 0)
                    logger.info(f"Loaded {len(self.error_references)} error references")
            except Exception as e:
                logger.error(f"Error loading error references: {str(e)}")
    
    def _save_error_reference_system(self):
        """Save error reference system for future use."""
        reference_file = os.path.join(self.log_dir, "error_references.json")
        
        try:
            with open(reference_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "references": self.error_references,
                    "counter": self.reference_counter
                }, f, indent=2)
            logger.info(f"Saved {len(self.error_references)} error references")
        except Exception as e:
            logger.error(f"Error saving error references: {str(e)}")
    
    def _get_error_reference(self, error_hash):
        """
        Get an error reference by hash or create a new reference if it doesn't exist.
        
        Args:
            error_hash (str): Hash of the error
            
        Returns:
            str: Reference ID for the error
        """
        if error_hash in self.error_references:
            return self.error_references[error_hash]
        
        # Create new reference
        self.reference_counter += 1
        reference_id = f"ERR-{self.reference_counter:04d}"
        self.error_references[error_hash] = reference_id
        
        return reference_id
    
    def process_logs(self, log_path):
        """
        Process logs using the stream log processor and generate compressed output.
        Implements auto-configuration based on file size.
        
        Args:
            log_path (str): Path to the log file to process
            
        Returns:
            tuple: (summary dict, path to the processed log file)
        """
        logger.info(f"Processing log file: {log_path}")
        
        try:
            # Auto-configure log processor based on file size
            config = self.log_processor.auto_configure(log_path)
            logger.info(f"Auto-configured for file size: chunk_size={config['chunk_size']}, profile={config['profile']}")
            
            # Process the log file using streaming approach
            summary, output_path = self.log_processor.process_log_file_streaming(
                log_path, token_limit=self.max_token_budget
            )
            
            # Rotate logs if necessary
            self.log_processor.rotate_logs()
            
            # Create summary file
            summary_path = self.log_processor.create_summary_file(summary)
            
            logger.info(f"Log processing complete. Summary saved to {summary_path}")
            logger.info(f"Processed log saved to {output_path}")
            logger.info(f"Compression ratio: {summary['compression_ratio']:.2%}")
            
            return summary, output_path
        
        except Exception as e:
            logger.error(f"Error processing log file: {str(e)}")
            raise
    
    def store_in_memory_server(self, summary, processed_log_path):
        """
        Store structured log data in Memory_Server MCP with enhanced referencing.
        Only stores error type summaries rather than full traces, with a reference system.
        
        Args:
            summary (dict): Log processing summary
            processed_log_path (str): Path to the processed log file
            
        Returns:
            bool: Success status
        """
        # Initialize entities and relations
        test_entities = []
        relations = []
        
        # Create a test run entity
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_run_entity = {
            "name": f"TestRun:{timestamp}",
            "entityType": "TestRun",
            "observations": [
                f"Processed at {datetime.now().isoformat()}",
                f"Original line count: {summary['original_size']}",
                f"Processed line count: {summary['processed_size']}",
                f"Compression ratio: {summary['compression_ratio']:.2%}",
                f"Total failures: {summary['test_failures']}",
                f"Duplicate traces removed: {summary['duplicate_traces_removed']}",
                f"Used token budget: {summary.get('estimated_tokens', 0)}/{self.max_token_budget}"
            ]
        }
        test_entities.append(test_run_entity)
        
        # Process error types and create references
        for error_type, count in summary["error_types"].items():
            # Generate a consistent hash for this error type
            error_hash = f"{error_type}:{count}"
            reference_id = self._get_error_reference(error_hash)
            
            # Create or reuse error type entity
            error_entity = {
                "name": f"Error:{reference_id}",
                "entityType": "ErrorType",
                "observations": [
                    f"Type: {error_type}",
                    f"Occurred {count} times in test logs",
                    f"Last observed: {datetime.now().isoformat()}"
                ]
            }
            test_entities.append(error_entity)
            
            # Create relation between test run and error type
            relation = {
                "from": f"TestRun:{timestamp}",
                "to": f"Error:{reference_id}",
                "relationType": "contains"
            }
            relations.append(relation)
        
        # Store entities and relations
        entities_success = self.mcp.store_entities(test_entities)
        relations_success = self.mcp.store_relations(relations)
        
        if entities_success:
            logger.info(f"Stored {len(test_entities)} entities in Memory_Server")
        if relations_success:
            logger.info(f"Stored {len(relations)} relations in Memory_Server")
        
        # Save error reference system for future use
        self._save_error_reference_system()
        
        return entities_success and relations_success
    
    def track_token_usage(self, estimated_tokens):
        """
        Track token usage with API_Monitoring MCP.
        
        Args:
            estimated_tokens (int): Estimated number of tokens consumed
            
        Returns:
            tuple: (tracked_successfully, under_budget)
        """
        # Set budget threshold
        self.mcp.set_token_budget(self.max_token_budget)
        
        # Track token usage
        tracked, under_budget = self.mcp.track_token_usage(estimated_tokens)
        
        if tracked:
            logger.info(f"Tracked {estimated_tokens} tokens")
            if not under_budget:
                logger.warning(f"Token budget exceeded! Budget: {self.max_token_budget}")
        
        return tracked, under_budget
    
    def process_data_streaming(self, data_path, chunk_size=None):
        """
        Process data in streaming mode using configurable chunk sizes.
        
        Args:
            data_path (str): Path to data file to process
            chunk_size (int, optional): Number of lines per chunk. If None, auto-configures.
            
        Returns:
            dict: Processed data summary
        """
        logger.info(f"Processing data from {data_path} using streaming")
        
        try:
            # Auto-configure if chunk_size is not provided
            if chunk_size is None:
                config = self.log_processor.auto_configure(data_path)
                chunk_size = config["chunk_size"]
                logger.info(f"Auto-configured chunk size: {chunk_size}")
            
            # Use StreamLogProcessor for processing
            summary, output_path = self.log_processor.process_log_file_streaming(
                data_path, token_limit=self.max_token_budget
            )
            
            logger.info(f"Data processing complete. Processed {summary['chunks_processed']} chunks")
            
            return summary, output_path
        
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            raise
    
    def save_optimal_configuration(self, name, summary):
        """
        Save optimal configuration based on processing results.
        
        Args:
            name (str): Configuration name
            summary (dict): Processing summary
            
        Returns:
            bool: Success status
        """
        # Extract relevant metrics for optimizing configuration
        metrics = {
            "compression_ratio": summary.get("compression_ratio", 0),
            "token_usage": summary.get("estimated_tokens", 0),
            "max_token_budget": self.max_token_budget,
            "chunk_size": self.log_processor.chunk_size,
            "profile": self.log_processor.profile,
        }
        
        # Create configuration based on results
        config = {
            "error_retention": self.log_processor.config["error_retention"],
            "stack_trace_detail": self.log_processor.config["stack_trace_detail"],
            "test_result_detail": self.log_processor.config["test_result_detail"],
            "summary_size": self.log_processor.config["summary_size"],
            "chunk_size": self.log_processor.chunk_size,
            "metrics": metrics
        }
        
        # Save configuration
        return self.log_processor.save_configuration(name, config)
    
    def load_optimal_configuration(self, name):
        """
        Load an optimal configuration by name.
        
        Args:
            name (str): Configuration name
            
        Returns:
            bool: Success status
        """
        # Load configuration
        success = self.log_processor.load_configuration(name)
        
        if success:
            logger.info(f"Loaded optimal configuration: {name}")
        else:
            logger.warning(f"Failed to load optimal configuration: {name}")
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced token optimizer with stream processing and adaptive configuration"
    )
    parser.add_argument("--log-file", default="test_output.log", help="Path to log file")
    parser.add_argument("--token-budget", type=int, default=76659, help="Maximum token budget")
    parser.add_argument("--store-memory", action="store_true", help="Store data in Memory_Server")
    parser.add_argument("--track-usage", action="store_true", help="Track token usage with API_Monitoring")
    parser.add_argument("--chunk-size", type=int, help="Chunk size for processing (auto-configures if not specified)")
    parser.add_argument("--config-profile", help="Configuration profile to use (auto-selects if not specified)")
    parser.add_argument("--save-config", help="Save optimal configuration with the given name")
    parser.add_argument("--load-config", help="Load configuration with the given name")
    
    args = parser.parse_args()
    
    optimizer = EnhancedTokenOptimizer(max_token_budget=args.token_budget)
    
    # Load configuration if specified
    if args.load_config:
        optimizer.load_optimal_configuration(args.load_config)
    
    # Set configuration profile if specified
    if args.config_profile:
        optimizer.log_processor.load_configuration(args.config_profile)
    
    # Set chunk size if specified
    if args.chunk_size:
        optimizer.log_processor.chunk_size = args.chunk_size
    
    # Process logs
    summary, output_path = optimizer.process_logs(args.log_file)
    
    # Save optimal configuration if specified
    if args.save_config:
        optimizer.save_optimal_configuration(args.save_config, summary)
    
    # Store in Memory_Server if requested
    if args.store_memory:
        success = optimizer.store_in_memory_server(summary, output_path)
        if success:
            print("Successfully stored structured log data in Memory_Server")
        else:
            print("Failed to store data in Memory_Server")
    
    # Track token usage if requested
    if args.track_usage:
        estimated_tokens = summary.get("estimated_tokens", 0)
        success, under_budget = optimizer.track_token_usage(estimated_tokens)
        if success:
            print(f"Token usage tracked: ~{estimated_tokens} tokens")
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
    print(f"Estimated tokens: {summary.get('estimated_tokens', 0)}")
    print(f"Processed log saved to: {output_path}")


if __name__ == "__main__":
    main()