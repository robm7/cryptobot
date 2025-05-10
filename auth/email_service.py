import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import BackgroundTasks
from typing import Optional
from config import settings

# Configure logging
logger = logging.getLogger("email-service")

async def send_email(
    recipient_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Send an email using SMTP
    
    Args:
        recipient_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content of the email (optional)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    # If SMTP is not configured, just log the email
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning(
            f"SMTP not configured. Email would have been sent to: {recipient_email}\n"
            f"Subject: {subject}\n"
            f"Content: {text_content or html_content}"
        )
        return True
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = settings.EMAIL_FROM
        message["To"] = recipient_email
        message["Subject"] = subject
        
        # Add text content
        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        
        # Add HTML content
        message.attach(MIMEText(html_content, "html"))
        
        # Send email
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            # Secure connection
            server.starttls()
            
            # Login
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            
            # Send email
            server.sendmail(
                settings.EMAIL_FROM,
                recipient_email,
                message.as_string()
            )
        
        logger.info(f"Email sent to {recipient_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")
        return False

async def send_password_reset_email(
    email: str,
    reset_token: str,
    app_url: str = "http://localhost:3000"
) -> bool:
    """
    Send a password reset email
    
    Args:
        email: Recipient email address
        reset_token: Password reset token
        app_url: Base URL of the frontend application
        
    Returns:
        True if email sent successfully, False otherwise
    """
    # Create reset URL
    reset_url = f"{app_url}/reset-password?token={reset_token}"
    
    # Create HTML content
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #f7f7f7; padding: 20px; border-radius: 5px; }}
            .header {{ background-color: #4a56e2; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ padding: 20px; background-color: white; border-radius: 0 0 5px 5px; }}
            .button {{ display: inline-block; background-color: #4a56e2; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-top: 20px; }}
            .footer {{ margin-top: 20px; font-size: 12px; color: #999; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>We received a request to reset your password for CryptoBot. Click the button below to reset your password:</p>
                <p><a href="{reset_url}" class="button">Reset Password</a></p>
                <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                <p>This link will expire in 30 minutes.</p>
                <p>Thank you,<br>The CryptoBot Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 CryptoBot. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create plain text content
    text_content = f"""
    Password Reset Request
    
    Hello,
    
    We received a request to reset your password for CryptoBot.
    
    Please visit the following link to reset your password:
    {reset_url}
    
    If you didn't request a password reset, please ignore this email or contact support if you have concerns.
    
    This link will expire in 30 minutes.
    
    Thank you,
    The CryptoBot Team
    """
    
    # Send email
    return await send_email(
        recipient_email=email,
        subject="CryptoBot Password Reset",
        html_content=html_content,
        text_content=text_content
    )

def send_password_reset_email_background(
    background_tasks: BackgroundTasks,
    email: str,
    reset_token: str,
    app_url: str = "http://localhost:3000"
):
    """
    Queue password reset email sending in background task
    
    Args:
        background_tasks: FastAPI BackgroundTasks
        email: Recipient email address
        reset_token: Password reset token
        app_url: Base URL of the frontend application
    """
    background_tasks.add_task(
        send_password_reset_email,
        email=email,
        reset_token=reset_token,
        app_url=app_url
    )