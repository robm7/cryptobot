"""
Reconciliation Alert Templates

This module defines notification templates for reconciliation alerts.
"""

from ..service import NotificationTemplate, NotificationChannel

# Template for reconciliation mismatch alerts
RECONCILIATION_MISMATCH_ALERT = NotificationTemplate(
    name="reconciliation_mismatch_alert",
    subject="Reconciliation Alert: Order Mismatches Detected",
    body="""
Reconciliation has detected order mismatches between local records and exchange data.

Time Period: {time_period}
Total Orders: {total_orders}
Mismatched Orders: {mismatched_orders}
Mismatch Rate: {mismatch_rate}

Missing Orders: {missing_orders}
Extra Orders: {extra_orders}

Please review the reconciliation dashboard for more details:
{dashboard_url}
""",
    channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SMS,
        NotificationChannel.SLACK
    ]
)

# Template for reconciliation failure alerts
RECONCILIATION_FAILURE_ALERT = NotificationTemplate(
    name="reconciliation_failure_alert",
    subject="Reconciliation Alert: Process Failed",
    body="""
The reconciliation process has failed to complete.

Time: {timestamp}
Error: {error_message}

Please check the logs for more details.
""",
    channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SMS,
        NotificationChannel.SLACK
    ]
)

# Template for reconciliation summary
RECONCILIATION_SUMMARY = NotificationTemplate(
    name="reconciliation_summary",
    subject="Reconciliation Summary: {date}",
    body="""
Daily Reconciliation Summary:

Total Reconciliation Runs: {total_runs}
Total Orders Processed: {total_orders}
Total Mismatches: {total_mismatches}
Average Mismatch Rate: {avg_mismatch_rate}
Alerts Triggered: {alerts_triggered}

View the full report on the dashboard:
{dashboard_url}
""",
    channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SLACK
    ]
)

# Template for threshold breach alerts
THRESHOLD_BREACH_ALERT = NotificationTemplate(
    name="threshold_breach_alert",
    subject="CRITICAL: Reconciliation Threshold Breach",
    body="""
ATTENTION: A critical threshold has been breached in the reconciliation process.

Threshold: {threshold_name} = {threshold_value}
Current Value: {current_value}
Time: {timestamp}

This requires immediate attention. Please check the reconciliation dashboard:
{dashboard_url}
""",
    channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SMS,
        NotificationChannel.SLACK
    ]
)

# Dictionary of all templates for easy access
RECONCILIATION_TEMPLATES = {
    "mismatch_alert": RECONCILIATION_MISMATCH_ALERT,
    "failure_alert": RECONCILIATION_FAILURE_ALERT,
    "summary": RECONCILIATION_SUMMARY,
    "threshold_breach": THRESHOLD_BREACH_ALERT
}