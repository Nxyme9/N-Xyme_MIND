"""
API Security Gateway
Advanced API protection: WAF, rate limiting, request validation, threat detection
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Threat levels."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"
    CRITICAL = "critical"


class AttackType(str, Enum):
    """Types of attacks."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    LDAP_INJECTION = "ldap_injection"
    XXE = "xxe"
    DESERIALIZATION = "deserialization"
    RATE_LIMIT = "rate_limit"
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    API_ABUSE = "api_abuse"


@dataclass
class ThreatDetection:
    """Threat detection result."""
    threat_level: ThreatLevel
    attack_type: Optional[AttackType]
    confidence: float
    details: str
    indicators: List[str] = field(default_factory=list)
    recommended_action: str = "allow"


@dataclass
class RequestValidation:
    """Request validation result."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized_params: Dict[str, Any] = field(default_factory=dict)


class APIWAF:
    """
    Web Application Firewall for API protection.
    Detects and blocks common attack patterns.
    """
    
    def __init__(self):
        self._patterns = self._load_attack_patterns()
        self._whitelist = set()
        self._blacklist = set()
    
    def _load_attack_patterns(self) -> Dict[AttackType, List[str]]:
        """Load attack detection patterns."""
        return {
            AttackType.SQL_INJECTION: [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b)",
                r"(--|;|/\*|\*/)",
                r"(\bOR\b.*=.*\bOR\b)",
                r"(\bAND\b.*=.*\bAND\b)",
                r"('\s*(OR|AND)\s*')",
                r"(exec\s*\(|xp_cmdshell)",
            ],
            AttackType.XSS: [
                r"(<script|</script>)",
                r"(javascript:)",
                r"(on\w+\s*=)",
                r"(<iframe|<object|<embed)",
                r"(eval\s*\(|alert\s*\()",
                r"(<.*\s+on\w+\s*=)",
            ],
            AttackType.PATH_TRAVERSAL: [
                r"(\.\./)",
                r"(\.\.\\)",
                r"(/etc/passwd)",
                r"(c:\\windows)",
                r"(%2e%2e)",
            ],
            AttackType.COMMAND_INJECTION: [
                r"(;\s*rm\s+)",
                r"(;\s*cat\s+)",
                r"(\|\s*nc\s+)",
                r"(`.*`)",
                r"(\$\(.*\))",
                r"( wget | curl | ping )",
            ],
            AttackType.LDAP_INJECTION: [
                r"(\*\)\()",
                r"(\(\|)",
                r"(\(\w+=)",
            ],
            AttackType.CSRF: [
                r"(csrf_token|xsrf_token)",
            ],
        }
    
    def detect_threats(self, request_data: Dict[str, Any]) -> ThreatDetection:
        """
        Analyze request for potential threats.
        
        Args:
            request_data: Dict with keys: url, method, headers, params, body
        
        Returns:
            ThreatDetection with threat assessment
        """
        indicators = []
        threat_level = ThreatLevel.SAFE
        attack_type = None
        confidence = 0.0
        
        # Check URL
        url = request_data.get("url", "")
        method = request_data.get("method", "GET")
        
        # Check parameters
        params = request_data.get("params", {})
        body = request_data.get("body", "")
        headers = request_data.get("headers", {})
        
        # Combine all text to analyze
        text_to_analyze = f"{url} {method} {json.dumps(params)} {str(body)} {json.dumps(headers)}"
        
        # Check each attack type
        for attack_type_enum, patterns in self._patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_to_analyze, re.IGNORECASE)
                if matches:
                    indicators.append(f"{attack_type_enum.value}: {matches[:3]}")
                    attack_type = attack_type_enum
                    confidence = min(1.0, confidence + 0.3)
        
        # Determine threat level
        if confidence >= 0.8:
            threat_level = ThreatLevel.CRITICAL
        elif confidence >= 0.6:
            threat_level = ThreatLevel.DANGEROUS
        elif confidence >= 0.3:
            threat_level = ThreatLevel.SUSPICIOUS
        
        # Check rate limiting
        if request_data.get("rate_limited", False):
            indicators.append("rate_limit_exceeded")
            if attack_type is None:
                attack_type = AttackType.RATE_LIMIT
            confidence = max(confidence, 0.7)
            threat_level = ThreatLevel.DANGEROUS
        
        # Set recommended action
        if threat_level in [ThreatLevel.CRITICAL, ThreatLevel.DANGEROUS]:
            recommended_action = "block"
        elif threat_level == ThreatLevel.SUSPICIOUS:
            recommended_action = "challenge"
        else:
            recommended_action = "allow"
        
        return ThreatDetection(
            threat_level=threat_level,
            attack_type=attack_type,
            confidence=confidence,
            details=f"Detected {len(indicators)} threat indicators",
            indicators=indicators,
            recommended_action=recommended_action,
        )
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input by removing dangerous patterns."""
        sanitized = text
        
        # Remove script tags
        sanitized = re.sub(r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove javascript: URLs
        sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)
        
        # Remove event handlers
        sanitized = re.sub(r"\s*on\w+\s*=", " data-safe=", sanitized)
        
        # Remove path traversal
        sanitized = sanitized.replace("../", "")
        sanitized = sanitized.replace("..\\", "")
        
        return sanitized
    
    def validate_request(self, request_data: Dict[str, Any]) -> RequestValidation:
        """Validate and sanitize request."""
        errors = []
        sanitized_params = {}
        
        # Validate method
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
        method = request_data.get("method", "").upper()
        if method not in allowed_methods:
            errors.append(f"Invalid HTTP method: {method}")
        
        # Validate URL
        url = request_data.get("url", "")
        if not url.startswith("/"):
            errors.append("Invalid URL path")
        
        # Check for path traversal in URL
        if ".." in url or url.startswith("/etc") or url.startswith("/proc"):
            errors.append("Path traversal detected")
        
        # Sanitize parameters
        params = request_data.get("params", {})
        for key, value in params.items():
            if isinstance(value, str):
                sanitized_params[key] = self.sanitize_input(value)
            else:
                sanitized_params[key] = value
        
        # Check content length
        body = request_data.get("body", "")
        if len(body) > 10 * 1024 * 1024:  # 10MB
            errors.append("Request body too large")
        
        return RequestValidation(
            valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized_params,
        )


class APIRateLimiter:
    """
    Advanced API rate limiting with multiple strategies.
    """
    
    def __init__(self):
        self._limits: Dict[str, Dict[str, Any]] = {}
        self._init_default_limits()
    
    def _init_default_limits(self):
        """Initialize default rate limits."""
        self._limits = {
            "default": {
                "requests": 100,
                "window": 60,  # seconds
                "strategy": "sliding_window",
            },
            "auth": {
                "requests": 5,
                "window": 300,  # 5 minutes
                "strategy": "fixed_window",
            },
            "api": {
                "requests": 1000,
                "window": 3600,  # 1 hour
                "strategy": "sliding_window",
            },
            "search": {
                "requests": 30,
                "window": 60,
                "strategy": "token_bucket",
            },
        }
    
    def check_rate_limit(
        self,
        identifier: str,
        limit_type: str = "default",
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit.
        
        Returns:
            (allowed, info_dict)
        """
        if limit_type not in self._limits:
            limit_type = "default"
        
        limit = self._limits[limit_type]
        
        # In production, this would use Redis
        # For now, return allowed
        return True, {
            "limit": limit["requests"],
            "remaining": limit["requests"] - 1,
            "reset": int(datetime.utcnow().timestamp()) + limit["window"],
        }
    
    def set_limit(self, limit_type: str, requests: int, window: int, strategy: str = "sliding_window"):
        """Set custom rate limit."""
        self._limits[limit_type] = {
            "requests": requests,
            "window": window,
            "strategy": strategy,
        }


class APISecurityGateway:
    """
    Combined API security gateway.
    """
    
    def __init__(self):
        self.waf = APIWAF()
        self.rate_limiter = APIRateLimiter()
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming API request through security checks.
        
        Returns:
            Dict with keys: allowed, validation, threat_detection, rate_limit
        """
        result = {
            "allowed": True,
            "validation": None,
            "threat_detection": None,
            "rate_limit": None,
        }
        
        # 1. Rate limiting
        identifier = request_data.get("ip", "unknown")
        limit_type = request_data.get("limit_type", "default")
        
        allowed, rate_info = self.rate_limiter.check_rate_limit(identifier, limit_type)
        result["rate_limit"] = rate_info
        
        if not allowed:
            result["allowed"] = False
            result["error"] = "Rate limit exceeded"
            return result
        
        # 2. Request validation
        validation = self.waf.validate_request(request_data)
        result["validation"] = {
            "valid": validation.valid,
            "errors": validation.errors,
        }
        
        if not validation.valid:
            result["allowed"] = False
            result["error"] = "Request validation failed"
            return result
        
        # 3. Threat detection (WAF)
        threat = self.waf.detect_threats(request_data)
        result["threat_detection"] = {
            "level": threat.threat_level.value,
            "attack_type": threat.attack_type.value if threat.attack_type else None,
            "confidence": threat.confidence,
            "indicators": threat.indicators,
        }
        
        if threat.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.DANGEROUS]:
            result["allowed"] = False
            result["error"] = f"Threat detected: {threat.attack_type.value if threat.attack_type else 'unknown'}"
            return result
        
        # 4. Sanitize input
        request_data["params"] = validation.sanitized_params
        
        return result


# Global instance
_api_security: Optional[APISecurityGateway] = None


def get_api_security() -> APISecurityGateway:
    """Get the API security gateway."""
    global _api_security
    if _api_security is None:
        _api_security = APISecurityGateway()
    return _api_security
