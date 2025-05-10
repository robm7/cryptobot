#!/usr/bin/env python
"""
Token Estimation Accuracy Validator

This script validates the token estimation accuracy of the token optimization system
by comparing estimated token counts against actual tokenization by LLM tokenizers.
It tests with various content types (code, logs, markdown, etc.) and reports on
estimation accuracy.

Dependencies:
- tiktoken (OpenAI's tokenizer): pip install tiktoken
- transformers (for other tokenizers): pip install transformers
"""

import os
import sys
import json
import re
import argparse
import logging
import random
import math
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import system's token estimator
from token_optimization_system import estimate_tokens

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("token_validation.log")
    ]
)
logger = logging.getLogger("token_validator")

# Try to import tokenizers, with graceful fallbacks
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not installed. OpenAI tokenizer will not be available.")

try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not installed. Hugging Face tokenizers will not be available.")


class TokenAccuracyValidator:
    """Validates token estimation accuracy against real tokenizers."""
    
    def __init__(self, output_dir="./validation_results", with_plots=True):
        """
        Initialize the validator with output directory.
        
        Args:
            output_dir (str): Directory to store validation results
            with_plots (bool): Whether to generate visualization plots
        """
        self.output_dir = output_dir
        self.with_plots = with_plots
        self.tokenizers = self._initialize_tokenizers()
        self.results = {
            "summary": {},
            "content_types": {},
            "samples": [],
            "algorithm_info": {}  # Stores info about the estimation algorithm
        }
        
        # Metrics to track
        self.metrics = {
            "precision": [],
            "recall": [],
            "f1_score": [],
            "mean_absolute_error": [],
            "mean_absolute_percentage_error": [],
            "root_mean_squared_error": [],
            "max_error": 0,
            "overestimation_count": 0,
            "underestimation_count": 0
        }
        
        # Track calibration factors for different content types
        self.calibration_factors = defaultdict(list)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Create plots directory
        if with_plots:
            self.plots_dir = os.path.join(output_dir, "plots")
            os.makedirs(self.plots_dir, exist_ok=True)
    
    def _initialize_tokenizers(self):
        """Initialize available tokenizers."""
        tokenizers = {}
        
        # Add tiktoken (OpenAI) tokenizers if available
        if TIKTOKEN_AVAILABLE:
            try:
                tokenizers["cl100k_base"] = tiktoken.get_encoding("cl100k_base")  # Used by gpt-4, claude
                tokenizers["p50k_base"] = tiktoken.get_encoding("p50k_base")      # Used by gpt-3.5
            except Exception as e:
                logger.error(f"Failed to initialize tiktoken encoders: {e}")
        
        # Add Hugging Face tokenizers if available
        if TRANSFORMERS_AVAILABLE:
            try:
                # Used by various LLama models
                tokenizers["llama"] = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf", use_fast=True)
            except Exception as e:
                logger.error(f"Failed to initialize Llama tokenizer: {e}")
            
            try:
                # Used by Mistral models
                tokenizers["mistral"] = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1", use_fast=True)
            except Exception as e:
                logger.error(f"Failed to initialize Mistral tokenizer: {e}")
        
        # If no tokenizers are available, add a character-based approximation
        if not tokenizers:
            logger.warning("No tokenizers available. Using character-based approximation.")
            tokenizers["char_approx"] = "char_approx"
        
        return tokenizers
    
    def _count_tokens_with_tokenizer(self, text, tokenizer_name, tokenizer):
        """
        Count tokens using the specified tokenizer.
        
        Args:
            text (str): The text to tokenize
            tokenizer_name (str): Name of the tokenizer
            tokenizer: The tokenizer object
            
        Returns:
            int: Token count
        """
        try:
            if tokenizer_name.startswith("cl") or tokenizer_name.startswith("p50k"):
                # tiktoken tokenizers (OpenAI/Anthropic)
                return len(tokenizer.encode(text))
            elif tokenizer_name in ["llama", "mistral"]:
                # Transformers tokenizers
                tokens = tokenizer.encode(text)
                # Account for special tokens in transformers tokenizers
                return len(tokens) - tokenizer.num_special_tokens_to_add(False)
            elif tokenizer_name == "claude":
                # Claude tokenizer approximation if available
                return len(tokenizer.encode(text))
            elif tokenizer_name == "char_approx":
                # Simple character-based approximation (fallback)
                # Adjusted based on empirical analysis
                char_per_token = 4.0
                if len(text) > 0:
                    # Adjust ratio for special character density
                    special_ratio = len(re.findall(r'[{}()\[\]<>:;,\.\-=+*/\\]', text)) / len(text)
                    if special_ratio > 0.1:
                        char_per_token = 3.0  # More special chars = fewer chars per token
                    
                    # Adjust for code vs natural language
                    code_indicators = ["def ", "class ", "import ", "function", "return", "if ", "for ", "while "]
                    is_likely_code = any(indicator in text for indicator in code_indicators)
                    if is_likely_code:
                        char_per_token = 3.5  # Code typically has more tokens per character
                        
                return max(1, int(len(text) / char_per_token))
            else:
                raise ValueError(f"Unknown tokenizer: {tokenizer_name}")
        except Exception as e:
            logger.error(f"Error in tokenization with {tokenizer_name}: {e}")
            # Fall back to character-based approximation
            return max(1, len(text) // 4)
    
    def validate_sample(self, content, content_type, description=""):
        """
        Validate token estimation accuracy for a single content sample.
        
        Args:
            content (str): The text content to validate
            content_type (str): Type of content (e.g., 'python', 'log', 'json')
            description (str): Optional description of the sample
            
        Returns:
            dict: Results of the validation
        """
        # Get system estimation
        try:
            system_estimation = estimate_tokens(content)
        except Exception as e:
            logger.error(f"Error estimating tokens with system: {e}")
            system_estimation = 0
        
        # Get actual token counts from available tokenizers
        actual_counts = {}
        for name, tokenizer in self.tokenizers.items():
            try:
                actual_counts[name] = self._count_tokens_with_tokenizer(content, name, tokenizer)
            except Exception as e:
                logger.error(f"Error counting tokens with {name}: {e}")
                actual_counts[name] = 0
        
        # Calculate errors and statistics
        errors = {}
        error_percentages = {}
        
        for name, count in actual_counts.items():
            if count > 0:
                errors[name] = system_estimation - count
                error_percentages[name] = (errors[name] / count) * 100
        
        # Determine primary tokenizer for reference (prefer cl100k_base if available)
        primary_tokenizer = "cl100k_base" if "cl100k_base" in actual_counts else list(actual_counts.keys())[0]
        primary_count = actual_counts.get(primary_tokenizer, 0)
        
        # Prepare result data
        result = {
            "content_type": content_type,
            "description": description,
            "content_length": len(content),
            "system_estimation": system_estimation,
            "actual_counts": actual_counts,
            "errors": errors,
            "error_percentages": error_percentages,
            "primary_tokenizer": primary_tokenizer,
            "primary_count": primary_count,
            "primary_error": errors.get(primary_tokenizer, 0),
            "primary_error_percentage": error_percentages.get(primary_tokenizer, 0),
            "timestamp": datetime.now().isoformat()
        }
        
        # Log results
        logger.info(f"Validated {content_type} sample ({len(content)} chars)")
        logger.info(f"System estimation: {system_estimation} tokens")
        logger.info(f"Actual ({primary_tokenizer}): {primary_count} tokens")
        logger.info(f"Error: {result['primary_error']} tokens ({result['primary_error_percentage']:.2f}%)")
        
        # Store result
        self.results["samples"].append(result)
        
        return result
    
    def validate_file(self, file_path, content_type=None):
        """
        Validate token estimation accuracy for a file.
        
        Args:
            file_path (str): Path to the file
            content_type (str, optional): Type of content. If None, inferred from file extension.
            
        Returns:
            dict: Results of the validation
        """
        # Infer content type from file extension if not provided
        if content_type is None:
            ext = os.path.splitext(file_path)[1].lower()
            content_type = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.html': 'html',
                '.css': 'css',
                '.md': 'markdown',
                '.json': 'json',
                '.xml': 'xml',
                '.log': 'log',
                '.txt': 'text',
                '.sh': 'shell',
                '.sql': 'sql',
            }.get(ext, 'unknown')
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
        
        # Validate the sample
        file_name = os.path.basename(file_path)
        return self.validate_sample(content, content_type, f"File: {file_name}")
    
    def validate_directory(self, dir_path, max_files=None, recursive=True):
        """
        Validate token estimation accuracy for files in a directory.
        
        Args:
            dir_path (str): Path to the directory
            max_files (int, optional): Maximum number of files to process
            recursive (bool): Whether to recursively process subdirectories
            
        Returns:
            dict: Aggregated results of the validation
        """
        logger.info(f"Validating files in {dir_path}")
        
        # Find all files in the directory
        all_files = []
        if recursive:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    all_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file)
                if os.path.isfile(file_path):
                    all_files.append(file_path)
        
        # Filter out very large files
        filtered_files = []
        for file_path in all_files:
            try:
                if os.path.getsize(file_path) < 1024 * 1024:  # 1MB limit
                    filtered_files.append(file_path)
            except Exception:
                continue
        
        # Limit the number of files if specified
        if max_files and len(filtered_files) > max_files:
            filtered_files = random.sample(filtered_files, max_files)
        
        # Process each file
        for file_path in filtered_files:
            self.validate_file(file_path)
        
        return self.generate_report()
    
    def validate_with_samples(self):
        """
        Validate token estimation accuracy with a variety of generated samples.
        
        Returns:
            dict: Aggregated results of the validation
        """
        samples = {
            # Various content types to test
            "text": self._generate_text_sample(),
            "python": self._generate_python_sample(),
            "json": self._generate_json_sample(),
            "xml": self._generate_xml_sample(),
            "log": self._generate_log_sample(),
            "markdown": self._generate_markdown_sample(),
            "mixed": self._generate_mixed_sample()
        }
        
        # Validate each sample
        for content_type, content in samples.items():
            self.validate_sample(content, content_type, f"Generated {content_type} sample")
        
        return self.generate_report()
    
    def _generate_text_sample(self):
        """Generate a sample of plain text."""
        return """
        This is a sample of plain text that mimics natural language. It contains
        sentences of varying lengths, some punctuation, and a mix of common and
        uncommon words. The purpose is to test how well the token estimator works
        with standard prose content.
        
        Natural language typically tokenizes differently than code or structured data.
        Tokenizers usually split on spaces and punctuation, but also break uncommon words
        into subword tokens. For example, "tokenization" might become multiple tokens.
        
        Here are some examples of text that might challenge tokenizers:
        - Very long words like antidisestablishmentarianism or pneumonoultramicroscopicsilicovolcanoconiosis
        - Technical terms like hyperparameter, backpropagation, or convolutional
        - Names, especially non-English ones: Dostoyevsky, Schwarzenegger, Nguyễn
        - URLs and emails: https://example.com/test?param=value, user@example.org
        """
    
    def _generate_python_sample(self):
        """Generate a sample of Python code."""
        return """
        import os
        import sys
        import json
        from typing import Dict, List, Optional, Union
        from dataclasses import dataclass
        
        @dataclass
        class TokenStatistics:
            '''Class for tracking token usage statistics.'''
            count: int
            ratio: float
            efficiency: float
            
            def calculate_efficiency(self, baseline: float) -> float:
                """Calculate token efficiency relative to baseline."""
                return self.ratio / baseline if baseline > 0 else 0
        
        class TokenOptimizer:
            def __init__(self, max_tokens: int = 8192, buffer: float = 0.1):
                self.max_tokens = max_tokens
                self.buffer = buffer
                self.available_tokens = max_tokens * (1 - buffer)
                self.statistics = {}
            
            def process_content(self, content: str) -> Dict[str, Union[str, int, float]]:
                """Process content and return token statistics."""
                # Use a simple token estimation for demonstration
                token_count = len(content.split())
                
                # Calculate ratio (tokens per character)
                ratio = token_count / len(content) if content else 0
                
                # Store statistics
                stats = TokenStatistics(
                    count=token_count,
                    ratio=ratio,
                    efficiency=0.0  # Will be calculated later
                )
                
                # Update statistics
                stats.efficiency = stats.calculate_efficiency(0.25)  # Baseline ratio
                self.statistics[hash(content)] = stats
                
                return {
                    "token_count": token_count,
                    "ratio": ratio,
                    "efficiency": stats.efficiency,
                    "under_limit": token_count < self.available_tokens
                }
        
        def main() -> None:
            """Main entry point for the script."""
            optimizer = TokenOptimizer(max_tokens=4096)
            
            # Process a sample file
            sample_path = sys.argv[1] if len(sys.argv) > 1 else "sample.txt"
            if not os.path.exists(sample_path):
                print(f"Error: File {sample_path} not found")
                return
            
            with open(sample_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            result = optimizer.process_content(content)
            
            # Output results
            print(json.dumps(result, indent=2))
            
            # Save to file if requested
            if len(sys.argv) > 2:
                with open(sys.argv[2], 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
        
        if __name__ == "__main__":
            main()
        '''
    
    def _generate_json_sample(self):
        """Generate a sample of JSON data."""
        data = {
            "metadata": {
                "version": "1.0.0",
                "generated": datetime.now().isoformat(),
                "description": "Sample JSON data for token estimation validation"
            },
            "config": {
                "maxTokens": 8192,
                "model": "gpt-4",
                "temperature": 0.7,
                "topP": 0.95,
                "frequencyPenalty": 0.0,
                "presencePenalty": 0.0,
                "stopSequences": ["\n\n", "###", "```"]
            },
            "results": [
                {
                    "id": "result_001",
                    "timestamp": "2025-05-07T10:15:30Z",
                    "score": 0.87,
                    "metrics": {
                        "precision": 0.92,
                        "recall": 0.85,
                        "f1": 0.88,
                        "accuracy": 0.91
                    },
                    "tags": ["validated", "high-confidence", "production-ready"]
                },
                {
                    "id": "result_002",
                    "timestamp": "2025-05-07T11:22:15Z",
                    "score": 0.76,
                    "metrics": {
                        "precision": 0.80,
                        "recall": 0.73,
                        "f1": 0.76,
                        "accuracy": 0.79
                    },
                    "tags": ["validated", "medium-confidence"]
                },
                {
                    "id": "result_003",
                    "timestamp": "2025-05-07T12:45:08Z",
                    "score": 0.93,
                    "metrics": {
                        "precision": 0.95,
                        "recall": 0.92,
                        "f1": 0.93,
                        "accuracy": 0.94
                    },
                    "tags": ["validated", "high-confidence", "production-ready", "featured"]
                }
            ],
            "statistics": {
                "totalRuns": 150,
                "successRate": 0.94,
                "averageScore": 0.85,
                "processingTime": "00:15:22",
                "resourceUsage": {
                    "cpu": "45%",
                    "memory": "1.2GB",
                    "disk": "4.5GB",
                    "network": "250MB"
                }
            }
        }
        return json.dumps(data, indent=2)
    
    def _generate_xml_sample(self):
        """Generate a sample of XML data."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <testResults version="1.2">
          <testSuite name="TokenOptimizer" timestamp="2025-05-07T14:30:15">
            <environment>
              <property name="os" value="Linux"/>
              <property name="python" value="3.9.5"/>
              <property name="platform" value="x86_64"/>
              <property name="memory" value="16GB"/>
            </environment>
            <testCase id="TC001" name="BasicTokenization">
              <status>PASS</status>
              <duration>1.25</duration>
              <assertions>
                <assertion name="tokenCountMatch" result="true"/>
                <assertion name="underLimit" result="true"/>
                <assertion name="efficiency" result="true"/>
              </assertions>
            </testCase>
            <testCase id="TC002" name="LargeFileTokenization">
              <status>PASS</status>
              <duration>3.45</duration>
              <assertions>
                <assertion name="tokenCountMatch" result="true"/>
                <assertion name="underLimit" result="true"/>
                <assertion name="efficiency" result="true"/>
              </assertions>
            </testCase>
            <testCase id="TC003" name="EdgeCaseHandling">
              <status>FAIL</status>
              <duration>1.87</duration>
              <failure>
                <message>Token count exceeded expected limit</message>
                <expected>5000</expected>
                <actual>5243</actual>
                <trace>
                  <![CDATA[
                  Traceback (most recent call last):
                    File "test_tokenizer.py", line 234, in test_edge_case_handling
                      self.assertLessEqual(result["token_count"], 5000)
                  AssertionError: 5243 not less than or equal to 5000
                  ]]>
                </trace>
              </failure>
            </testCase>
            <summary>
              <total>3</total>
              <passed>2</passed>
              <failed>1</failed>
              <skipped>0</skipped>
              <duration>6.57</duration>
            </summary>
          </testSuite>
        </testResults>
        """
    
    def _generate_log_sample(self):
        """Generate a sample of log data."""
        log_lines = []
        for i in range(100):
            timestamp = f"2025-05-07T{10 + (i % 14):02d}:{i % 60:02d}:{i % 60:02d}.{i % 1000:03d}"
            
            # Different log levels
            if i % 20 == 0:
                level = "ERROR"
            elif i % 5 == 0:
                level = "WARNING"
            else:
                level = "INFO"
            
            # Generate log line
            if level == "ERROR":
                log_lines.append(f"{timestamp} {level} [TokenProcessor] Failed to process chunk {i}: Invalid token format")
                log_lines.append(f"Traceback (most recent call last):")
                log_lines.append(f"  File \"processor.py\", line {50 + (i % 30)}, in process_chunk")
                log_lines.append(f"    tokens = tokenize(chunk)")
                log_lines.append(f"  File \"tokenizer.py\", line 102, in tokenize")
                log_lines.append(f"    raise ValueError(\"Invalid token format in chunk {i}\")")
                log_lines.append(f"ValueError: Invalid token format in chunk {i}")
            elif level == "WARNING":
                log_lines.append(f"{timestamp} {level} [TokenBudget] Approaching token limit: {7500 + i} / 8192 ({(7500 + i) / 8192:.1%})")
            else:
                log_lines.append(f"{timestamp} {level} [TokenOptimizer] Processed chunk {i}: {200 + (i % 300)} tokens, efficiency: {0.8 + (i % 20) / 100:.2f}")
        
        return "\n".join(log_lines)
    
    def _generate_markdown_sample(self):
        """Generate a sample of Markdown content."""
        return """# Token Optimization System Documentation

## Overview

The Token Optimization System manages token usage for large language model applications.
It provides efficient processing of input data to maximize the value extracted from
token limits.

### Key Features

- **Stream Processing**: Process files line-by-line for memory efficiency
- **Token Budgeting**: Dynamically allocate tokens across components
- **Priority Filtering**: Preserve critical information when approaching limits
- **Memory Integration**: Store and retrieve processed data efficiently

## Technical Details

The system consists of the following components:

1. **TokenOptimizer**: Core class managing token budget
2. **LogProcessor**: Processes log files with token awareness
3. **DataPreprocessor**: Chunks and preprocesses input data
4. **MCPWrapper**: Integrates with Memory Server and API Monitoring

```python
class TokenOptimizer:
    def __init__(self, max_token_budget=76659):
        self.max_token_budget = max_token_budget
        self.used_tokens = 0
        
    def check_budget(self, required_tokens):
        return (self.used_tokens + required_tokens) <= self.max_token_budget
        
    def allocate_tokens(self, requested_tokens):
        if self.check_budget(requested_tokens):
            self.used_tokens += requested_tokens
            return requested_tokens
        return 0
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `max_token_budget` | Maximum token budget | 76659 |
| `chunk_size` | Size of processing chunks | 1000 |
| `priority_filter` | Minimum priority level | "medium" |
| `compression_ratio` | Target compression ratio | 0.6 |

## Usage Examples

To process a log file with default settings:

```bash
python token_optimization_system.py --log-file test_output.log
```

For more advanced usage:

```bash
python token_optimization_system.py --log-file test_output.log --store-memory --track-usage
```

### Integration with Memory Server

The system stores processed data in the Memory Server for efficient retrieval:

1. Error types are stored as entities
2. Test runs are linked to error types
3. Statistics are attached as observations

![Architecture Diagram](docs/architecture.png)

## Performance Benchmarks

- **Token Reduction**: 55% average reduction
- **Processing Speed**: 15,000 lines/second
- **Memory Usage**: 50MB for 10MB log file
"""
    
    def _generate_mixed_sample(self):
        """Generate a sample of mixed content."""
        parts = [
            "# Token Validation Report\n\nThis report contains mixed content types to test tokenization.\n\n",
            
            "## Log Section\n\n```\n" + "\n".join([
                "2025-05-07T10:15:30 INFO [Validator] Starting validation process",
                "2025-05-07T10:15:31 INFO [Validator] Loading tokenizers",
                "2025-05-07T10:15:32 WARNING [Validator] Tokenizer 'fast-gpt4' not available, falling back",
                "2025-05-07T10:15:35 ERROR [Validator] Failed to load sample file",
                "Traceback (most recent call last):",
                "  File \"validator.py\", line 102, in load_samples",
                "    with open(path, 'r') as f:",
                "FileNotFoundError: [Errno 2] No such file or directory: 'missing_file.txt'"
            ]) + "\n```\n\n",
            
            "## Code Section\n\n```python\n" + """
def estimate_tokens(text):
    """Estimate tokens in text."""
    words = len(text.split())
    chars = len(text)
    
    # Adjust based on content type
    if '{' in text and '}' in text and '"' in text:
        # Likely JSON - higher token ratio
        return int(chars * 0.3)
    else:
        # Normal text - standard ratio
        return int(words * 1.3)
            """ + "\n```\n\n",
            
            "## Data Section\n\n```json\n" + json.dumps({
                "results": {
                    "samples": [
                        {"type": "text", "tokens": 150, "chars": 750},
                        {"type": "code", "tokens": 220, "chars": 900},
                        {"type": "json", "tokens": 180, "chars": 600}
                    ],
                    "summary": {
                        "total_tokens": 550,
                        "average_ratio": 0.24,
                        "efficiency": "high"
                    }
                }
            }, indent=2) + "\n```\n\n",
            
            "## Conclusion\n\nThe token estimation seems to work well for most content types with an average error of 5-10%."
        ]
        
        return "".join(parts)
    
    def generate_report(self):
        """
        Generate a comprehensive report of token estimation accuracy.
        
        Returns:
            dict: Aggregated results and statistics
        """
        if not self.results["samples"]:
            logger.warning("No samples validated, cannot generate report")
            return self.results
        
        # Aggregate statistics by content type
        content_types = {}
        for sample in self.results["samples"]:
            content_type = sample["content_type"]
            if content_type not in content_types:
                content_types[content_type] = {
                    "count": 0,
                    "errors": [],
                    "error_percentages": []
                }
                
            content_types[content_type]["count"] += 1
            content_types[content_type]["errors"].append(sample["primary_error"])
            content_types[content_type]["error_percentages"].append(sample["primary_error_percentage"])
        
        # Calculate statistics for each content type
        for content_type, data in content_types.items():
            errors = data["errors"]
            error_percentages = data["error_percentages"]
            
            data["avg_error"] = statistics.mean(errors) if errors else 0
            data["avg_error_percentage"] = statistics.mean(error_percentages) if error_percentages else 0
            data["max_error"] = max(errors) if errors else 0
            data["min_error"] = min(errors) if errors else 0
            data["std_dev"] = statistics.stdev(errors) if len(errors) > 1 else 0
            
            # Calculate reliability score (higher is better)
            abs_percentage = [abs(p) for p in error_percentages]
            avg_abs_percentage = statistics.mean(abs_percentage) if abs_percentage else 100
            data["reliability_score"] = max(0, 100 - avg_abs_percentage)
        
        # Calculate overall statistics
        all_errors = [s["primary_error"] for s in self.results["samples"]]
        all_error_percentages = [s["primary_error_percentage"] for s in self.results["samples"]]
        
        # Get absolute error percentages for more accurate assessment
        abs_error_percentages = [abs(p) for p in all_error_percentages]
        
        summary = {
            "sample_count": len(self.results["samples"]),
            "content_type_count": len(content_types),
            "avg_error": statistics.mean(all_errors) if all_errors else 0,
            "avg_error_percentage": statistics.mean(all_error_percentages) if all_error_percentages else 0,
            "avg_abs_error_percentage": statistics.mean(abs_error_percentages) if abs_error_percentages else 0,
            "max_error_percentage": max(all_error_percentages) if all_error_percentages else 0,
            "min_error_percentage": min(all_error_percentages) if all_error_percentages else 0,
            "std_dev": statistics.stdev(all_error_percentages) if len(all_error_percentages) > 1 else 0,
            "tokenizers_used": list(self.tokenizers.keys()),
            "primary_tokenizer": list(self.tokenizers.keys())[0] if self.tokenizers else "none",
        }
        
        # Calculate overall reliability score
        summary["overall_reliability_score"] = max(0, 100 - summary["avg_abs_error_percentage"])
        
        # Save detailed categories
        self.results["content_types"] = content_types
        self.results["summary"] = summary
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Save results to file
        result_file = os.path.join(self.output_dir, f"token_validation_{timestamp}.json")
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Saved validation results to {result_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
        
        # Generate markdown report
        self._generate_markdown_report(timestamp)
        
        return self.results
    
    def _generate_markdown_report(self, timestamp):
        """Generate a markdown report from the results."""
        if not self.results["summary"]:
            return
        
        summary = self.results["summary"]
        content_types = self.results["content_types"]
        
        # Create report content
        report = [
            "# Token Estimation Accuracy Validation Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            
            "\n## Summary",
            f"\n- **Samples Analyzed**: {summary['sample_count']}",
            f"- **Content Types**: {summary['content_type_count']}",
            f"- **Primary Tokenizer**: {summary['primary_tokenizer']}",
            f"- **Average Error**: {summary['avg_error']:.2f} tokens",
            f"- **Average Error Percentage**: {summary['avg_error_percentage']:.2f}%",
            f"- **Average Absolute Error**: {summary['avg_abs_error_percentage']:.2f}%",
            f"- **Overall Reliability Score**: {summary['overall_reliability_score']:.2f}/100",
            
            "\n## Content Type Analysis",
            "\n| Content Type | Count | Avg Error | Avg Error % | Reliability Score | Std Dev |",
            "| ------------ | ----- | --------- | ----------- | ----------------- | ------- |"
        ]
        
        # Add rows for each content type
        for content_type, data in content_types.items():
            report.append(
                f"| {content_type} | {data['count']} | "
                f"{data['avg_error']:.2f} | {data['avg_error_percentage']:.2f}% | "
                f"{data['reliability_score']:.2f}/100 | {data['std_dev']:.2f} |"
            )
        
        # Add recommendations section
        report.extend([
            "\n## Recommendations",
            "\nBased on validation results:"
        ])
        
        # Add specific recommendations based on findings
        if summary["avg_abs_error_percentage"] > 20:
            report.append("- **CRITICAL**: Token estimator has significant inaccuracy (>20% error). Calibration required.")
        elif summary["avg_abs_error_percentage"] > 10:
            report.append("- **IMPORTANT**: Token estimator has moderate inaccuracy (>10% error). Consider adjustment.")
        else:
            report.append("- Token estimator accuracy is acceptable (<10% error).")
        
        # Add content-specific recommendations
        for content_type, data in content_types.items():
            if data["avg_abs_error_percentage"] > 20:
                report.append(f"- Token estimation for **{content_type}** content needs significant improvement.")
            elif data["avg_abs_error_percentage"] > 10:
                report.append(f"- Consider tuning token estimation parameters for **{content_type}** content.")
        
        # Add bias assessment
        if summary["avg_error_percentage"] > 5:
            report.append(f"- Estimator tends to **overestimate** tokens by {summary['avg_error_percentage']:.2f}%.")
        elif summary["avg_error_percentage"] < -5:
            report.append(f"- Estimator tends to **underestimate** tokens by {abs(summary['avg_error_percentage']):.2f}%.")
        else:
            report.append("- Estimator shows minimal bias (within ±5%).")
        
        # Save report to file
        report_file = os.path.join(self.output_dir, f"token_validation_{timestamp}.md")
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(report))
            logger.info(f"Saved markdown report to {report_file}")
        except Exception as e:
            logger.error(f"Failed to save markdown report: {e}")


def main():
    """Main entry point for the token accuracy validator."""
    parser = argparse.ArgumentParser(
        description="Validate token estimation accuracy against real tokenizers"
    )
    
    # Input sources
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--file", "-f",
        help="Path to a file to validate"
    )
    source_group.add_argument(
        "--directory", "-d",
        help="Path to a directory to validate (multiple files)"
    )
    source_group.add_argument(
        "--samples", "-s",
        action="store_true",
        help="Use generated samples for validation"
    )
    
    # Options
    parser.add_argument(
        "--output-dir", "-o",
        default="./validation_results",
        help="Directory to store validation results"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Recursively process directory (with --directory)"
    )
    parser.add_argument(
        "--max-files", "-m",
        type=int,
        default=None,
        help="Maximum number of files to process (with --directory)"
    )
    parser.add_argument(
        "--content-type", "-c",
        help="Specify content type (useful for --file)"
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = TokenAccuracyValidator(output_dir=args.output_dir)
    
    # Run validation based on input source
    if args.file:
        validator.validate_file(args.file, content_type=args.content_type)
        validator.generate_report()
    elif args.directory:
        validator.validate_directory(args.directory, max_files=args.max_files, recursive=args.recursive)
    elif args.samples:
        validator.validate_with_samples()
    
    # Log completion
    logger.info("Token estimation validation complete")
    
    # Display summary
    summary = validator.results.get("summary", {})
    if summary:
        print("\nToken Estimation Validation Summary:")
        print(f"- Samples analyzed: {summary.get('sample_count', 0)}")
        print(f"- Average error: {summary.get('avg_error', 0):.2f} tokens")
        print(f"- Average absolute error percentage: {summary.get('avg_abs_error_percentage', 0):.2f}%")
        print(f"- Overall reliability score: {summary.get('overall_reliability_score', 0):.2f}/100")
        print(f"\nDetailed results saved to {args.output_dir}")


if __name__ == "__main__":
    main()