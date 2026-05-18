#!/usr/bin/env python3
"""NAP Protocol Validator — Ensures protocol changes are safe and consistent."""
import json, os, sys, hashlib
from typing import Dict, List, Any

class NAPValidator:
    """Validate NAP protocol changes."""
    
    def __init__(self, protocol_path: str):
        self.protocol_path = protocol_path
        self.protocol = self._load_protocol()
    
    def _load_protocol(self) -> dict:
        """Load current protocol."""
        if not os.path.exists(self.protocol_path):
            return {}
        with open(self.protocol_path) as f:
            return json.load(f)
    
    def validate_protocol(self, new_protocol: dict) -> Dict[str, Any]:
        """Validate a new protocol version."""
        errors = []
        warnings = []
        
        # 1. Check required fields
        required_fields = ["name", "short_name", "version", "status", "tool_naming"]
        for field in required_fields:
            if field not in new_protocol:
                errors.append(f"Missing required field: {field}")
        
        # 2. Check version format (semver)
        version = new_protocol.get("version", "")
        if not self._is_valid_semver(version):
            errors.append(f"Invalid version format: {version} (expected X.Y.Z)")
        
        # 3. Check tool naming consistency
        tools = new_protocol.get("tool_naming", {}).get("tools", [])
        if not tools:
            errors.append("No tools defined in tool_naming")
        
        # 4. Check for duplicate tools
        if len(tools) != len(set(tools)):
            duplicates = [t for t in tools if tools.count(t) > 1]
            errors.append(f"Duplicate tools: {set(duplicates)}")
        
        # 5. Check naming convention
        for tool in tools:
            if not self._is_valid_tool_name(tool):
                warnings.append(f"Tool name doesn't follow convention: {tool}")
        
        # 6. Check delegation chain structure
        delegation = new_protocol.get("delegation_chain", {})
        if delegation:
            if "spec" not in delegation:
                warnings.append("Delegation chain missing spec")
            if "resolution" not in delegation:
                warnings.append("Delegation chain missing resolution order")
        
        # 7. Check MCP servers
        mcp_servers = new_protocol.get("mcp_servers", {})
        if not mcp_servers:
            warnings.append("No MCP servers defined")
        
        # 8. Check version progression
        old_version = self.protocol.get("version", "0.0.0")
        if not self._is_valid_version_progression(old_version, version):
            errors.append(f"Invalid version progression: {old_version} → {version}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "old_version": old_version,
            "new_version": version
        }
    
    def _is_valid_semver(self, version: str) -> bool:
        """Check if version is valid semver."""
        parts = version.split(".")
        if len(parts) != 3:
            return False
        try:
            return all(int(p) >= 0 for p in parts)
        except ValueError:
            return False
    
    def _is_valid_tool_name(self, name: str) -> bool:
        """Check if tool name follows convention."""
        # Should be lowercase with underscores
        return name.islower() and "_" in name
    
    def _is_valid_version_progression(self, old: str, new: str) -> bool:
        """Check if version progression is valid."""
        old_parts = [int(p) for p in old.split(".")]
        new_parts = [int(p) for p in new.split(".")]
        
        # Major version can only increase
        if new_parts[0] > old_parts[0]:
            return True
        # Minor version can increase if major same
        if new_parts[0] == old_parts[0] and new_parts[1] > old_parts[1]:
            return True
        # Patch version can increase if major/minor same
        if new_parts[0] == old_parts[0] and new_parts[1] == old_parts[1] and new_parts[2] > old_parts[2]:
            return True
        
        return False
    
    def compute_hash(self, protocol: dict = None) -> str:
        """Compute hash of protocol for integrity checking."""
        if protocol is None:
            protocol = self.protocol
        return hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    
    def generate_migration_script(self, old_protocol: dict, new_protocol: dict) -> str:
        """Generate migration script between protocol versions."""
        changes = []
        
        # Compare tool lists
        old_tools = set(old_protocol.get("tool_naming", {}).get("tools", []))
        new_tools = set(new_protocol.get("tool_naming", {}).get("tools", []))
        
        added = new_tools - old_tools
        removed = old_tools - new_tools
        
        if added:
            changes.append(f"# Added tools: {', '.join(added)}")
        if removed:
            changes.append(f"# Removed tools: {', '.join(removed)}")
        
        # Compare MCP servers
        old_servers = set(old_protocol.get("mcp_servers", {}).keys())
        new_servers = set(new_protocol.get("mcp_servers", {}).keys())
        
        added_servers = new_servers - old_servers
        removed_servers = old_servers - new_servers
        
        if added_servers:
            changes.append(f"# Added MCP servers: {', '.join(added_servers)}")
        if removed_servers:
            changes.append(f"# Removed MCP servers: {', '.join(removed_servers)}")
        
        return "\n".join(changes) if changes else "# No changes detected"

if __name__ == "__main__":
    protocol_path = "services/mcp-core/nap-protocol.json"
    validator = NAPValidator(protocol_path)
    
    if len(sys.argv) > 1:
        # Validate new protocol from file
        new_path = sys.argv[1]
        with open(new_path) as f:
            new_protocol = json.load(f)
        
        result = validator.validate_protocol(new_protocol)
        print(json.dumps(result, indent=2))
        
        if result["valid"]:
            print("\n✅ Protocol is valid")
            sys.exit(0)
        else:
            print("\n❌ Protocol has errors")
            sys.exit(1)
    else:
        # Validate current protocol
        result = validator.validate_protocol(validator.protocol)
        print(json.dumps(result, indent=2))
