"""
Intent-Based Orchestration — Ported from N-Xyme MIND

Allows users to express high-level goals (what they want to achieve)
and the system automatically determines how to accomplish it.

Usage:
    parser = IntentParser()
    intent = parser.parse("I want a reliable chat service with 99.9% uptime")
    print(intent.type, intent.description)
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of intents that can be expressed."""

    SERVICE = "service"  # "I want a reliable chat service"
    PERFORMANCE = "performance"  # "API should respond in under 200ms"
    SECURITY = "security"  # "Only authenticated users can access"
    SCALE = "scale"  # "Handle 10,000 concurrent users"
    DEPLOY = "deploy"  # "Deploy this module to production"
    MONITOR = "monitor"  # "Monitor this service for errors"
    BACKUP = "backup"  # "Backup my data daily"
    CUSTOM = "custom"  # User-defined intent


class IntentPriority(Enum):
    """Priority levels for intents."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntentStatus(Enum):
    """Status of an intent."""

    PENDING = "pending"
    PARSING = "parsing"
    VALIDATING = "validating"
    COMPILING = "compiling"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    SATISFIED = "satisfied"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class IntentConstraint:
    """A constraint that must be satisfied."""

    name: str
    metric: str
    threshold: float
    operator: str = "lt"  # lt, lte, gt, gte, eq

    def evaluate(self, metrics: Dict[str, float]) -> bool:
        """Evaluate if constraint is satisfied."""
        value = metrics.get(self.metric, 0)
        if self.operator == "lt":
            return value < self.threshold
        elif self.operator == "lte":
            return value <= self.threshold
        elif self.operator == "gt":
            return value > self.threshold
        elif self.operator == "gte":
            return value >= self.threshold
        elif self.operator == "eq":
            return value == self.threshold
        return False


@dataclass
class Intent:
    """Represents a user intent — what the user wants to achieve."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: IntentType = IntentType.CUSTOM
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: IntentPriority = IntentPriority.MEDIUM
    status: IntentStatus = IntentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    constraints: List[IntentConstraint] = field(default_factory=list)
    execution_plan: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "parameters": self.parameters,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "constraints": [
                {
                    "name": c.name,
                    "metric": c.metric,
                    "threshold": c.threshold,
                    "operator": c.operator,
                }
                for c in self.constraints
            ],
            "execution_plan": self.execution_plan,
        }


# Pre-defined intent templates
INTENT_TEMPLATES = {
    "reliable_service": {
        "type": IntentType.SERVICE,
        "description": "I want a reliable {service_name} with {sla}% uptime",
        "parameters": [
            {"name": "service_name", "type": "string", "required": True},
            {"name": "sla", "type": "number", "required": False, "default": "99.9"},
        ],
    },
    "fast_api": {
        "type": IntentType.PERFORMANCE,
        "description": "{api_name} should respond in under {latency}ms",
        "parameters": [
            {"name": "api_name", "type": "string", "required": True},
            {"name": "latency", "type": "number", "required": True},
        ],
    },
    "secure_access": {
        "type": IntentType.SECURITY,
        "description": "Only {role} users can access {resource}",
        "parameters": [
            {"name": "role", "type": "string", "required": True},
            {"name": "resource", "type": "string", "required": True},
        ],
    },
    "high_scale": {
        "type": IntentType.SCALE,
        "description": "Handle {capacity} concurrent users",
        "parameters": [
            {"name": "capacity", "type": "number", "required": True},
        ],
    },
}


class IntentParser:
    """
    Parses natural language into structured Intent objects.
    Uses pattern matching first, then falls back to LLM.
    """

    PATTERNS = {
        IntentType.SERVICE: [
            re.compile(r"reliable.*?(\w+)\s+(?:service|module)", re.I),
            re.compile(r"create.*?(\w+)\s+service", re.I),
            re.compile(r"set up.*?(\w+).*?availability", re.I),
        ],
        IntentType.PERFORMANCE: [
            re.compile(r"respond in under\s+(\d+)\s*ms", re.I),
            re.compile(r"be faster than\s+(\d+)\s*ms", re.I),
            re.compile(r"reduce latency.*?(\d+)\s*ms", re.I),
        ],
        IntentType.SECURITY: [
            re.compile(r"only\s+(\w+)\s+users", re.I),
            re.compile(r"require\s+(\w+)\s+(?:authentication|authorization)", re.I),
            re.compile(r"restrict access to\s+(\w+)\s+role", re.I),
        ],
        IntentType.SCALE: [
            re.compile(r"handle\s+([\d,]+)\s+concurrent", re.I),
            re.compile(r"scale to\s+([\d,]+)\s+users", re.I),
            re.compile(r"support\s+([\d,]+)\s+(?:simultaneous|connections)", re.I),
        ],
        IntentType.DEPLOY: [
            re.compile(r"deploy\s+(.+?)\s+to\s+(?:production|staging|development)", re.I),
            re.compile(r"(?:push|ship)\s+(.+?)\s+(?:to|into)\s+production", re.I),
        ],
        IntentType.MONITOR: [
            re.compile(r"monitor\s+(\w+)\s+for\s+(?:errors|issues|problems)", re.I),
            re.compile(r"set up\s+(?:monitoring|alerting)\s+for\s+(\w+)", re.I),
        ],
    }

    def parse(self, text: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """
        Parse natural language text into an Intent.
        First tries pattern matching, then falls back to LLM.
        """
        # Try pattern matching first
        intent = self._parse_with_patterns(text)
        if intent:
            intent.context = context or {}
            return intent

        # Default: create a custom intent
        return Intent(
            id=str(uuid.uuid4()),
            type=IntentType.CUSTOM,
            description=text,
            parameters={"raw_text": text},
        )

    def _parse_with_patterns(self, text: str) -> Optional[Intent]:
        """Parse using regex patterns."""
        text_lower = text.lower()

        for intent_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return Intent(
                        id=str(uuid.uuid4()),
                        type=intent_type,
                        description=text,
                        parameters=self._extract_parameters(text, intent_type),
                    )
        return None

    def _extract_parameters(self, text: str, intent_type: IntentType) -> Dict[str, Any]:
        """Extract parameters from text based on intent type."""
        params = {}

        if intent_type == IntentType.PERFORMANCE:
            match = re.search(r"(\d+)ms", text)
            if match:
                params["latency_ms"] = int(match.group(1))

        elif intent_type == IntentType.SCALE:
            match = re.search(r"(\d+(?:,\d+)?)", text)
            if match:
                params["capacity"] = int(match.group(1).replace(",", ""))

        elif intent_type == IntentType.SERVICE:
            match = re.search(r"(?:reliable |stable )?(\w+) (?:service|module)", text, re.I)
            if match:
                params["service_name"] = match.group(1)

        return params


class IntentResolver:
    """
    Resolves intents into execution plans.
    Converts high-level goals into concrete actions.
    """

    def __init__(self, service_registry: Optional[Dict[str, Any]] = None):
        self.service_registry = service_registry or {}

    def resolve(self, intent: Intent) -> Intent:
        """Resolve an intent into an execution plan."""
        intent.status = IntentStatus.COMPILING

        if intent.type == IntentType.SERVICE:
            intent.execution_plan = self._resolve_service(intent)
        elif intent.type == IntentType.PERFORMANCE:
            intent.execution_plan = self._resolve_performance(intent)
        elif intent.type == IntentType.SECURITY:
            intent.execution_plan = self._resolve_security(intent)
        elif intent.type == IntentType.SCALE:
            intent.execution_plan = self._resolve_scale(intent)
        else:
            intent.execution_plan = [{"action": "manual_review", "intent": intent.description}]

        intent.status = IntentStatus.EXECUTING
        return intent

    def _resolve_service(self, intent: Intent) -> List[Dict[str, Any]]:
        """Resolve a service intent into actions."""
        service_name = intent.parameters.get("service_name", "unknown")
        sla = intent.parameters.get("sla", 99.9)

        return [
            {"action": "check_health", "target": service_name},
            {"action": "set_monitoring", "target": service_name, "sla": sla},
            {"action": "configure_alerting", "target": service_name},
        ]

    def _resolve_performance(self, intent: Intent) -> List[Dict[str, Any]]:
        """Resolve a performance intent into actions."""
        api_name = intent.parameters.get("api_name", "unknown")
        latency_ms = intent.parameters.get("latency_ms", 200)

        return [
            {"action": "measure_latency", "target": api_name},
            {"action": "set_threshold", "target": api_name, "max_ms": latency_ms},
            {"action": "configure_alerting", "target": api_name, "threshold": latency_ms},
        ]

    def _resolve_security(self, intent: Intent) -> List[Dict[str, Any]]:
        """Resolve a security intent into actions."""
        return [
            {"action": "enable_authentication"},
            {"action": "configure_rbac", "roles": intent.parameters},
            {"action": "audit_access_logs"},
        ]

    def _resolve_scale(self, intent: Intent) -> List[Dict[str, Any]]:
        """Resolve a scale intent into actions."""
        capacity = intent.parameters.get("capacity", 1000)

        return [
            {"action": "measure_current_load"},
            {"action": "calculate_required_resources", "target_capacity": capacity},
            {"action": "configure_auto_scaling", "max_instances": max(1, capacity // 1000)},
        ]


# ============================================
# CONVENIENCE: Create parser for Catalyst
# ============================================


def create_catalyst_parser() -> IntentParser:
    """Create an IntentParser for Catalyst."""
    return IntentParser()


def create_catalyst_resolver() -> IntentResolver:
    """Create an IntentResolver for Catalyst."""
    return IntentResolver()
