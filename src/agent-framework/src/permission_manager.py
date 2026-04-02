import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import re


class PermissionManager:
    """Manage granular permissions with roles and rules."""

    def __init__(self, permissions_file: str):
        self.permissions_file = Path(permissions_file)
        if not self.permissions_file.exists():
            raise FileNotFoundError(f"Permissions file not found: {permissions_file}")

        with open(self.permissions_file, "r") as f:
            self.data = json.load(f)

        self.roles = self.data.get("roles", {})
        self.rules = self.data.get("rules", [])
        self.defaults = self.data.get("defaults", {})

    def check_permission(self, role: str, permission: str) -> bool:
        """Check if a role has a specific permission."""
        if role not in self.roles:
            return False

        role_data = self.roles[role]
        allowed = role_data.get("permissions", [])
        denied = role_data.get("deny", [])

        # Check deny list first
        if permission in denied:
            return False

        # Check allow list
        return permission in allowed

    def get_role_permissions(self, role: str) -> List[str]:
        """Get all permissions for a role."""
        if role not in self.roles:
            return []
        return self.roles[role].get("permissions", [])

    def evaluate_rule(self, command: str, role: str) -> str:
        """Evaluate command against rules, returning allow/deny/prompt."""
        for rule in self.rules:
            pattern = rule.get("pattern")
            action = rule.get("action")
            rule_role = rule.get("role", "user")

            # If rule has a specific role and it doesn't match, skip
            if rule_role != "any" and rule_role != role:
                continue

            if pattern and re.match(pattern, command):
                return action

        # Default action from defaults
        return self.defaults.get("action", "prompt")

    def get_default_role(self) -> str:
        return self.defaults.get("role", "user")

    def get_cache_ttl(self) -> int:
        return self.defaults.get("timeout", 300)

    def __repr__(self):
        return f"<PermissionManager roles={len(self.roles)} rules={len(self.rules)}>"
