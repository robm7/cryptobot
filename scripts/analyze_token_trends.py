#!/usr/bin/env python
"""
Token Usage Trend Analysis Tool

This script analyzes token usage trends over time and generates visualizations
to help identify patterns and predict future token usage.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_token_report(report_path):
    """Load token usage data from report file"""
    try:
        with open(report_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading token report: {str(e)}")
        sys.exit(1)

def extract_history_data(report_data):
    """Extract historical usage data from report"""
    history = report_data.get('usage_history', [])
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(history)
    
    # Convert timestamps to datetime
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    
    return df

def predict_future_usage(df, days_ahead=30):
    """Predict future token usage based on historical trends"""
    if len(df) < 3:
        logger.warning("Not enough data points for reliable prediction")
        return None
    
    # Use recent data for trend calculation (last 14 days or all if less than 14 entries)
    recent_df = df.tail(min(14, len(df)))
    
    # Calculate linear regression
    if 'tokens' in df.columns and 'timestamp' in df.columns:
        x = np.array(range(len(recent_df)))
        y = recent_df['tokens'].values
        
        # Fit line: y = mx + b
        m, b = np.polyfit(x, y, 1)
        
        # Generate future dates
        last_date = recent_df['timestamp'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, days_ahead + 1)]
        
        # Generate predictions
        predictions = [m * (len(recent_df) + i) + b for i in range(1, days_ahead + 1)]
        
        # Create prediction DataFrame
        pred_df = pd.DataFrame({
            'timestamp': future_dates,
            'tokens': predictions
        })
        
        return pred_df
    else:
        logger.warning("Required columns not found in data")
        return None

def plot_usage_trends(historical_df, prediction_df, budget, output_path):
    """Generate visualization of token usage trends with predictions"""
    plt.figure(figsize=(12, 6))
    
    # Plot historical data
    if 'tokens' in historical_df.columns and 'timestamp' in historical_df.columns:
        plt.plot(historical_df['timestamp'], historical_df['tokens'], 
                 marker='o', linestyle='-', color='blue', label='Historical Usage')
    
    # Plot prediction data
    if prediction_df is not None and 'tokens' in prediction_df.columns and 'timestamp' in prediction_df.columns:
        plt.plot(prediction_df['timestamp'], prediction_df['tokens'], 
                 marker='x', linestyle='--', color='orange', label='Predicted Usage')
    
    # Add budget lines
    if budget:
        plt.axhline(y=budget, color='red', linestyle='-', label='Token Budget')
        plt.axhline(y=budget * 0.9, color='orange', linestyle='--', label='90% Threshold')
        plt.axhline(y=budget * 0.7, color='yellow', linestyle='--', label='70% Threshold')
    
    # Format plot
    plt.title('Token Usage Trend Analysis')
    plt.xlabel('Date')
    plt.ylabel('Token Count')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Tight layout to ensure labels fit
    plt.tight_layout()
    
    # Add crossing point annotation if prediction crosses budget
    if prediction_df is not None and budget:
        for i, row in prediction_df.iterrows():
            if row['tokens'] > budget:
                plt.annotate('Predicted Budget Crossing', 
                            xy=(row['timestamp'], budget),
                            xytext=(row['timestamp'], budget - budget * 0.1),
                            arrowprops=dict(facecolor='red', shrink=0.05),
                            fontsize=10,
                            color='red')
                break
    
    # Save figure
    plt.savefig(output_path)
    logger.info(f"Token trend analysis saved to {output_path}")
    
    return output_path

def analyze_usage_patterns(df):
    """Analyze usage patterns to identify potential optimizations"""
    patterns = {
        'trend': 'stable',
        'volatility': 'low',
        'anomalies': [],
        'recommendations': []
    }
    
    if len(df) < 3:
        return patterns
    
    # Analyze trend using simple linear regression
    if 'tokens' in df.columns:
        tokens = df['tokens'].values
        x = np.array(range(len(tokens)))
        
        # Calculate slope
        slope, _ = np.polyfit(x, tokens, 1)
        
        # Determine trend direction and strength
        if slope > 0:
            strength = abs(slope) / np.mean(tokens) * 100
            if strength > 10:
                patterns['trend'] = 'strongly increasing'
                patterns['recommendations'].append('Implement immediate token reduction strategies')
            elif strength > 5:
                patterns['trend'] = 'moderately increasing'
                patterns['recommendations'].append('Monitor closely and prepare optimization plans')
            else:
                patterns['trend'] = 'slightly increasing'
                patterns['recommendations'].append('Review token usage periodically')
        elif slope < 0:
            patterns['trend'] = 'decreasing'
            patterns['recommendations'].append('Current optimizations are effective')
        
        # Analyze volatility
        std_dev = np.std(tokens)
        mean = np.mean(tokens)
        cv = std_dev / mean if mean > 0 else 0
        
        if cv > 0.3:
            patterns['volatility'] = 'high'
            patterns['recommendations'].append('Investigate the cause of usage spikes')
        elif cv > 0.1:
            patterns['volatility'] = 'medium'
        
        # Check for anomalies (simple approach: values outside 2 standard deviations)
        mean = np.mean(tokens)
        std = np.std(tokens)
        threshold = 2 * std
        
        for i, val in enumerate(tokens):
            if abs(val - mean) > threshold:
                if 'timestamp' in df.columns:
                    date = df.iloc[i]['timestamp']
                    patterns['anomalies'].append({
                        'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        'tokens': int(val),
                        'deviation': f"{(val - mean) / std:.1f} sigma"
                    })
                else:
                    patterns['anomalies'].append({
                        'index': i,
                        'tokens': int(val),
                        'deviation': f"{(val - mean) / std:.1f} sigma"
                    })
    
    return patterns

def main():
    """Main entry point for token trend analysis"""
    parser = argparse.ArgumentParser(
        description="Analyze token usage trends and generate visualizations"
    )
    
    parser.add_argument(
        "--report", 
        required=True,
        help="Path to token usage report JSON file"
    )
    
    parser.add_argument(
        "--output", 
        default="token_trends.png",
        help="Path to save the output visualization"
    )
    
    parser.add_argument(
        "--days", 
        type=int,
        default=30,
        help="Number of days to predict into the future"
    )
    
    parser.add_argument(
        "--analysis-output",
        default="token_analysis.json",
        help="Path to save the analysis results in JSON format"
    )
    
    args = parser.parse_args()
    
    # Load report data
    report_data = load_token_report(args.report)
    token_budget = report_data.get('budget', 76659)
    
    # Extract historical data
    historical_df = extract_history_data(report_data)
    
    # Predict future usage
    prediction_df = predict_future_usage(historical_df, args.days)
    
    # Analyze usage patterns
    patterns = analyze_usage_patterns(historical_df)
    
    # Generate visualization
    plot_path = plot_usage_trends(historical_df, prediction_df, token_budget, args.output)
    
    # Calculate crossing day (if applicable)
    crossing_day = None
    days_until_crossing = None
    
    if prediction_df is not None and token_budget:
        for i, row in prediction_df.iterrows():
            if row['tokens'] > token_budget:
                crossing_day = row['timestamp'].strftime('%Y-%m-%d')
                days_until_crossing = (row['timestamp'] - datetime.now()).days
                break
    
    # Create analysis result
    analysis_result = {
        'token_budget': token_budget,
        'current_usage': report_data.get('current_usage', 0),
        'usage_percentage': report_data.get('current_usage', 0) / token_budget * 100 if token_budget else 0,
        'trend': patterns['trend'],
        'volatility': patterns['volatility'],
        'anomalies': patterns['anomalies'],
        'predictions': {
            'budget_crossing_date': crossing_day,
            'days_until_crossing': days_until_crossing,
            'prediction_confidence': 'medium' if len(historical_df) >= 7 else 'low'
        },
        'recommendations': patterns['recommendations']
    }
    
    # Save analysis result
    with open(args.analysis_output, 'w') as f:
        json.dump(analysis_result, f, indent=2)
    
    logger.info(f"Token analysis saved to {args.analysis_output}")
    
    # Print summary to console
    print("\n=== Token Usage Trend Analysis ===")
    print(f"Current Usage: {analysis_result['current_usage']} / {token_budget} tokens ({analysis_result['usage_percentage']:.1f}%)")
    print(f"Trend: {patterns['trend']}")
    print(f"Volatility: {patterns['volatility']}")
    
    if crossing_day:
        print(f"\nWARNING: Projected to exceed token budget on {crossing_day} ({days_until_crossing} days from now)")
    
    if patterns['recommendations']:
        print("\nRecommendations:")
        for rec in patterns['recommendations']:
            print(f"- {rec}")
    
    print(f"\nAnalysis output saved to {args.analysis_output}")
    print(f"Visualization saved to {plot_path}")

if __name__ == "__main__":
    main()