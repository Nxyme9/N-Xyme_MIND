#!/usr/bin/env python3
"""
Database Management for Orchestrator
SQLite-based storage for VPN history, API keys, and instance stats
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

DATABASE_PATH = "/home/nxyme/projects/modelrouter/data/orchestrator.db"

class OrchestratorDB:
    """Database manager for orchestrator"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        
    @contextmanager
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # VPN History
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vpn_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    country TEXT,
                    connection_name TEXT,
                    ip_address TEXT,
                    socks_port INTEGER,
                    connected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    disconnected_at DATETIME,
                    rotation_reason TEXT,
                    bytes_transferred INTEGER DEFAULT 0
                )
            """)
            
            # API Keys
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    key_hash TEXT NOT NULL,
                    key_prefix TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME,
                    request_count INTEGER DEFAULT 0,
                    token_count INTEGER DEFAULT 0,
                    quota_limit INTEGER,
                    is_active INTEGER DEFAULT 1,
                    notes TEXT
                )
            """)
            
            # Instance Stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS instance_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    instance_name TEXT,
                    vpn_country TEXT,
                    socks_port INTEGER,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_heartbeat DATETIME,
                    requests_handled INTEGER DEFAULT 0,
                    tokens_generated INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    uptime_seconds INTEGER DEFAULT 0,
                    is_online INTEGER DEFAULT 1
                )
            """)
            
            # Model Stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    provider TEXT,
                    request_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    avg_latency_ms REAL,
                    last_used DATETIME,
                    is_healthy INTEGER DEFAULT 1,
                    UNIQUE(model_name, provider)
                )
            """)
            
            # Orchestration Sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orchestration_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    mode TEXT,
                    status TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    total_tokens INTEGER DEFAULT 0,
                    total_requests INTEGER DEFAULT 0
                )
            """)
            
            # Token Aggregation Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS token_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    source_id TEXT,
                    content_hash TEXT,
                    token_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vpn_session ON vpn_history(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_keys_provider ON api_keys(provider)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_instance_id ON instance_stats(instance_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_name ON model_stats(model_name)")
            
    # VPN Operations
    def log_vpn_connection(self, session_id: str, country: str, connection_name: str, 
                           ip_address: str, socks_port: int):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO vpn_history (session_id, country, connection_name, ip_address, socks_port)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, country, connection_name, ip_address, socks_port))
    
    def log_vpn_disconnection(self, session_id: str, rotation_reason: str = None):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE vpn_history 
                SET disconnected_at = CURRENT_TIMESTAMP, rotation_reason = ?
                WHERE session_id = ? AND disconnected_at IS NULL
            """, (rotation_reason, session_id))
    
    def get_vpn_history(self, limit: int = 100) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM vpn_history ORDER BY connected_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # API Key Operations
    def add_api_key(self, provider: str, key_hash: str, key_prefix: str, 
                    quota_limit: int = None, notes: str = None):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO api_keys (provider, key_hash, key_prefix, quota_limit, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (provider, key_hash, key_prefix, quota_limit, notes))
            return cursor.lastrowid
    
    def update_key_usage(self, key_id: int, tokens: int = 0):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE api_keys 
                SET request_count = request_count + 1,
                    token_count = token_count + ?,
                    last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (tokens, key_id))
    
    def get_active_keys(self, provider: str = None) -> List[Dict]:
        with self._get_connection() as conn:
            if provider:
                cursor = conn.execute("""
                    SELECT * FROM api_keys WHERE provider = ? AND is_active = 1
                """, (provider,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM api_keys WHERE is_active = 1
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    # Instance Operations
    def register_instance(self, instance_id: str, instance_name: str, 
                         vpn_country: str, socks_port: int):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO instance_stats (instance_id, instance_name, vpn_country, socks_port)
                VALUES (?, ?, ?, ?)
            """, (instance_id, instance_name, vpn_country, socks_port))
    
    def update_instance_stats(self, instance_id: str, tokens: int = 0, error: bool = False):
        with self._get_connection() as conn:
            if error:
                conn.execute("""
                    UPDATE instance_stats 
                    SET errors = errors + 1, last_heartbeat = CURRENT_TIMESTAMP
                    WHERE instance_id = ?
                """, (instance_id,))
            else:
                conn.execute("""
                    UPDATE instance_stats 
                    SET requests_handled = requests_handled + 1,
                        tokens_generated = tokens_generated + ?,
                        last_heartbeat = CURRENT_TIMESTAMP
                    WHERE instance_id = ?
                """, (tokens, instance_id))
    
    def get_instance_stats(self, instance_id: str = None) -> List[Dict]:
        with self._get_connection() as conn:
            if instance_id:
                cursor = conn.execute("""
                    SELECT * FROM instance_stats WHERE instance_id = ?
                """, (instance_id,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM instance_stats WHERE is_online = 1
                """)
            return [dict(row) for row in cursor.fetchall()]
    
    # Model Operations
    def record_model_request(self, model_name: str, provider: str, 
                           tokens: int = 0, latency_ms: float = None,
                           success: bool = True):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO model_stats (model_name, provider, request_count, success_count, 
                                        failure_count, total_tokens, avg_latency_ms, last_used)
                VALUES (?, ?, 1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(model_name, provider) DO UPDATE SET
                    request_count = request_count + 1,
                    success_count = success_count + ?,
                    failure_count = failure_count + ?,
                    total_tokens = total_tokens + ?,
                    avg_latency_ms = COALESCE(?, avg_latency_ms),
                    last_used = CURRENT_TIMESTAMP
            """, (model_name, provider, 
                  1 if success else 0, 0 if success else 1, tokens,
                  latency_ms if latency_ms else None,
                  1 if success else 0, 0 if success else 1, tokens,
                  latency_ms))
    
    def get_healthy_models(self) -> List[Dict]:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM model_stats 
                WHERE is_healthy = 1 
                ORDER BY (success_count * 1.0 / request_count) DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    # Session Operations
    def create_session(self, session_id: str, mode: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO orchestration_sessions (session_id, mode, status)
                VALUES (?, ?, 'running')
            """, (session_id, mode))
    
    def complete_session(self, session_id: str, total_tokens: int, total_requests: int):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE orchestration_sessions 
                SET status = 'complete', 
                    completed_at = CURRENT_TIMESTAMP,
                    total_tokens = ?,
                    total_requests = ?
                WHERE session_id = ?
            """, (total_tokens, total_requests, session_id))
    
    # Token Log
    def log_token(self, session_id: str, source_id: str, content: str, token_count: int):
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO token_log (session_id, source_id, content_hash, token_count)
                VALUES (?, ?, ?, ?)
            """, (session_id, source_id, content_hash, token_count))
    
    # Analytics
    def get_analytics(self) -> Dict:
        with self._get_connection() as conn:
            # Total VPN rotations
            cursor = conn.execute("SELECT COUNT(*) as count FROM vpn_history")
            vpn_rotations = cursor.fetchone()["count"]
            
            # Active keys
            cursor = conn.execute("SELECT COUNT(*) as count FROM api_keys WHERE is_active = 1")
            active_keys = cursor.fetchone()["count"]
            
            # Online instances
            cursor = conn.execute("SELECT COUNT(*) as count FROM instance_stats WHERE is_online = 1")
            online_instances = cursor.fetchone()["count"]
            
            # Total tokens generated
            cursor = conn.execute("SELECT SUM(tokens_generated) as total FROM instance_stats")
            total_tokens = cursor.fetchone()["total"] or 0
            
            return {
                "vpn_rotations": vpn_rotations,
                "active_api_keys": active_keys,
                "online_instances": online_instances,
                "total_tokens_generated": total_tokens
            }


# Singleton
_db = None

def get_db() -> OrchestratorDB:
    global _db
    if _db is None:
        _db = OrchestratorDB()
    return _db


if __name__ == "__main__":
    db = get_db()
    print("📊 Analytics:", json.dumps(db.get_analytics(), indent=2, default=str))
    print("\n🔑 API Keys:", json.dumps(db.get_active_keys(), indent=2, default=str))
    print("\n🖥️ Instances:", json.dumps(db.get_instance_stats(), indent=2, default=str))
