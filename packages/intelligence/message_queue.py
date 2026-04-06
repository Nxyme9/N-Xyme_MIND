"""Message Queue for Agent Communication

Provides a persistent message queue for inter-agent communication.
Supports request/response and pub/sub patterns.
"""

import sqlite3
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger("message-queue")


class MessageQueue:
    """SQLite-based message queue for agent communication."""
    
    def __init__(self, db_path: str = ".sisyphus/messages.db"):
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
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT,
                    type TEXT NOT NULL,
                    subject TEXT,
                    content TEXT,
                    priority INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    created_at REAL,
                    updated_at REAL,
                    response_to TEXT,
                    metadata TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_messages_to_agent ON messages(to_agent, status);
                CREATE INDEX IF NOT EXISTS idx_messages_from_agent ON messages(from_agent);
                CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
                CREATE INDEX IF NOT EXISTS idx_messages_response_to ON messages(response_to);
            """)
    
    def send_message(self, from_agent: str, to_agent: str, subject: str, content: str, 
                     message_type: str = "direct", priority: int = 0, 
                     response_to: str = None, metadata: Dict[str, Any] = None) -> str:
        """Send a message to an agent."""
        message_id = str(uuid.uuid4())
        now = time.time()
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO messages (id, from_agent, to_agent, type, subject, content, 
                                     priority, status, created_at, updated_at, response_to, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """, (
                message_id, from_agent, to_agent, message_type, subject, content,
                priority, now, now, response_to, json.dumps(metadata or {})
            ))
        
        logger.debug(f"Message sent: {message_id} from {from_agent} to {to_agent}")
        return message_id
    
    def get_messages(self, to_agent: str, status: str = "pending", limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for an agent."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM messages 
                WHERE to_agent = ? AND status = ?
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            """, (to_agent, status, limit)).fetchall()
            
            return [dict(row) for row in rows]
    
    def mark_read(self, message_id: str):
        """Mark a message as read."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE messages SET status = 'read', updated_at = ? WHERE id = ?
            """, (time.time(), message_id))
    
    def mark_processed(self, message_id: str):
        """Mark a message as processed."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE messages SET status = 'processed', updated_at = ? WHERE id = ?
            """, (time.time(), message_id))
    
    def send_response(self, from_agent: str, response_to: str, content: str, 
                      subject: str = None, metadata: Dict[str, Any] = None) -> str:
        """Send a response to a message."""
        return self.send_message(
            from_agent=from_agent,
            to_agent=None,  # Response doesn't need specific recipient
            subject=subject or f"Re: {response_to}",
            content=content,
            message_type="response",
            response_to=response_to,
            metadata=metadata
        )
    
    def get_conversation(self, message_id: str) -> List[Dict[str, Any]]:
        """Get full conversation thread for a message."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM messages 
                WHERE id = ? OR response_to = ?
                ORDER BY created_at ASC
            """, (message_id, message_id)).fetchall()
            
            return [dict(row) for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get message queue statistics."""
        with self.get_connection() as conn:
            stats = {}
            
            # Total messages
            stats['total'] = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            
            # Messages by status
            status_counts = conn.execute("""
                SELECT status, COUNT(*) as count FROM messages GROUP BY status
            """).fetchall()
            stats['by_status'] = {row['status']: row['count'] for row in status_counts}
            
            # Messages by type
            type_counts = conn.execute("""
                SELECT type, COUNT(*) as count FROM messages GROUP BY type
            """).fetchall()
            stats['by_type'] = {row['type']: row['count'] for row in type_counts}
            
            # Recent activity (last hour)
            hour_ago = time.time() - 3600
            stats['recent'] = conn.execute("""
                SELECT COUNT(*) FROM messages WHERE created_at > ?
            """, (hour_ago,)).fetchone()[0]
            
            return stats


# Global message queue instance
_message_queue = None

def get_message_queue() -> MessageQueue:
    """Get or create the global message queue."""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue
