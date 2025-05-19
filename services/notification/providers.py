import smtplib
from email.mime.text import MIMEText
from typing import Optional
import logging
from twilio.rest import Client
from .service import NotificationChannel, NotificationTemplate
from .providers.slack_provider import SlackProvider

class EmailProvider:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.logger = logging.getLogger(__name__)

    async def send(
        self,
        to_email: str,
        template: NotificationTemplate,
        context: Optional[dict] = None
    ) -> bool:
        try:
            # Render template with context
            subject = template.subject.format(**(context or {}))
            body = template.body.format(**(context or {}))

            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = to_email

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            return False

class SMSProvider:
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
        self.logger = logging.getLogger(__name__)

    async def send(
        self,
        to_phone: str,
        template: NotificationTemplate,
        context: Optional[dict] = None
    ) -> bool:
        try:
            # Render template with context
            body = template.body.format(**(context or {}))
            
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_phone
            )
            
            return message.status in ['queued', 'sent']
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {str(e)}")
            return False

class NotificationProviderFactory:
    @staticmethod
    def create_provider(channel: NotificationChannel, config: dict):
        if channel == NotificationChannel.EMAIL:
            return EmailProvider(
                smtp_host=config['smtp_host'],
                smtp_port=config['smtp_port'],
                username=config['username'],
                password=config['password']
            )
        elif channel == NotificationChannel.SMS:
            return SMSProvider(
                account_sid=config['account_sid'],
                auth_token=config['auth_token'],
                from_number=config['from_number']
            )
        elif channel == NotificationChannel.SLACK:
            return SlackProvider(
                webhook_url=config['webhook_url']
            )
        raise ValueError(f"Unsupported channel: {channel}")