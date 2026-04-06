"""Cross-Session Context Sharing

Shares context across sessions so agents don't start fresh each time.
Persists important context in SQLite and retrieves it on session start.
"""

import json
import time
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger("context-sharing")


class ContextSharing:
    """Manages cross-session context sharing."""
    
    def __init__(self, db_path: str = ".sisyphus/context.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic commit/close."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS session_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    context_type TEXT NOT NULL,
                    context_key TEXT NOT NULL,
                    context_value TEXT,
                    priority INTEGER DEFAULT 0,
                    created_at REAL,
                    expires_at REAL,
                    metadata TEXT
                );
                
                CREATE TABLE IF NOT EXISTS session_summary (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT,
                    key_decisions TEXT,
                    active_tasks TEXT,
                    created_at REAL,
                    updated_at REAL
                );
                
                CREATE INDEX IF NOT EXISTS idx_context_session ON session_context(session_id);
                CREATE INDEX IF NOT EXISTS idx_context_type ON session_context(context_type);
                CREATE INDEX IF NOT EXISTS idx_context_key ON session_context(context_key);
            """)
    
    def save_context(self, session_id: str, context_type: str, context_key: str,
                    context_value: str, priority: int = 0, ttl: float = 86400,
                    metadata: Dict[str, Any] = None):
        """Save context for a session."""
        now = time.time()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO session_context (session_id, context_type, context_key, 
                                          context_value, priority, created_at, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, context_type, context_key, context_value,
                priority, now, now + ttl, json.dumps(metadata or {})
            ))
    
    def get_context(self, session_id: str = None, context_type: str = None,
                   context_key: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get context, optionally filtered."""
        now = time.time()
        
        query = """
            SELECT * FROM session_context 
            WHERE expires_at > ?
        """
        params = [now]
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        if context_type:
            query += " AND context_type = ?"
            params.append(context_type)
        
        if context_key:
            query += " AND context_key = ?"
            params.append(context_key)
        
        query += " ORDER BY priority DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    
    def save_session_summary(self, session_id: str, summary: str,
                           key_decisions: List[str] = None,
                           active_tasks: List[str] = None):
        """Save a session summary."""
        now = time.time()
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO session_summary 
                (session_id, summary, key_decisions, active_tasks, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id, summary,
                json.dumps(key_decisions or []),
                json.dumps(active_tasks or []),
                now, now
            ))
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary for a session."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM session_summary WHERE session_id = ?
            """, (session_id,)).fetchone()
            
            if row:
                data = dict(row)
                data['key_decisions'] = json.loads(data.get('key_decisions', '[]'))
                data['active_tasks'] = json.loads(data.get('active_tasks', '[]'))
                return data
            return None
    
    def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent session summaries."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM session_summary 
                ORDER BY updated_at DESC LIMIT ?
            """, (limit,)).fetchall()
            
            sessions = []
            for row in rows:
                data = dict(row)
                data['key_decisions'] = json.loads(data.get('key_decisions', '[]'))
                data['active_tasks'] = json.loads(data.get('active_tasks', '[]'))
                sessions.append(data)
            
            return sessions
    
    def get_shared_context(self) -> Dict[str, Any]:
        """Get context shared across all sessions."""
        contexts = self.get_context(context_type="shared")
        
        shared = {
            'global_knowledge': {},
            'best_practices': [],
            'common_patterns': [],
            'system_config': {}
        }
        
        for ctx in contexts:
            key = ctx['context_key']
            try:
                value = json.loads(ctx['context_value'])
            except (json.JSONDecodeError, KeyError):
                value = ctx['context_value']
            
            if key.startswith('global.'):
                shared['global_knowledge'][key[7:]] = value
            elif key.startswith('practice.'):
                shared['best_practices'].append(value)
            elif key.startswith('pattern.'):
                shared['common_patterns'].append(value)
            elif key.startswith('config.'):
                shared['system_config'][key[7:]] = value
        
        return shared
    
    def cleanup_expired(self) -> int:
        """Clean up expired context."""
        now = time.time()
        with self.get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM session_context WHERE expires_at <= ?
            """, (now,))
            deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired context entries")
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context sharing statistics."""
        with self.get_connection() as conn:
            total_context = conn.execute("SELECT COUNT(*) FROM session_context").fetchone()[0]
            total_sessions = conn.execute("SELECT COUNT(*) FROM session_summary").fetchone()[0]
            active_context = conn.execute(
                "SELECT COUNT(*) FROM session_context WHERE expires_at > ?",
                (time.time(),)
            ).fetchone()[0]
            
            return {
                'total_context_entries': total_context,
                'active_context_entries': active_context,
                'total_sessions': total_sessions,
                'expired_entries': total_context - active_context
            }


# Global context sharing instance
_context_sharing = None

def get_context_sharing() -> ContextSharing:
    """Get or create the global context sharing system."""
    global _context_sharing
    if _context_sharing is None:
        _context_sharing = ContextSharing()
    return _context_sharing
