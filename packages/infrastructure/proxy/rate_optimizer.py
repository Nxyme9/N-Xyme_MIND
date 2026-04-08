"""
Rate Optimizer - Learns optimal RPM per tuple via feedback with AIMD control loop.

Features:
- SQLite persistence for learned rates
- AIMD control loop with cooldown
- Tracks success/rate_limit events per tuple
"""

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class RateOptimizer:
    """
    Learns optimal RPM per (provider, model, vpn_ip, api_key) tuple using AIMD.
    
    Uses SQLite for persistence and applies AIMD control loop with cooldown
    to prevent oscillation between rate limits.
    """
    
    def __init__(
        self,
        db_path: str = "data/proxy/rate_optimizer.db",
        default_rpm: float = 10.0,
        max_rpm: float = 50.0,
        min_rpm: float = 1.0,
        increase_delta: float = 1.0,
        decrease_multiplier: float = 0.5,
        cooldown_seconds: float = 30.0,
        success_threshold: int = 10  # N consecutive successes before increasing
    ):
        self.default_rpm = default_rpm
        self.max_rpm = max_rpm
        self.min_rpm = min_rpm
        self.increase_delta = increase_delta
        self.decrease_multiplier = decrease_multiplier
        self.cooldown_seconds = cooldown_seconds
        self.success_threshold = success_threshold
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                vpn_ip TEXT,
                api_key TEXT,
                rpm REAL NOT NULL DEFAULT 10.0,
                success_count INTEGER DEFAULT 0,
                rate_limit_count INTEGER DEFAULT 0,
                consecutive_successes INTEGER DEFAULT 0,
                last_updated REAL NOT NULL,
                created_at REAL NOT NULL,
                UNIQUE(provider, model, vpn_ip, api_key)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tuple
            ON rate_learnings(provider, model, vpn_ip, api_key)
        """)
        
        conn.commit()
        conn.close()
    
    def _make_key(self, provider: str, model: str, vpn_ip: str, api_key: str) -> str:
        """Create unique key for tuple."""
        return f"{provider}:{model}:{vpn_ip or ''}:{api_key or ''}"
    
    def _get_or_create(
        self,
        provider: str,
        model: str,
        vpn_ip: str,
        api_key: str
    ) -> Dict:
        """Get existing record or create new one."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try to get existing
        cursor.execute("""
            SELECT rpm, success_count, rate_limit_count, consecutive_successes, last_updated
            FROM rate_learnings
            WHERE provider = ? AND model = ? AND vpn_ip = ? AND api_key = ?
        """, (provider, model, vpn_ip or "", api_key or ""))
        
        row = cursor.fetchone()
        
        if row is None:
            # Create new record
            now = time.time()
            cursor.execute("""
                INSERT INTO rate_learnings
                (provider, model, vpn_ip, api_key, rpm, success_count, rate_limit_count,
                 consecutive_successes, last_updated, created_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
            """, (provider, model, vpn_ip or "", api_key or "", self.default_rpm, now, now))
            conn.commit()
            
            conn.close()
            return {
                "rpm": self.default_rpm,
                "success_count": 0,
                "rate_limit_count": 0,
                "consecutive_successes": 0,
                "last_updated": now
            }
        
        conn.close()
        return {
            "rpm": row[0],
            "success_count": row[1],
            "rate_limit_count": row[2],
            "consecutive_successes": row[3],
            "last_updated": row[4]
        }
    
    def _update_record(
        self,
        provider: str,
        model: str,
        vpn_ip: str,
        api_key: str,
        data: Dict
    ):
        """Update record in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE rate_learnings
            SET rpm = ?,
                success_count = ?,
                rate_limit_count = ?,
                consecutive_successes = ?,
                last_updated = ?
            WHERE provider = ? AND model = ? AND vpn_ip = ? AND api_key = ?
        """, (
            data["rpm"],
            data["success_count"],
            data["rate_limit_count"],
            data["consecutive_successes"],
            data["last_updated"],
            provider, model, vpn_ip or "", api_key or ""
        ))
        
        conn.commit()
        conn.close()
    
    def get_optimal_rpm(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ) -> float:
        """Get the learned optimal RPM for a tuple."""
        with self._lock:
            record = self._get_or_create(provider, model, vpn_ip, api_key)
            return record["rpm"]
    
    def record_success(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ):
        """Record successful request - increase RPM if threshold reached."""
        with self._lock:
            record = self._get_or_create(provider, model, vpn_ip, api_key)
            
            # Check cooldown
            if time.time() - record["last_updated"] < self.cooldown_seconds:
                return
            
            # Increment consecutive successes
            record["consecutive_successes"] += 1
            record["success_count"] += 1
            
            # Increase RPM if threshold reached
            if record["consecutive_successes"] >= self.success_threshold:
                new_rpm = min(self.max_rpm, record["rpm"] + self.increase_delta)
                record["rpm"] = new_rpm
                record["consecutive_successes"] = 0  # Reset after increase
            
            record["last_updated"] = time.time()
            self._update_record(provider, model, vpn_ip, api_key, record)
    
    def record_rate_limit(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ):
        """Record 429 response - decrease RPM immediately."""
        with self._lock:
            record = self._get_or_create(provider, model, vpn_ip, api_key)
            
            # Multiplicative decrease
            new_rpm = max(self.min_rpm, record["rpm"] * self.decrease_multiplier)
            record["rpm"] = new_rpm
            
            # Reset consecutive successes
            record["consecutive_successes"] = 0
            record["rate_limit_count"] += 1
            record["last_updated"] = time.time()
            
            self._update_record(provider, model, vpn_ip, api_key, record)
            
            logger.info(
                f"Rate limit detected for {provider}/{model}: "
                f"RPM {record['rpm'] + self.increase_delta:.1f} -> {new_rpm:.1f}"
            )
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get all learned rates and statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT provider, model, vpn_ip, api_key, rpm, success_count,
                   rate_limit_count, consecutive_successes, last_updated
            FROM rate_learnings
            ORDER BY last_updated DESC
        """)
        
        results = {}
        for row in cursor.fetchall():
            key = f"{row[0]}/{row[1]}"
            results[key] = {
                "provider": row[0],
                "model": row[1],
                "vpn_ip": row[2],
                "api_key_id": row[3][:20] + "..." if row[3] and len(row[3]) > 20 else (row[3] or ""),
                "rpm": row[4],
                "success_count": row[5],
                "rate_limit_count": row[6],
                "consecutive_successes": row[7],
                "last_updated": row[8]
            }
        
        conn.close()
        return results
    
    def get_total_stats(self) -> Dict:
        """Get aggregate statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                COUNT(*) as total_tuples,
                SUM(success_count) as total_successes,
                SUM(rate_limit_count) as total_rate_limits,
                AVG(rpm) as avg_rpm
            FROM rate_learnings
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_tuples": row[0] or 0,
            "total_successes": row[1] or 0,
            "total_rate_limits": row[2] or 0,
            "average_rpm": row[3] or self.default_rpm
        }
    
    def clear_learnings(self, provider: Optional[str] = None, model: Optional[str] = None):
        """Clear learned rates (optionally filtered by provider/model)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if provider and model:
            cursor.execute("""
                DELETE FROM rate_learnings
                WHERE provider = ? AND model = ?
            """, (provider, model))
        elif provider:
            cursor.execute("""
                DELETE FROM rate_learnings
                WHERE provider = ?
            """, (provider,))
        else:
            cursor.execute("DELETE FROM rate_learnings")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleared rate learnings: provider={provider}, model={model}")