#!/usr/bin/env python
"""
Token Efficiency Badge Generator

This script generates a badge SVG file to display token usage efficiency,
which can be included in GitHub README or other documentation.
"""

import os
import json
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Colors based on efficiency percentage
COLOR_EXCELLENT = "#4c1"  # Green
COLOR_GOOD = "#97CA00"     # Light green
COLOR_MODERATE = "#dfb317"  # Yellow
COLOR_WARNING = "#fe7d37"   # Orange
COLOR_CRITICAL = "#e05d44"  # Red

def get_badge_color(percentage):
    """
    Get the badge color based on the percentage of token budget used.
    
    Args:
        percentage: Percentage of token budget used
        
    Returns:
        str: Hex color code
    """
    if percentage <= 25:
        return COLOR_EXCELLENT
    elif percentage <= 50:
        return COLOR_GOOD
    elif percentage <= 75:
        return COLOR_MODERATE
    elif percentage <= 90:
        return COLOR_WARNING
    else:
        return COLOR_CRITICAL

def generate_badge_svg(label, message, color, output_path):
    """
    Generate an SVG badge image.
    
    Args:
        label: Badge label (left side)
        message: Badge message (right side)
        color: Badge color (hex code)
        output_path: Path to save the SVG file
    """
    logger.info(f"Generating badge: {label} {message} ({color})")
    
    # Calculate text sizes (approximate)
    label_width = len(label) * 6 + 10  # 6px per character + 10px padding
    message_width = len(message) * 6 + 10  # 6px per character + 10px padding
    
    # Generate SVG XML
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{label_width + message_width}" height="20">
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <mask id="a">
        <rect width="{label_width + message_width}" height="20" rx="3" fill="#fff"/>
    </mask>
    <g mask="url(#a)">
        <path fill="#555" d="M0 0h{label_width}v20H0z"/>
        <path fill="{color}" d="M{label_width} 0h{message_width}v20H{label_width}z"/>
        <path fill="url(#b)" d="M0 0h{label_width + message_width}v20H0z"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
        <text x="{label_width/2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
        <text x="{label_width/2}" y="14">{label}</text>
        <text x="{label_width + message_width/2}" y="15" fill="#010101" fill-opacity=".3">{message}</text>
        <text x="{label_width + message_width/2}" y="14">{message}</text>
    </g>
</svg>"""
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg)
        logger.info(f"Badge saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving badge to {output_path}: {str(e)}")

def generate_token_efficiency_badge(report_path, output_path=None):
    """
    Generate a token efficiency badge from a validation report.
    
    Args:
        report_path: Path to the validation report JSON file
        output_path: Path to save the badge SVG (defaults to token_efficiency_badge.svg)
    """
    if output_path is None:
        output_path = "token_efficiency_badge.svg"
    
    logger.info(f"Generating token efficiency badge from {report_path}")
    
    try:
        # Load the report
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        # Extract relevant data
        percentage = report.get("percentage_of_budget_used", 0)
        
        # Format the message
        message = f"{percentage:.1f}% of {report.get('token_budget', 76659)}"
        
        # Get the appropriate color
        color = get_badge_color(percentage)
        
        # Generate the badge
        generate_badge_svg("Token Efficiency", message, color, output_path)
        
    except Exception as e:
        logger.error(f"Error generating token efficiency badge: {str(e)}")
        # Generate a fallback badge
        generate_badge_svg("Token Efficiency", "Unknown", COLOR_WARNING, output_path)

def main():
    parser = argparse.ArgumentParser(description="Generate a token efficiency badge")
    parser.add_argument("--report", required=True, help="Path to the validation report JSON file")
    parser.add_argument("--output", help="Path to save the badge SVG")
    args = parser.parse_args()
    
    # Generate the badge
    generate_token_efficiency_badge(args.report, args.output)

if __name__ == "__main__":
    main()