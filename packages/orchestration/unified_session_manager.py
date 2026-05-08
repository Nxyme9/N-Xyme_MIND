"""
Unified Session Manager - Single Source of Truth for N-Xyme_MIND

Consolidates:
- Session state from brain_mcp.session
- MIND state from nx_mind_mcp  
- Session pool from session-pool-mcp
- Context injection from fingerprint

SQLite (state.db) is the source of truth. 
All other representations (.json, .md) are generated from DB.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("unified_session_manager")

# ============================================================================
# PATH CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DB = PROJECT_ROOT / ".sisyphus" / "state.db"
SESSION_JSON = PROJECT_ROOT / ".sisyphus" / "session-state.json"
CONTEXT_MD = PROJECT_ROOT / ".context" / "activeContext.md"


class UnifiedSessionManager:
    """Single source of truth for all session/context data.
    
    Design principles:
    - SQLite is the write-through cache
    - JSON/MD files are read-only projections
    - Thread-safe operations
    - Auto-sync on changes
    """
    
    def __init__(self, db_path: Path = STATE_DB):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Ensure tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table - PRIMARY record of sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                last_agent TEXT NOT NULL DEFAULT '',
                last_action TEXT NOT NULL DEFAULT '',
                session_started TEXT NOT NULL DEFAULT '',
                last_updated TEXT NOT NULL DEFAULT '',
                current_task TEXT NOT NULL DEFAULT '',
                pending_changes TEXT NOT NULL DEFAULT '[]',
                completed_changes TEXT NOT NULL DEFAULT '[]',
                context TEXT NOT NULL DEFAULT '{}'
            )
        """)
        
        # Delegations table - task delegation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delegations (
                delegation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                task_description TEXT NOT NULL,
                agent TEXT NOT NULL,
                level INTEGER NOT NULL,
                success INTEGER NOT NULL,
                latency_ms INTEGER NOT NULL,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Agent performance - rolling stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                agent TEXT PRIMARY KEY,
                total_tasks INTEGER NOT NULL DEFAULT 0,
                successful_tasks INTEGER NOT NULL DEFAULT 0,
                avg_latency_ms REAL NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL DEFAULT ''
            )
        """)
        
        # Context injection - stores context state
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT ''
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"UnifiedSessionManager initialized with DB: {self.db_path}")
    
    # ============================================================================
    # SESSION OPERATIONS
    # ============================================================================
    
    def upsert_session(self, session_id: str, **kwargs) -> dict[str, Any]:
        """Create or update a session."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now(timezone.utc).isoformat()
            
            # Get existing to merge
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update - merge changes
                cursor.execute("""
                    UPDATE sessions SET
                        last_agent = COALESCE(?, last_agent),
                        last_action = COALESCE(?, last_action),
                        last_updated = ?,
                        current_task = COALESCE(?, current_task),
                        pending_changes = COALESCE(?, pending_changes),
                        completed_changes = COALESCE(?, completed_changes),
                        context = COALESCE(?, context)
                    WHERE session_id = ?
                """, (
                    kwargs.get('last_agent'),
                    kwargs.get('last_action'),
                    now,
                    kwargs.get('current_task'),
                    kwargs.get('pending_changes'),
                    kwargs.get('completed_changes'),
                    kwargs.get('context'),
                    session_id
                ))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO sessions (
                        session_id, last_agent, last_action, session_started,
                        last_updated, current_task, pending_changes, completed_changes, context
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    kwargs.get('last_agent', 'sisyphus'),
                    kwargs.get('last_action', ''),
                    kwargs.get('session_started', now),
                    now,
                    kwargs.get('current_task', ''),
                    kwargs.get('pending_changes', '[]'),
                    kwargs.get('completed_changes', '[]'),
                    kwargs.get('context', '{}')
                ))
            
            conn.commit()
            conn.close()
            
            # Auto-sync to other representations
            self._sync_to_json()
            self._sync_to_md()
            
            return {"status": "ok", "session_id": session_id}
    
    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get a session by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def list_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent sessions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM sessions 
            ORDER BY last_updated DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_current_session(self) -> dict[str, Any]:
        """Get the most recent session."""
        sessions = self.list_sessions(1)
        if sessions:
            return sessions[0]
        
        # Create a new session if none exists
        session_id = f"session_{int(time.time())}"
        self.upsert_session(session_id, last_agent="sisyphus", current_task="New session")
        return self.get_session(session_id)
    
    # ============================================================================
    # CONTEXT OPERATIONS
    # ============================================================================
    
    def set_context(self, key: str, value: Any) -> dict[str, Any]:
        """Set a context key-value pair."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now(timezone.utc).isoformat()
            value_json = json.dumps(value) if not isinstance(value, str) else value
            
            cursor.execute("""
                INSERT OR REPLACE INTO context_state (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value_json, now))
            
            conn.commit()
            conn.close()
            
            return {"status": "ok", "key": key}
    
    def get_context(self, key: str) -> Any:
        """Get a context value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM context_state WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return None
    
    def get_all_context(self) -> dict[str, Any]:
        """Get all context as dict."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM context_state")
        rows = cursor.fetchall()
        conn.close()
        
        result = {}
        for key, value in rows:
            try:
                result[key] = json.loads(value)
            except:
                result[key] = value
        return result
    
    # ============================================================================
    # DELEGATION TRACKING
    # ============================================================================
    
    def log_delegation(
        self,
        task_description: str,
        agent: str,
        level: int,
        success: bool,
        latency_ms: int,
        tokens_used: int = 0,
    ) -> dict[str, Any]:
        """Log a delegation outcome for learning."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session = self.get_current_session()
            session_id = session.get('session_id', 'unknown') if session else 'unknown'
            delegation_id = f"del_{int(time.time() * 1000)}"
            now = datetime.now(timezone.utc).isoformat()
            
            cursor.execute("""
                INSERT INTO delegations (
                    delegation_id, session_id, task_description, agent, level,
                    success, latency_ms, tokens_used, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                delegation_id, session_id, task_description, agent, level,
                1 if success else 0, latency_ms, tokens_used, now
            ))
            
            # Update agent performance stats
            cursor.execute("""
                INSERT INTO agent_performance (agent, total_tasks, successful_tasks, avg_latency_ms, last_updated)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(agent) DO UPDATE SET
                    total_tasks = total_tasks + 1,
                    successful_tasks = successful_tasks + ?,
                    avg_latency_ms = (avg_latency_ms * total_tasks + ?) / (total_tasks + 1),
                    last_updated = ?
            """, (
                agent,
                1 if success else 0,
                latency_ms,
                now,
                1 if success else 0,
                latency_ms,
                now
            ))
            
            conn.commit()
            conn.close()
            
            return {"status": "ok", "delegation_id": delegation_id}
    
    def get_agent_stats(self, agent: Optional[str] = None) -> list[dict[str, Any]]:
        """Get agent performance stats."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if agent:
            cursor.execute("SELECT * FROM agent_performance WHERE agent = ?", (agent,))
        else:
            cursor.execute("SELECT * FROM agent_performance")
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ============================================================================
    # SYNC OPERATIONS
    # ============================================================================
    
    def _sync_to_json(self):
        """Sync DB to session-state.json for backward compatibility."""
        session = self.get_current_session()
        if session:
            data = {
                "last_agent": session.get("last_agent", ""),
                "last_action": session.get("last_action", ""),
                "session_started": session.get("session_started", ""),
                "last_updated": session.get("last_updated", ""),
                "current_task": session.get("current_task", ""),
                "pending_changes": json.loads(session.get("pending_changes", "[]")),
                "completed_changes": json.loads(session.get("completed_changes", "[]")),
            }
            try:
                SESSION_JSON.write_text(json.dumps(data, indent=2))
            except Exception as e:
                logger.warning(f"Failed to sync to JSON: {e}")
    
    def _sync_to_md(self):
        """Sync DB to activeContext.md for agent context injection."""
        session = self.get_current_session()
        if not session:
            return
        
        agent = session.get("last_agent", "sisyphus")
        task = session.get("current_task", "")
        updated = session.get("last_updated", "")
        
        context = f"""# System Context - Auto-loaded

## Current Session
- **Last Agent**: {agent}
- **Current Task**: {task}
- **Last Updated**: {updated}

## Agent Performance
"""
        # Add agent stats
        stats = self.get_agent_stats()
        for s in stats[:5]:
            context += f"- **{s['agent']}**: {s['total_tasks']} tasks, {s['successful_tasks']} success, {s['avg_latency_ms']:.0f}ms avg\n"
        
        context += """
*Context loaded: " + datetime.now(timezone.utc).isoformat() + "*"
        
        try:
            CONTEXT_MD.write_text(context)
        except Exception as e:
            logger.warning(f"Failed to sync to MD: {e}")
    
    def full_sync(self):
        """Force full sync to all representations."""
        self._sync_to_json()
        self._sync_to_md()
    
    # ============================================================================
    # DIAGNOSTICS
    # ============================================================================
    
    def get_health(self) -> dict[str, Any]:
        """Get system health status."""
        sessions = self.list_sessions(1)
        agent_stats = self.get_agent_stats()
        context = self.get_all_context()
        
        return {
            "db_exists": self.db_path.exists(),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "session_count": len(self.list_sessions(100)),
            "current_session": sessions[0] if sessions else None,
            "agent_count": len(agent_stats),
            "context_keys": list(context.keys()),
            "json_synced": SESSION_JSON.exists(),
            "md_synced": CONTEXT_MD.exists(),
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_manager: Optional[UnifiedSessionManager] = None
_manager_lock = threading.Lock()


def get_session_manager() -> UnifiedSessionManager:
    """Get or create the global session manager."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = UnifiedSessionManager()
    return _manager


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys
    
    mgr = get_session_manager()
    health = mgr.get_health()
    
    print("=== Unified Session Manager Health ===")
    print(json.dumps(health, indent=2))
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for s in mgr.list_sessions(10):
                print(f"  {s['session_id']}: {s['last_agent']} - {s['current_task']}")
        elif cmd == "stats":
            for s in mgr.get_agent_stats():
                print(f"  {s['agent']}: {s['total_tasks']} tasks, {s['avg_latency_ms']:.0f}ms")
        elif cmd == "sync":
            mgr.full_sync()
            print("Full sync complete")