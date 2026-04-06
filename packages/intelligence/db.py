"""SQLite Persistence Store (Optimized)

Replaces JSON/JSONL files with SQLite for better scalability, queries, and transactions.
Optimized with:
- WAL mode for better concurrent read/write performance
- Batch writes for reduced disk I/O
- Async write queue for non-blocking operations
"""

import sqlite3
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager
from collections import deque

logger = logging.getLogger("sqlite-store")


class SQLiteStore:
    """SQLite-based persistence store for routing data."""
    
    def __init__(self, db_path: str = ".sisyphus/routing.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_queue: deque = deque()
        self._batch_size: int = 50
        self._flush_interval: float = 1.0  # seconds
        self._last_flush: float = time.time()
        self._init_db()
        self._start_flush_task()
    
    def _start_flush_task(self):
        """Start background flush task."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._periodic_flush())
        except RuntimeError:
            pass  # No event loop running yet
    
    async def _periodic_flush(self):
        """Periodically flush write queue."""
        while True:
            await asyncio.sleep(self._flush_interval)
            if self._write_queue:
                await self.flush_writes()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic commit/close."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema with WAL mode."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    task_description TEXT,
                    level INTEGER,
                    agent TEXT,
                    success BOOLEAN,
                    latency_ms REAL,
                    tokens_used INTEGER,
                    timestamp REAL
                );
                
                CREATE TABLE IF NOT EXISTS agent_weights (
                    agent TEXT PRIMARY KEY,
                    success_rate REAL DEFAULT 0.5,
                    avg_latency_ms REAL DEFAULT 0.0,
                    total_tasks INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    by_level TEXT DEFAULT '{}',
                    last_updated REAL
                );
                
                CREATE TABLE IF NOT EXISTS triggers (
                    name TEXT PRIMARY KEY,
                    pattern TEXT NOT NULL,
                    level INTEGER,
                    agent TEXT,
                    priority INTEGER
                );
                
                CREATE INDEX IF NOT EXISTS idx_outcomes_task_id ON outcomes(task_id);
                CREATE INDEX IF NOT EXISTS idx_outcomes_agent ON outcomes(agent);
                CREATE INDEX IF NOT EXISTS idx_outcomes_timestamp ON outcomes(timestamp);
            """)
    
    def migrate_from_json(self):
        """Migrate existing JSON/JSONL data to SQLite."""
        # Migrate outcomes
        outcomes_file = Path('.sisyphus/outcomes.jsonl')
        if outcomes_file.exists():
            with open(outcomes_file) as f:
                outcomes = [json.loads(line) for line in f if line.strip()]
            
            with self.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
                if count == 0:
                    conn.executemany("""
                        INSERT INTO outcomes (task_id, task_description, level, agent, success, latency_ms, tokens_used, timestamp)
                        VALUES (:task_id, :task_description, :level, :agent, :success, :latency_ms, :tokens_used, :timestamp)
                    """, outcomes)
                    logger.info(f"Migrated {len(outcomes)} outcomes to SQLite")
        
        # Migrate weights
        weights_file = Path('.sisyphus/routing-weights.json')
        if weights_file.exists():
            with open(weights_file) as f:
                weights = json.load(f)
            
            with self.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM agent_weights").fetchone()[0]
                if count == 0:
                    for agent, data in weights.items():
                        conn.execute("""
                            INSERT INTO agent_weights (agent, success_rate, avg_latency_ms, total_tasks, success_count, failure_count, by_level, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            agent,
                            data.get('success_rate', 0.5),
                            data.get('avg_latency_ms', 0.0),
                            data.get('total_tasks', 0),
                            data.get('success_count', 0),
                            data.get('failure_count', 0),
                            json.dumps(data.get('by_level', {})),
                            time.time()
                        ))
                    logger.info(f"Migrated {len(weights)} agent weights to SQLite")
        
        # Migrate triggers
        triggers_file = Path('.sisyphus/routing-triggers.json')
        if triggers_file.exists():
            with open(triggers_file) as f:
                config = json.load(f)
            triggers = config.get('routing_triggers', [])
            
            with self.get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0]
                if count == 0:
                    conn.executemany("""
                        INSERT INTO triggers (name, pattern, level, agent, priority)
                        VALUES (:name, :pattern, :level, :agent, :priority)
                    """, triggers)
                    logger.info(f"Migrated {len(triggers)} triggers to SQLite")
    
    # Optimized write methods
    def queue_outcome(self, task_id: str, task_description: str, level: int, agent: str, success: bool, latency_ms: float = 0, tokens_used: int = 0):
        """Queue an outcome for batch write."""
        self._write_queue.append({
            'type': 'outcome',
            'data': {
                'task_id': task_id,
                'task_description': task_description,
                'level': level,
                'agent': agent,
                'success': success,
                'latency_ms': latency_ms,
                'tokens_used': tokens_used,
                'timestamp': time.time()
            }
        })
        
        # Flush if batch size reached
        if len(self._write_queue) >= self._batch_size:
            asyncio.create_task(self.flush_writes()) if asyncio.get_event_loop().is_running() else self.flush_writes_sync()
    
    def queue_agent_weight_update(self, agent: str, success: bool, latency_ms: float = 0, level: int = 0):
        """Queue an agent weight update for batch write."""
        self._write_queue.append({
            'type': 'weight_update',
            'data': {
                'agent': agent,
                'success': success,
                'latency_ms': latency_ms,
                'level': level
            }
        })
        
        if len(self._write_queue) >= self._batch_size:
            asyncio.create_task(self.flush_writes()) if asyncio.get_event_loop().is_running() else self.flush_writes_sync()
    
    async def flush_writes(self):
        """Flush all queued writes to database."""
        if not self._write_queue:
            return
        
        items = list(self._write_queue)
        self._write_queue.clear()
        
        outcomes = [item['data'] for item in items if item['type'] == 'outcome']
        weight_updates = [item['data'] for item in items if item['type'] == 'weight_update']
        
        with self.get_connection() as conn:
            # Batch insert outcomes
            if outcomes:
                conn.executemany("""
                    INSERT INTO outcomes (task_id, task_description, level, agent, success, latency_ms, tokens_used, timestamp)
                    VALUES (:task_id, :task_description, :level, :agent, :success, :latency_ms, :tokens_used, :timestamp)
                """, outcomes)
            
            # Batch update weights
            for update in weight_updates:
                self._update_agent_weight_sync(conn, **update)
        
        self._last_flush = time.time()
        logger.debug(f"Flushed {len(outcomes)} outcomes and {len(weight_updates)} weight updates")
    
    def flush_writes_sync(self):
        """Synchronous version of flush_writes."""
        if not self._write_queue:
            return
        
        items = list(self._write_queue)
        self._write_queue.clear()
        
        outcomes = [item['data'] for item in items if item['type'] == 'outcome']
        weight_updates = [item['data'] for item in items if item['type'] == 'weight_update']
        
        with self.get_connection() as conn:
            if outcomes:
                conn.executemany("""
                    INSERT INTO outcomes (task_id, task_description, level, agent, success, latency_ms, tokens_used, timestamp)
                    VALUES (:task_id, :task_description, :level, :agent, :success, :latency_ms, :tokens_used, :timestamp)
                """, outcomes)
            
            for update in weight_updates:
                self._update_agent_weight_sync(conn, **update)
        
        self._last_flush = time.time()
    
    def _update_agent_weight_sync(self, conn, agent: str, success: bool, latency_ms: float = 0, level: int = 0):
        """Update agent weights synchronously within a connection."""
        row = conn.execute("SELECT * FROM agent_weights WHERE agent = ?", (agent,)).fetchone()
        
        if row:
            total_tasks = row['total_tasks'] + 1
            success_count = row['success_count'] + (1 if success else 0)
            failure_count = row['failure_count'] + (0 if success else 1)
            success_rate = success_count / total_tasks if total_tasks > 0 else 0.5
            
            alpha = 0.1
            current_latency = row['avg_latency_ms']
            new_latency = alpha * latency_ms + (1 - alpha) * current_latency if current_latency > 0 else latency_ms
            
            by_level = json.loads(row['by_level']) if row['by_level'] else {}
            if level > 0:
                level_key = str(level)
                if level_key not in by_level:
                    by_level[level_key] = {'success_rate': 0.5, 'avg_latency_ms': 0.0}
                level_data = by_level[level_key]
                level_success = level_data.get('success_rate', 0.5)
                level_latency = level_data.get('avg_latency_ms', 0.0)
                level_data['success_rate'] = 0.1 * (1.0 if success else 0.0) + 0.9 * level_success
                level_data['avg_latency_ms'] = 0.1 * latency_ms + 0.9 * level_latency
                by_level[level_key] = level_data
            
            conn.execute("""
                UPDATE agent_weights
                SET success_rate = ?, avg_latency_ms = ?, total_tasks = ?, success_count = ?, failure_count = ?, by_level = ?, last_updated = ?
                WHERE agent = ?
            """, (success_rate, new_latency, total_tasks, success_count, failure_count, json.dumps(by_level), time.time(), agent))
        else:
            by_level = {}
            if level > 0:
                by_level[str(level)] = {'success_rate': 1.0 if success else 0.0, 'avg_latency_ms': latency_ms}
            
            conn.execute("""
                INSERT INTO agent_weights (agent, success_rate, avg_latency_ms, total_tasks, success_count, failure_count, by_level, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent,
                1.0 if success else 0.0,
                latency_ms,
                1,
                1 if success else 0,
                0 if success else 1,
                json.dumps(by_level),
                time.time()
            ))
    
    # Original methods (now use queueing)
    def add_outcome(self, task_id: str, task_description: str, level: int, agent: str, success: bool, latency_ms: float = 0, tokens_used: int = 0):
        """Add a delegation outcome (queued for batch write)."""
        self.queue_outcome(task_id, task_description, level, agent, success, latency_ms, tokens_used)
    
    def get_outcomes(self, limit: int = 100, agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent outcomes."""
        # Flush pending writes first
        if self._write_queue:
            self.flush_writes_sync()
        
        with self.get_connection() as conn:
            if agent:
                rows = conn.execute("""
                    SELECT * FROM outcomes WHERE agent = ? ORDER BY timestamp DESC LIMIT ?
                """, (agent, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM outcomes ORDER BY timestamp DESC LIMIT ?
                """, (limit,)).fetchall()
            return [dict(row) for row in rows]
    
    def get_outcome_stats(self) -> Dict[str, Any]:
        """Get outcome statistics."""
        if self._write_queue:
            self.flush_writes_sync()
        
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                       AVG(latency_ms) as avg_latency
                FROM outcomes
            """).fetchone()
            return {
                'total': row['total'],
                'success_count': row['success_count'],
                'success_rate': row['success_count'] / row['total'] if row['total'] > 0 else 0,
                'avg_latency': row['avg_latency'] or 0
            }
    
    def update_agent_weight(self, agent: str, success: bool, latency_ms: float = 0, level: int = 0):
        """Update agent weights after a delegation (queued for batch write)."""
        self.queue_agent_weight_update(agent, success, latency_ms, level)
    
    def get_agent_weights(self) -> Dict[str, Dict[str, Any]]:
        """Get all agent weights."""
        if self._write_queue:
            self.flush_writes_sync()
        
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM agent_weights ORDER BY success_rate DESC, total_tasks DESC").fetchall()
            result = {}
            for row in rows:
                data = dict(row)
                data['by_level'] = json.loads(data['by_level']) if data['by_level'] else {}
                result[data['agent']] = data
            return result
    
    def get_triggers(self) -> List[Dict[str, Any]]:
        """Get all triggers."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM triggers ORDER BY priority DESC").fetchall()
            return [dict(row) for row in rows]
    
    def add_trigger(self, name: str, pattern: str, level: int, agent: str, priority: int):
        """Add or update a trigger."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO triggers (name, pattern, level, agent, priority)
                VALUES (?, ?, ?, ?, ?)
            """, (name, pattern, level, agent, priority))


# Global store instance
_store = None

def get_store() -> SQLiteStore:
    """Get or create the global SQLite store."""
    global _store
    if _store is None:
        _store = SQLiteStore()
        _store.migrate_from_json()
    return _store
