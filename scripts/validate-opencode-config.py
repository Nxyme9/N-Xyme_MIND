#!/usr/bin/env python3
"""
OpenCode Config Validator
Validates opencode.json before any changes
"""

import json
import sys
from pathlib import Path

CONFIG_PATH = Path("C:/Users/N-Xyme/.config/opencode/opencode.json")
BACKUP_PATH = Path("C:/Users/N-Xyme/.config/opencode/opencode.json.backup")


def validate_config():
    """Validate opencode.json configuration"""
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        # Check required fields
        required = ["model", "mcp"]
        missing = [field for field in required if field not in config]
        if missing:
            print(f"ERROR: Missing required fields: {missing}")
            return False

        # Check MCP servers
        mcp = config.get("mcp", {})
        enabled_mcp = [k for k, v in mcp.items() if v.get("enabled", True)]
        print(f"MCP servers enabled: {len(enabled_mcp)}")

        # Check agents
        agents = config.get("agent", {})
        print(f"Agents configured: {len(agents)}")

        # Check plugins
        plugins = config.get("plugin", [])
        print(f"Plugins: {plugins}")

        # Backup current config
        with open(BACKUP_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"Backup saved to: {BACKUP_PATH}")

        print("✅ Config is VALID")
        return True

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)
