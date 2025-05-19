"""
Email Service for API Key Rotation System

This module provides email notification services for:
- API key expiration notifications
- API key rotation notifications
- Security alerts
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime

from .config import settings # Corrected to use local auth.config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self):
        """Initialize email service"""
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
    
    async def send_email(self, to: str, subject: str, html_content: str, text_content: str = None):
        """
        Send an email
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content of the email (optional)
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_from
            message["To"] = to
            
            # Add plain text version if provided, otherwise create from HTML
            if text_content is None:
                # Simple conversion from HTML to text (not perfect but works for simple emails)
                text_content = html_content.replace("<p>", "").replace("</p>", "\n\n")
                text_content = text_content.replace("<br>", "\n").replace("<br/>", "\n")
                text_content = text_content.replace("<strong>", "").replace("</strong>", "")
                text_content = text_content.replace("<em>", "").replace("</em>", "")
                text_content = text_content.replace("&nbsp;", " ")
            
            # Attach parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            message.attach(part1)
            message.attach(part2)
            
            # Create secure connection and send email
            context = ssl.create_default_context()
            
            # Log email sending (without sensitive content)
            logger.info(f"Sending email to {to} with subject '{subject}'")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.email_from, to, message.as_string())
            
            logger.info(f"Email sent successfully to {to}")
            return True
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    async def send_key_expiration_email(self, email: str, username: str, keys: List[Dict[str, Any]], days_left: int):
        """
        Send API key expiration notification
        
        Args:
            email: User's email address
            username: User's username
            keys: List of expiring keys
            days_left: Days until expiration
        """
        # Create subject based on urgency
        if days_left <= 1:
            subject = f"URGENT: Your API keys expire TODAY"
        elif days_left <= 3:
            subject = f"IMPORTANT: Your API keys expire in {days_left} days"
        else:
            subject = f"Notification: Your API keys expire in {days_left} days"
        
        # Create HTML content
        html_content = f"""
        <html>
        <body>
            <h2>API Key Expiration Notice</h2>
            <p>Hello {username},</p>
            <p>This is a notification that the following API keys will expire in <strong>{days_left} days</strong>:</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse;">
                <tr>
                    <th>Exchange</th>
                    <th>Description</th>
                    <th>Expiration Date</th>
                </tr>
        """
        
        # Add each key to the table
        for key in keys:
            # Format expiration date
            expires_at = datetime.fromisoformat(key["expires_at"])
            expiry_date = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            html_content += f"""
                <tr>
                    <td>{key["exchange"]}</td>
                    <td>{key["description"]}</td>
                    <td>{expiry_date}</td>
                </tr>
            """
        
        # Complete the HTML content
        html_content += f"""
            </table>
            <p>Please log in to your account to rotate these keys before they expire to avoid any service disruptions.</p>
            <p>If you have automatic key rotation enabled, these keys will be rotated automatically {days_left-1} days before expiration.</p>
            <p>Thank you,<br>
            The Security Team</p>
        </body>
        </html>
        """
        
        # Send the email
        await self.send_email(email, subject, html_content)
    
    async def send_key_rotation_email(self, email: str, username: str, old_key: Dict[str, Any], new_key: Dict[str, Any]):
        """
        Send API key rotation notification
        
        Args:
            email: User's email address
            username: User's username
            old_key: Old key data
            new_key: New key data
        """
        # Format dates
        grace_period_ends = datetime.fromisoformat(old_key["grace_period_ends"])
        grace_period_date = grace_period_ends.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        expires_at = datetime.fromisoformat(new_key["expires_at"])
        expiry_date = expires_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Create subject
        subject = f"API Key Rotation: New {new_key['exchange']} API Key"
        
        # Create HTML content
        html_content = f"""
        <html>
        <body>
            <h2>API Key Rotation Complete</h2>
            <p>Hello {username},</p>
            <p>Your API key for <strong>{new_key['exchange']}</strong> has been rotated successfully.</p>
            
            <h3>New API Key</h3>
            <p><strong>Description:</strong> {new_key['description']}</p>
            <p><strong>Key:</strong> {new_key['key']}</p>
            <p><strong>Expires:</strong> {expiry_date}</p>
            
            <h3>Old API Key</h3>
            <p>Your old API key will continue to work until <strong>{grace_period_date}</strong>.</p>
            <p>Please update your applications to use the new API key before this grace period ends.</p>
            
            <p>Thank you,<br>
            The Security Team</p>
        </body>
        </html>
        """
        
        # Send the email
        await self.send_email(email, subject, html_content)
    
    async def send_security_alert(self, email: str, username: str, alert_type: str, details: Dict[str, Any]):
        """
        Send security alert
        
        Args:
            email: User's email address
            username: User's username
            alert_type: Type of security alert
            details: Alert details
        """
        # Create subject based on alert type
        if alert_type == "compromised_key":
            subject = "SECURITY ALERT: API Key Compromised"
        elif alert_type == "unauthorized_access":
            subject = "SECURITY ALERT: Unauthorized Access Detected"
        else:
            subject = f"SECURITY ALERT: {alert_type}"
        
        # Create HTML content
        html_content = f"""
        <html>
        <body>
            <h2 style="color: #cc0000;">SECURITY ALERT</h2>
            <p>Hello {username},</p>
            <p>We have detected a potential security issue with your account:</p>
            
            <div style="background-color: #fff8f8; border-left: 4px solid #cc0000; padding: 10px; margin: 15px 0;">
                <h3>{alert_type}</h3>
        """
        
        # Add details based on alert type
        if alert_type == "compromised_key":
            html_content += f"""
                <p><strong>Exchange:</strong> {details.get('exchange', 'Unknown')}</p>
                <p><strong>Key Description:</strong> {details.get('description', 'Unknown')}</p>
                <p><strong>Detected At:</strong> {details.get('detected_at', 'Unknown')}</p>
                <p><strong>Details:</strong> {details.get('details', 'No additional details')}</p>
                
                <p>This key has been automatically revoked for your security.</p>
            """
        elif alert_type == "unauthorized_access":
            html_content += f"""
                <p><strong>IP Address:</strong> {details.get('ip_address', 'Unknown')}</p>
                <p><strong>Location:</strong> {details.get('location', 'Unknown')}</p>
                <p><strong>Time:</strong> {details.get('time', 'Unknown')}</p>
                <p><strong>Details:</strong> {details.get('details', 'No additional details')}</p>
            """
        else:
            # Generic details
            for key, value in details.items():
                html_content += f"<p><strong>{key}:</strong> {value}</p>"
        
        # Complete the HTML content
        html_content += f"""
            </div>
            
            <p>If you did not initiate this action, please contact our security team immediately.</p>
            
            <p>Security Team<br>
            <a href="mailto:security@example.com">security@example.com</a></p>
        </body>
        </html>
        """
        
        # Send the email with high priority
        await self.send_email(email, subject, html_content)