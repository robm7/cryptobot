#!/usr/bin/env python
"""
Token Validation Script for CI/CD

This script validates that modified files stay within token limits
and generates a report on token usage.
"""

import os
import sys
import json
import argparse
import re
import logging
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import token optimizing utilities
from utils.token_optimizer import TokenOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def estimate_tokens(content):
    """
    Estimate the number of tokens in the content using a smarter model
    that accounts for code-specific patterns in tokenization.
    
    Args:
        content: The text content to estimate tokens for
        
    Returns:
        int: Estimated number of tokens with a 20% safety margin
    """
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

def validate_file(file_path, token_budget):
    """
    Validate that a file stays within the token budget.
    
    Args:
        file_path: Path to the file to validate
        token_budget: Maximum token budget
        
    Returns:
        dict: Validation results including token count, status, and file info
    """
    logger.info(f"Validating file: {file_path}")
    
    result = {
        "file_path": file_path,
        "file_size_bytes": 0,
        "token_count": 0,
        "under_budget": True,
        "percentage_of_budget": 0,
        "validation_time": datetime.now().isoformat()
    }
    
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            result["error"] = "File does not exist"
            return result
            
        # Get file stats
        file_stats = os.stat(file_path)
        result["file_size_bytes"] = file_stats.st_size
        
        # Skip binary files and very large files that are unlikely to be processed directly
        if file_path.endswith(('.pyc', '.png', '.jpg', '.jpeg', '.gif', '.db', '.sqlite', '.sqlite3')):
            logger.info(f"Skipping binary file: {file_path}")
            result["skipped"] = "Binary file"
            return result
            
        if file_stats.st_size > 10 * 1024 * 1024:  # 10 MB
            logger.info(f"Skipping large file: {file_path}")
            result["skipped"] = "File too large"
            return result
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Estimate token count
        token_count = estimate_tokens(content)
        result["token_count"] = token_count
        
        # Check if under budget
        result["under_budget"] = token_count <= token_budget
        result["percentage_of_budget"] = (token_count / token_budget) * 100
        
        if not result["under_budget"]:
            logger.warning(f"File exceeds token budget: {file_path} ({token_count} tokens, {result['percentage_of_budget']:.1f}% of budget)")
        else:
            logger.info(f"File is under token budget: {file_path} ({token_count} tokens, {result['percentage_of_budget']:.1f}% of budget)")
            
        return result
        
    except Exception as e:
        logger.error(f"Error validating file {file_path}: {str(e)}")
        result["error"] = str(e)
        return result

def validate_files(files, token_budget, report_path=None):
    """
    Validate multiple files against the token budget.
    
    Args:
        files: List of file paths to validate
        token_budget: Maximum token budget
        report_path: Path to save the JSON report
        
    Returns:
        dict: Validation report including results for all files
    """
    report = {
        "validation_time": datetime.now().isoformat(),
        "token_budget": token_budget,
        "total_files_checked": 0,
        "files_over_budget": 0,
        "files_under_budget": 0,
        "skipped_files": 0,
        "total_token_count": 0,
        "percentage_of_budget_used": 0,
        "files": []
    }
    
    # Split file list if it's a string
    if isinstance(files, str):
        files = files.split()
    
    # Validate each file
    for file_path in files:
        if file_path and os.path.exists(file_path):
            result = validate_file(file_path, token_budget)
            report["files"].append(result)
            
            if "skipped" in result:
                report["skipped_files"] += 1
            elif "error" in result:
                report["skipped_files"] += 1
            else:
                report["total_files_checked"] += 1
                report["total_token_count"] += result["token_count"]
                
                if result["under_budget"]:
                    report["files_under_budget"] += 1
                else:
                    report["files_over_budget"] += 1
    
    # Calculate overall percentage of budget used
    if report["total_files_checked"] > 0:
        report["percentage_of_budget_used"] = (report["total_token_count"] / token_budget) * 100
    
    # Save report if path is provided
    if report_path:
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=4)
            logger.info(f"Report saved to {report_path}")
        except Exception as e:
            logger.error(f"Error saving report to {report_path}: {str(e)}")
    
    # Print summary
    print("\nToken Validation Summary:")
    print(f"Total files checked: {report['total_files_checked']}")
    print(f"Files over budget: {report['files_over_budget']}")
    print(f"Files under budget: {report['files_under_budget']}")
    print(f"Skipped files: {report['skipped_files']}")
    print(f"Total token count: {report['total_token_count']}")
    print(f"Percentage of budget used: {report['percentage_of_budget_used']:.1f}%")
    
    # Determine if validation passed
    validation_passed = report["files_over_budget"] == 0
    
    # Return report and validation status
    return report, validation_passed

def main():
    parser = argparse.ArgumentParser(description="Validate files against token limits")
    parser.add_argument("--files", required=True, help="Space-separated list of files to validate")
    parser.add_argument("--token-budget", type=int, default=76659, help="Maximum token budget")
    parser.add_argument("--report-json", help="Path to save JSON report")
    parser.add_argument("--fail-on-over-budget", action="store_true", help="Exit with non-zero code if any file is over budget")
    args = parser.parse_args()
    
    # Run validation
    report, validation_passed = validate_files(args.files, args.token_budget, args.report_json)
    
    # Exit with appropriate status code
    if args.fail_on_over_budget and not validation_passed:
        print("\nValidation failed: Files exceed token budget")
        sys.exit(1)
    else:
        print("\nValidation complete")

if __name__ == "__main__":
    main()