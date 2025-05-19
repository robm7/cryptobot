#!/usr/bin/env python
"""
Example script demonstrating how to use the ReconciliationJob

This script shows how to:
1. Initialize the ReconciliationJob
2. Configure it with custom settings
3. Run a one-time reconciliation
4. Schedule recurring reconciliation jobs
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import directly using relative path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # order_execution directory
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from reconciliation_job import ReconciliationJob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("reconciliation_example.log")
    ]
)
logger = logging.getLogger(__name__)

async def run_one_time_reconciliation():
    """Run a one-time reconciliation job"""
    logger.info("Running one-time reconciliation")
    
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0,
                "initial_delay": 1.0,
                "max_delay": 30.0
            },
            "circuit_breaker": {
                "error_threshold": 30,
                "warning_threshold": 10,
                "window_size_minutes": 5,
                "cool_down_seconds": 60
            }
        },
        "reporting": {
            "file": "example_reconciliation_reports.json",
            "history_days": 7
        }
    }
    
    # Create and configure the job
    job = ReconciliationJob(config)
    await job.configure()
    
    # Run the reconciliation
    result = await job.run_reconciliation()
    
    # Print the result
    logger.info("Reconciliation result:")
    logger.info(json.dumps(result, indent=2, default=str))
    
    # Get and print job status
    status = job.get_status()
    logger.info("Job status:")
    logger.info(json.dumps(status, indent=2, default=str))
    
    return result

async def simulate_scheduled_reconciliation(run_count=3, interval_seconds=5):
    """Simulate a scheduled reconciliation job running multiple times"""
    logger.info(f"Simulating scheduled reconciliation with {run_count} runs")
    
    # Create configuration for simulation
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0,
                "initial_delay": 1.0,
                "max_delay": 30.0
            }
        },
        "schedule": {
            "interval": "hourly",  # This won't actually be used in the simulation
            "time": "00:00"
        },
        "reporting": {
            "file": "example_scheduled_reports.json",
            "history_days": 7
        },
        "run_on_start": True
    }
    
    # Create and configure the job
    job = ReconciliationJob(config)
    await job.configure()
    
    # Run multiple times to simulate scheduled execution
    for i in range(run_count):
        logger.info(f"Simulation run {i+1}/{run_count}")
        
        # Run the reconciliation
        result = await job.run_reconciliation()
        
        # Print the result
        logger.info(f"Run {i+1} result:")
        logger.info(json.dumps(result, indent=2, default=str))
        
        # Get and print job status
        status = job.get_status()
        logger.info(f"Run {i+1} status:")
        logger.info(json.dumps(status, indent=2, default=str))
        
        # Wait for the next interval (except for the last run)
        if i < run_count - 1:
            logger.info(f"Waiting {interval_seconds} seconds for next run...")
            await asyncio.sleep(interval_seconds)
    
    logger.info("Simulation completed")

async def main():
    """Main function demonstrating ReconciliationJob usage"""
    logger.info("Starting ReconciliationJob example")
    
    try:
        # Run a one-time reconciliation
        logger.info("=== ONE-TIME RECONCILIATION ===")
        await run_one_time_reconciliation()
        
        # Simulate scheduled reconciliation
        logger.info("\n=== SIMULATED SCHEDULED RECONCILIATION ===")
        await simulate_scheduled_reconciliation(run_count=2, interval_seconds=3)
        
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())