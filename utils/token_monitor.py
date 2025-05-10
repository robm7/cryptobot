import os
import json
import time
import logging
import threading
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from mcp_wrapper import MCPWrapper

logger = logging.getLogger(__name__)

class TokenMonitor:
    """
    Token usage monitoring and alerting system that tracks token consumption,
    provides alerts when approaching limits, and suggests optimizations.
    
    This class integrates with the token optimization system to provide:
    - Real-time token usage monitoring
    - Historical token usage tracking
    - Alert generation when approaching token limits
    - Optimization suggestions based on usage patterns
    """
    
    def __init__(self, token_budget=76659, 
                 warning_threshold=0.7, 
                 critical_threshold=0.9,
                 check_interval=300,
                 history_file="./logs/token_history.json"):
        """
        Initialize the token monitor.
        
        Args:
            token_budget (int): Maximum token budget (default: 76659)
            warning_threshold (float): Threshold for warning alerts (0.0-1.0)
            critical_threshold (float): Threshold for critical alerts (0.0-1.0)
            check_interval (int): Time between checks in seconds (default: 300s/5min)
            history_file (str): Path to store token usage history
        """
        self.token_budget = token_budget
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.check_interval = check_interval
        self.history_file = history_file
        
        # Initialize MCP wrapper for token tracking
        self.mcp = MCPWrapper()
        
        # Initialize state
        self.history = self._load_history()
        self.alert_state = {
            "warning_sent": False,
            "critical_sent": False,
            "last_alert_time": 0
        }
        
        # Initialize monitoring thread
        self.monitor_thread = None
        self.should_stop = threading.Event()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load token usage history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading token history: {str(e)}")
                return []
        return []
    
    def _save_history(self):
        """Save token usage history to file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving token history: {str(e)}")
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Monitoring thread is already running")
            return
        
        self.should_stop.clear()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"Token monitoring started. Checking every {self.check_interval} seconds")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if not (self.monitor_thread and self.monitor_thread.is_alive()):
            logger.warning("Monitoring thread is not running")
            return
        
        self.should_stop.set()
        self.monitor_thread.join(timeout=5.0)
        
        if self.monitor_thread.is_alive():
            logger.warning("Monitoring thread did not stop gracefully")
        else:
            logger.info("Token monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop that checks token usage periodically."""
        while not self.should_stop.is_set():
            try:
                self.check_token_usage()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
            
            # Wait for check_interval or until should_stop is set
            self.should_stop.wait(timeout=self.check_interval)
    
    def check_token_usage(self) -> Dict[str, Any]:
        """
        Check current token usage and generate alerts if needed.
        
        Returns:
            Dict[str, Any]: Token usage information
        """
        # Get current token usage
        usage_data = self.mcp.get_token_usage()
        current_usage = usage_data.get("current_usage", 0)
        
        # Calculate percentage of budget used
        usage_percentage = current_usage / self.token_budget if self.token_budget > 0 else 0
        
        # Add timestamp
        timestamp = datetime.now().isoformat()
        
        # Create usage record
        usage_record = {
            "timestamp": timestamp,
            "tokens": current_usage,
            "budget": self.token_budget,
            "percentage": usage_percentage
        }
        
        # Add to history
        self.history.append(usage_record)
        
        # Trim history to last 1000 entries
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        
        # Save updated history
        self._save_history()
        
        # Check for alerts
        self._check_alerts(usage_percentage, current_usage)
        
        # Generate report
        report = {
            "timestamp": timestamp,
            "current_usage": current_usage,
            "budget": self.token_budget,
            "percentage": usage_percentage,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "status": self._get_status(usage_percentage),
            "optimization_suggestions": self._get_optimization_suggestions(usage_percentage)
        }
        
        logger.info(f"Token usage: {current_usage}/{self.token_budget} tokens "
                  f"({usage_percentage:.1%}) - Status: {report['status']}")
        
        return report
    
    def _get_status(self, usage_percentage: float) -> str:
        """Get status based on usage percentage."""
        if usage_percentage >= self.critical_threshold:
            return "CRITICAL"
        elif usage_percentage >= self.warning_threshold:
            return "WARNING"
        else:
            return "OK"
    
    def _check_alerts(self, usage_percentage: float, current_usage: int):
        """Check if alerts should be generated."""
        current_time = time.time()
        alert_cooldown = 3600  # Don't send another alert of the same type for 1 hour
        
        if usage_percentage >= self.critical_threshold:
            # Critical alert
            if (not self.alert_state["critical_sent"] or 
                current_time - self.alert_state["last_alert_time"] > alert_cooldown):
                
                message = (f"CRITICAL: Token usage at {usage_percentage:.1%} "
                          f"({current_usage}/{self.token_budget} tokens), "
                          f"exceeding critical threshold of {self.critical_threshold:.1%}")
                
                self._send_alert("CRITICAL", message, usage_percentage)
                
                self.alert_state["critical_sent"] = True
                self.alert_state["last_alert_time"] = current_time
        
        elif usage_percentage >= self.warning_threshold:
            # Warning alert
            if (not self.alert_state["warning_sent"] or 
                current_time - self.alert_state["last_alert_time"] > alert_cooldown):
                
                message = (f"WARNING: Token usage at {usage_percentage:.1%} "
                          f"({current_usage}/{self.token_budget} tokens), "
                          f"exceeding warning threshold of {self.warning_threshold:.1%}")
                
                self._send_alert("WARNING", message, usage_percentage)
                
                self.alert_state["warning_sent"] = True
                self.alert_state["last_alert_time"] = current_time
        
        else:
            # Reset alert states when back to normal
            self.alert_state["warning_sent"] = False
            self.alert_state["critical_sent"] = False
    
    def _send_alert(self, level: str, message: str, usage_percentage: float):
        """Send an alert."""
        logger.warning(f"TOKEN ALERT {level}: {message}")
        
        # Log to file
        alert_log_path = os.path.join(os.path.dirname(self.history_file), "token_alerts.log")
        timestamp = datetime.now().isoformat()
        
        with open(alert_log_path, 'a') as f:
            f.write(f"{timestamp} - {level}: {message}\n")
        
        # Send email alert if configured
        if os.environ.get("TOKEN_ALERT_EMAIL"):
            self._send_email_alert(level, message, usage_percentage)
        
        # Send system notification if available
        self._send_system_notification(level, message)
    
    def _send_email_alert(self, level: str, message: str, usage_percentage: float):
        """Send an email alert."""
        try:
            recipient = os.environ.get("TOKEN_ALERT_EMAIL")
            if not recipient:
                return
            
            # Get SMTP settings from environment or use defaults
            smtp_server = os.environ.get("SMTP_SERVER", "localhost")
            smtp_port = int(os.environ.get("SMTP_PORT", "25"))
            smtp_user = os.environ.get("SMTP_USER", "")
            smtp_password = os.environ.get("SMTP_PASSWORD", "")
            
            # Create message
            msg = MIMEMultipart()
            msg["Subject"] = f"[{level}] CryptoBot Token Usage Alert"
            msg["From"] = os.environ.get("SMTP_FROM", "cryptobot@example.com")
            msg["To"] = recipient
            
            # Create HTML content with gauge visualization
            percentage = int(usage_percentage * 100)
            color = "red" if level == "CRITICAL" else "orange" if level == "WARNING" else "green"
            
            html = f"""
            <html>
                <body>
                    <h2>CryptoBot Token Usage Alert</h2>
                    <p>{message}</p>
                    <div style="margin: 20px 0; width: 100%; background-color: #f0f0f0; height: 30px; border-radius: 15px; overflow: hidden;">
                        <div style="width: {percentage}%; height: 100%; background-color: {color};"></div>
                    </div>
                    <p>Current Usage: {percentage}%</p>
                    <h3>Optimization Suggestions:</h3>
                    <ul>
            """
            
            # Add optimization suggestions
            for suggestion in self._get_optimization_suggestions(usage_percentage):
                html += f"<li><strong>{suggestion['title']}</strong>: {suggestion['description']}</li>"
            
            html += """
                    </ul>
                    <p>View the token monitoring dashboard for more details.</p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html, "html"))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if smtp_user and smtp_password:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {recipient}")
        
        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
    
    def _send_system_notification(self, level: str, message: str):
        """Send a system notification."""
        try:
            if os.name == "posix":  # Linux/MacOS
                # Try using notify-send (Linux)
                os.system(f'notify-send "Token Alert {level}" "{message}"')
            elif os.name == "nt":  # Windows
                # Try using Windows toast notifications
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(f"Token Alert {level}", 
                                      message, 
                                      duration=10)
                except ImportError:
                    pass
        except Exception as e:
            logger.error(f"Error sending system notification: {str(e)}")
    
    def _get_optimization_suggestions(self, usage_percentage: float) -> List[Dict[str, str]]:
        """Get optimization suggestions based on usage percentage."""
        suggestions = []
        
        # Basic optimizations always included
        suggestions.append({
            "title": "Increase Compression Ratio",
            "description": "Adjust log processing algorithms to achieve higher compression."
        })
        
        suggestions.append({
            "title": "Optimize Memory Integration",
            "description": "Store error type summaries rather than full traces."
        })
        
        # Add progressively more aggressive optimizations as usage increases
        if usage_percentage >= 0.5:
            suggestions.append({
                "title": "Adjust Chunk Size",
                "description": "Increasing chunk size can improve processing efficiency."
            })
        
        if usage_percentage >= self.warning_threshold:
            suggestions.append({
                "title": "Reduce Log Verbosity",
                "description": "Configure logging to capture only essential information."
            })
            
            suggestions.append({
                "title": "Implement Token Budgeting",
                "description": "Assign token budgets to different components to balance usage."
            })
        
        if usage_percentage >= self.critical_threshold:
            suggestions.append({
                "title": "URGENT: Truncate Non-Critical Data",
                "description": "Immediately truncate non-critical data to avoid hitting token limits."
            })
            
            suggestions.append({
                "title": "URGENT: Implement Rate Limiting",
                "description": "Temporarily reduce processing frequency until usage decreases."
            })
        
        return suggestions
    
    def get_token_usage_history(self, days=7) -> Dict[str, Any]:
        """
        Get token usage history for specified number of days.
        
        Args:
            days (int): Number of days of history to return
            
        Returns:
            Dict[str, Any]: Token usage history data
        """
        # Filter history to requested days
        cutoff_time = datetime.now().timestamp() - (days * 86400)
        filtered_history = [
            entry for entry in self.history 
            if datetime.fromisoformat(entry["timestamp"]).timestamp() >= cutoff_time
        ]
        
        # Calculate average usage
        if filtered_history:
            avg_usage = sum(entry["tokens"] for entry in filtered_history) / len(filtered_history)
        else:
            avg_usage = 0
        
        # Get current usage
        current_usage = filtered_history[-1]["tokens"] if filtered_history else 0
        
        # Calculate trend
        if len(filtered_history) >= 2:
            first_usage = filtered_history[0]["tokens"]
            trend_percentage = ((current_usage - first_usage) / first_usage) * 100 if first_usage > 0 else 0
        else:
            trend_percentage = 0
        
        return {
            "history": filtered_history,
            "current_usage": current_usage,
            "average_usage": avg_usage,
            "trend_percentage": trend_percentage,
            "budget": self.token_budget,
            "usage_percentage": current_usage / self.token_budget if self.token_budget > 0 else 0
        }
    
    def get_usage_report(self) -> str:
        """
        Generate a human-readable token usage report.
        
        Returns:
            str: Formatted report text
        """
        # Get current usage data
        usage_data = self.mcp.get_token_usage()
        current_usage = usage_data.get("current_usage", 0)
        usage_percentage = current_usage / self.token_budget if self.token_budget > 0 else 0
        
        # Get history data
        history_data = self.get_token_usage_history(days=7)
        
        # Format the report
        report = [
            "# Token Usage Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Current Status",
            f"Current Usage: {current_usage:,} tokens ({usage_percentage:.1%} of budget)",
            f"Budget: {self.token_budget:,} tokens",
            f"Status: {self._get_status(usage_percentage)}",
            "",
            "## 7-Day Trends",
            f"Average Usage: {history_data['average_usage']:,.0f} tokens",
            f"Trend: {history_data['trend_percentage']:+.1f}% over 7 days",
            "",
            "## Optimization Suggestions"
        ]
        
        # Add optimization suggestions
        for suggestion in self._get_optimization_suggestions(usage_percentage):
            report.append(f"- **{suggestion['title']}**: {suggestion['description']}")
        
        # Add recent history
        report.extend([
            "",
            "## Recent Usage History"
        ])
        
        # Add the 5 most recent entries
        for entry in history_data["history"][-5:]:
            timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
            report.append(f"- {timestamp}: {entry['tokens']:,} tokens ({entry['percentage']:.1%})")
        
        return "\n".join(report)
    
    def reset_token_count(self):
        """
        Reset the token counter.
        This can be used after implementing optimizations or at the start of a new period.
        """
        try:
            # Store the reset event in history
            current_usage = self.mcp.get_token_usage().get("current_usage", 0)
            
            self.history.append({
                "timestamp": datetime.now().isoformat(),
                "tokens": current_usage,
                "budget": self.token_budget,
                "percentage": current_usage / self.token_budget if self.token_budget > 0 else 0,
                "event": "RESET"
            })
            
            # Reset counter in MCP or local storage
            self.mcp.set_token_budget(self.token_budget)  # This resets usage in the wrapper
            
            logger.info(f"Token count reset. Previous usage: {current_usage} tokens")
            
            # Save history
            self._save_history()
            
            # Reset alert state
            self.alert_state = {
                "warning_sent": False,
                "critical_sent": False,
                "last_alert_time": 0
            }
            
            return True
        
        except Exception as e:
            logger.error(f"Error resetting token count: {str(e)}")
            return False


def main():
    """Main entry point for the token monitor command-line tool."""
    parser = argparse.ArgumentParser(description="Token Usage Monitor for CryptoBot")
    
    parser.add_argument(
        "--check", 
        action="store_true", 
        help="Check current token usage"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a token usage report"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset token counter"
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Start the monitoring service"
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=76659,
        help="Maximum token budget"
    )
    parser.add_argument(
        "--warning-threshold",
        type=float,
        default=0.7,
        help="Warning threshold (0.0-1.0)"
    )
    parser.add_argument(
        "--critical-threshold",
        type=float,
        default=0.9,
        help="Critical threshold (0.0-1.0)"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=300,
        help="Check interval in seconds"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("token_monitor.log")
        ]
    )
    
    # Initialize monitor
    monitor = TokenMonitor(
        token_budget=args.token_budget,
        warning_threshold=args.warning_threshold,
        critical_threshold=args.critical_threshold,
        check_interval=args.check_interval
    )
    
    if args.check:
        # Check current usage
        usage = monitor.check_token_usage()
        print(f"\nToken Usage: {usage['current_usage']:,}/{usage['budget']:,} tokens ({usage['percentage']:.1%})")
        print(f"Status: {usage['status']}")
        
        if usage['status'] != "OK":
            print("\nOptimization Suggestions:")
            for suggestion in usage['optimization_suggestions']:
                print(f"- {suggestion['title']}: {suggestion['description']}")
    
    elif args.report:
        # Generate report
        report = monitor.get_usage_report()
        print(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_path = f"./logs/token_report_{timestamp}.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_path}")
    
    elif args.reset:
        # Reset token counter
        success = monitor.reset_token_count()
        if success:
            print("Token count reset successfully")
        else:
            print("Failed to reset token count")
    
    elif args.monitor:
        # Start monitoring service
        print(f"Starting token monitoring service...")
        print(f"Checking every {args.check_interval} seconds")
        print(f"Warning threshold: {args.warning_threshold:.1%}")
        print(f"Critical threshold: {args.critical_threshold:.1%}")
        print("Press Ctrl+C to stop")
        
        # Initial check
        monitor.check_token_usage()
        
        # Start monitoring thread
        monitor.start_monitoring()
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping monitoring service...")
            monitor.stop_monitoring()
            print("Monitoring service stopped")
    
    else:
        # Default: check usage
        usage = monitor.check_token_usage()
        print(f"\nToken Usage: {usage['current_usage']:,}/{usage['budget']:,} tokens ({usage['percentage']:.1%})")
        print(f"Status: {usage['status']}")
        
        # Show help
        parser.print_help()


if __name__ == "__main__":
    main()