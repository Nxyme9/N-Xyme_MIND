"""Tests for permission system."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.orchestration.permissions import (
    PermissionChecker,
    PermissionBehavior,
    create_default_deny_rules,
    create_tool_permission_rules,
)


class TestPermissionChecker:
    """Tests for PermissionChecker."""

    def test_add_and_check_rule(self):
        """Basic rule matching."""
        checker = PermissionChecker()
        checker.add_rule("*.env", PermissionBehavior.DENY, "Env files denied")

        result = checker.check(".env")
        assert result["behavior"] == "deny"

    def test_no_matching_rule(self):
        """No match returns allow."""
        checker = PermissionChecker()
        result = checker.check("some_file.txt")
        assert result["behavior"] == "allow"

    def test_wildcard_star(self):
        """* matches within directory."""
        checker = PermissionChecker()
        checker.add_rule("src/*.ts", PermissionBehavior.ALLOW, "TS files")

        assert checker.check("src/main.ts")["behavior"] == "allow"
        assert (
            checker.check("src/deep/main.ts")["behavior"] == "allow"
        )  # ** matches across dirs

    def test_double_star(self):
        """** matches across directories."""
        checker = PermissionChecker()
        checker.add_rule("src/**/*.ts", PermissionBehavior.ALLOW, "All TS")

        assert checker.check("src/main.ts")["behavior"] == "allow"
        assert checker.check("src/deep/nested/file.ts")["behavior"] == "allow"

    def test_get_matching_rules(self):
        """Get all matching rules."""
        checker = PermissionChecker()
        checker.add_rule("*.env", PermissionBehavior.DENY, "Env denied")
        checker.add_rule("*", PermissionBehavior.ALLOW, "All allowed")

        rules = checker.get_matching_rules(".env")
        assert len(rules) >= 1

    def test_clear_rules(self):
        """Clear all rules."""
        checker = PermissionChecker()
        checker.add_rule("*", PermissionBehavior.DENY)
        checker.clear()

        result = checker.check("anything")
        assert result["behavior"] == "allow"

    def test_default_deny_rules(self):
        """Pre-built deny rules work."""
        checker = create_default_deny_rules()

        assert checker.check("sudo rm -rf /")["behavior"] == "deny"
        assert checker.check("test.env")["behavior"] == "deny"

    def test_tool_permission_rules(self):
        """Tool-specific rules work."""
        checker = create_tool_permission_rules("file_read")
        assert checker.check("any_file.txt")["behavior"] == "allow"

        checker = create_tool_permission_rules("Bash")
        assert checker.check("git status")["behavior"] == "allow"
