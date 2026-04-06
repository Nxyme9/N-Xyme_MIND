"""
Audit Logging Service — Track all system events.

Logs events to Graphiti and local file for compliance and debugging.

Usage:
    logger = AuditLogger()
    logger.log('service_start', 'Ollama started', severity='info')
    logger.log('error', 'Connection failed', severity='error')
    events = logger.query('error')
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """Audit logging for Catalyst system."""

    def __init__(
        self,
        graphiti_url: str = "http://localhost:8001",
        log_file: Optional[str] = None,
    ):
        self.graphiti_url = graphiti_url
        self.log_file = Path(log_file) if log_file else Path("data/audit.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self._http_client = None
        self._local_events: List[Dict[str, Any]] = []
        logger.info(f"AuditLogger: Initialized (log: {self.log_file})")

    def _get_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=10.0)
        return self._http_client

    def log(
        self,
        event_type: str,
        description: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log an audit event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "description": description,
            "severity": severity,
            "metadata": metadata or {},
        }

        # Store locally
        self._local_events.append(event)
        self._write_to_file(event)

        # Store in Graphiti (async-friendly)
        try:
            client = self._get_client()
            resp = client.post(
                f"{self.graphiti_url}/json-rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "graphiti_add_episode",
                    "params": {
                        "name": f"audit_{event_type}_{int(time.time())}",
                        "text": f"[{severity.upper()}] {event_type}: {description}",
                        "source": "audit_log",
                        "source_description": "System audit event",
                    },
                    "id": f"audit_{event_type[:8]}",
                },
            )
            data = resp.json()
            success = data.get("result", {}).get("success", False)
            if not success:
                logger.warning(f"AuditLogger: Failed to store in Graphiti")
        except Exception as e:
            logger.warning(f"AuditLogger: Graphiti store failed: {e}")

        logger.info(f"AuditLogger: [{severity}] {event_type}: {description}")
        return True

    def _write_to_file(self, event: Dict[str, Any]):
        """Write event to local log file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"AuditLogger: File write failed: {e}")

    def query(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Query audit events from local storage."""
        events = self._local_events[-limit:]

        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        if severity:
            events = [e for e in events if e.get("severity") == severity]

        return events

    def get_summary(self) -> Dict[str, Any]:
        """Get audit summary."""
        total = len(self._local_events)
        by_severity = {}
        for event in self._local_events:
            sev = event.get("severity", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        by_type = {}
        for event in self._local_events:
            typ = event.get("event_type", "unknown")
            by_type[typ] = by_type.get(typ, 0) + 1

        return {
            "total_events": total,
            "by_severity": by_severity,
            "by_type": by_type,
        }

    def close(self):
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()


def create_catalyst_audit_logger() -> AuditLogger:
    """Create audit logger for Catalyst."""
    return AuditLogger(
        graphiti_url="http://localhost:8001",
        log_file="data/audit.log",
    )
