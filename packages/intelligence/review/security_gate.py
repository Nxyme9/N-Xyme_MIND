"""Gate 8: Security-Sensitive Path Detection.

Enhanced with pattern-based validation from production-grade patterns.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Optional


BLOCK_KEYWORDS = [
    "auth",
    "crypto",
    "encrypt",
    "decrypt",
    "password",
    "secret",
    "credential",
    "payment",
    "billing",
    "private.key",
]

WARN_KEYWORDS = [
    "ssl",
    "tls",
    "jwt",
    "oauth",
    "token",
    "api.key",
    "certificate",
]

# Command substitution patterns (from ant-source-code bashSecurity.ts)
COMMAND_SUBSTITUTION_PATTERNS = [
    re.compile(r"\$\(.*\)"),  # $(command)
    re.compile(r"`[^`]+`"),  # `command`
    re.compile(r"\$\{[^}]+\}"),  # ${variable}
]

# Shell injection patterns
INJECTION_PATTERNS = [
    re.compile(r";\s*(rm|curl|wget|chmod|chown|sudo)"),
    re.compile(r"\|\s*(rm|curl|wget|chmod|chown|sudo)"),
    re.compile(r"&&\s*(rm|curl|wget|chmod|chown|sudo)"),
    re.compile(r"\$\(.*rm\s"),
    re.compile(r"`.*rm\s"),
]

# Dangerous commands (from ant-source-code)
DANGEROUS_COMMANDS = [
    re.compile(r"\brm\s+-rf\s+/"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r"\beval\b"),
    re.compile(r"\bexec\b"),
    re.compile(r"\bsource\s+/dev/"),
]


def _build_pattern(keyword: str) -> re.Pattern:
    """Build a word-boundary regex pattern for a keyword."""
    escaped = re.escape(keyword)
    return re.compile(rf"\b{escaped}\b", re.IGNORECASE)


def check_security(task: str) -> tuple[bool, str]:
    """Check if task touches security-sensitive files or keywords.

    Args:
        task: Task description to check.

    Returns:
        Tuple of (passed, message).
        passed=True means no security risk detected.
        passed=False means Oracle review is required.
    """
    if not task:
        return True, "Gate 8: Empty task - PASS (no security risk)"

    # Check block keywords
    for keyword in BLOCK_KEYWORDS:
        pattern = _build_pattern(keyword)
        if pattern.search(task):
            return False, (
                f"Gate 8: BLOCK - Security-sensitive keyword detected: '{keyword}'\n"
                f"   → Requires Oracle review regardless of complexity level"
            )

    # Check warn keywords
    for keyword in WARN_KEYWORDS:
        pattern = _build_pattern(keyword)
        if pattern.search(task):
            return True, (
                f"Gate 8: WARN - Security-related keyword detected: '{keyword}'\n"
                f"   → Logged for awareness, no Oracle review required"
            )

    # Check command substitution patterns
    for pattern in COMMAND_SUBSTITUTION_PATTERNS:
        if pattern.search(task):
            return True, (
                f"Gate 8: WARN - Command substitution detected\n"
                f"   → Logged for awareness"
            )

    # Check injection patterns
    for pattern in INJECTION_PATTERNS:
        if pattern.search(task):
            return False, (
                f"Gate 8: BLOCK - Potential shell injection detected\n"
                f"   → Requires Oracle review"
            )

    # Check dangerous commands
    for pattern in DANGEROUS_COMMANDS:
        if pattern.search(task):
            return False, (
                f"Gate 8: BLOCK - Dangerous command detected\n"
                f"   → Requires Oracle review"
            )

    return True, "Gate 8: No security-sensitive paths detected"


def check_permission(tool_name: str, content: str = "") -> tuple[str, Optional[str]]:
    """Check permission for a tool execution using the permission engine."""
    try:
        from packages.intelligence.permission_engine import get_permission_engine

        engine = get_permission_engine()
        return engine.check_permission("global", tool_name, content)
    except Exception:
        return "allow", "Permission engine not available"


class SecurityGate:
    @staticmethod
    def check(task: str) -> tuple[bool, str]:
        return check_security(task)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Security-sensitive path detection gate"
    )
    parser.add_argument("task", nargs="?", default="", help="Task description")
    args = parser.parse_args()

    passed, message = check_security(args.task)
    print(message)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
