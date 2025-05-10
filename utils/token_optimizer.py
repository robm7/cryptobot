import os
import sys
import json
import logging
import argparse
import re
from datetime import datetime
from log_processor import LogProcessor
from mcp_wrapper import MCPWrapper

logger = logging.getLogger(__name__)

class TokenOptimizer:
    """
    Token optimization system that processes log files, stores structured 
    representations in Memory_Server, and tracks token usage with API_Monitoring MCP.
    """
    
    def __init__(self, max_token_budget=76659):
        """
        Initialize the token optimizer with a maximum token budget.
        
        Args:
            max_token_budget (int): Maximum number of tokens allowed for API usage
        """
        self.max_token_budget = max_token_budget
        self.log_processor = LogProcessor(log_dir="./logs", max_log_size_mb=5, max_logs=10)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("token_optimizer.log")
            ]
        )
    
    def process_logs(self, log_path):
        """
        Process logs using the log processor and generate compressed output.
        
        Args:
            log_path (str): Path to the log file to process
            
        Returns:
            tuple: (summary dict, path to the processed log file)
        """
        logger.info(f"Processing log file: {log_path}")
        
        try:
            # Process the log file
            summary, output_path = self.log_processor.process_log_file(log_path)
            
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
        Store structured log data in Memory_Server MCP.
        
        Args:
            summary (dict): Log processing summary
            processed_log_path (str): Path to the processed log file
            
        Returns:
            bool: Success status
        """
        # Initialize MCP wrapper
        mcp = MCPWrapper()
        
        # Extract error information for the knowledge graph
        test_entities = []
        relations = []
        
        # Create entities for each error type
        for error_type, count in summary["error_types"].items():
            error_entity = {
                "name": f"Error:{error_type}",
                "entityType": "ErrorType",
                "observations": [
                    f"Occurred {count} times in test logs",
                    f"Last observed: {datetime.now().isoformat()}"
                ]
            }
            test_entities.append(error_entity)
        
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
                f"Duplicate traces removed: {summary['duplicate_traces_removed']}"
            ]
        }
        test_entities.append(test_run_entity)
        
        # Create relations between test run and error types
        for error_type in summary["error_types"].keys():
            relation = {
                "from": f"TestRun:{timestamp}",
                "to": f"Error:{error_type}",
                "relationType": "contains"
            }
            relations.append(relation)
        
        # Store entities and relations using the wrapper
        entities_success = mcp.store_entities(test_entities)
        relations_success = mcp.store_relations(relations)
        
        if entities_success:
            logger.info(f"Stored {len(test_entities)} entities in Memory_Server")
        if relations_success:
            logger.info(f"Stored {len(relations)} relations in Memory_Server")
        
        return entities_success and relations_success
    
    def track_token_usage(self, estimated_tokens):
        """
        Track token usage with API_Monitoring MCP.
        
        Args:
            estimated_tokens (int): Estimated number of tokens consumed
            
        Returns:
            tuple: (tracked_successfully, under_budget)
        """
        # Initialize MCP wrapper
        mcp = MCPWrapper()
        
        # Set budget threshold
        mcp.set_token_budget(self.max_token_budget)
        
        # Track token usage
        tracked, under_budget = mcp.track_token_usage(estimated_tokens)
        
        if tracked:
            logger.info(f"Tracked {estimated_tokens} tokens")
            if not under_budget:
                logger.warning(f"Token budget exceeded! Budget: {self.max_token_budget}")
        
        return tracked, under_budget
    
    def preprocess_data(self, data_path, chunk_size=1000):
        """
        Preprocess data in chunks to reduce token usage.
        
        Args:
            data_path (str): Path to data file to process
            chunk_size (int): Number of lines to process in each chunk
            
        Returns:
            dict: Processed data summary
        """
        logger.info(f"Preprocessing data from {data_path} in chunks of {chunk_size} lines")
        
        try:
            results = {
                "chunks_processed": 0,
                "total_lines": 0,
                "essential_info": []
            }
            
            # Process data in chunks
            with open(data_path, 'r', encoding='utf-8', errors='replace') as file:
                chunk = []
                for i, line in enumerate(file):
                    chunk.append(line)
                    
                    # Process chunk when it reaches chunk_size
                    if len(chunk) >= chunk_size:
                        processed_chunk = self._process_chunk(chunk)
                        results["essential_info"].extend(processed_chunk)
                        results["chunks_processed"] += 1
                        results["total_lines"] += len(chunk)
                        chunk = []
                
                # Process any remaining lines
                if chunk:
                    processed_chunk = self._process_chunk(chunk)
                    results["essential_info"].extend(processed_chunk)
                    results["chunks_processed"] += 1
                    results["total_lines"] += len(chunk)
            
            logger.info(f"Data preprocessing complete. Processed {results['total_lines']} lines in {results['chunks_processed']} chunks")
            
            return results
        
        except Exception as e:
            logger.error(f"Error preprocessing data: {str(e)}")
            raise
    
    def _process_chunk(self, chunk):
        """
        Process a chunk of data to extract essential information.
        
        Args:
            chunk (list): List of strings representing lines to process
            
        Returns:
            list: Extracted essential information
        """
        essential_info = []
        
        # Join chunk into text for processing
        text = ''.join(chunk)
        
        # Extract test results
        test_results = re.findall(r'(PASSED|FAILED).*?(\w+/\w+\.py::\w+)', text)
        for result, test_name in test_results:
            essential_info.append(f"{result}: {test_name}")
        
        # Extract errors
        errors = re.findall(r'([A-Za-z]+Error|Exception):\s*([^\n]+)', text)
        for error_type, message in errors:
            essential_info.append(f"{error_type}: {message.strip()}")
        
        return essential_info


def main():
    parser = argparse.ArgumentParser(description="Optimize token usage for crypto trading bot logs")
    parser.add_argument("--log-file", default="test_output.log", help="Path to log file")
    parser.add_argument("--token-budget", type=int, default=150000, help="Maximum token budget")
    parser.add_argument("--store-memory", action="store_true", help="Store data in Memory_Server")
    parser.add_argument("--track-usage", action="store_true", help="Track token usage with API_Monitoring")
    args = parser.parse_args()
    
    optimizer = TokenOptimizer(max_token_budget=args.token_budget)
    
    # Process logs
    summary, output_path = optimizer.process_logs(args.log_file)
    
    # Store in Memory_Server if requested
    if args.store_memory:
        success = optimizer.store_in_memory_server(summary, output_path)
        if success:
            print("Successfully stored structured log data in Memory_Server")
        else:
            print("Failed to store data in Memory_Server")
    
    # Track token usage if requested
    if args.track_usage:
        # Estimate tokens based on processed log size (rough estimate: 1 token ≈ 4 chars)
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            estimated_tokens = len(content) // 4
        
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
    print(f"Processed log saved to: {output_path}")


if __name__ == "__main__":
    main()