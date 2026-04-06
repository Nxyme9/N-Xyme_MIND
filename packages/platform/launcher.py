#!/usr/bin/env python3
"""
launcher.py — Unified launcher for N-Xyme MIND workspace.

Replaces bin/n-xyme-mind.sh with a Python-based session lifecycle manager.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime, timezone


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


def load_memory_context() -> dict:
    """Load memory context and return stats."""
    project_root = get_project_root()
    sys.path.insert(0, str(project_root))
    
    try:
        from packages.memory_core.mcp_server import get_memory_stats
        stats = get_memory_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def save_session_summary() -> dict:
    """Save session summary to state file."""
    project_root = get_project_root()
    state_path = project_root / ".sisyphus" / "session-state.json"
    
    try:
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
        else:
            state = {}
        
        state["last_updated"] = datetime.now(timezone.utc).isoformat()
        state["last_action"] = "Session completed"
        
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def start_opencode(args: list[str] = None) -> int:
    """Start OpenCode with optional arguments."""
    try:
        result = subprocess.run(
            ["opencode"] + (args or []),
            cwd=get_project_root()
        )
        return result.returncode
    except FileNotFoundError:
        print("  ⚠️  opencode not found in PATH")
        print("  Trying: pip install opencode")
        return 1


def main():
    """Main launcher entry point."""
    project_root = get_project_root()
    os.chdir(project_root)
    
    print("========================================")
    print("🧠 N-Xyme MIND — AI Coding Workspace")
    print("========================================")
    print()
    
    # Step 1: Load memory context
    print("📖 Loading memory context...")
    mem_result = load_memory_context()
    if mem_result["success"]:
        stats = mem_result["stats"]
        print(f"  Memory sources: {stats.get('total_sources', '?')}")
        for s in stats.get("sources", []):
            status = "✅" if s.get("status") == "healthy" else "⚠️"
            print(f"  {status} {s.get('name', 'unknown')}: {s.get('status', 'unknown')}")
    else:
        print(f"  ⚠️  Memory error: {mem_result.get('error')}")
    
    print()
    
    # Step 2: Check Ollama
    print("🤖 Checking Ollama...")
    if check_ollama():
        print("  ✅ Ollama running")
    else:
        print("  ⚠️  Ollama not running")
    
    print()
    
    # Step 3: Start OpenCode
    print("🚀 Starting OpenCode...")
    opencode_args = sys.argv[1:] if len(sys.argv) > 1 else []
    start_opencode(opencode_args)
    
    # Step 4: Save session summary
    print()
    print("💾 Saving session summary...")
    save_result = save_session_summary()
    if save_result["success"]:
        print("  ✅ Session state updated")
    else:
        print(f"  ⚠️  Session save failed: {save_result.get('error')}")
    
    print()
    print("========================================")
    print("✅ Session ended")
    print("========================================")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
