"""Routing data provider for N-Xyme MIND Dashboard.

This module provides access to the routing system data stored in routing.db.
"""

import json
from pathlib import Path
from typing import Any

import sqlite3


class RoutingDataProvider:
    """Provides routing system data for the dashboard.
    
    Accesses .sisyphus/routing.db to retrieve and manage routing data including
    triggers, agent weights, and routing statistics.
    """
    
    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize the routing data provider.
        
        Args:
            db_path: Path to routing.db. Defaults to .sisyphus/routing.db.
        """
        if db_path is None:
            base_path = Path(__file__).parent.parent.parent
            db_path = base_path / ".sisyphus" / "routing.db"
        
        self._db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection | None:
        """Get database connection.
        
        Returns:
            SQLite connection or None if DB doesn't exist.
        """
        if not self._db_path.exists():
            return None
        return sqlite3.connect(self._db_path)
    
    def get_triggers(self) -> list[dict[str, Any]]:
        """Get all registered triggers.
        
        Returns:
            List of trigger dictionaries with keys: name, pattern, level, agent, priority.
        """
        conn = self._get_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.execute(
                "SELECT name, pattern, level, agent, priority FROM triggers ORDER BY priority DESC"
            )
            rows = cursor.fetchall()
            return [
                {
                    "name": row[0],
                    "pattern": row[1],
                    "level": row[2],
                    "agent": row[3],
                    "priority": row[4],
                }
                for row in rows
            ]
        finally:
            conn.close()
    
    def get_weights(self) -> dict[str, dict[str, Any]]:
        """Get agent weights from the database.
        
        Returns:
            Dictionary mapping agent names to their weight data.
        """
        conn = self._get_connection()
        if conn is None:
            return {}
        
        try:
            cursor = conn.execute("SELECT * FROM agent_weights")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            return {
                row[0]: dict(zip(columns[1:], row[1:]))
                for row in rows
            }
        finally:
            conn.close()
    
    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics.
        
        Returns:
            Dictionary with total_routes, successful_routes, failed_routes, and other stats.
        """
        conn = self._get_connection()
        if conn is None:
            return {
                "total_routes": 0,
                "successful_routes": 0,
                "failed_routes": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
            }
        
        try:
            # Get outcome statistics
            cursor = conn.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    AVG(CASE WHEN success = 1 THEN latency_ms ELSE NULL END) as avg_latency
                FROM outcomes
                """
            )
            row = cursor.fetchone()
            
            total = row[0] or 0
            successful = row[1] or 0
            failed = row[2] or 0
            success_rate = (successful / total * 100) if total > 0 else 0.0
            
            return {
                "total_routes": total,
                "successful_routes": successful,
                "failed_routes": failed,
                "success_rate": round(success_rate, 2),
                "avg_latency_ms": round(row[3] or 0.0, 2),
            }
        finally:
            conn.close()
    
    def add_trigger(self, phrase: str, handler: str, level: int = 1, priority: int = 5) -> bool:
        """Add a new trigger to the routing system.
        
        Args:
            phrase: Trigger phrase or pattern.
            handler: Handler/agent to route to.
            level: Routing level (1-5).
            priority: Trigger priority.
        
        Returns:
            True if successful, False otherwise.
        """
        conn = self._get_connection()
        if conn is None:
            return False
        
        try:
            conn.execute(
                "INSERT OR REPLACE INTO triggers (name, pattern, level, agent, priority) VALUES (?, ?, ?, ?, ?)",
                (phrase, phrase, level, handler, priority)
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def remove_trigger(self, phrase: str) -> bool:
        """Remove a trigger from the routing system.
        
        Args:
            phrase: Trigger name/pattern to remove.
        
        Returns:
            True if successful, False otherwise.
        """
        conn = self._get_connection()
        if conn is None:
            return False
        
        try:
            cursor = conn.execute("DELETE FROM triggers WHERE name = ?", (phrase,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def get_agents(self) -> list[dict[str, Any]]:
        """Get agent configurations from weights table.
        
        Returns:
            List of agent configuration dictionaries.
        """
        conn = self._get_connection()
        if conn is None:
            return [
                {"name": "sisyphus-junior", "level": 1, "description": "Trivial fixes"},
                {"name": "hephaestus", "level": 2, "description": "Implementation"},
                {"name": "explore", "level": 3, "description": "Codebase search"},
                {"name": "oracle", "level": 4, "description": "Architecture review"},
                {"name": "metis", "level": 5, "description": "Pre-planning"},
            ]
        
        try:
            cursor = conn.execute("SELECT * FROM agent_weights")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            return [
                dict(zip(columns, row))
                for row in rows
            ]
        finally:
            conn.close()


# Module-level convenience instance
_provider: RoutingDataProvider | None = None


def get_routing_provider() -> RoutingDataProvider:
    """Get the global routing data provider instance.
    
    Returns:
        RoutingDataProvider instance.
    """
    global _provider
    if _provider is None:
        _provider = RoutingDataProvider()
    return _provider
