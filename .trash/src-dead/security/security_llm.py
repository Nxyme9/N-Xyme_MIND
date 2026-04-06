"""
OWASP LLM Top 10 (2025) Security Baseline for CATALYST.

Provides security controls for LLM-based agent systems:
- LLM01: Prompt Injection Detection
- LLM02: Sensitive Information Disclosure Prevention
- LLM03: Supply Chain Vulnerability Checks
- LLM04: Data and Model Poisoning Validation
- LLM05: Improper Output Handling Sanitization
- LLM06: Excessive Agency Prevention (Tool Access Limiting)
- LLM07: System Prompt Leakage Prevention
- LLM08: Vector and Embedding Weakness Protection
- LLM09: Misinformation Detection
- LLM10: Unbounded Consumption Rate Limiting

Usage:
    from security_llm import SecurityManager
    security = SecurityManager()
    result = security.validate_input(user_message)
    safe_output = security.sanitize_output(llm_response)
"""

import re
import json
import time
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


# ── Security Event Types ─────────────────────────────────────────────


class SecurityEventType(Enum):
    """Types of security events for audit logging."""

    PROMPT_INJECTION_DETECTED = "prompt_injection"
    SENSITIVE_DATA_REDACTED = "sensitive_data_redacted"
    INVALID_INPUT = "invalid_input"
    MALICIOUS_OUTPUT = "malicious_output"
    TOOL_ACCESS_DENIED = "tool_access_denied"
    SYSTEM_PROMPT_LEAK_ATTEMPT = "system_prompt_leak"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUPPLY_CHAIN_WARNING = "supply_chain_warning"
    MISINFORMATION_DETECTED = "misinformation_detected"
    EMBEDDING_ATTACK = "embedding_attack"


@dataclass
class SecurityEvent:
    """A security event for audit logging."""

    event_type: SecurityEventType
    severity: str  # low, medium, high, critical
    message: str
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a security validation check."""

    is_valid: bool
    sanitized_content: str = ""
    violations: List[str] = field(default_factory=list)
    events: List[SecurityEvent] = field(default_factory=list)


# ── LLM01: Prompt Injection Detector ─────────────────────────────────


class PromptInjectionDetector:
    """
    Detect prompt injection attempts in user inputs.

    Patterns detected:
    - Direct instruction overrides ("ignore previous", "disregard")
    - Role hijacking ("you are now", "act as")
    - System prompt extraction ("show your system prompt", "reveal instructions")
    - Encoding tricks (base64, hex, unicode)
    - Delimiter confusion (markdown injection, XML tags)
    """

    # Direct override patterns
    OVERRIDE_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+(instructions|prompts|rules|context)",
        r"disregard\s+(all\s+)?(prior|previous|earlier|above)",
        r"forget\s+(everything|all|your)\s+(instructions|rules|training)",
        r"override\s+(your|the)\s+(instructions|rules|programming)",
        r"new\s+instructions?:",
        r"system\s*:\s*you\s+are",
    ]

    # Role hijacking patterns
    ROLE_HIJACK_PATTERNS = [
        r"you\s+are\s+now\s+(a|an|the)\s+",
        r"act\s+as\s+(if|though|like)\s+you\s+(are|were|have)",
        r"pretend\s+(to\s+be|you\s+are|you're)",
        r"roleplay\s+as\s+",
        r"from\s+now\s+on[,.]?\s+you",
    ]

    # System prompt extraction patterns
    EXTRACTION_PATTERNS = [
        r"(show|reveal|display|print|output|repeat|tell)\s+(me\s+)?(your|the)?\s*(system|initial|original)\s*(prompt|instructions|rules)",
        r"what\s+(are|is)\s+your\s+(system|initial|original)\s*(prompt|instructions)",
        r"repeat\s+(everything|all)\s+(above|before)",
        r"verbatim\s+(output|copy|repeat)",
    ]

    # Encoding tricks
    ENCODING_PATTERNS = [
        r"base64[\s:]+[A-Za-z0-9+/=]{8,}",
        r"0x[0-9a-fA-F]{8,}",
        r"&#x?[0-9a-fA-F]+;",
        r"\\u[0-9a-fA-F]{4}",
    ]

    # Delimiter confusion
    DELIMITER_PATTERNS = [
        r"```\s*(system|assistant|instruction)",
        r"<\s*(system|instructions?|prompt)\s*>",
        r"\[INST\]|\[/INST\]",
        r"<<SYS>>|<</SYS>>",
    ]

    def __init__(self, custom_patterns: Optional[List[str]] = None):
        """Initialize with optional custom detection patterns."""
        self.all_patterns = (
            self.OVERRIDE_PATTERNS
            + self.ROLE_HIJACK_PATTERNS
            + self.EXTRACTION_PATTERNS
            + self.ENCODING_PATTERNS
            + self.DELIMITER_PATTERNS
        )
        if custom_patterns:
            self.all_patterns.extend(custom_patterns)

        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.all_patterns]

    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect prompt injection in text.

        Returns:
            Tuple of (is_injection_detected, list_of_matched_patterns)
        """
        if not text:
            return False, []

        matches = []
        for pattern in self._compiled:
            if pattern.search(text):
                matches.append(pattern.pattern)

        return bool(matches), matches

    def get_severity(self, matches: List[str]) -> str:
        """Determine severity based on matched patterns."""
        if not matches:
            return "low"

        # Check for direct overrides = critical
        override_matches = [
            m for m in matches if any(p in m for p in ["ignore", "disregard", "forget", "override"])
        ]
        if override_matches:
            return "critical"

        # Extraction attempts = high
        extraction_matches = [
            m for m in matches if any(p in m for p in ["show", "reveal", "system prompt", "repeat"])
        ]
        if extraction_matches:
            return "high"

        # Role hijacking = medium
        role_matches = [
            m for m in matches if "you" in m and ("are" in m or "act" in m or "pretend" in m)
        ]
        if role_matches:
            return "medium"

        return "low"


# ── LLM02: Sensitive Data Redactor ───────────────────────────────────


class SensitiveDataRedactor:
    """
    Redact PII and secrets from text.

    Detects and redacts:
    - API keys (AWS, OpenAI, GitHub, generic)
    - Passwords and tokens
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - Social security numbers
    - IP addresses
    - Private keys
    """

    PATTERNS = {
        # API Keys
        "aws_key": (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
        "openai_key": (r"sk-[a-zA-Z0-9]{48}", "[REDACTED_OPENAI_KEY]"),
        "github_token": (r"ghp_[a-zA-Z0-9]{36}", "[REDACTED_GITHUB_TOKEN]"),
        "generic_api_key": (
            r"(?:api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            "[REDACTED_API_KEY]",
        ),
        # Passwords and tokens
        "password": (
            r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
            "[REDACTED_PASSWORD]",
        ),
        "bearer_token": (r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED_TOKEN]"),
        "jwt": (r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+", "[REDACTED_JWT]"),
        # Private keys
        "private_key": (
            r"-----BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE KEY-----",
            "[REDACTED_PRIVATE_KEY]",
        ),
        # PII
        "email": (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]"),
        "phone": (r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", "[REDACTED_PHONE]"),
        "ssn": (r"\b\d{3}[-]?\d{2}[-]?\d{4}\b", "[REDACTED_SSN]"),
        "credit_card": (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[REDACTED_CC]"),
        # Network
        "ipv4": (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[REDACTED_IP]"),
        "ipv6": (r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}", "[REDACTED_IP]"),
    }

    def __init__(self, custom_patterns: Optional[Dict[str, Tuple[str, str]]] = None):
        """Initialize with optional custom redaction patterns."""
        patterns = dict(self.PATTERNS)
        if custom_patterns:
            patterns.update(custom_patterns)

        self._compiled = {
            name: (re.compile(pattern, re.IGNORECASE), replacement)
            for name, (pattern, replacement) in patterns.items()
        }

    def redact(self, text: str) -> Tuple[str, List[str]]:
        """
        Redact sensitive data from text.

        Returns:
            Tuple of (redacted_text, list_of_redacted_types)
        """
        if not text:
            return text, []

        redacted_types = []
        result = text

        for name, (pattern, replacement) in self._compiled.items():
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                redacted_types.append(name)

        return result, redacted_types

    def has_sensitive_data(self, text: str) -> bool:
        """Check if text contains sensitive data."""
        if not text:
            return False

        for pattern, _ in self._compiled.values():
            if pattern.search(text):
                return True
        return False


# ── LLM05: Output Sanitizer ──────────────────────────────────────────


class OutputSanitizer:
    """
    Sanitize LLM outputs to prevent injection and unsafe content.

    Sanitizes:
    - HTML/script injection
    - Shell command injection
    - Path traversal
    - Markdown injection
    - JSON/XML injection
    """

    # Dangerous patterns to remove or escape
    DANGEROUS_PATTERNS = [
        (r"<script[^>]*>.*?</script>", "", re.IGNORECASE | re.DOTALL),
        (r"javascript\s*:", "", re.IGNORECASE),
        (r"on\w+\s*=\s*['\"].*?['\"]", "", re.IGNORECASE),  # onclick=, onerror=, etc.
        (r"data\s*:\s*text/html", "", re.IGNORECASE),
        (r"vbscript\s*:", "", re.IGNORECASE),
    ]

    # Shell injection patterns
    SHELL_PATTERNS = [
        (r"[;&|`$]", lambda m: f"\\{m.group()}"),  # Escape shell metacharacters
        (r"\.\./", ""),  # Path traversal
        (r"/etc/(passwd|shadow|hosts)", "[REDACTED_PATH]"),
    ]

    def __init__(self, strict_mode: bool = False):
        """
        Initialize sanitizer.

        Args:
            strict_mode: If True, be more aggressive with sanitization
        """
        self.strict_mode = strict_mode
        self._dangerous_compiled = [(re.compile(p, f), r) for p, r, f in self.DANGEROUS_PATTERNS]
        self._shell_compiled = [(re.compile(p), r) for p, r in self.SHELL_PATTERNS]

    def sanitize(self, text: str, context: str = "general") -> str:
        """
        Sanitize text based on context.

        Args:
            text: Text to sanitize
            context: Context type (general, html, shell, json, markdown)

        Returns:
            Sanitized text
        """
        if not text:
            return text

        result = text

        # Always apply dangerous pattern removal
        for pattern, replacement in self._dangerous_compiled:
            if callable(replacement):
                result = pattern.sub(replacement, result)
            else:
                result = pattern.sub(replacement, result)

        # Context-specific sanitization
        if context in ("shell", "command"):
            result = self._sanitize_shell(result)
        elif context == "html":
            result = self._sanitize_html(result)
        elif context == "json":
            result = self._sanitize_json(result)
        elif context == "markdown":
            result = self._sanitize_markdown(result)

        if self.strict_mode:
            result = self._strict_sanitize(result)

        return result

    def _sanitize_shell(self, text: str) -> str:
        """Sanitize text for shell context."""
        for pattern, replacement in self._shell_compiled:
            if callable(replacement):
                text = pattern.sub(replacement, text)
            else:
                text = pattern.sub(replacement, text)
        return text

    def _sanitize_html(self, text: str) -> str:
        """Sanitize text for HTML context."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        return text

    def _sanitize_json(self, text: str) -> str:
        """Sanitize text for JSON context."""
        # Remove control characters
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
        return text

    def _sanitize_markdown(self, text: str) -> str:
        """Sanitize text for markdown context."""
        # Escape markdown links that could be malicious
        text = re.sub(
            r"\[([^\]]*)\]\((javascript|data|vbscript):[^)]+\)", r"\1", text, flags=re.IGNORECASE
        )
        return text

    def _strict_sanitize(self, text: str) -> str:
        """Apply strict sanitization rules."""
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"(?<!http:)(?<!https:)//[^\s]+", "[REDACTED_URL]", text)
        return text

    def is_safe(self, text: str) -> bool:
        """Check if text is safe (no dangerous patterns found)."""
        if not text:
            return True

        for pattern, _ in self._dangerous_compiled:
            if pattern.search(text):
                return False
        return True


# ── LLM04: Input Validator ───────────────────────────────────────────


class InputValidator:
    """
    Validate user inputs for data poisoning and malicious content.

    Checks:
    - Input length limits
    - Character encoding validity
    - Known attack patterns
    - Anomalous content detection
    """

    def __init__(
        self,
        max_length: int = 50000,
        max_lines: int = 1000,
        allowed_encodings: Optional[Set[str]] = None,
    ):
        """Initialize validator with limits."""
        self.max_length = max_length
        self.max_lines = max_lines
        self.allowed_encodings = allowed_encodings or {"utf-8", "ascii", "latin-1"}

        # Known attack patterns
        self.attack_patterns = [
            re.compile(r"(?i)training\s+data\s*:"),
            re.compile(r"(?i)(?:ignore|bypass)\s+(?:safety|filter|guardrail)"),
            re.compile(r"(?i)(?:jailbreak|DAN|do\s+anything\s+now)"),
            re.compile(r"(?i)you\s+must\s+(?:always|never)\s+"),
            re.compile(r"(?:\x00|\x01|\x02|\x03|\x04|\x05){3,}"),  # Control character flood
        ]

    def validate(self, text: str) -> ValidationResult:
        """
        Validate input text.

        Returns:
            ValidationResult with is_valid flag and any violations
        """
        violations = []
        events = []

        if not text:
            return ValidationResult(is_valid=True, sanitized_content="")

        # Length check
        if len(text) > self.max_length:
            violations.append(f"Input exceeds max length ({len(text)} > {self.max_length})")
            events.append(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    severity="medium",
                    message=f"Input length {len(text)} exceeds limit {self.max_length}",
                )
            )

        # Line count check
        line_count = text.count("\n") + 1
        if line_count > self.max_lines:
            violations.append(f"Input exceeds max lines ({line_count} > {self.max_lines})")
            events.append(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    severity="medium",
                    message=f"Input line count {line_count} exceeds limit {self.max_lines}",
                )
            )

        # Encoding check
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as e:
            violations.append(f"Invalid encoding: {e}")
            events.append(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    severity="high",
                    message=f"Invalid character encoding detected",
                )
            )

        # Attack pattern check
        for pattern in self.attack_patterns:
            if pattern.search(text):
                violations.append(f"Attack pattern detected: {pattern.pattern}")
                events.append(
                    SecurityEvent(
                        event_type=SecurityEventType.INVALID_INPUT,
                        severity="high",
                        message=f"Known attack pattern detected",
                    )
                )

        # Null byte check
        if "\x00" in text:
            violations.append("Null bytes detected in input")
            events.append(
                SecurityEvent(
                    event_type=SecurityEventType.INVALID_INPUT,
                    severity="high",
                    message="Null bytes in input (potential injection)",
                )
            )

        is_valid = len(violations) == 0
        return ValidationResult(
            is_valid=is_valid,
            sanitized_content=text if is_valid else "",
            violations=violations,
            events=events,
        )


# ── LLM06: Tool Access Limiter ───────────────────────────────────────


class ToolAccessLimiter:
    """
    Enforce least-privilege access to tools.

    Limits:
    - Tool allowlists/blocklists
    - Rate limiting per tool
    - Permission levels
    - Dangerous tool restrictions
    """

    # Tools considered dangerous (require elevated permissions)
    DANGEROUS_TOOLS = {
        "exec",
        "shell",
        "subprocess",
        "os.system",
        "delete",
        "rm",
        "remove",
        "write_file",
        "modify_file",
        "network",
        "http",
        "fetch",
        "curl",
        "install",
        "pip",
        "npm",
    }

    def __init__(
        self,
        allowed_tools: Optional[Set[str]] = None,
        blocked_tools: Optional[Set[str]] = None,
        rate_limits: Optional[Dict[str, int]] = None,
        permission_level: str = "standard",
    ):
        """
        Initialize tool access limiter.

        Args:
            allowed_tools: Set of allowed tool names (None = all allowed)
            blocked_tools: Set of blocked tool names
            rate_limits: Dict of tool_name -> max_calls_per_minute
            permission_level: "restricted", "standard", or "elevated"
        """
        self.allowed_tools = allowed_tools
        self.blocked_tools = blocked_tools or set()
        self.rate_limits = rate_limits or {}
        self.permission_level = permission_level

        # Rate limiting state
        self._call_counts: Dict[str, List[float]] = defaultdict(list)
        self._window_seconds = 60

    def is_allowed(self, tool_name: str) -> Tuple[bool, str]:
        """
        Check if a tool call is allowed.

        Returns:
            Tuple of (is_allowed, reason)
        """
        if not tool_name:
            return False, "Empty tool name"

        # Check blocklist
        if tool_name in self.blocked_tools:
            return False, f"Tool '{tool_name}' is blocked"

        # Check allowlist (if set)
        if self.allowed_tools is not None and tool_name not in self.allowed_tools:
            return False, f"Tool '{tool_name}' not in allowlist"

        # Check dangerous tools
        if tool_name in self.DANGEROUS_TOOLS and self.permission_level != "elevated":
            return False, f"Tool '{tool_name}' requires elevated permissions"

        # Check rate limit
        if not self._check_rate_limit(tool_name):
            return False, f"Rate limit exceeded for '{tool_name}'"

        return True, "Allowed"

    def _check_rate_limit(self, tool_name: str) -> bool:
        """Check if tool call is within rate limit."""
        if tool_name not in self.rate_limits:
            return True

        limit = self.rate_limits[tool_name]
        now = time.time()

        self._call_counts[tool_name] = [
            t for t in self._call_counts[tool_name] if now - t < self._window_seconds
        ]

        return len(self._call_counts[tool_name]) < limit

    def record_call(self, tool_name: str) -> None:
        """Record a tool call for rate limiting."""
        self._call_counts[tool_name].append(time.time())


# ── LLM07: System Prompt Guard ───────────────────────────────────────


class SystemPromptGuard:
    """
    Prevent system prompt leakage in LLM outputs.

    Detects:
    - System prompt fragments in output
    - Instruction leakage
    - Configuration exposure
    """

    def __init__(self, system_prompt_fragments: Optional[List[str]] = None):
        """
        Initialize with system prompt fragments to protect.

        Args:
            system_prompt_fragments: List of sensitive phrases from system prompt
        """
        self.protected_fragments: List[str] = []
        if system_prompt_fragments:
            for fragment in system_prompt_fragments:
                if len(fragment) > 10:  # Only protect meaningful fragments
                    self.protected_fragments.append(fragment.lower())

        # Common system prompt indicators
        self.system_indicators = [
            re.compile(r"(?i)system\s*prompt\s*:", re.IGNORECASE),
            re.compile(
                r"(?i)you\s+are\s+an?\s+(?:ai|assistant|agent)\s+(?:designed|built|created)",
                re.IGNORECASE,
            ),
            re.compile(r"(?i)your\s+(?:instructions|rules|guidelines)\s+(?:are|is)", re.IGNORECASE),
            re.compile(
                r"(?i)(?:here\s+are|follow)\s+(?:your|the)\s+(?:instructions|rules)", re.IGNORECASE
            ),
        ]

    def check_output(self, output: str) -> Tuple[bool, List[str]]:
        """
        Check if output contains system prompt leakage.

        Returns:
            Tuple of (is_safe, list_of_leaked_fragments)
        """
        if not output:
            return True, []

        leaked = []
        output_lower = output.lower()

        # Check protected fragments
        for fragment in self.protected_fragments:
            if fragment in output_lower:
                leaked.append(f"Protected fragment: {fragment[:50]}...")

        # Check system indicators
        for pattern in self.system_indicators:
            if pattern.search(output):
                leaked.append(f"System indicator: {pattern.pattern}")

        return len(leaked) == 0, leaked

    def sanitize_output(self, output: str) -> str:
        """Remove system prompt content from output."""
        if not output:
            return output

        result = output

        # Remove protected fragments
        for fragment in self.protected_fragments:
            # Case-insensitive replacement
            result = re.sub(re.escape(fragment), "[REDACTED]", result, flags=re.IGNORECASE)

        # Remove system indicator matches
        for pattern in self.system_indicators:
            result = pattern.sub("[REDACTED_SYSTEM_REFERENCE]", result)

        return result


# ── LLM09/LLM10: Security Auditor (Audit Logging + Rate Limiting) ────


class SecurityAuditor:
    """
    Audit logging and rate limiting for security events.

    Features:
    - Security event logging
    - Rate limiting for LLM calls
    - Consumption tracking
    - Alert thresholds
    """

    def __init__(
        self,
        max_events: int = 10000,
        rate_limit_calls: int = 100,
        rate_limit_window: int = 60,
        alert_thresholds: Optional[Dict[str, int]] = None,
    ):
        """
        Initialize auditor.

        Args:
            max_events: Maximum events to keep in memory
            rate_limit_calls: Max LLM calls per window
            rate_limit_window: Rate limit window in seconds
            alert_thresholds: Dict of event_type -> count before alert
        """
        self.max_events = max_events
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_window = rate_limit_window
        self.alert_thresholds = alert_thresholds or {}

        # Event storage
        self.events: List[SecurityEvent] = []
        self._event_counts: Dict[SecurityEventType, int] = defaultdict(int)

        # Rate limiting state
        self._call_timestamps: List[float] = []

        # Alert state
        self._alert_counts: Dict[SecurityEventType, int] = defaultdict(int)

    def log_event(self, event: SecurityEvent) -> None:
        """Log a security event."""
        self.events.append(event)
        self._event_counts[event.event_type] += 1

        # Trim if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Check alert threshold
        self._alert_counts[event.event_type] += 1
        threshold = self.alert_thresholds.get(event.event_type.value, 0)
        if threshold > 0 and self._alert_counts[event.event_type] >= threshold:
            self._raise_alert(event.event_type)

        # Log based on severity
        if event.severity == "critical":
            logger.critical(f"SECURITY: {event.event_type.value} - {event.message}")
        elif event.severity == "high":
            logger.error(f"SECURITY: {event.event_type.value} - {event.message}")
        elif event.severity == "medium":
            logger.warning(f"SECURITY: {event.event_type.value} - {event.message}")
        else:
            logger.info(f"SECURITY: {event.event_type.value} - {event.message}")

    def check_rate_limit(self) -> Tuple[bool, int]:
        """
        Check if LLM call is within rate limit.

        Returns:
            Tuple of (is_allowed, remaining_calls)
        """
        now = time.time()

        # Clean old timestamps
        self._call_timestamps = [
            t for t in self._call_timestamps if now - t < self.rate_limit_window
        ]

        remaining = self.rate_limit_calls - len(self._call_timestamps)

        if remaining <= 0:
            self.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                    severity="high",
                    message=f"Rate limit exceeded: {self.rate_limit_calls} calls in {self.rate_limit_window}s",
                )
            )
            return False, 0

        return True, remaining

    def record_call(self) -> None:
        """Record an LLM call for rate limiting."""
        self._call_timestamps.append(time.time())

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        return {
            "total_events": len(self.events),
            "event_counts": {k.value: v for k, v in self._event_counts.items()},
            "recent_events": [
                {
                    "type": e.event_type.value,
                    "severity": e.severity,
                    "message": e.message,
                    "timestamp": e.timestamp,
                }
                for e in self.events[-10:]
            ],
            "rate_limit": {
                "limit": self.rate_limit_calls,
                "window": self.rate_limit_window,
                "current_calls": len(self._call_timestamps),
                "remaining": self.rate_limit_calls - len(self._call_timestamps),
            },
        }

    def _raise_alert(self, event_type: SecurityEventType) -> None:
        """Raise an alert when threshold is exceeded."""
        logger.critical(
            f"SECURITY ALERT: {event_type.value} threshold exceeded "
            f"({self._alert_counts[event_type]} events)"
        )
        # Reset counter after alert
        self._alert_counts[event_type] = 0

    def get_events(
        self,
        event_type: Optional[SecurityEventType] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[SecurityEvent]:
        """Get filtered events."""
        filtered = self.events

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        return filtered[-limit:]


# ── Security Manager ─────────────────────────────────────────────────


class SecurityManager:
    """
    Central security manager orchestrating all security components.

    Provides unified interface for:
    - Input validation and injection detection
    - Output sanitization
    - Sensitive data redaction
    - Tool access control
    - System prompt protection
    - Audit logging and rate limiting
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        system_prompt_fragments: Optional[List[str]] = None,
    ):
        """
        Initialize security manager.

        Args:
            config: Optional configuration dict
            system_prompt_fragments: Fragments from system prompt to protect
        """
        config = config or {}

        # Initialize components
        self.injection_detector = PromptInjectionDetector(
            custom_patterns=config.get("custom_injection_patterns")
        )
        self.data_redactor = SensitiveDataRedactor(
            custom_patterns=config.get("custom_redaction_patterns")
        )
        self.output_sanitizer = OutputSanitizer(
            strict_mode=config.get("strict_sanitization", False)
        )
        self.input_validator = InputValidator(
            max_length=config.get("max_input_length", 50000),
            max_lines=config.get("max_input_lines", 1000),
        )
        self.tool_limiter = ToolAccessLimiter(
            allowed_tools=config.get("allowed_tools"),
            blocked_tools=config.get("blocked_tools"),
            rate_limits=config.get("tool_rate_limits"),
            permission_level=config.get("permission_level", "standard"),
        )
        self.prompt_guard = SystemPromptGuard(system_prompt_fragments=system_prompt_fragments)
        self.auditor = SecurityAuditor(
            max_events=config.get("max_audit_events", 10000),
            rate_limit_calls=config.get("rate_limit_calls", 100),
            rate_limit_window=config.get("rate_limit_window", 60),
            alert_thresholds=config.get("alert_thresholds"),
        )

        logger.info("SecurityManager: Initialized with all security components")

    def validate_input(self, text: str) -> ValidationResult:
        """
        Validate and check user input for security issues.

        Runs:
        1. Input validation (length, encoding, attack patterns)
        2. Prompt injection detection

        Returns:
            ValidationResult with sanitized content if valid
        """
        # Step 1: Input validation
        validation = self.input_validator.validate(text)
        for event in validation.events:
            self.auditor.log_event(event)

        if not validation.is_valid:
            return validation

        # Step 2: Injection detection
        is_injection, matches = self.injection_detector.detect(text)
        if is_injection:
            severity = self.injection_detector.get_severity(matches)
            event = SecurityEvent(
                event_type=SecurityEventType.PROMPT_INJECTION_DETECTED,
                severity=severity,
                message=f"Prompt injection detected: {len(matches)} patterns matched",
                details={"patterns": matches[:5]},
            )
            self.auditor.log_event(event)

            return ValidationResult(
                is_valid=False,
                violations=[f"Prompt injection detected ({len(matches)} patterns)"],
                events=[event],
            )

        # Step 3: Redact sensitive data from input
        redacted, redacted_types = self.data_redactor.redact(text)
        if redacted_types:
            event = SecurityEvent(
                event_type=SecurityEventType.SENSITIVE_DATA_REDACTED,
                severity="medium",
                message=f"Sensitive data redacted from input: {', '.join(redacted_types)}",
                details={"types": redacted_types},
            )
            self.auditor.log_event(event)

        return ValidationResult(
            is_valid=True,
            sanitized_content=redacted,
            events=validation.events,
        )

    def sanitize_output(self, text: str, context: str = "general") -> str:
        """
        Sanitize LLM output.

        Runs:
        1. System prompt leak detection and removal
        2. Sensitive data redaction
        3. Output sanitization

        Args:
            text: LLM output to sanitize
            context: Context for sanitization (general, html, shell, json, markdown)

        Returns:
            Sanitized text
        """
        if not text:
            return text

        # Step 1: Check for system prompt leakage
        is_safe, leaked = self.prompt_guard.check_output(text)
        if not is_safe:
            event = SecurityEvent(
                event_type=SecurityEventType.SYSTEM_PROMPT_LEAK_ATTEMPT,
                severity="high",
                message=f"System prompt leakage detected: {len(leaked)} fragments",
                details={"fragments": leaked[:3]},
            )
            self.auditor.log_event(event)
            text = self.prompt_guard.sanitize_output(text)

        # Step 2: Redact sensitive data
        text, redacted_types = self.data_redactor.redact(text)
        if redacted_types:
            event = SecurityEvent(
                event_type=SecurityEventType.SENSITIVE_DATA_REDACTED,
                severity="medium",
                message=f"Sensitive data redacted from output: {', '.join(redacted_types)}",
            )
            self.auditor.log_event(event)

        # Step 3: Sanitize output
        text = self.output_sanitizer.sanitize(text, context)

        # Step 4: Check if output is safe
        if not self.output_sanitizer.is_safe(text):
            event = SecurityEvent(
                event_type=SecurityEventType.MALICIOUS_OUTPUT,
                severity="high",
                message="Potentially malicious content detected in output",
            )
            self.auditor.log_event(event)

        return text

    def check_tool_access(self, tool_name: str) -> Tuple[bool, str]:
        """
        Check if a tool call is allowed.

        Returns:
            Tuple of (is_allowed, reason)
        """
        allowed, reason = self.tool_limiter.is_allowed(tool_name)

        if not allowed:
            event = SecurityEvent(
                event_type=SecurityEventType.TOOL_ACCESS_DENIED,
                severity="medium",
                message=f"Tool access denied: {tool_name} - {reason}",
                details={"tool": tool_name, "reason": reason},
            )
            self.auditor.log_event(event)

        return allowed, reason

    def check_rate_limit(self) -> Tuple[bool, int]:
        """
        Check if LLM call is within rate limit.

        Returns:
            Tuple of (is_allowed, remaining_calls)
        """
        return self.auditor.check_rate_limit()

    def record_llm_call(self) -> None:
        """Record an LLM call for rate limiting."""
        self.auditor.record_call()

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        return self.auditor.get_stats()

    def get_recent_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get recent security events."""
        evt_type = SecurityEventType(event_type) if event_type else None
        events = self.auditor.get_events(event_type=evt_type, severity=severity, limit=limit)

        return [
            {
                "type": e.event_type.value,
                "severity": e.severity,
                "message": e.message,
                "timestamp": e.timestamp,
                "source": e.source,
                "details": e.details,
            }
            for e in events
        ]


# ── Global Instance ──────────────────────────────────────────────────

SECURITY: Optional[SecurityManager] = None


def get_security(
    config: Optional[Dict[str, Any]] = None,
    system_prompt_fragments: Optional[List[str]] = None,
) -> SecurityManager:
    """Get or create the global security manager instance."""
    global SECURITY

    if SECURITY is None:
        SECURITY = SecurityManager(
            config=config,
            system_prompt_fragments=system_prompt_fragments,
        )

    return SECURITY


def init_security(
    config: Optional[Dict[str, Any]] = None,
    system_prompt_fragments: Optional[List[str]] = None,
) -> SecurityManager:
    """Initialize security with custom configuration."""
    global SECURITY
    SECURITY = SecurityManager(
        config=config,
        system_prompt_fragments=system_prompt_fragments,
    )
    return SECURITY
