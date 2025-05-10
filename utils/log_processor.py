import os
import re
import json
import logging
from datetime import datetime
from collections import defaultdict, Counter
import hashlib

logger = logging.getLogger(__name__)

class LogProcessor:
    """
    Utility to process test logs and optimize token usage by:
    - Extracting only essential information
    - Implementing log rotation with configurable size limits
    - Summarizing test failures by error type
    - Filtering duplicate stack traces
    """
    
    def __init__(self, log_dir="./logs", max_log_size_mb=10, max_logs=5):
        """
        Initialize the log processor.
        
        Args:
            log_dir (str): Directory to store processed logs
            max_log_size_mb (int): Maximum size of each log file in MB
            max_logs (int): Maximum number of log files to keep
        """
        self.log_dir = log_dir
        self.max_log_size_mb = max_log_size_mb
        self.max_logs = max_logs
        self.error_patterns = defaultdict(int)
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def _clean_text(self, text):
        """Remove excessive spacing and normalize text."""
        # Remove spaces between characters (which appear in the log file)
        text = re.sub(r'(?<=\w) (?=\w)', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_error_type(self, error_line):
        """
        Extract error type and message from an error line.
        Truncates error messages over a certain length to save tokens.
        """
        # Maximum error message length to keep
        MAX_ERROR_MSG_LENGTH = 150
        
        match = re.search(r'([A-Za-z]+Error): (.+)', error_line)
        if match:
            error_type = match.group(1)
            error_message = match.group(2)
            
            # Truncate long error messages
            if len(error_message) > MAX_ERROR_MSG_LENGTH:
                error_message = error_message[:MAX_ERROR_MSG_LENGTH] + "... [truncated]"
            
            return error_type, error_message
        
        # Additional patterns for extracting critical parts from stack traces
        # Look for file and line information
        file_line_match = re.search(r'File "([^"]+)", line (\d+)', error_line)
        if file_line_match:
            file_path = file_line_match.group(1)
            line_num = file_line_match.group(2)
            # Extract just the filename without the full path
            file_name = os.path.basename(file_path)
            return "StackTrace", f"In {file_name}:{line_num}"
        
        return "Unknown", error_line[:MAX_ERROR_MSG_LENGTH] if len(error_line) > MAX_ERROR_MSG_LENGTH else error_line
    
    def _hash_traceback(self, traceback_text):
        """Generate a hash for a traceback to identify duplicates."""
        # Clean and normalize the traceback before hashing
        cleaned = re.sub(r'0x[0-9a-fA-F]+', '0xXXXXXXXX', traceback_text)  # Remove memory addresses
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', 'TIMESTAMP', cleaned)  # Remove timestamps
        return hashlib.md5(cleaned.encode()).hexdigest()
    
    def process_log_file(self, input_path, output_path=None, token_limit=None):
        """
        Process a log file to extract essential information.
        
        Args:
            input_path (str): Path to the input log file
            output_path (str): Path to the output log file. If None, a default path is used.
            token_limit (int, optional): Maximum token limit for the processed output.
                                         Processing stops when this limit is approached.
            
        Returns:
            dict: Summary of processed log information
        """
        import re
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = os.path.join(self.log_dir, f"processed_log_{timestamp}.log")
        
        summary = {
            "test_failures": 0,
            "error_types": defaultdict(int),
            "duplicate_traces_removed": 0,
            "original_size": 0,
            "processed_size": 0,
            "compression_ratio": 0,
            "estimated_tokens": 0,
            "token_limit_reached": False
        }
        
        # Track seen tracebacks to eliminate duplicates
        seen_tracebacks = set()
        current_traceback = []
        in_traceback = False
        estimated_tokens = 0  # Track estimated tokens
        
        # Regex patterns for stack trace extraction
        stack_trace_patterns = [
            # Pattern for file paths in tracebacks
            r'File "([^"]+)", line (\d+)',
            # Pattern for exception headers
            r'([A-Za-z]+Error|Exception)(\s*:)',
            # Pattern for relevant function calls
            r'in ([a-zA-Z_][a-zA-Z0-9_]*)\(',
        ]
        
        with open(input_path, 'r', encoding='utf-8', errors='replace') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            # Write header to the processed log
            header = f"PROCESSED LOG - {datetime.now().isoformat()}\n"
            header += "===============================\n\n"
            outfile.write(header)
            estimated_tokens += len(header) // 4  # Simple initial estimate for header
            
            failure_count = 0
            line_count = 0
            processed_line_count = 0
            
            for line in infile:
                line_count += 1
                cleaned_line = self._clean_text(line)
                
                # Skip empty lines after cleaning
                if not cleaned_line:
                    continue
                
                # Track traceback sections
                if "Traceback (most recent call last):" in cleaned_line:
                    in_traceback = True
                    current_traceback = [cleaned_line]
                    continue
                
                if in_traceback:
                    # Add line to current traceback
                    current_traceback.append(cleaned_line)
                    
                    # Check if traceback ends (typically with an exception message)
                    if re.search(r'([A-Za-z]+Error|Exception):', cleaned_line):
                        in_traceback = False
                        # Apply regex patterns to extract critical parts of stack trace
                        critical_lines = []
                        for line in current_traceback:
                            # Always include the first and last lines of the traceback
                            if line == current_traceback[0] or line == current_traceback[-1]:
                                critical_lines.append(line)
                                continue
                                
                            # Check if line matches any important pattern
                            if any(re.search(pattern, line) for pattern in stack_trace_patterns):
                                critical_lines.append(line)
                        
                        # Use critical lines instead of full traceback if we have enough
                        if len(critical_lines) >= 3:
                            traceback_text = "\n".join(critical_lines)
                        else:
                            traceback_text = "\n".join(current_traceback)
                            
                        traceback_hash = self._hash_traceback(traceback_text)
                        
                        # Only output this traceback if we haven't seen it before
                        if traceback_hash not in seen_tracebacks:
                            # Estimate tokens for this traceback
                            traceback_tokens = len(traceback_text) // 4
                            
                            # Check if adding this would exceed token limit
                            if token_limit and (estimated_tokens + traceback_tokens > token_limit):
                                summary["token_limit_reached"] = True
                                outfile.write("\n\n--- TOKEN LIMIT REACHED - TRUNCATING OUTPUT ---\n")
                                break
                                
                            outfile.write(traceback_text + "\n\n")
                            estimated_tokens += traceback_tokens
                            seen_tracebacks.add(traceback_hash)
                            
                            # Extract and count error type
                            error_type, error_message = self._extract_error_type(cleaned_line)
                            summary["error_types"][error_type] += 1
                        else:
                            summary["duplicate_traces_removed"] += 1
                        
                        current_traceback = []
                    continue
                
                # Handle test failures
                if "FAILED" in cleaned_line and "test" in cleaned_line:
                    failure_count += 1
                    failure_text = f"FAILURE #{failure_count}: {cleaned_line}\n"
                    
                    # Check if adding this would exceed token limit
                    failure_tokens = len(failure_text) // 4
                    if token_limit and (estimated_tokens + failure_tokens > token_limit):
                        summary["token_limit_reached"] = True
                        outfile.write("\n\n--- TOKEN LIMIT REACHED - TRUNCATING OUTPUT ---\n")
                        break
                    
                    outfile.write(failure_text)
                    estimated_tokens += failure_tokens
                    processed_line_count += 1
                    continue
                
                # Process normal log lines (excluding verbose/repetitive content)
                if any(important in cleaned_line for important in
                      ["ERROR", "CRITICAL", "WARNING", "FAIL", "test", "assert", "Exception"]):
                    log_line = cleaned_line + "\n"
                    
                    # Check if adding this would exceed token limit
                    line_tokens = len(log_line) // 4
                    if token_limit and (estimated_tokens + line_tokens > token_limit):
                        summary["token_limit_reached"] = True
                        outfile.write("\n\n--- TOKEN LIMIT REACHED - TRUNCATING OUTPUT ---\n")
                        break
                    
                    outfile.write(log_line)
                    estimated_tokens += line_tokens
                    processed_line_count += 1
            
            # Write summary at the end
            summary_text = "\n\n=== SUMMARY ===\n"
            summary_text += f"Total failures: {failure_count}\n"
            
            for error_type, count in summary["error_types"].items():
                summary_text += f"{error_type}: {count} occurrences\n"
            
            summary_text += f"Duplicate stack traces removed: {summary['duplicate_traces_removed']}\n"
            
            if summary["token_limit_reached"]:
                summary_text += f"NOTE: Log processing was truncated to stay within token limit.\n"
                
            outfile.write(summary_text)
            estimated_tokens += len(summary_text) // 4
            
            # Update summary statistics
            summary["test_failures"] = failure_count
            summary["original_size"] = line_count
            summary["processed_size"] = processed_line_count
            summary["estimated_tokens"] = estimated_tokens
            if line_count > 0:
                summary["compression_ratio"] = 1 - (processed_line_count / line_count)
        
        return summary, output_path
    
    def rotate_logs(self):
        """
        Implement log rotation to keep log directory within size limits.
        Removes oldest logs when total count exceeds max_logs.
        """
        log_files = []
        for filename in os.listdir(self.log_dir):
            if filename.startswith("processed_log_") and filename.endswith(".log"):
                file_path = os.path.join(self.log_dir, filename)
                log_files.append((file_path, os.path.getmtime(file_path)))
        
        # Sort by modification time (oldest first)
        log_files.sort(key=lambda x: x[1])
        
        # Remove oldest logs if we exceed the maximum
        while len(log_files) > self.max_logs:
            oldest_file = log_files.pop(0)[0]
            try:
                os.remove(oldest_file)
                logger.info(f"Rotated log file: {oldest_file}")
            except Exception as e:
                logger.error(f"Failed to rotate log file {oldest_file}: {str(e)}")
    
    def summarize_test_failures(self, input_path):
        """
        Create a summary of test failures by error type.
        
        Args:
            input_path (str): Path to the log file to analyze
            
        Returns:
            dict: Summary of failures by error type
        """
        errors_by_type = defaultdict(list)
        test_file_patterns = defaultdict(Counter)
        
        with open(input_path, 'r', encoding='utf-8', errors='replace') as infile:
            for line in infile:
                cleaned_line = self._clean_text(line)
                
                # Look for FAILED test lines
                if "FAILED" in cleaned_line and "test" in cleaned_line:
                    # Extract test file and test name
                    match = re.search(r'FAILED\s+([\w\/]+\.py)::([\w_]+)', cleaned_line)
                    if match:
                        test_file = match.group(1)
                        test_name = match.group(2)
                        
                        # Look for error message
                        error_match = re.search(r'([A-Za-z]+Error):\s+(.+)', cleaned_line)
                        if error_match:
                            error_type = error_match.group(1)
                            error_msg = error_match.group(2)
                            
                            errors_by_type[error_type].append({
                                "test_file": test_file,
                                "test_name": test_name,
                                "error_message": error_msg
                            })
                            
                            test_file_patterns[error_type][test_file] += 1
        
        # Create the summary
        summary = {
            "errors_by_type": {k: v for k, v in errors_by_type.items()},
            "test_file_patterns": {k: dict(v) for k, v in test_file_patterns.items()},
            "total_failures": sum(len(v) for v in errors_by_type.values())
        }
        
        return summary
    
    def create_summary_file(self, summary, output_path=None):
        """
        Create a summary file with error statistics.
        
        Args:
            summary (dict): Summary data
            output_path (str): Path to output summary file
            
        Returns:
            str: Path to the summary file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = os.path.join(self.log_dir, f"summary_{timestamp}.json")
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            json.dump(summary, outfile, indent=2)
        
        return output_path