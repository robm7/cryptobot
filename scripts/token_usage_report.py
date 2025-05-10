#!/usr/bin/env python
"""
Token Usage Report Generator

This script generates a comprehensive report on token usage across the project,
identifying potential issues and suggesting optimization strategies.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def scan_directory_for_files(directory, extension_filter=None):
    """
    Scan a directory recursively for files matching the extension filter.
    
    Args:
        directory: Directory to scan
        extension_filter: List of file extensions to include (e.g., ['.py', '.js'])
        
    Returns:
        list: List of file paths
    """
    file_paths = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            # Skip hidden files and directories
            if file.startswith('.') or '/.git/' in root:
                continue
                
            # Apply extension filter if provided
            if extension_filter:
                if not any(file.endswith(ext) for ext in extension_filter):
                    continue
            
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    
    return file_paths

def analyze_token_usage(report_path, output_dir=None):
    """
    Analyze a token validation report and generate a comprehensive summary.
    
    Args:
        report_path: Path to token validation report JSON
        output_dir: Directory for output files
        
    Returns:
        dict: Analysis results
    """
    logger.info(f"Analyzing token usage from report: {report_path}")
    
    # Set output directory
    if output_dir is None:
        output_dir = "./logs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the report
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
    except Exception as e:
        logger.error(f"Error loading report: {str(e)}")
        return None
    
    # Extract basic metrics
    total_files = report.get("total_files_checked", 0)
    files_over_budget = report.get("files_over_budget", 0)
    total_tokens = report.get("total_token_count", 0)
    token_budget = report.get("token_budget", 76659)
    budget_percentage = report.get("percentage_of_budget_used", 0)
    
    # Extract file details
    files = report.get("files", [])
    
    # Group files by type
    file_types = {}
    for file in files:
        if "skipped" in file or "error" in file:
            continue
            
        file_path = file.get("file_path", "")
        _, extension = os.path.splitext(file_path)
        
        if extension not in file_types:
            file_types[extension] = {
                "count": 0,
                "total_tokens": 0,
                "max_tokens": 0,
                "max_file": "",
                "avg_tokens": 0
            }
        
        tokens = file.get("token_count", 0)
        file_types[extension]["count"] += 1
        file_types[extension]["total_tokens"] += tokens
        
        if tokens > file_types[extension]["max_tokens"]:
            file_types[extension]["max_tokens"] = tokens
            file_types[extension]["max_file"] = file_path
    
    # Calculate averages
    for ext, data in file_types.items():
        if data["count"] > 0:
            data["avg_tokens"] = data["total_tokens"] / data["count"]
    
    # Find the top token-consuming files
    sorted_files = sorted(
        [f for f in files if "token_count" in f],
        key=lambda x: x["token_count"],
        reverse=True
    )
    top_files = sorted_files[:10]
    
    # Identify optimization opportunities
    optimization_suggestions = []
    
    # Check for files approaching token limit
    approaching_limit = [
        f for f in files
        if "token_count" in f and f["token_count"] > token_budget * 0.8
    ]
    if approaching_limit:
        suggestion = {
            "type": "approaching_limit",
            "description": "Files approaching token limit",
            "files": approaching_limit,
            "impact": "high"
        }
        optimization_suggestions.append(suggestion)
    
    # Check for types with high average token count
    high_avg_types = [
        (ext, data) for ext, data in file_types.items()
        if data["avg_tokens"] > 5000 and data["count"] >= 3
    ]
    if high_avg_types:
        suggestion = {
            "type": "high_avg_type",
            "description": "File types with high average token usage",
            "types": high_avg_types,
            "impact": "medium"
        }
        optimization_suggestions.append(suggestion)
    
    # Generate plots
    try:
        # Create a dataframe for easier plotting
        df = pd.DataFrame([
            {
                "file": os.path.basename(f["file_path"]),
                "tokens": f["token_count"],
                "percentage": f["percentage_of_budget"]
            }
            for f in sorted_files[:20]  # Top 20 files
        ])
        
        # Bar chart of top token-consuming files
        plt.figure(figsize=(12, 6))
        plt.bar(df["file"], df["tokens"], color="skyblue")
        plt.title("Top Token-Consuming Files")
        plt.xlabel("File")
        plt.ylabel("Token Count")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        
        chart_path = os.path.join(output_dir, "token_usage_by_file.png")
        plt.savefig(chart_path)
        logger.info(f"Chart saved to {chart_path}")
        
        # Pie chart of token usage by file type
        type_df = pd.DataFrame([
            {"type": ext, "tokens": data["total_tokens"]}
            for ext, data in file_types.items()
        ])
        
        plt.figure(figsize=(10, 10))
        plt.pie(
            type_df["tokens"],
            labels=type_df["type"],
            autopct="%1.1f%%",
            startangle=90,
            shadow=True
        )
        plt.title("Token Usage by File Type")
        plt.axis("equal")  # Equal aspect ratio ensures the pie chart is circular
        
        type_chart_path = os.path.join(output_dir, "token_usage_by_type.png")
        plt.savefig(type_chart_path)
        logger.info(f"Type chart saved to {type_chart_path}")
        
    except Exception as e:
        logger.error(f"Error generating charts: {str(e)}")
    
    # Prepare analysis results
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "total_files": total_files,
        "files_over_budget": files_over_budget,
        "total_tokens": total_tokens,
        "token_budget": token_budget,
        "budget_percentage": budget_percentage,
        "file_types": file_types,
        "top_files": top_files,
        "optimization_suggestions": optimization_suggestions,
        "charts": {
            "token_usage_by_file": os.path.join(output_dir, "token_usage_by_file.png"),
            "token_usage_by_type": os.path.join(output_dir, "token_usage_by_type.png")
        }
    }
    
    # Save analysis to JSON
    analysis_path = os.path.join(output_dir, "token_analysis.json")
    try:
        with open(analysis_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Analysis saved to {analysis_path}")
    except Exception as e:
        logger.error(f"Error saving analysis: {str(e)}")
    
    return analysis

def generate_markdown_report(analysis, output_path=None):
    """
    Generate a Markdown report from token usage analysis.
    
    Args:
        analysis: Analysis results
        output_path: Path to save the Markdown report
        
    Returns:
        str: Markdown report content
    """
    if output_path is None:
        output_path = "token_usage_report.md"
    
    logger.info(f"Generating Markdown report to {output_path}")
    
    # Format timestamp
    timestamp = datetime.fromisoformat(analysis["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
    
    # Start building the report
    report = [
        f"# Token Usage Report",
        f"Generated: {timestamp}",
        "",
        f"## Summary",
        "",
        f"- **Total Files Analyzed**: {analysis['total_files']}",
        f"- **Files Over Budget**: {analysis['files_over_budget']}",
        f"- **Total Token Count**: {analysis['total_tokens']}",
        f"- **Token Budget**: {analysis['token_budget']}",
        f"- **Budget Utilization**: {analysis['budget_percentage']:.1f}%",
        ""
    ]
    
    # Add top files section
    report.extend([
        f"## Top Token-Consuming Files",
        ""
    ])
    
    # Create table of top files
    top_files_table = []
    for i, file in enumerate(analysis["top_files"], 1):
        top_files_table.append([
            i,
            os.path.basename(file["file_path"]),
            file["token_count"],
            f"{file['percentage_of_budget']:.1f}%"
        ])
    
    report.append(tabulate(
        top_files_table,
        headers=["#", "File", "Tokens", "% of Budget"],
        tablefmt="pipe"
    ))
    report.append("")
    
    # Add file types section
    report.extend([
        f"## Token Usage by File Type",
        ""
    ])
    
    # Create table of file types
    types_table = []
    for ext, data in analysis["file_types"].items():
        types_table.append([
            ext if ext else "(no extension)",
            data["count"],
            data["total_tokens"],
            f"{data['avg_tokens']:.1f}",
            os.path.basename(data["max_file"]),
            data["max_tokens"]
        ])
    
    # Sort by total tokens
    types_table = sorted(types_table, key=lambda x: x[2], reverse=True)
    
    report.append(tabulate(
        types_table,
        headers=["Type", "Count", "Total Tokens", "Avg Tokens", "Largest File", "Max Tokens"],
        tablefmt="pipe"
    ))
    report.append("")
    
    # Add optimization suggestions
    if analysis["optimization_suggestions"]:
        report.extend([
            f"## Optimization Suggestions",
            ""
        ])
        
        for suggestion in analysis["optimization_suggestions"]:
            report.extend([
                f"### {suggestion['description']}",
                f"**Impact**: {suggestion['impact'].upper()}",
                ""
            ])
            
            if suggestion["type"] == "approaching_limit":
                approaching_table = []
                for file in suggestion["files"]:
                    approaching_table.append([
                        os.path.basename(file["file_path"]),
                        file["token_count"],
                        f"{file['percentage_of_budget']:.1f}%"
                    ])
                
                report.append(tabulate(
                    approaching_table,
                    headers=["File", "Tokens", "% of Budget"],
                    tablefmt="pipe"
                ))
                report.append("")
                report.append("**Recommendation**: Consider splitting these files into smaller components to reduce token count.")
                report.append("")
                
            elif suggestion["type"] == "high_avg_type":
                type_table = []
                for ext, data in suggestion["types"]:
                    type_table.append([
                        ext,
                        data["count"],
                        f"{data['avg_tokens']:.1f}",
                        os.path.basename(data["max_file"])
                    ])
                
                report.append(tabulate(
                    type_table,
                    headers=["Type", "File Count", "Avg Tokens", "Example File"],
                    tablefmt="pipe"
                ))
                report.append("")
                report.append("**Recommendation**: Review files of these types for potential optimization opportunities.")
                report.append("")
    
    # Add charts section
    report.extend([
        f"## Charts",
        "",
        f"### Token Usage by File",
        f"![Token Usage by File]({os.path.relpath(analysis['charts']['token_usage_by_file'])})",
        "",
        f"### Token Usage by File Type",
        f"![Token Usage by File Type]({os.path.relpath(analysis['charts']['token_usage_by_type'])})",
        ""
    ])
    
    # Save the report
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))
        logger.info(f"Report saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving report: {str(e)}")
    
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Generate a comprehensive token usage report")
    parser.add_argument("--report", help="Path to token validation report JSON")
    parser.add_argument("--output-dir", default="./logs", help="Directory for output files")
    parser.add_argument("--markdown", help="Path to save Markdown report")
    parser.add_argument("--scan-directory", help="Directory to scan for files")
    parser.add_argument("--extensions", help="Comma-separated list of extensions to include (e.g., .py,.js)")
    parser.add_argument("--token-budget", type=int, default=76659, help="Maximum token budget")
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Check if we need to scan a directory
    if args.scan_directory:
        logger.info(f"Scanning directory: {args.scan_directory}")
        
        # Parse extensions if provided
        extensions = None
        if args.extensions:
            extensions = args.extensions.split(",")
            logger.info(f"Filtering by extensions: {extensions}")
        
        # Scan for files
        file_paths = scan_directory_for_files(args.scan_directory, extensions)
        logger.info(f"Found {len(file_paths)} files to analyze")
        
        # Create a temporary file list for validate_tokens.py
        temp_file_list = os.path.join(args.output_dir, "temp_file_list.txt")
        with open(temp_file_list, 'w', encoding='utf-8') as f:
            f.write("\n".join(file_paths))
        
        # Generate a report path
        report_path = os.path.join(args.output_dir, "token_report.json")
        
        # Run token validation
        logger.info("Running token validation...")
        os.system(f"python scripts/validate_tokens.py --files \"$(cat {temp_file_list})\" --token-budget {args.token_budget} --report-json {report_path}")
        
        # Use the generated report
        args.report = report_path
    
    # Check if we have a report to analyze
    if args.report:
        # Analyze token usage
        analysis = analyze_token_usage(args.report, args.output_dir)
        
        if analysis:
            # Generate Markdown report
            markdown_path = args.markdown or os.path.join(args.output_dir, "token_usage_report.md")
            generate_markdown_report(analysis, markdown_path)
            
            # Print summary
            print("\nToken Usage Summary:")
            print(f"Total Files: {analysis['total_files']}")
            print(f"Files Over Budget: {analysis['files_over_budget']}")
            print(f"Total Token Count: {analysis['total_tokens']}")
            print(f"Budget Utilization: {analysis['budget_percentage']:.1f}% of {analysis['token_budget']}")
            
            if analysis["optimization_suggestions"]:
                print("\nOptimization Opportunities:")
                for suggestion in analysis["optimization_suggestions"]:
                    print(f"- {suggestion['description']} (Impact: {suggestion['impact'].upper()})")
            
            print(f"\nFull report saved to {markdown_path}")
        else:
            logger.error("Failed to analyze token usage.")
    else:
        logger.error("No report specified. Use --report or --scan-directory.")

if __name__ == "__main__":
    main()