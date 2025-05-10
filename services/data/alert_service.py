import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import AuditLog
from database.db import get_db
import smtplib
from email.mime.text import MIMEText
from config import settings

class AlertService:
    """Service for detecting and alerting on suspicious activities"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session if db_session else next(get_db())
        self.logger = logging.getLogger('alerts')
        self.rules = self._load_alert_rules()
        
    def _load_alert_rules(self) -> List[Dict[str, Any]]:
        """Load alert rules from configuration"""
        return [
            {
                'name': 'multiple_failed_logins',
                'description': 'Multiple failed login attempts from same IP',
                'query': {
                    'event_type': 'login_failure',
                    'time_window': timedelta(minutes=5),
                    'threshold': 3
                },
                'severity': 'high'
            },
            {
                'name': 'sensitive_config_change',
                'description': 'Changes to sensitive configuration',
                'query': {
                    'event_type': 'config_change',
                    'resource_type': ['api_keys', 'security_settings'],
                    'threshold': 1
                },
                'severity': 'critical'
            },
            {
                'name': 'unusual_time_access',
                'description': 'Activity during unusual hours',
                'query': {
                    'time_range': (datetime.strptime('00:00', '%H:%M').time(),
                                 datetime.strptime('05:00', '%H:%M').time()),
                    'threshold': 1
                },
                'severity': 'medium'
            }
        ]
        
    def check_suspicious_activities(self) -> List[Dict[str, Any]]:
        """Check for suspicious activities based on rules"""
        alerts = []
        for rule in self.rules:
            if rule['name'] == 'multiple_failed_logins':
                alerts.extend(self._check_failed_logins(rule))
            elif rule['name'] == 'sensitive_config_change':
                alerts.extend(self._check_sensitive_changes(rule))
            elif rule['name'] == 'unusual_time_access':
                alerts.extend(self._check_unusual_time(rule))
                
        return alerts
        
    def _check_failed_logins(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for multiple failed logins from same IP"""
        time_window = datetime.utcnow() - rule['query']['time_window']
        threshold = rule['query']['threshold']
        
        # Get IPs with multiple failed logins
        query = self.db.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('count'))
        query = query.filter(AuditLog.event_type == 'login_failure')
        query = query.filter(AuditLog.timestamp >= time_window)
        query = query.group_by(AuditLog.ip_address)
        query = query.having(func.count(AuditLog.id) >= threshold)
        results = query.all()
            
        alerts = []
        for ip, count in results:
            alerts.append({
                'rule': rule['name'],
                'severity': rule['severity'],
                'message': f"Multiple failed logins ({count}) from IP {ip}",
                'details': {
                    'ip_address': ip,
                    'count': count,
                    'time_window': str(rule['query']['time_window'])
                }
            })
            
        return alerts
        
    def _check_sensitive_changes(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for changes to sensitive configurations"""
        resource_types = rule['query']['resource_type']
        threshold = rule['query']['threshold']
        
        query = self.db.query(AuditLog)
        query = query.filter(AuditLog.event_type == 'config_change')
        query = query.filter(AuditLog.resource_type.in_(resource_types))
        query = query.filter(AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=1))
        results = query.all()
            
        alerts = []
        if len(results) >= threshold:
            for log in results:
                alerts.append({
                    'rule': rule['name'],
                    'severity': rule['severity'],
                    'message': f"Sensitive config change: {log.resource_type}",
                    'details': log.to_dict()
                })
                
        return alerts
        
    def _check_unusual_time(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for activity during unusual hours"""
        start_time, end_time = rule['query']['time_range']
        threshold = rule['query']['threshold']
        
        query = self.db.query(AuditLog)
        query = query.filter(func.time(AuditLog.timestamp).between(start_time, end_time))
        query = query.filter(AuditLog.timestamp >= datetime.utcnow() - timedelta(days=1))
        results = query.all()
            
        alerts = []
        if len(results) >= threshold:
            for log in results:
                alerts.append({
                    'rule': rule['name'],
                    'severity': rule['severity'],
                    'message': f"Unusual time activity: {log.event_type} at {log.timestamp.time()}",
                    'details': log.to_dict()
                })
                
        return alerts
        
    def send_alert_notification(self, alert: Dict[str, Any]):
        """Send alert notification via email"""
        if not settings.ALERT_EMAIL_ENABLED:
            return
            
        msg = MIMEText(
            f"Security Alert - {alert['severity'].upper()}\n\n"
            f"Rule: {alert['rule']}\n"
            f"Message: {alert['message']}\n\n"
            f"Details:\n{alert['details']}"
        )
        
        msg['Subject'] = f"[CRYPTOBOT ALERT] {alert['severity'].upper()}: {alert['rule']}"
        msg['From'] = settings.ALERT_EMAIL_FROM
        msg['To'] = settings.ALERT_EMAIL_TO
        
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            self.logger.info(f"Alert notification sent: {alert['rule']}")
        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {str(e)}")
            
    def run_alerts(self):
        """Run all alert checks and send notifications"""
        alerts = self.check_suspicious_activities()
        for alert in alerts:
            self.send_alert_notification(alert)
            self.logger.warning(f"Security alert triggered: {alert['message']}")
            
        return len(alerts)

