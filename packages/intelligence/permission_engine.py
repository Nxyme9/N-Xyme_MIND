"""Permission Rule Engine — Typed permission rules with source tracking.

Adapted from ant-source-code permissions.ts pattern.
Provides granular tool-level permissions with rule source tracking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PermissionRule:
    """A single permission rule with source tracking.

    Attributes:
        source: Where the rule came from (user, project, session, cli)
        behavior: What to do (allow, deny, ask)
        tool_pattern: Regex pattern for tool names
        content_pattern: Optional regex pattern for content matching
        description: Human-readable description
    """

    source: str  # "user", "project", "session", "cli"
    behavior: str  # "allow", "deny", "ask"
    tool_pattern: str
    content_pattern: Optional[str] = None
    description: str = ""

    def matches(self, tool_name: str, content: str = "") -> bool:
        """Check if this rule matches the given tool and content.

        Args:
            tool_name: Tool name to check
            content: Optional content to check

        Returns:
            True if rule matches
        """
        tool_match = bool(re.search(self.tool_pattern, tool_name, re.IGNORECASE))
        if not tool_match:
            return False
        if self.content_pattern:
            return bool(re.search(self.content_pattern, content, re.IGNORECASE))
        return True


@dataclass
class ToolPermissionContext:
    """Permission context for tool execution.

    Attributes:
        mode: Permission mode (default, uphill, downhill, bypass)
        always_allow_rules: Rules that always allow
        always_deny_rules: Rules that always deny
        always_ask_rules: Rules that always ask
        denial_count: Number of denials for fallback tracking
    """

    mode: str = "default"
    always_allow_rules: list[PermissionRule] = field(default_factory=list)
    always_deny_rules: list[PermissionRule] = field(default_factory=list)
    always_ask_rules: list[PermissionRule] = field(default_factory=list)
    denial_count: int = 0

    def check_permission(
        self, tool_name: str, content: str = ""
    ) -> tuple[str, Optional[str]]:
        """Check permission for a tool execution.

        Args:
            tool_name: Tool name
            content: Optional content

        Returns:
            Tuple of (behavior, reason)
            behavior: "allow", "deny", "ask"
            reason: Optional reason string
        """
        # Check deny rules first (most restrictive)
        for rule in self.always_deny_rules:
            if rule.matches(tool_name, content):
                self.denial_count += 1
                return (
                    "deny",
                    f"Denied by {rule.source} rule: {rule.description or rule.tool_pattern}",
                )

        # Check ask rules
        for rule in self.always_ask_rules:
            if rule.matches(tool_name, content):
                return (
                    "ask",
                    f"Ask required by {rule.source} rule: {rule.description or rule.tool_pattern}",
                )

        # Check allow rules
        for rule in self.always_allow_rules:
            if rule.matches(tool_name, content):
                return (
                    "allow",
                    f"Allowed by {rule.source} rule: {rule.description or rule.tool_pattern}",
                )

        # Default behavior based on mode
        if self.mode == "bypass":
            return "allow", "Bypass mode"
        elif self.mode == "downhill":
            return "allow", "Downhill mode (read-only allowed)"
        elif self.mode == "uphill":
            return "ask", "Uphill mode (requires confirmation)"
        else:
            return "ask", "Default mode (requires confirmation)"

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a permission rule.

        Args:
            rule: Permission rule to add
        """
        if rule.behavior == "allow":
            self.always_allow_rules.append(rule)
        elif rule.behavior == "deny":
            self.always_deny_rules.append(rule)
        elif rule.behavior == "ask":
            self.always_ask_rules.append(rule)

    def get_stats(self) -> dict:
        """Get permission context statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "mode": self.mode,
            "allow_rules": len(self.always_allow_rules),
            "deny_rules": len(self.always_deny_rules),
            "ask_rules": len(self.always_ask_rules),
            "denial_count": self.denial_count,
        }


class PermissionEngine:
    """Engine for managing permission contexts and rules."""

    def __init__(self):
        self._contexts: dict[str, ToolPermissionContext] = {}

    def get_context(self, context_id: str) -> ToolPermissionContext:
        """Get or create a permission context.

        Args:
            context_id: Context ID

        Returns:
            Permission context
        """
        if context_id not in self._contexts:
            self._contexts[context_id] = ToolPermissionContext()
        return self._contexts[context_id]

    def check_permission(
        self, context_id: str, tool_name: str, content: str = ""
    ) -> tuple[str, Optional[str]]:
        """Check permission for a tool execution.

        Args:
            context_id: Context ID
            tool_name: Tool name
            content: Optional content

        Returns:
            Tuple of (behavior, reason)
        """
        context = self.get_context(context_id)
        return context.check_permission(tool_name, content)

    def add_rule(self, context_id: str, rule: PermissionRule) -> None:
        """Add a permission rule to a context.

        Args:
            context_id: Context ID
            rule: Permission rule to add
        """
        context = self.get_context(context_id)
        context.add_rule(rule)

    def get_stats(self, context_id: str) -> dict:
        """Get permission context statistics.

        Args:
            context_id: Context ID

        Returns:
            Statistics dictionary
        """
        context = self.get_context(context_id)
        return context.get_stats()


# Global engine
_engine = PermissionEngine()


def get_permission_engine() -> PermissionEngine:
    """Get the global permission engine.

    Returns:
        Global permission engine instance
    """
    return _engine
