#!/usr/bin/env python3
"""Secret Scanner — Pre-Capture Hook for Credential Leak Prevention.

Phase 4.2 of Masterplan: Production Readiness.

Provides:
- Scan code BEFORE LLM context capture
- Pattern matching for secrets (API keys, tokens, passwords)
- Block context capture if secrets detected
- Integration with PreCaptureHook from agent_trace

Usage:
    from packages.orchestration.secret_scanner import (
        SecretScanner,
        scan_content,
        register_pre_capture_hook,
    )

    # Register as pre-capture hook
    register_pre_capture_hook()

    # Or scan manually
    result = scan_content("your code here")
    if result.blocked:
        print(f"Secrets detected: {result.secrets}")
"""

from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

__version__ = "1.0.0"

# =============================================================================
# Secret Types
# =============================================================================


class SecretType(str, Enum):
    """Types of secrets that can be detected."""

    API_KEY = "api_key"
    AWS_KEY = "aws_key"
    AWS_SECRET = "aws_secret"
    GITHUB_TOKEN = "github_token"
    OPENAI_KEY = "openai_key"
    ANTHROPIC_KEY = "anthropic_key"
    JWT_TOKEN = "jwt_token"
    PRIVATE_KEY = "private_key"
    PASSWORD = "password"
    SECRET = "secret"
    DATABASE_URL = "database_url"
    SSH_KEY = "ssh_key"
    Bearer_TOKEN = "bearer_token"
    CUSTOM_TOKEN = "custom_token"


# =============================================================================
# Patterns
# =============================================================================

# Compiled regex patterns for secret detection
SECRET_PATTERNS: dict[SecretType, re.Pattern] = {
    # AWS Access Key ID (AKIA...)
    SecretType.AWS_KEY: re.compile(
        r'(?:AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']?([A-Z0-9]{20})["\']?',
        re.IGNORECASE,
    ),
    # Generic API Key patterns
    SecretType.API_KEY: re.compile(
        r'(?:api[_-]?key|apikey|API[_-]?KEY)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,64})["\']?',
        re.IGNORECASE,
    ),
    # GitHub Token (ghp_, gho_, ghu_, ghs_, ghr_)
    SecretType.GITHUB_TOKEN: re.compile(
        r'(?:GH_TOKEN|GITHUB_TOKEN|GITHUB_AUTH|gh_token)\s*[:=]\s*["\']?(ghp_[a-zA-Z0-9]{36,})["\']?',
        re.IGNORECASE,
    ),
    # OpenAI API Key (sk-...)
    SecretType.OPENAI_KEY: re.compile(
        r'(?:OPENAI_API_KEY|sk_openai|SK_OPENAI)\s*[:=]\s*["\']?(sk-[a-zA-Z0-9]{32,})["\']?',
        re.IGNORECASE,
    ),
    # Anthropic API Key (sk-ant-...)
    SecretType.ANTHROPIC_KEY: re.compile(
        r'(?:ANTHROPIC_API_KEY|ANTHROPIC_KEY|sk_ant)\s*[:=]\s*["\']?(sk-ant-[a-zA-Z0-9_-]{30,})["\']?',
        re.IGNORECASE,
    ),
    # JWT Token
    SecretType.JWT_TOKEN: re.compile(
        r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", re.IGNORECASE
    ),
    # Private Key (PEM format)
    SecretType.PRIVATE_KEY: re.compile(
        r"(?:-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)", re.MULTILINE
    ),
    # Password patterns
    SecretType.PASSWORD: re.compile(
        r'(?:password|passwd|pwd|secret)\s*[:=]\s*["\']?([a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;:\'",.<>?]{6,64})["\']?',
        re.IGNORECASE,
    ),
    # Generic secret patterns
    SecretType.SECRET: re.compile(
        r'(?:secret|token|auth|credential)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,64})["\']?',
        re.IGNORECASE,
    ),
    # Database URL with credentials
    SecretType.DATABASE_URL: re.compile(
        r"(?:mysql|postgres|postgresql|mongodb|redis)://[^:]+:[^@]+@", re.IGNORECASE
    ),
    # Bearer Token
    SecretType.Bearer_TOKEN: re.compile(
        r"(?:Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE
    ),
    # SSH Private Key
    SecretType.SSH_KEY: re.compile(
        r"-----BEGIN OPENSSH PRIVATE KEY-----", re.MULTILINE
    ),
}

# Paths to exclude from scanning
EXCLUDE_PATHS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".sisyphus",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
]

# File extensions to scan
SCAN_EXTENSIONS = [
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".sh",
    ".bash",
    ".zsh",
    ".md",
    ".txt",
    ".properties",
    ".xml",
]


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class SecretMatch:
    """Represents a detected secret."""

    secret_type: SecretType
    pattern: str
    line_number: int
    line_content: str
    context_before: str = ""
    context_after: str = ""


@dataclass
class ScanResult:
    """Result of secret scanning."""

    blocked: bool
    secrets: list[SecretMatch] = field(default_factory=list)
    sanitized_content: str = ""
    scan_time_ms: float = 0.0
    file_scanned: Optional[str] = None

    @property
    def has_secrets(self) -> bool:
        """Check if any secrets were found."""
        return len(self.secrets) > 0

    def summary(self) -> str:
        """Get human-readable summary."""
        if not self.has_secrets:
            return "No secrets detected"

        types = [s.secret_type.value for s in self.secrets]
        unique_types = list(set(types))
        return (
            f"Blocked: {len(self.secrets)} secret(s) found ({', '.join(unique_types)})"
        )


# =============================================================================
# Scanner Implementation
# =============================================================================


class SecretScanner:
    """Scans content for secrets before LLM context capture.

    Usage:
        scanner = SecretScanner()
        result = scanner.scan("your code here")

        if result.blocked:
            print(f"Secrets found: {result.secrets}")
            print(f"Sanitized: {result.sanitized_content[:100]}...")
    """

    def __init__(
        self,
        enabled: bool = True,
        strict: bool = False,
    ):
        """Initialize SecretScanner.

        Args:
            enabled: Whether scanning is enabled
            strict: If True, block on any secret. If False, only block on high-confidence
        """
        self.enabled = enabled
        self.strict = strict

        # High-confidence secrets (block in non-strict mode)
        self._high_confidence = {
            SecretType.AWS_KEY,
            SecretType.AWS_SECRET,
            SecretType.GITHUB_TOKEN,
            SecretType.OPENAI_KEY,
            SecretType.ANTHROPIC_KEY,
            SecretType.JWT_TOKEN,
            SecretType.PRIVATE_KEY,
            SecretType.SSH_KEY,
            SecretType.DATABASE_URL,
        }

    def scan(self, content: str) -> ScanResult:
        """Scan content for secrets.

        Args:
            content: Content to scan

        Returns:
            ScanResult with findings and sanitized content
        """
        import time

        start_time = time.time()

        if not self.enabled:
            return ScanResult(
                blocked=False,
                sanitized_content=content,
                scan_time_ms=0.0,
            )

        secrets: list[SecretMatch] = []

        # Split into lines for context
        lines = content.split("\n")

        for secret_type, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(content):
                # Get line number
                line_num = content[: match.start()].count("\n") + 1

                # Get line content
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""

                # Get context (2 lines before and after)
                context_before = lines[line_num - 3] if line_num > 2 else ""
                context_after = lines[line_num] if line_num < len(lines) else ""

                secret_match = SecretMatch(
                    secret_type=secret_type,
                    pattern=pattern.pattern,
                    line_number=line_num,
                    line_content=line_content.strip()[:100],  # Truncate for safety
                    context_before=context_before.strip()[:50],
                    context_after=context_after.strip()[:50],
                )
                secrets.append(secret_match)

        # Determine if blocked
        blocked = False
        if secrets:
            if self.strict:
                blocked = True
            else:
                # Only block on high-confidence secrets
                blocked = any(s.secret_type in self._high_confidence for s in secrets)

        # Generate sanitized content
        sanitized = self._sanitize(content, secrets)

        scan_time = (time.time() - start_time) * 1000

        return ScanResult(
            blocked=blocked,
            secrets=secrets,
            sanitized_content=sanitized,
            scan_time_ms=scan_time,
        )

    def scan_file(self, file_path: str) -> ScanResult:
        """Scan a file for secrets.

        Args:
            file_path: Path to file

        Returns:
            ScanResult
        """
        # Check if file should be scanned
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SCAN_EXTENSIONS:
            return ScanResult(
                blocked=False,
                sanitized_content="",
                file_scanned=file_path,
            )

        # Check excluded paths
        for exclude in EXCLUDE_PATHS:
            if exclude in file_path:
                return ScanResult(
                    blocked=False,
                    sanitized_content="",
                    file_scanned=file_path,
                )

        # Read and scan
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return ScanResult(
                blocked=False,
                sanitized_content="",
                file_scanned=file_path,
            )

        result = self.scan(content)
        result.file_scanned = file_path
        return result

    def _sanitize(self, content: str, secrets: list[SecretMatch]) -> str:
        """Sanitize content by redacting secrets.

        Args:
            content: Original content
            secrets: List of detected secrets

        Returns:
            Sanitized content
        """
        if not secrets:
            return content

        sanitized = content

        for secret in secrets:
            # Redact the secret in the content
            # Use a placeholder based on secret type
            placeholder = f"[{secret.secret_type.value.upper()}_REDACTED]"

            # Replace the specific line content
            if secret.line_content:
                # Find and replace the specific occurrence
                sanitized = sanitized.replace(
                    secret.line_content,
                    f"# {placeholder} # {secret.line_content[:50]}...",
                )

        return sanitized


# =============================================================================
# Pre-Capture Hook Integration
# =============================================================================


# Default scanner instance
_default_scanner: Optional[SecretScanner] = None


def get_scanner() -> SecretScanner:
    """Get default scanner instance."""
    global _default_scanner
    if _default_scanner is None:
        _default_scanner = SecretScanner()
    return _default_scanner


def scan_content(content: str) -> ScanResult:
    """Scan content for secrets.

    Args:
        content: Content to scan

    Returns:
        ScanResult
    """
    scanner = get_scanner()
    return scanner.scan(content)


def pre_capture_hook(content: str) -> tuple[str, bool]:
    """Pre-capture hook for context loader.

    This function can be registered with PreCaptureHook from agent_trace.

    Args:
        content: Content to scan

    Returns:
        Tuple of (sanitized_content, blocked)
    """
    result = scan_content(content)

    if result.blocked:
        logger.warning(
            f"Context capture blocked: {result.summary()}",
            extra={
                "secret_count": len(result.secrets),
                "secret_types": [s.secret_type.value for s in result.secrets],
            },
        )

    return result.sanitized_content, result.blocked


def register_pre_capture_hook() -> None:
    """Register this scanner as a pre-capture hook with agent_trace."""
    try:
        from packages.orchestration.agent_trace import PreCaptureHook

        PreCaptureHook.register(pre_capture_hook)
        logger.info("SecretScanner registered as pre-capture hook")
    except ImportError as e:
        logger.warning(f"Failed to register pre-capture hook: {e}")


# =============================================================================
# CLI for Testing
# =============================================================================


def main():
    """CLI for testing the scanner."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Secret Scanner")
    parser.add_argument("file", nargs="?", help="File to scan")
    parser.add_argument("--strict", action="store_true", help="Block on any secret")
    parser.add_argument("--content", type=str, help="Content to scan")

    args = parser.parse_args()

    # Create scanner
    scanner = SecretScanner(strict=args.strict)

    if args.file:
        result = scanner.scan_file(args.file)
        print(f"File: {result.file_scanned}")
        print(f"Blocked: {result.blocked}")
        print(f"Secrets: {len(result.secrets)}")
        for secret in result.secrets:
            print(f"  - {secret.secret_type.value} at line {secret.line_number}")
    elif args.content:
        result = scanner.scan(args.content)
        print(f"Blocked: {result.blocked}")
        print(f"Secrets: {len(result.secrets)}")
    else:
        print("Usage: secret_scanner.py <file> [--strict] or --content <text>")
        sys.exit(1)


if __name__ == "__main__":
    main()

__all__ = [
    "SecretScanner",
    "SecretType",
    "SecretMatch",
    "ScanResult",
    "scan_content",
    "pre_capture_hook",
    "register_pre_capture_hook",
    "get_scanner",
]
