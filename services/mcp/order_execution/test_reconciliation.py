"""
Test script for demonstrating the reconciliation job functionality.
This is a simplified version that doesn't rely on complex imports.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockReliableOrderExecutor:
    """Mock implementation of ReliableOrderExecutor for testing"""
    
    def __init__(self):
        self.orders = {}
        logger.info("MockReliableOrderExecutor initialized")
    
    async def configure(self, config):
        logger.info(f"Configured with: {json.dumps(config, indent=2)}")
        return True
    
    async def reconcile_orders(self, time_period="daily"):
        """Simulate order reconciliation"""
        logger.info(f"Running {time_period} reconciliation")
        
        # Simulate reconciliation process
        await asyncio.sleep(0.5)  # Simulate processing time
        
        # Generate random reconciliation results
        mismatch = random.uniform(0, 0.02)  # 0-2% mismatch
        alert = mismatch > 0.01  # Alert if > 1% mismatch
        
        result = {
            "total_orders": random.randint(80, 120),
            "matched_orders": 0,
            "mismatched_orders": 0,
            "missing_orders": 0,
            "extra_orders": 0,
            "mismatch_percentage": mismatch,
            "alert_triggered": alert,
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate matched and mismatched orders
        result["mismatched_orders"] = int(result["total_orders"] * mismatch)
        result["matched_orders"] = result["total_orders"] - result["mismatched_orders"]
        
        logger.info(f"Reconciliation completed with {mismatch:.2%} mismatch")
        if alert:
            logger.warning("Alert triggered due to high mismatch percentage!")
        
        return result

class ReconciliationJob:
    """Simplified reconciliation job for testing"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.executor = MockReliableOrderExecutor()
        self.last_run_time = None
        self.last_run_status = None
        self.last_run_result = None
        self.reports = []
        
        # Configure schedule
        self.schedule_interval = self.config.get('schedule', {}).get('interval', 'daily')
        self.schedule_time = self.config.get('schedule', {}).get('time', '00:00')
        
        logger.info(f"ReconciliationJob initialized with schedule: {self.schedule_interval} at {self.schedule_time}")
    
    async def configure(self):
        """Configure the executor"""
        executor_config = self.config.get('executor', {})
        return await self.executor.configure(executor_config)
    
    async def run_reconciliation(self):
        """Run the reconciliation process"""
        logger.info("Starting reconciliation job")
        self.last_run_time = datetime.now()
        
        try:
            # Run reconciliation
            result = await self.executor.reconcile_orders(self.schedule_interval)
            
            # Store result
            self.last_run_status = "success"
            self.last_run_result = result
            self.reports.append({
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
            
            # Trim reports to keep only last 30 days
            cutoff = datetime.now() - timedelta(days=30)
            self.reports = [r for r in self.reports 
                           if datetime.fromisoformat(r["timestamp"]) > cutoff]
            
            logger.info(f"Reconciliation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Reconciliation failed: {str(e)}")
            self.last_run_status = "failed"
            self.last_run_result = {"error": str(e)}
            return {"error": str(e), "status": "failed"}
    
    def get_status(self):
        """Get current status of the reconciliation job"""
        return {
            "last_run_time": self.last_run_time,
            "last_run_status": self.last_run_status,
            "schedule": {
                "interval": self.schedule_interval,
                "time": self.schedule_time
            },
            "report_count": len(self.reports)
        }

async def simulate_scheduled_runs(job, count=3, interval_seconds=2):
    """Simulate multiple scheduled runs"""
    logger.info(f"Simulating {count} scheduled runs")
    
    for i in range(count):
        logger.info(f"Run {i+1}/{count}")
        result = await job.run_reconciliation()
        logger.info(f"Result: {json.dumps(result, indent=2, default=str)}")
        
        if i < count - 1:
            logger.info(f"Waiting {interval_seconds} seconds for next run...")
            await asyncio.sleep(interval_seconds)
    
    logger.info("All scheduled runs completed")
    return job.reports

async def main():
    """Main test function"""
    logger.info("Starting reconciliation job test")
    
    # Create configuration
    config = {
        "executor": {
            "retry": {
                "max_retries": 3,
                "backoff_base": 2.0
            },
            "circuit_breaker": {
                "error_threshold": 30,
                "warning_threshold": 10
            }
        },
        "schedule": {
            "interval": "daily",
            "time": "00:00"
        }
    }
    
    # Create and configure job
    job = ReconciliationJob(config)
    await job.configure()
    
    # Run once
    logger.info("=== SINGLE RECONCILIATION RUN ===")
    result = await job.run_reconciliation()
    logger.info(f"Single run result: {json.dumps(result, indent=2, default=str)}")
    
    # Get status
    status = job.get_status()
    logger.info(f"Job status: {json.dumps(status, indent=2, default=str)}")
    
    # Simulate scheduled runs
    logger.info("\n=== SIMULATED SCHEDULED RUNS ===")
    reports = await simulate_scheduled_runs(job, count=3, interval_seconds=2)
    
    # Print summary
    logger.info("\n=== RECONCILIATION SUMMARY ===")
    logger.info(f"Total runs: {len(reports)}")
    
    # Calculate average mismatch
    mismatches = [r["result"]["mismatch_percentage"] for r in reports]
    avg_mismatch = sum(mismatches) / len(mismatches)
    logger.info(f"Average mismatch: {avg_mismatch:.2%}")
    
    # Count alerts
    alerts = sum(1 for r in reports if r["result"].get("alert_triggered", False))
    logger.info(f"Alerts triggered: {alerts}/{len(reports)}")
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    asyncio.run(main())