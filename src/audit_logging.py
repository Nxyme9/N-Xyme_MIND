"""
Audit Logging Service
Agent 7 - Security Hardening & Compliance
"""

import time
import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_PASSWORD_CHANGE = "user.password_change"
    USER_PROFILE_UPDATE = "user.profile_update"
    
    PROJECT_CREATE = "project.create"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"
    PROJECT_SHARE = "project.share"
    
    FILE_UPLOAD = "file.upload"
    FILE_DOWNLOAD = "file.download"
    FILE_DELETE = "file.delete"
    
    PLUGIN_INSTALL = "plugin.install"
    PLUGIN_UNINSTALL = "plugin.uninstall"
    PLUGIN_CONFIG_CHANGE = "plugin.config_change"
    
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_REFUNDED = "payment.refunded"
    
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"
    
    SETTINGS_CHANGE = "settings.change"
    ADMIN_ACTION = "admin.action"
    
    SECURITY_VIOLATION = "security.violation"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


class AuditSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    id: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """Audit logging for sensitive actions"""
    
    def __init__(self):
        self.events: List[AuditEvent] = []
        self._event_id = 0
    
    def log(
        self,
        event_type: AuditEventType,
        action: str,
        result: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log an audit event"""
        
        self._event_id += 1
        
        event = AuditEvent(
            id=f"audit_{self._event_id}",
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            result=result,
            details=details or {},
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        self.events.append(event)
        
        log_message = (
            f"AUDIT: {event_type.value} | User: {user_id or 'anonymous'} | "
            f"Action: {action} | Result: {result}"
        )
        
        if severity == AuditSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == AuditSeverity.ERROR:
            logger.error(log_message)
        elif severity == AuditSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        return event
    
    def log_login(self, user_id: str, ip_address: str, success: bool, **kwargs):
        """Log user login attempt"""
        return self.log(
            event_type=AuditEventType.USER_LOGIN,
            action="login",
            result="success" if success else "failed",
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id if success else None,
            ip_address=ip_address,
            details={"method": kwargs.get("method", "password")}
        )
    
    def log_project_action(
        self,
        action: str,
        user_id: str,
        project_id: str,
        result: str,
        **kwargs
    ):
        """Log project-related action"""
        
        action_map = {
            "create": AuditEventType.PROJECT_CREATE,
            "update": AuditEventType.PROJECT_UPDATE,
            "delete": AuditEventType.PROJECT_DELETE,
            "share": AuditEventType.PROJECT_SHARE,
        }
        
        return self.log(
            event_type=action_map.get(action, AuditEventType.PROJECT_UPDATE),
            action=action,
            result=result,
            user_id=user_id,
            resource_type="project",
            resource_id=project_id,
            details=kwargs
        )
    
    def log_payment(self, action: str, user_id: str, amount: float, result: str, **kwargs):
        """Log payment-related action"""
        
        action_map = {
            "initiate": AuditEventType.PAYMENT_INITIATED,
            "complete": AuditEventType.PAYMENT_COMPLETED,
            "refund": AuditEventType.PAYMENT_REFUNDED,
        }
        
        return self.log(
            event_type=action_map.get(action, AuditEventType.PAYMENT_INITIATED),
            action=action,
            result=result,
            user_id=user_id,
            details={"amount": amount, **kwargs}
        )
    
    def log_security_violation(
        self,
        violation_type: str,
        ip_address: str,
        details: Dict[str, Any],
        severity: AuditSeverity = AuditSeverity.WARNING
    ):
        """Log security violation"""
        
        return self.log(
            event_type=AuditEventType.SECURITY_VIOLATION,
            action=violation_type,
            result="blocked",
            severity=severity,
            ip_address=ip_address,
            details=details
        )
    
    def query(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        severity: Optional[AuditSeverity] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Query audit events"""
        
        results = self.events
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        
        if severity:
            results = [e for e in results if e.severity == severity]
        
        return results[-limit:]
    
    def get_user_activity(self, user_id: str, limit: int = 50) -> List[AuditEvent]:
        """Get recent activity for a user"""
        return self.query(user_id=user_id, limit=limit)
    
    def get_security_events(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Get security-related events"""
        
        security_types = [
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.RATE_LIMIT_EXCEEDED,
        ]
        
        results = self.events
        
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]
        
        results = [e for e in results if e.event_type in security_types]
        
        return results[-limit:]
    
    def export_events(
        self,
        start_time: float,
        end_time: float,
        format: str = "json"
    ) -> str:
        """Export audit events for compliance"""
        
        events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time
        ]
        
        if format == "json":
            return json.dumps([asdict(e) for e in events], indent=2)
        
        return str(events)
    
    def get_event_counts(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, int]:
        """Get counts of events by type"""
        
        events = self.events
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        counts = {}
        for event in events:
            key = event.event_type.value
            counts[key] = counts.get(key, 0) + 1
        
        return counts


_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    return _global_audit_logger
