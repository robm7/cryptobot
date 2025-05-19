"""
Reconciliation Job for Order Execution System

This module implements a scheduled job to run order reconciliation automatically.
It compares local order records with exchange data to ensure consistency and
alerts on any discrepancies.

Usage:
    python -m services.mcp.order_execution.reconciliation_job

Configuration:
    The job can be configured through environment variables or a config file.
    See the README.md for details.
"""

import asyncio
import logging
import os
import sys
import time
import json
from datetime import datetime, timedelta
import schedule
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("reconciliation.log")
    ]
)
logger = logging.getLogger(__name__)

# Import the ReliableOrderExecutor and AlertManager
from reliable_executor import ReliableOrderExecutor
from trade.utils.alerting import AlertManager

class ReconciliationJob:
    """
    Scheduled job to run order reconciliation automatically.
    
    Features:
    - Configurable schedule (daily, hourly, etc.)
    - Automatic retry on failure
    - Detailed reporting
    - Integration with alerting system
    - Multi-channel notifications (email, SMS, Slack)
    """
    
    async def __init__(self, config: Optional[Dict] = None):
        """Initialize the reconciliation job with configuration"""
        try:
            self.config = config or {}
            self.executor = ReliableOrderExecutor()
            self.last_run_time = None
            self.last_run_status = None
            self.last_run_result = None
            
            # Configure the executor
            self.executor_config = self.config.get('executor', {})
            
            # Configure the job schedule
            self.schedule_config = self.config.get('schedule', {})
            self.schedule_time = self.schedule_config.get('time', '00:00')  # Default to midnight
            
            # Validate schedule time format
            try:
                hour, minute = self.schedule_time.split(':')
                if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
                    logger.warning(f"Invalid schedule time format: {self.schedule_time}, defaulting to 00:00")
                    self.schedule_time = '00:00'
            except (ValueError, IndexError):
                logger.warning(f"Invalid schedule time format: {self.schedule_time}, defaulting to 00:00")
                self.schedule_time = '00:00'
                
            # Validate schedule interval
            valid_intervals = ['hourly', 'daily', 'weekly']
            self.schedule_interval = self.schedule_config.get('interval', 'daily')
            if self.schedule_interval not in valid_intervals:
                logger.warning(f"Invalid schedule interval: {self.schedule_interval}, defaulting to daily")
                self.schedule_interval = 'daily'
            
            # Configure reporting
            self.reporting_config = self.config.get('reporting', {})
            self.report_file = self.reporting_config.get('file', 'reconciliation_reports.json')
            self.report_history_days = self.reporting_config.get('history_days', 30)
            
            # Configure alerting
            self.alerting_config = self.config.get('alerting', {})
            self.alert_thresholds = self.alerting_config.get('thresholds', {
                'mismatch_percentage': 0.01,  # Default to 1%
                'missing_orders': 5,          # Default to 5 orders
                'extra_orders': 5             # Default to 5 orders
            })
            self.notification_users = self.alerting_config.get('notification_users', [])
            self.dashboard_url = self.alerting_config.get('dashboard_url', 'http://localhost:3000/reconciliation')
            
            # Initialize alert manager with error handling
            try:
                self.alert_manager = AlertManager(min_level=self.alerting_config.get('min_level', 'warning'))
                logger.info("Alert manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize alert manager: {str(e)}")
            
            logger.info(f"Reconciliation job initialized with schedule: {self.schedule_interval} at {self.schedule_time}")
        except Exception as e:
            logger.critical(f"Failed to initialize reconciliation job: {str(e)}")
            raise

        # Pass alerting config to executor
        executor_config = self.config.get('executor', {})
        executor_config['alerting'] = self.alerting_config
        await self.executor.configure(executor_config)
    async def configure(self):
        """Configure the executor with settings"""
        try:
            asyncio.run(self.executor.configure(self.executor_config))
            logger.info("Executor configured successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to configure executor: {str(e)}")
            return False
    
    async def run_reconciliation(self):
        """Run the reconciliation process"""
        logger.info("Starting reconciliation job")
        self.last_run_time = datetime.now()
        
        # Check if executor is properly initialized
        if not hasattr(self, 'executor') or self.executor is None:
            error_msg = "Executor not properly initialized"
            logger.error(error_msg)
            self.last_run_status = "failed"
            self.last_run_result = {"error": error_msg, "status": "failed"}
            return self.last_run_result
        
        try:
            # Run the reconciliation using the executor
            result = await self.executor.reconcile_orders(self.schedule_interval)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise ValueError(f"Invalid result format: expected dict, got {type(result)}")
            
            # Store the result
            self.last_run_status = "success"
            self.last_run_result = result
            
            # Save the report
            save_success = self._save_report(result)
            if not save_success:
                logger.warning("Failed to save reconciliation report")
            
            logger.info(f"Reconciliation completed: {json.dumps(result, indent=2, default=str)}")
            
            # Check for alerts and send notifications if needed
            if result.get("alert_triggered", False):
                logger.warning("Reconciliation triggered an alert!")
                
                try:
                    # Determine alert severity based on discrepancies
                    severity = self._determine_alert_severity(result)
                    
                    # Send alert through the alert manager
                    if self.alert_manager:
                        self.alert_manager.send_alert(
                            level=severity,
                            title="Order Reconciliation Alert",
                            message=self._format_alert_message(result),
                            data={"alert_type": "reconciliation", **result}
                        )
                        logger.info(f"Sent {severity} alert")
                    else:
                        logger.error("Alert manager not available, cannot send alert")
                except Exception as alert_error:
                    logger.error(f"Failed to send alert: {str(alert_error)}")
                
            return result
            
        except ValueError as ve:
            # Handle data validation errors
            logger.error(f"Validation error during reconciliation: {str(ve)}")
            self.last_run_status = "failed"
            self.last_run_result = {"error": str(ve), "status": "failed", "error_type": "validation"}
            
            self._send_error_alert("Validation Error", str(ve), "warning")
            self._save_report(self.last_run_result)
            
            return self.last_run_result
            
        except asyncio.TimeoutError:
            # Handle timeout errors
            error_msg = "Reconciliation timed out"
            logger.error(error_msg)
            self.last_run_status = "failed"
            self.last_run_result = {"error": error_msg, "status": "failed", "error_type": "timeout"}
            
            self._send_error_alert("Timeout Error", error_msg, "error")
            self._save_report(self.last_run_result)
            
            return self.last_run_result
            
        except ConnectionError as ce:
            # Handle connection errors
            logger.error(f"Connection error during reconciliation: {str(ce)}")
            self.last_run_status = "failed"
            self.last_run_result = {"error": str(ce), "status": "failed", "error_type": "connection"}
            
            self._send_error_alert("Connection Error", str(ce), "error")
            self._save_report(self.last_run_result)
            
            return self.last_run_result
            
        except Exception as e:
            # Handle all other errors
            logger.error(f"Reconciliation failed: {str(e)}")
            self.last_run_status = "failed"
            self.last_run_result = {"error": str(e), "status": "failed", "error_type": "unknown"}
            
            self._send_error_alert("Reconciliation Job Failed", str(e), "error")
            self._save_report(self.last_run_result)
            
            return self.last_run_result
            
    async def _send_error_alert(self, title, error_message, level="error"):
        """Send an error alert with error handling"""
        try:
            if self.alert_manager:
                self.alert_manager.send_alert(
                    level=level,
                    title=title,
                    message=f"The reconciliation job encountered an error: {error_message}",
                    data={"alert_type": "reconciliation", "error": error_message, "status": "failed"}
                )
            else:
                logger.error(f"Alert manager not available, cannot send error alert: {title} - {error_message}")
        except Exception as e:
            logger.error(f"Failed to send error alert: {str(e)}")
    
    def _save_report(self, result: Dict) -> bool:
        """
        Save the reconciliation report to a file
        
        Returns:
            bool: True if the report was saved successfully, False otherwise
        """
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Create reports directory if it doesn't exist
                report_dir = os.path.dirname(self.report_file)
                if report_dir:  # Only create directory if there's a directory path
                    os.makedirs(report_dir, exist_ok=True)
                
                # Load existing reports
                reports = []
                if os.path.exists(self.report_file):
                    try:
                        with open(self.report_file, 'r') as f:
                            reports = json.load(f)
                        
                        # Validate reports format
                        if not isinstance(reports, list):
                            logger.warning(f"Invalid reports format in {self.report_file}, resetting to empty list")
                            reports = []
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in {self.report_file}, resetting to empty list")
                        reports = []
                
                # Add new report
                new_report = {
                    "timestamp": datetime.now().isoformat(),
                    "result": result
                }
                reports.append(new_report)
                
                # Trim old reports
                try:
                    cutoff_date = datetime.now() - timedelta(days=self.report_history_days)
                    reports = [r for r in reports if datetime.fromisoformat(r["timestamp"]) > cutoff_date]
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error trimming old reports: {str(e)}")
                    # Continue with all reports if trimming fails
                
                # Save updated reports
                with open(self.report_file, 'w') as f:
                    json.dump(reports, f, indent=2, default=str)
                    
                logger.info(f"Reconciliation report saved to {self.report_file}")
                return True
                
            except PermissionError:
                logger.warning(f"Permission error saving report (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            except OSError as e:
                logger.error(f"OS error saving report: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
            except Exception as e:
                logger.error(f"Failed to save reconciliation report: {str(e)}")
                break
        
        # If we get here, all attempts failed
        return False
    
    def schedule_job(self):
        """Schedule the reconciliation job based on configuration"""
        if self.schedule_interval == 'hourly':
            schedule.every().hour.at(":00").do(self._run_job_wrapper)
            logger.info("Reconciliation job scheduled to run hourly")
        elif self.schedule_interval == 'daily':
            schedule.every().day.at(self.schedule_time).do(self._run_job_wrapper)
            logger.info(f"Reconciliation job scheduled to run daily at {self.schedule_time}")
        elif self.schedule_interval == 'weekly':
            schedule.every().monday.at(self.schedule_time).do(self._run_job_wrapper)
            logger.info(f"Reconciliation job scheduled to run weekly on Monday at {self.schedule_time}")
        else:
            # Default to daily
            schedule.every().day.at(self.schedule_time).do(self._run_job_wrapper)
            logger.info(f"Reconciliation job scheduled to run daily at {self.schedule_time}")
    
    def _run_job_wrapper(self):
        """Wrapper to run the async job from the scheduler"""
        asyncio.run(self.run_reconciliation())
    
    def get_status(self) -> Dict:
        """Get the current status of the reconciliation job"""
        return {
            "last_run_time": self.last_run_time,
            "last_run_status": self.last_run_status,
            "last_run_result": self.last_run_result,
            "next_run_time": self._get_next_run_time(),
            "schedule": {
                "interval": self.schedule_interval,
                "time": self.schedule_time
            }
        }
    
    def _get_next_run_time(self):
        """Get the next scheduled run time"""
        return schedule.next_run()
        
    def _determine_alert_severity(self, result: Dict) -> str:
        """Determine the severity of the alert based on reconciliation results"""
        try:
            # Extract metrics from the result with safe defaults
            mismatch_percentage = float(result.get("mismatch_percentage", 0))
            
            # Safely get list lengths
            missing_orders = result.get("missing_orders", [])
            extra_orders = result.get("extra_orders", [])
            
            # Ensure we have lists or convert to empty lists
            if not isinstance(missing_orders, list):
                logger.warning(f"missing_orders is not a list: {type(missing_orders)}")
                missing_orders = []
            
            if not isinstance(extra_orders, list):
                logger.warning(f"extra_orders is not a list: {type(extra_orders)}")
                extra_orders = []
            
            missing_count = len(missing_orders)
            extra_count = len(extra_orders)
            
            # Check against thresholds
            if (mismatch_percentage >= self.alert_thresholds["mismatch_percentage"] * 3 or
                missing_count >= self.alert_thresholds["missing_orders"] * 3 or
                extra_count >= self.alert_thresholds["extra_orders"] * 3):
                return "critical"
            elif (mismatch_percentage >= self.alert_thresholds["mismatch_percentage"] * 2 or
                  missing_count >= self.alert_thresholds["missing_orders"] * 2 or
                  extra_count >= self.alert_thresholds["extra_orders"] * 2):
                return "error"
            elif (mismatch_percentage >= self.alert_thresholds["mismatch_percentage"] or
                  missing_count >= self.alert_thresholds["missing_orders"] or
                  extra_count >= self.alert_thresholds["extra_orders"]):
                return "warning"
            else:
                return "info"
        except Exception as e:
            logger.error(f"Error determining alert severity: {str(e)}")
            # Default to error level if we can't determine severity
            return "error"
    
    def _format_alert_message(self, result: Dict) -> str:
        """Format an alert message based on reconciliation results"""
        try:
            # Extract metrics with safe defaults
            mismatch_percentage = float(result.get("mismatch_percentage", 0))
            
            # Safely get list lengths
            missing_orders = result.get("missing_orders", [])
            extra_orders = result.get("extra_orders", [])
            
            # Ensure we have lists or convert to empty lists
            if not isinstance(missing_orders, list):
                missing_orders = []
            if not isinstance(extra_orders, list):
                extra_orders = []
            
            missing_count = len(missing_orders)
            extra_count = len(extra_orders)
            
            total_orders = int(result.get("total_orders", 0))
            
            # Format the message
            message = f"Order Reconciliation Alert: {missing_count} missing orders, {extra_count} extra orders "
            
            # Format percentage with error handling
            try:
                percentage_str = f"{mismatch_percentage:.2%}"
            except (ValueError, TypeError):
                percentage_str = f"{mismatch_percentage}%"
            
            message += f"({percentage_str} mismatch rate out of {total_orders} total orders).\n\n"
            
            # Add details about specific orders if available
            if missing_count > 0:
                message += "\nMissing Orders:\n"
                # Limit to first 5 orders to avoid overly long messages
                for i, order in enumerate(missing_orders[:5]):
                    order_id = order.get("id", "unknown") if isinstance(order, dict) else str(order)
                    message += f"- {order_id}\n"
                if missing_count > 5:
                    message += f"... and {missing_count - 5} more\n"
                
            if extra_count > 0:
                message += "\nExtra Orders:\n"
                # Limit to first 5 orders
                for i, order in enumerate(extra_orders[:5]):
                    order_id = order.get("id", "unknown") if isinstance(order, dict) else str(order)
                    message += f"- {order_id}\n"
                if extra_count > 5:
                    message += f"... and {extra_count - 5} more\n"
            
            message += f"\nView details at: {self.dashboard_url}"
            
            return message
        except Exception as e:
            logger.error(f"Error formatting alert message: {str(e)}")
            # Return a basic message if formatting fails
            return f"Order Reconciliation Alert: Discrepancies detected. View details at: {self.dashboard_url}"
    
    def start(self):
        """Start the reconciliation job scheduler"""
        logger.info("Starting reconciliation job scheduler")
        
        try:
            # Schedule the job
            self.schedule_job()
            
            # Run initial configuration
            config_success = self.configure()
            if not config_success:
                logger.warning("Initial configuration failed, continuing with defaults")
            
            # Run immediately if configured
            if self.config.get('run_on_start', False):
                logger.info("Running initial reconciliation job")
                asyncio.run(self.run_reconciliation())
            
            # Start the scheduler loop with error recovery
            logger.info("Scheduler started, waiting for next run time")
            consecutive_errors = 0
            max_consecutive_errors = 5
            retry_delay = 60  # seconds
            
            while True:
                try:
                    schedule.run_pending()
                    time.sleep(retry_delay)  # Check every minute
                    consecutive_errors = 0  # Reset error counter on success
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Scheduler error (attempt {consecutive_errors}): {str(e)}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.critical(f"Too many consecutive errors ({consecutive_errors}), stopping scheduler")
                        raise
                    
                    # Exponential backoff for retry delay, capped at 5 minutes
                    retry_delay = min(retry_delay * 2, 300)
                    logger.info(f"Retrying scheduler in {retry_delay} seconds")
                    time.sleep(retry_delay)
        except Exception as e:
            logger.critical(f"Fatal error in reconciliation job scheduler: {str(e)}")
            # Re-raise to allow the calling code to handle the error
            raise

async def run_once():
    """Run the reconciliation job once"""
    try:
        # Load configuration
        config_file = os.environ.get('RECONCILIATION_CONFIG_FILE', 'config.json')
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Initialize and run the job
        job = ReconciliationJob(config)
        await job.run_reconciliation()
        
        # Print the status
        status = job.get_status()
        print(json.dumps(status, indent=2, default=str))
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in configuration file: {config_file}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Failed to run reconciliation job: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    """Entry point for running the reconciliation job"""
    try:
        asyncio.run(run_once())
    except Exception as e:
        logger.critical(f"Failed to start reconciliation job: {str(e)}")
        sys.exit(1)