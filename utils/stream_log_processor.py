import os
import re
import json
import logging
import hashlib
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any, Optional, Set
from token_budget_manager import TokenBudgetManager

logger = logging.getLogger(__name__)

class StreamLogProcessor:
    """
    Enhanced log processor that processes files line-by-line using a streaming approach.
    
    Improvements over the original LogProcessor:
    - Stream processing architecture (processes files line-by-line)
    - Token budget management for different components
    - Processes files in smaller chunks with budget allocation per chunk
    - Deduplication logic that works across processing sessions
    - Adaptive configuration based on input file size and log type
    """
    
    # Configuration profiles for different log types
    CONFIG_PROFILES = {
        "test_logs": {
            "error_retention": 0.8,    # Focus on error information
            "stack_trace_detail": 0.5, # Medium stack trace detail
            "test_result_detail": 0.8, # High test result detail
            "summary_size": 0.5,       # Medium summary size
        },
        "error_logs": {
            "error_retention": 0.9,    # High error information retention
            "stack_trace_detail": 0.7, # High stack trace detail
            "test_result_detail": 0.3, # Low test result detail
            "summary_size": 0.6,       # Medium summary size
        },
        "info_logs": {
            "error_retention": 0.5,    # Low error information retention
            "stack_trace_detail": 0.3, # Low stack trace detail
            "test_result_detail": 0.5, # Medium test result detail
            "summary_size": 0.4,       # Low summary size
        }
    }
    
    def __init__(self, 
                 log_dir: str = "./logs", 
                 max_log_size_mb: int = 5, 
                 max_logs: int = 10,
                 token_budget: int = 76659,
                 chunk_size: int = 500,
                 profile: str = "test_logs",
                 deduplication_file: str = None):
        """
        Initialize the stream log processor.
        
        Args:
            log_dir (str): Directory to store processed logs
            max_log_size_mb (int): Maximum size of each log file in MB
            max_logs (int): Maximum number of log files to keep
            token_budget (int): Maximum token budget for processing
            chunk_size (int): Number of lines to process in each chunk
            profile (str): Configuration profile to use
            deduplication_file (str): Path to file storing known error patterns
        """
        self.log_dir = log_dir
        self.max_log_size_mb = max_log_size_mb
        self.max_logs = max_logs
        self.chunk_size = chunk_size
        self.profile = profile if profile in self.CONFIG_PROFILES else "test_logs"
        self.config = self.CONFIG_PROFILES[self.profile]
        
        # Create token budget manager
        self.token_manager = TokenBudgetManager(max_token_budget=token_budget)
        
        # Error pattern tracking
        self.error_patterns = defaultdict(int)
        self.known_traceback_hashes = set()
        
        # Set up deduplication file for persistence across runs
        if deduplication_file is None:
            self.deduplication_file = os.path.join(log_dir, "known_error_patterns.json")
        else:
            self.deduplication_file = deduplication_file
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Load known error patterns if available
        self._load_known_error_patterns()
    
    def _load_known_error_patterns(self):
        """Load known error patterns from the deduplication file."""
        if os.path.exists(self.deduplication_file):
            try:
                with open(self.deduplication_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.error_patterns = defaultdict(int, data.get("error_patterns", {}))
                    self.known_traceback_hashes = set(data.get("traceback_hashes", []))
                    logger.info(f"Loaded {len(self.known_traceback_hashes)} known error patterns")
            except Exception as e:
                logger.error(f"Error loading known error patterns: {str(e)}")
    
    def _save_known_error_patterns(self):
        """Save known error patterns to the deduplication file."""
        try:
            with open(self.deduplication_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "error_patterns": dict(self.error_patterns),
                    "traceback_hashes": list(self.known_traceback_hashes)
                }, f, indent=2)
            logger.info(f"Saved {len(self.known_traceback_hashes)} known error patterns")
        except Exception as e:
            logger.error(f"Error saving known error patterns: {str(e)}")
    
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
        # Maximum error message length to keep - adapted by config profile
        max_error_msg_length = int(150 * self.config["error_retention"])
        
        match = re.search(r'([A-Za-z]+Error): (.+)', error_line)
        if match:
            error_type = match.group(1)
            error_message = match.group(2)
            
            # Truncate long error messages
            if len(error_message) > max_error_msg_length:
                error_message = error_message[:max_error_msg_length] + "... [truncated]"
            
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
        
        return "Unknown", error_line[:max_error_msg_length] if len(error_message) > max_error_msg_length else error_line
    
    def _hash_traceback(self, traceback_text):
        """Generate a hash for a traceback to identify duplicates."""
        # Clean and normalize the traceback before hashing
        cleaned = re.sub(r'0x[0-9a-fA-F]+', '0xXXXXXXXX', traceback_text)  # Remove memory addresses
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', 'TIMESTAMP', cleaned)  # Remove timestamps
        cleaned = re.sub(r'line \d+', 'line XX', cleaned)  # Normalize line numbers
        return hashlib.md5(cleaned.encode()).hexdigest()
    
    def _extract_critical_stack_trace(self, traceback_lines):
        """
        Extract critical lines from a stack trace based on config profile.
        
        Args:
            traceback_lines (List[str]): Lines of the stack trace
            
        Returns:
            List[str]: Critical lines from the stack trace
        """
        if not traceback_lines:
            return []
            
        # Patterns for important lines in stack traces
        stack_trace_patterns = [
            # Pattern for file paths in tracebacks
            r'File "([^"]+)", line (\d+)',
            # Pattern for exception headers
            r'([A-Za-z]+Error|Exception)(\s*:)',
            # Pattern for relevant function calls
            r'in ([a-zA-Z_][a-zA-Z0-9_]*)\(',
        ]
        
        # Always include first and last lines (traceback header and exception)
        critical_lines = [traceback_lines[0], traceback_lines[-1]]
        
        # Calculate how many additional lines to include based on stack trace detail config
        detail_level = self.config["stack_trace_detail"]
        max_additional_lines = max(1, int(len(traceback_lines) * detail_level))
        
        # Add lines matching important patterns, up to the maximum
        additional_lines = []
        for line in traceback_lines[1:-1]:  # Skip first and last which we always include
            if any(re.search(pattern, line) for pattern in stack_trace_patterns):
                additional_lines.append(line)
                
                if len(additional_lines) >= max_additional_lines:
                    break
        
        # Insert additional lines in their original order
        for line in additional_lines:
            insert_pos = traceback_lines.index(line)
            if insert_pos > 0 and insert_pos < len(critical_lines):
                critical_lines.insert(insert_pos, line)
            else:
                critical_lines.append(line)
        
        return critical_lines
    
    def _estimate_tokens(self, text):
        """Estimate the number of tokens in a text."""
        # Simple estimate: 1 token ≈ 4 characters
        return len(text) // 4
    
    def estimate_file_size(self, file_path):
        """
        Estimate file size and suggest optimal chunk size and processing parameters.
        
        Args:
            file_path (str): Path to the file to estimate
            
        Returns:
            dict: Estimated parameters including file size, line count, and recommended chunk size
        """
        try:
            file_size = os.path.getsize(file_path)
            
            # Sample the file to estimate average line length
            sample_size = min(5000, file_size)  # Read up to 5KB
            sample_lines = 0
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                sample = f.read(sample_size)
                sample_lines = sample.count('\n') + (0 if sample.endswith('\n') else 1)
            
            avg_line_length = sample_size / max(1, sample_lines)
            estimated_lines = int(file_size / avg_line_length)
            
            # Determine optimal chunk size
            if estimated_lines > 10000:
                chunk_size = 1000
            elif estimated_lines > 5000:
                chunk_size = 500
            elif estimated_lines > 1000:
                chunk_size = 200
            else:
                chunk_size = 100
            
            # Determine optimal configuration profile based on file content
            profile = "test_logs"  # Default
            if "error" in sample.lower() and "test" not in sample.lower():
                profile = "error_logs"
            elif "info" in sample.lower() and "error" not in sample.lower():
                profile = "info_logs"
            
            return {
                "file_size_bytes": file_size,
                "estimated_lines": estimated_lines,
                "recommended_chunk_size": chunk_size,
                "recommended_profile": profile,
                "avg_line_length": avg_line_length
            }
            
        except Exception as e:
            logger.error(f"Error estimating file size: {str(e)}")
            return {
                "file_size_bytes": 0,
                "estimated_lines": 0,
                "recommended_chunk_size": self.chunk_size,
                "recommended_profile": self.profile,
                "avg_line_length": 0
            }
    
    def auto_configure(self, file_path):
        """
        Automatically configure processing parameters based on input file.
        
        Args:
            file_path (str): Path to the input file
            
        Returns:
            dict: Updated configuration
        """
        # Estimate file size and parameters
        estimates = self.estimate_file_size(file_path)
        
        # Update configuration
        self.chunk_size = estimates["recommended_chunk_size"]
        self.profile = estimates["recommended_profile"]
        self.config = self.CONFIG_PROFILES[self.profile]
        
        logger.info(f"Auto-configured for file: {file_path}")
        logger.info(f"Chunk size: {self.chunk_size}")
        logger.info(f"Profile: {self.profile}")
        
        return {
            "chunk_size": self.chunk_size,
            "profile": self.profile,
            "config": self.config,
            "estimates": estimates
        }
    
    def save_configuration(self, name, config_dict=None):
        """
        Save current configuration as a named profile.
        
        Args:
            name (str): Profile name
            config_dict (dict, optional): Configuration to save. If None, uses current config.
            
        Returns:
            bool: Success status
        """
        if config_dict is None:
            config_dict = self.config.copy()
        
        # Update CONFIG_PROFILES
        self.CONFIG_PROFILES[name] = config_dict
        
        # Save to configuration file
        config_path = os.path.join(self.log_dir, "log_processor_configs.json")
        try:
            # Load existing configurations
            configs = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
            
            # Update with new configuration
            configs[name] = config_dict
            
            # Save updated configurations
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=2)
            
            logger.info(f"Saved configuration profile: {name}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def load_configuration(self, name):
        """
        Load a named configuration profile.
        
        Args:
            name (str): Profile name
            
        Returns:
            bool: Success status
        """
        # Check if profile exists in memory
        if name in self.CONFIG_PROFILES:
            self.profile = name
            self.config = self.CONFIG_PROFILES[name]
            logger.info(f"Loaded configuration profile: {name}")
            return True
        
        # Try to load from file
        config_path = os.path.join(self.log_dir, "log_processor_configs.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
                
                if name in configs:
                    self.CONFIG_PROFILES[name] = configs[name]
                    self.profile = name
                    self.config = configs[name]
                    logger.info(f"Loaded configuration profile: {name}")
                    return True
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
        
        logger.warning(f"Configuration profile not found: {name}")
        return False
    
    def process_log_file_streaming(self, input_path, output_path=None, token_limit=None):
        """
        Process a log file using streaming to extract essential information.
        
        Args:
            input_path (str): Path to the input log file
            output_path (str): Path to the output log file. If None, a default path is used.
            token_limit (int, optional): Maximum token limit for the processed output.
            
        Returns:
            dict: Summary of processed log information
        """
        # Auto-configure based on input file if token_limit is provided
        if token_limit is not None:
            self.token_manager.max_token_budget = token_limit
            self.auto_configure(input_path)
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = os.path.join(self.log_dir, f"processed_log_{timestamp}.log")
        
        # Initialize budget allocation
        self.token_manager.allocate_budget([
            "header", "test_failures", "stack_traces", "warnings", "summary"
        ])
        
        # Initialize summary statistics
        summary = {
            "test_failures": 0,
            "error_types": defaultdict(int),
            "duplicate_traces_removed": 0,
            "original_size": 0,
            "processed_size": 0,
            "compression_ratio": 0,
            "estimated_tokens": 0,
            "token_limit_reached": False,
            "chunks_processed": 0
        }
        
        # Open output file for writing
        with open(output_path, 'w', encoding='utf-8') as outfile:
            # Write header
            header = f"PROCESSED LOG - {datetime.now().isoformat()}\n"
            header += f"Profile: {self.profile}\n"
            header += "===============================\n\n"
            outfile.write(header)
            header_tokens = self._estimate_tokens(header)
            self.token_manager.track_usage("header", header_tokens)
            summary["estimated_tokens"] += header_tokens
            
            # Process the file in chunks
            try:
                file_size = os.path.getsize(input_path)
                chunk_budget = self.token_manager.allocate_chunk_budget(
                    file_size, self.chunk_size
                )
                
                self._process_file_in_chunks(
                    input_path, outfile, summary, chunk_budget
                )
                
                # Write summary at the end
                self._write_summary(outfile, summary)
                
                # Save known error patterns for future deduplication
                self._save_known_error_patterns()
                
            except Exception as e:
                logger.error(f"Error processing log file: {str(e)}")
                error_msg = f"\n\nERROR DURING PROCESSING: {str(e)}\n"
                outfile.write(error_msg)
                summary["error"] = str(e)
        
        return summary, output_path
    
    def _process_file_in_chunks(self, input_path, outfile, summary, chunk_budget):
        """
        Process a file in chunks to extract essential information.
        
        Args:
            input_path (str): Path to the input file
            outfile: Output file object for writing
            summary (dict): Summary statistics to update
            chunk_budget (int): Token budget per chunk
        """
        seen_tracebacks = self.known_traceback_hashes.copy()
        current_traceback = []
        in_traceback = False
        line_count = 0
        processed_line_count = 0
        current_chunk = []
        current_chunk_size = 0
        chunk_count = 0
        
        # Stack trace extraction patterns
        stack_trace_patterns = [
            # Pattern for file paths in tracebacks
            r'File "([^"]+)", line (\d+)',
            # Pattern for exception headers
            r'([A-Za-z]+Error|Exception)(\s*:)',
            # Pattern for relevant function calls
            r'in ([a-zA-Z_][a-zA-Z0-9_]*)\(',
        ]
        
        with open(input_path, 'r', encoding='utf-8', errors='replace') as infile:
            for line in infile:
                line_count += 1
                cleaned_line = self._clean_text(line)
                
                # Skip empty lines after cleaning
                if not cleaned_line:
                    continue
                
                # Add line to current chunk
                current_chunk.append(cleaned_line)
                current_chunk_size += len(cleaned_line)
                
                # Process chunk when it reaches chunk_size
                if len(current_chunk) >= self.chunk_size:
                    self._process_chunk_content(
                        current_chunk, outfile, summary, chunk_budget,
                        seen_tracebacks, stack_trace_patterns
                    )
                    
                    processed_line_count += len(current_chunk)
                    chunk_count += 1
                    current_chunk = []
                    current_chunk_size = 0
                    
                    # Check if we're approaching token limit
                    if summary["estimated_tokens"] >= self.token_manager.max_token_budget * 0.9:
                        summary["token_limit_reached"] = True
                        outfile.write("\n\n--- TOKEN LIMIT APPROACHED - TRUNCATING OUTPUT ---\n")
                        break
            
            # Process any remaining lines
            if current_chunk:
                self._process_chunk_content(
                    current_chunk, outfile, summary, chunk_budget,
                    seen_tracebacks, stack_trace_patterns
                )
                processed_line_count += len(current_chunk)
                chunk_count += 1
        
        # Update summary statistics
        summary["original_size"] = line_count
        summary["processed_size"] = processed_line_count
        summary["chunks_processed"] = chunk_count
        if line_count > 0:
            summary["compression_ratio"] = 1 - (processed_line_count / line_count)
    
    def _process_chunk_content(self, chunk, outfile, summary, chunk_budget,
                              seen_tracebacks, stack_trace_patterns):
        """
        Process a chunk of content and extract essential information.
        
        Args:
            chunk (List[str]): List of lines in the chunk
            outfile: Output file object for writing
            summary (dict): Summary statistics to update
            chunk_budget (int): Token budget for this chunk
            seen_tracebacks (Set[str]): Set of seen traceback hashes
            stack_trace_patterns (List[str]): Patterns to match in stack traces
        """
        in_traceback = False
        current_traceback = []
        current_chunk_tokens = 0
        chunk_verbosity = "full"  # Start with full verbosity
        
        for line in chunk:
            # Track traceback sections
            if "Traceback (most recent call last):" in line:
                in_traceback = True
                current_traceback = [line]
                continue
            
            if in_traceback:
                # Add line to current traceback
                current_traceback.append(line)
                
                # Check if traceback ends (typically with an exception message)
                if re.search(r'([A-Za-z]+Error|Exception):', line):
                    in_traceback = False
                    
                    # Extract critical parts of stack trace
                    critical_lines = self._extract_critical_stack_trace(current_traceback)
                    
                    # Use critical lines instead of full traceback
                    if critical_lines:
                        traceback_text = "\n".join(critical_lines)
                    else:
                        traceback_text = "\n".join(current_traceback)
                    
                    traceback_hash = self._hash_traceback(traceback_text)
                    
                    # Only output this traceback if we haven't seen it before
                    if traceback_hash not in seen_tracebacks:
                        # Estimate tokens for this traceback
                        traceback_tokens = self._estimate_tokens(traceback_text)
                        
                        # Check if adding this would exceed chunk budget
                        if current_chunk_tokens + traceback_tokens <= chunk_budget:
                            outfile.write(traceback_text + "\n\n")
                            current_chunk_tokens += traceback_tokens
                            summary["estimated_tokens"] += traceback_tokens
                            seen_tracebacks.add(traceback_hash)
                            self.known_traceback_hashes.add(traceback_hash)
                            
                            # Extract and count error type
                            error_type, error_message = self._extract_error_type(line)
                            summary["error_types"][error_type] += 1
                            
                            # Add as prioritized content for error types
                            self.token_manager.add_prioritized_content(
                                f"{error_type}: {error_message}",
                                "high",
                                traceback_tokens
                            )
                        else:
                            # Reduce verbosity if budget is tight
                            chunk_verbosity = self.token_manager.adjust_verbosity(
                                (chunk_budget - current_chunk_tokens) / chunk_budget
                            )
                            
                            if chunk_verbosity == "minimal":
                                # Just extract error type for minimal verbosity
                                error_type, error_message = self._extract_error_type(line)
                                error_line = f"{error_type}: {error_message}\n"
                                error_tokens = self._estimate_tokens(error_line)
                                
                                if current_chunk_tokens + error_tokens <= chunk_budget:
                                    outfile.write(error_line)
                                    current_chunk_tokens += error_tokens
                                    summary["estimated_tokens"] += error_tokens
                                    
                                    # Count error type
                                    summary["error_types"][error_type] += 1
                    else:
                        summary["duplicate_traces_removed"] += 1
                    
                    current_traceback = []
                continue
            
            # Handle test failures
            if "FAILED" in line and "test" in line:
                summary["test_failures"] += 1
                failure_text = f"FAILURE #{summary['test_failures']}: {line}\n"
                
                # Estimate tokens for this failure
                failure_tokens = self._estimate_tokens(failure_text)
                
                # Check if adding this would exceed chunk budget
                if current_chunk_tokens + failure_tokens <= chunk_budget:
                    outfile.write(failure_text)
                    current_chunk_tokens += failure_tokens
                    summary["estimated_tokens"] += failure_tokens
                    
                    # Add as prioritized content for test failures
                    self.token_manager.add_prioritized_content(
                        failure_text,
                        "critical",
                        failure_tokens
                    )
                else:
                    # Break if we're out of budget
                    break
                
                continue
            
            # Process normal log lines based on verbosity level
            if any(important in line for important in
                  ["ERROR", "CRITICAL", "WARNING", "FAIL", "test", "assert", "Exception"]):
                
                priority = "medium"
                if "ERROR" in line or "CRITICAL" in line or "FAIL" in line:
                    priority = "high"
                elif "WARNING" in line:
                    priority = "medium"
                else:
                    priority = "low"
                
                # Skip lower priority content if verbosity is reduced
                if (chunk_verbosity == "minimal" and priority not in ["critical", "high"]) or \
                   (chunk_verbosity == "reduced" and priority == "low"):
                    continue
                
                log_line = line + "\n"
                line_tokens = self._estimate_tokens(log_line)
                
                # Check if adding this would exceed chunk budget
                if current_chunk_tokens + line_tokens <= chunk_budget:
                    outfile.write(log_line)
                    current_chunk_tokens += line_tokens
                    summary["estimated_tokens"] += line_tokens
                    
                    # Add to prioritized content
                    self.token_manager.add_prioritized_content(
                        log_line,
                        priority,
                        line_tokens
                    )
                else:
                    # Break if we're out of budget
                    break
    
    def _write_summary(self, outfile, summary):
        """
        Write summary information at the end of the processed log file.
        
        Args:
            outfile: Output file object for writing
            summary (dict): Summary statistics
        """
        summary_text = "\n\n=== SUMMARY ===\n"
        summary_text += f"Total failures: {summary['test_failures']}\n"
        
        for error_type, count in summary["error_types"].items():
            summary_text += f"{error_type}: {count} occurrences\n"
        
        summary_text += f"Duplicate stack traces removed: {summary['duplicate_traces_removed']}\n"
        summary_text += f"Chunks processed: {summary['chunks_processed']}\n"
        summary_text += f"Original lines: {summary['original_size']}\n"
        summary_text += f"Processed lines: {summary['processed_size']}\n"
        summary_text += f"Compression ratio: {summary['compression_ratio']:.2%}\n"
        summary_text += f"Estimated tokens: {summary['estimated_tokens']}\n"
        
        if summary["token_limit_reached"]:
            summary_text += f"NOTE: Log processing was truncated to stay within token limit.\n"
        
        summary_tokens = self._estimate_tokens(summary_text)
        summary["estimated_tokens"] += summary_tokens
        
        outfile.write(summary_text)
    
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
        # This can be done more efficiently with streaming
        errors_by_type = defaultdict(list)
        test_file_patterns = defaultdict(Counter)
        line_count = 0
        
        with open(input_path, 'r', encoding='utf-8', errors='replace') as infile:
            for line in infile:
                line_count += 1
                if line_count % 1000 == 0:
                    logger.debug(f"Processed {line_count} lines for summary")
                
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