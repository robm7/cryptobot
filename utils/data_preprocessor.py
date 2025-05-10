import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Iterator
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DataPreprocessor:
    """
    Data preprocessing pipeline that processes log files in chunks,
    extracts critical information, and maintains essential context
    while reducing token count.
    """
    
    def __init__(self, output_dir="./processed_data", max_chunk_size=5000):
        """
        Initialize the data preprocessor.
        
        Args:
            output_dir (str): Directory to store processed data
            max_chunk_size (int): Maximum size of each chunk in lines
        """
        self.output_dir = output_dir
        self.max_chunk_size = max_chunk_size
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("data_preprocessor.log")
            ]
        )
    
    def process_file(self, file_path: str, chunk_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Process a file in chunks, extracting critical information.
        
        Args:
            file_path (str): Path to the file to process
            chunk_size (int, optional): Size of each chunk in lines
            
        Returns:
            Dict[str, Any]: Summary of processing results
        """
        if chunk_size is None:
            chunk_size = self.max_chunk_size
        
        logger.info(f"Processing file {file_path} in chunks of {chunk_size} lines")
        
        # Calculate total file size and line count
        file_size = os.path.getsize(file_path)
        line_count = self._count_lines(file_path)
        
        chunks = []
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            chunk_num = 0
            while True:
                chunk = self._read_chunk(f, chunk_size)
                if not chunk:
                    break
                
                processed_chunk = self._process_chunk(chunk, chunk_num)
                chunks.append(processed_chunk)
                chunk_num += 1
                
                logger.info(f"Processed chunk {chunk_num} ({len(processed_chunk['data'])} items)")
        
        # Combine chunks and generate summary
        summary = self._combine_chunks(chunks, file_path, file_size, line_count)
        
        # Save combined processed data
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_path = os.path.join(self.output_dir, f"processed_{os.path.basename(file_path)}_{timestamp}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Saved processed data to {output_path}")
        
        return summary
    
    def _count_lines(self, file_path: str) -> int:
        """Count the number of lines in a file."""
        lines = 0
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for _ in f:
                lines += 1
        return lines
    
    def _read_chunk(self, file_handle, chunk_size: int) -> List[str]:
        """Read a chunk of lines from a file."""
        chunk = []
        for _ in range(chunk_size):
            line = file_handle.readline()
            if not line:
                break
            chunk.append(line)
        return chunk
    
    def _process_chunk(self, chunk: List[str], chunk_num: int) -> Dict[str, Any]:
        """
        Process a chunk of data to extract essential information.
        
        Args:
            chunk (List[str]): List of lines in the chunk
            chunk_num (int): Chunk number
            
        Returns:
            Dict[str, Any]: Processed chunk data
        """
        processed = {
            "chunk_num": chunk_num,
            "data": [],
            "test_results": [],
            "errors": [],
            "summary": {}
        }
        
        # Combine lines for processing
        text = ''.join(chunk)
        
        # Clean up text (remove excessive spaces, normalize newlines)
        text = self._clean_text(text)
        
        # Extract test results
        test_results = re.findall(r'(PASSED|FAILED)\s+([\w/]+\.py::\w+)', text)
        for result, test_name in test_results:
            processed["test_results"].append({
                "result": result,
                "test": test_name
            })
        
        # Extract errors and exception traces
        error_blocks = []
        error_block = []
        in_error_block = False
        
        for line in chunk:
            clean_line = self._clean_text(line)
            
            # Start of error trace
            if "Traceback (most recent call last):" in clean_line:
                in_error_block = True
                error_block = [clean_line]
            # Part of error trace
            elif in_error_block:
                error_block.append(clean_line)
                
                # End of error trace (error message)
                if re.search(r'([A-Za-z]+Error|Exception):', clean_line):
                    error_blocks.append('\n'.join(error_block))
                    error_block = []
                    in_error_block = False
            # Stand-alone error (not part of a traceback)
            elif re.search(r'([A-Za-z]+Error|Exception):', clean_line):
                processed["errors"].append({
                    "type": re.search(r'([A-Za-z]+Error|Exception)', clean_line).group(1),
                    "message": clean_line
                })
        
        # Process error blocks (eliminate duplicates by hash)
        error_hashes = set()
        for block in error_blocks:
            error_hash = self._hash_error_block(block)
            if error_hash not in error_hashes:
                error_type_match = re.search(r'([A-Za-z]+Error|Exception):', block)
                if error_type_match:
                    error_type = error_type_match.group(1)
                    processed["errors"].append({
                        "type": error_type,
                        "trace": block
                    })
                    error_hashes.add(error_hash)
        
        # Extract log messages
        log_matches = re.findall(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})\s+-\s+(\w+)\s+-\s+(\w+)\s+-\s+(.+)', text)
        for timestamp, module, level, message in log_matches:
            if level in ["ERROR", "CRITICAL", "WARNING"]:
                processed["data"].append({
                    "timestamp": timestamp,
                    "module": module,
                    "level": level,
                    "message": message
                })
        
        # Generate summary for this chunk
        processed["summary"] = {
            "line_count": len(chunk),
            "test_results_count": len(processed["test_results"]),
            "errors_count": len(processed["errors"]),
            "logs_count": len(processed["data"])
        }
        
        return processed
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing excessive spaces and normalizing whitespace."""
        # Remove spaces between characters
        text = re.sub(r'(?<=\w) (?=\w)', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _hash_error_block(self, block: str) -> str:
        """Generate a hash for an error block to identify duplicates."""
        # Remove line numbers, memory addresses, timestamps
        normalized = re.sub(r'File ".*?", line \d+', 'File "X", line N', block)
        normalized = re.sub(r'0x[0-9a-fA-F]+', '0xXXXXXXXX', normalized)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', 'TIMESTAMP', normalized)
        
        import hashlib
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _combine_chunks(self, chunks: List[Dict[str, Any]], file_path: str, file_size: int, line_count: int) -> Dict[str, Any]:
        """
        Combine processed chunks into a single result with summary.
        
        Args:
            chunks (List[Dict[str, Any]]): List of processed chunks
            file_path (str): Path to the original file
            file_size (int): Size of the original file in bytes
            line_count (int): Number of lines in the original file
            
        Returns:
            Dict[str, Any]: Combined data with summary
        """
        combined = {
            "file_info": {
                "path": file_path,
                "size_bytes": file_size,
                "line_count": line_count,
                "processed_at": datetime.now().isoformat()
            },
            "summary": {
                "chunks_processed": len(chunks),
                "test_results": {
                    "total": 0,
                    "passed": 0,
                    "failed": 0
                },
                "errors": {
                    "total": 0,
                    "by_type": {}
                },
                "logs": {
                    "total": 0,
                    "by_level": {}
                }
            },
            "data": [],
            "test_results": [],
            "errors": []
        }
        
        # Combine data from all chunks
        for chunk in chunks:
            combined["data"].extend(chunk["data"])
            combined["test_results"].extend(chunk["test_results"])
            combined["errors"].extend(chunk["errors"])
            
            # Update summary counters
            combined["summary"]["test_results"]["total"] += chunk["summary"]["test_results_count"]
            combined["summary"]["errors"]["total"] += chunk["summary"]["errors_count"]
            combined["summary"]["logs"]["total"] += chunk["summary"]["logs_count"]
        
        # Count passed/failed tests
        for result in combined["test_results"]:
            if result["result"] == "PASSED":
                combined["summary"]["test_results"]["passed"] += 1
            else:
                combined["summary"]["test_results"]["failed"] += 1
        
        # Count errors by type
        for error in combined["errors"]:
            error_type = error.get("type", "Unknown")
            if error_type not in combined["summary"]["errors"]["by_type"]:
                combined["summary"]["errors"]["by_type"][error_type] = 0
            combined["summary"]["errors"]["by_type"][error_type] += 1
        
        # Count logs by level
        for log in combined["data"]:
            level = log.get("level", "Unknown")
            if level not in combined["summary"]["logs"]["by_level"]:
                combined["summary"]["logs"]["by_level"][level] = 0
            combined["summary"]["logs"]["by_level"][level] += 1
        
        return combined

    def generate_token_efficient_report(self, processed_data: Dict[str, Any]) -> str:
        """
        Generate a token-efficient report from processed data.
        
        Args:
            processed_data (Dict[str, Any]): Processed data structure
            
        Returns:
            str: Token-efficient report text
        """
        report = []
        
        # Add header
        report.append("# TOKEN-OPTIMIZED TEST REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Source: {processed_data['file_info']['path']}")
        report.append(f"Original size: {processed_data['file_info']['line_count']} lines")
        report.append("")
        
        # Add summary section
        report.append("## SUMMARY")
        report.append(f"- Tests: {processed_data['summary']['test_results']['total']} " + 
                     f"(Passed: {processed_data['summary']['test_results']['passed']}, " + 
                     f"Failed: {processed_data['summary']['test_results']['failed']})")
        report.append(f"- Errors: {processed_data['summary']['errors']['total']}")
        report.append(f"- Log entries: {processed_data['summary']['logs']['total']}")
        report.append("")
        
        # Add error breakdown
        report.append("## ERROR TYPES")
        for error_type, count in processed_data['summary']['errors']['by_type'].items():
            report.append(f"- {error_type}: {count}")
        report.append("")
        
        # Add failed tests
        report.append("## FAILED TESTS")
        failed_tests = [test for test in processed_data['test_results'] if test['result'] == 'FAILED']
        for test in failed_tests[:10]:  # Limit to top 10 for token efficiency
            report.append(f"- {test['test']}")
        
        if len(failed_tests) > 10:
            report.append(f"- ... and {len(failed_tests) - 10} more")
        report.append("")
        
        # Add top errors
        report.append("## TOP ERRORS")
        for error in processed_data['errors'][:5]:  # Limit to top 5 for token efficiency
            report.append(f"- Type: {error.get('type', 'Unknown')}")
            if 'message' in error:
                report.append(f"  Message: {error['message']}")
            elif 'trace' in error:
                # Extract just the error message from the trace
                last_line = error['trace'].strip().split('\n')[-1]
                report.append(f"  Message: {last_line}")
            report.append("")
        
        report.append("## TOKEN EFFICIENCY")
        original_tokens = processed_data['file_info']['line_count'] * 8  # Rough estimate: 8 tokens per line
        report_tokens = len('\n'.join(report)) // 4  # Rough estimate: 1 token per 4 chars
        savings = 1 - (report_tokens / original_tokens)
        report.append(f"- Original estimated tokens: {original_tokens}")
        report.append(f"- Report tokens: {report_tokens}")
        report.append(f"- Token savings: {savings:.1%}")
        
        return '\n'.join(report)

# Command-line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process log files in chunks to optimize token usage")
    parser.add_argument("--file", required=True, help="Path to the log file to process")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Size of each chunk in lines")
    parser.add_argument("--output-dir", default="./processed_data", help="Directory for processed output")
    args = parser.parse_args()
    
    preprocessor = DataPreprocessor(output_dir=args.output_dir, max_chunk_size=args.chunk_size)
    processed_data = preprocessor.process_file(args.file, args.chunk_size)
    
    # Generate and print report
    report = preprocessor.generate_token_efficient_report(processed_data)
    print("\n" + report)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    report_path = os.path.join(args.output_dir, f"report_{os.path.basename(args.file)}_{timestamp}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")