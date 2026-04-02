#!/usr/bin/env python3
"""
Echo Delegation Module
Routes voice commands to OpenCode sessions via session_diff files.
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

SESSION_DIR = Path("C:/Users/N-Xyme/.local/share/opencode/storage/session_diff")

# Import centralized Graphiti configuration
try:
    from jarvis.config.graphiti_config import (
        GRAPHITI_RPC_URL as GRAPHITI_URL,
        TOOLBRIDGE_HEALTH_URL,
    )
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")
    TOOLBRIDGE_HEALTH_URL = os.getenv("TOOLBRIDGE_HEALTH_URL", "http://localhost:3100/health")

# ─── NEVER-DO LIST (Hard Block) ─────────────────────────────────────────────
NEVER_DO = [
    r"\bformat\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bdel\s+[a-z]:\\",
    r"\brmdir\s+/s\b",
    r"\brm\s+-rf\b",
    r"\bregedit\b",
    r"\breg\s+(add|delete|query)\b",
    r"\bnet\s+user\b",
    r"\bnet\s+localgroup\b",
    r"\bschtasks\b",
    r"\bwmic\b",
    r"\bC:\\Windows\b",
    r"\bC:\\Program Files\b",
    r"\b\.git\b.*\bdelete\b",
    r"\bforce\s+push\b",
    r"\bbanking\b",
    r"\bemail\b.*\bsend\b",
    r"\bsocial\s+media\b.*\bpost\b",
]

# ─── REQUIRE CONFIRMATION (Soft Block) ──────────────────────────────────────
REQUIRE_CONFIRM = [
    r"\bgit push\b",
    r"\bgit commit\b",
    r"\bpush to github\b",
    r"\bcommit\b",
    r"\bdelete\b",
    r"\brm\b",
    r"\bremove\b",
    r"\binstall\b",
    r"\bnpm\b",
    r"\bpip\b",
    r"\bdocker\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bchmod\b",
    r"\bsudo\b",
    r"\bopen\b.*\bbrowser\b",
    r"\bnavigate\b",
    r"\bclick\b",
    r"\brun\b",
    r"\bexecute\b",
]


class DelegationRouter:
    def __init__(self):
        self.active_sessions = self._scan_sessions()

    def _scan_sessions(self) -> Dict[str, dict]:
        """Scan for active OpenCode sessions."""
        sessions = {}
        if not SESSION_DIR.exists():
            return sessions

        for f in SESSION_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text("utf-8"))
                session_id = f.stem
                messages = data.get("messages", [])
                last_msg = messages[-1] if messages else {}

                sessions[session_id] = {
                    "id": session_id,
                    "file": str(f),
                    "message_count": len(messages),
                    "last_role": last_msg.get("role", "?"),
                    "last_content": last_msg.get("content", "")[:100],
                    "modified": os.path.getmtime(f),
                }
            except Exception as e:
                logging.error(f"Error scanning session diff: {e}")
                continue

        return sessions

    def is_never_do(self, text: str) -> bool:
        """Check if action is on NEVER-DO list."""
        return any(re.search(p, text, re.IGNORECASE) for p in NEVER_DO)

    def requires_confirm(self, text: str) -> bool:
        """Check if action requires confirmation."""
        return any(re.search(p, text, re.IGNORECASE) for p in REQUIRE_CONFIRM)

    def find_target_session(self, target: str) -> Optional[str]:
        """Find session matching target name."""
        target_lower = target.lower()

        # Direct ID match
        for sid in self.active_sessions:
            if target_lower in sid.lower():
                return sid

        # Content match (look for sessions discussing the target)
        for sid, info in self.active_sessions.items():
            if target_lower in info.get("last_content", "").lower():
                return sid

        # Most recent session
        if self.active_sessions:
            most_recent = max(self.active_sessions.values(), key=lambda x: x["modified"])
            return most_recent["id"]

        return None

    def inject_message(self, session_id: str, message: str) -> dict:
        """Inject a message into a session file."""
        session_file = SESSION_DIR / f"{session_id}.json"

        if not session_file.exists():
            return {"success": False, "error": f"Session {session_id} not found"}

        try:
            data = json.loads(session_file.read_text("utf-8"))
            messages = data.get("messages", [])

            # Add user message
            messages.append(
                {
                    "role": "user",
                    "content": f"[Echo Delegation] {message}",
                    "timestamp": datetime.now().isoformat(),
                    "source": "echo-voice",
                }
            )

            data["messages"] = messages
            session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

            return {"success": True, "session_id": session_id, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def route(self, text: str) -> dict:
        """
        Route voice command to appropriate action.
        Returns: {action, target, command, safety_level}
        """
        # 1. Check NEVER-DO
        if self.is_never_do(text):
            return {
                "action": "blocked",
                "reason": "This action is on the NEVER-DO list.",
                "safety": "blocked",
            }

        # 2. Parse delegation patterns
        patterns = [
            (r"tell (?:the )?(\w+) (?:chat|session|agent) to (.+)", "inject"),
            (r"ask (\w+) about (.+)", "query"),
            (r"check if (.+) is (?:running|working|up)", "check"),
            (r"what(?:'s| is) the (.+) (?:status|state)", "status"),
            (r"open (.+)", "navigate"),
            (r"go to (.+)", "navigate"),
            (r"search for (.+)", "search"),
            (r"push to github", "git_push"),
            (r"commit (.+)", "git_commit"),
            (r"delete (.+)", "delete"),
            (r"remove (.+)", "delete"),
            (r"install (.+)", "install"),
            (r"run (.+)", "run_command"),
        ]

        for pattern, action_type in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                target = match.group(1) if (match.lastindex or 0) >= 1 else ""
                command = match.group(2) if (match.lastindex or 0) >= 2 else ""

                # Check if requires confirmation
                safety = "allowed"
                if self.requires_confirm(text):
                    safety = "confirm"

                return {
                    "action": action_type,
                    "target": target,
                    "command": command,
                    "safety": safety,
                    "full_text": text,
                }

        # 3. No pattern matched - just conversation
        return {"action": "conversation", "safety": "allowed", "full_text": text}

    def execute(self, routing: dict) -> dict:
        """Execute a routed action."""
        action = routing.get("action")

        if action == "inject":
            session_id = self.find_target_session(routing["target"])
            if session_id:
                result = self.inject_message(session_id, routing["command"])
                return result
            else:
                return {
                    "success": False,
                    "error": f"No session found for '{routing['target']}'",
                }

        elif action == "check":
            # Check if service is running
            import subprocess

            try:
                result = subprocess.run(
                    ["curl", "-s", TOOLBRIDGE_HEALTH_URL],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return {
                    "success": True,
                    "status": "running" if result.returncode == 0 else "down",
                }
            except Exception as e:
                return {"success": True, "status": "unknown"}

        elif action == "status":
            return {
                "success": True,
                "sessions": len(self.active_sessions),
                "active": list(self.active_sessions.keys())[:5],
            }

        else:
            return {"success": False, "error": f"Unknown action: {action}"}


# ─── TEST ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    router = DelegationRouter()

    test_commands = [
        "Tell the coding chat to fix the bug",
        "Ask Prometheus about Rosetta Stone",
        "Check if ToolBridge is running",
        "What's the session status",
        "Push to GitHub",
        "Delete node_modules",
        "Format the hard drive",
        "Open GitHub",
    ]

    print("=" * 50)
    print("  ECHO DELEGATION TEST")
    print("=" * 50)

    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        routing = router.route(cmd)
        print(f"  Action: {routing['action']}")
        print(f"  Safety: {routing['safety']}")
        if routing.get("target"):
            print(f"  Target: {routing['target']}")
        if routing.get("command"):
            print(f"  Command: {routing['command']}")
