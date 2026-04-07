#!/usr/bin/env python3
"""TriggerSystem — SQLite-based trigger management for N-Xyme MIND.

Ported from CATALYST archive triggers.json (538 lines) with:
- TriggerSystem class with register_trigger, evaluate_triggers, execute_trigger
- TriggerRecord dataclass: id, name, condition, action, priority, enabled, timestamp
- TriggerResult dataclass: success, action, output, error
- SQLite storage at ~/.cache/n-xyme-mind/triggers.db
- Thread-safe with threading.Lock
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

# Default database path
DEFAULT_DB_PATH = "~/.cache/n-xyme-mind/triggers.db"


@dataclass
class TriggerRecord:
    """Record of a registered trigger."""

    id: str
    name: str
    condition: str  # Condition type: "greater_than", "not_equal", etc.
    action: str  # Action name to execute
    priority: int = 0  # Higher priority triggers evaluated first
    enabled: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    # Runtime fields (not persisted)
    last_triggered: float = 0.0
    cooldown_seconds: int = 60
    action_params: dict = field(default_factory=dict)


@dataclass
class TriggerResult:
    """Result of trigger execution."""

    success: bool
    action: str
    output: Any = None
    error: Optional[str] = None


@dataclass
class TriggerAction:
    """Action to be executed from trigger evaluation."""

    trigger: TriggerRecord
    params: dict = field(default_factory=dict)


class TriggerSystem:
    """SQLite-based trigger system with thread-safe operations."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """Initialize TriggerSystem.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.cache/n-xyme-mind/triggers.db
        """
        self.db_path = str(Path(db_path).expanduser())
        self._lock = threading.RLock()
        self._triggers: dict[str, TriggerRecord] = {}
        self._action_registry: dict[str, dict] = {}
        self._cooldowns: dict[str, float] = {}
        self._ensure_db()
        self._load_triggers()

    def _ensure_db(self) -> None:
        """Ensure database and tables exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        # Enable WAL mode for concurrent reads
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                condition TEXT NOT NULL,
                action TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,
                timestamp TEXT NOT NULL,
                cooldown_seconds INTEGER NOT NULL DEFAULT 60,
                action_params TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trigger_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_id TEXT NOT NULL,
                trigger_name TEXT NOT NULL,
                action TEXT NOT NULL,
                success INTEGER NOT NULL,
                output TEXT,
                error TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (trigger_id) REFERENCES triggers(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_triggers_name ON triggers(name)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_triggers_priority ON triggers(priority DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_executions_timestamp ON trigger_executions(timestamp)"
        )
        conn.commit()
        conn.close()

    def _load_triggers(self) -> None:
        """Load triggers from database into memory."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT * FROM triggers").fetchall()
        conn.close()

        for row in rows:
            trigger = TriggerRecord(
                id=row[0],
                name=row[1],
                condition=row[2],
                action=row[3],
                priority=row[4],
                enabled=bool(row[5]),
                timestamp=row[6],
                cooldown_seconds=row[7],
                action_params=self._parse_json(row[8]) if row[8] else {},
            )
            self._triggers[trigger.name] = trigger

    def _parse_json(self, s: str) -> dict:
        """Parse JSON string safely."""
        import json

        try:
            return json.loads(s) if s else {}
        except Exception:
            return {}

    def register_trigger(
        self,
        name: str,
        condition: str,
        action: str,
        priority: int = 0,
        enabled: bool = True,
        cooldown_seconds: int = 60,
        action_params: Optional[dict] = None,
    ) -> TriggerRecord:
        """Register a new trigger.

        Args:
            name: Unique name for the trigger
            condition: Condition type (e.g., "greater_than", "not_equal")
            action: Action name to execute
            priority: Higher priority triggers evaluated first (default 0)
            enabled: Whether trigger is active (default True)
            cooldown_seconds: Cooldown between trigger executions (default 60)
            action_params: Optional parameters for the action

        Returns:
            TriggerRecord: The registered trigger
        """
        with self._lock:
            trigger_id = str(uuid.uuid4())
            trigger = TriggerRecord(
                id=trigger_id,
                name=name,
                condition=condition,
                action=action,
                priority=priority,
                enabled=enabled,
                cooldown_seconds=cooldown_seconds,
                action_params=action_params or {},
            )

            # Persist to database
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT OR REPLACE INTO triggers 
                   (id, name, condition, action, priority, enabled, timestamp, cooldown_seconds, action_params)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    trigger.id,
                    trigger.name,
                    trigger.condition,
                    trigger.action,
                    trigger.priority,
                    1 if trigger.enabled else 0,
                    trigger.timestamp,
                    trigger.cooldown_seconds,
                    str(trigger.action_params) if trigger.action_params else None,
                ),
            )
            conn.commit()
            conn.close()

            # Add to memory
            self._triggers[name] = trigger
            return trigger

    def evaluate_triggers(self, context: dict[str, Any]) -> list[TriggerAction]:
        """Evaluate all enabled triggers against context.

        Args:
            context: Dictionary containing metrics to evaluate (e.g., {"temperature_c": 86})

        Returns:
            List of TriggerAction objects for triggers that matched
        """
        with self._lock:
            current_time = time.time()
            triggered_actions: list[TriggerAction] = []

            # Sort triggers by priority (higher first)
            sorted_triggers = sorted(
                [t for t in self._triggers.values() if t.enabled],
                key=lambda x: x.priority,
                reverse=True,
            )

            for trigger in sorted_triggers:
                # Check cooldown
                if trigger.name in self._cooldowns:
                    last_triggered = self._cooldowns[trigger.name]
                    if current_time - last_triggered < trigger.cooldown_seconds:
                        continue

                # Evaluate condition
                if self._evaluate_condition(trigger, context):
                    triggered_actions.append(
                        TriggerAction(
                            trigger=trigger,
                            params={**trigger.action_params, "context": context},
                        )
                    )
                    self._cooldowns[trigger.name] = current_time

            return triggered_actions

    def _evaluate_condition(self, trigger: TriggerRecord, context: dict) -> bool:
        """Evaluate a trigger condition against context.

        Args:
            trigger: TriggerRecord with condition
            context: Context dictionary with metrics

        Returns:
            True if condition matches
        """
        # Parse condition: "greater_than", "greater_than_or_equal", "not_equal", etc.
        condition_parts = trigger.condition.split("_")
        operator = condition_parts[0] if condition_parts else ""
        threshold_str = (
            "_".join(condition_parts[1:]) if len(condition_parts) > 1 else ""
        )

        # Find the metric in context (look for key matching trigger condition's metric)
        # For simple conditions, check if the condition itself is a boolean in context
        if trigger.condition in context:
            return bool(context[trigger.condition])

        # Try to find metric-based conditions
        # Expected context format: {"metric_name": value, "threshold": value}
        metric_value = context.get("value")
        threshold_value = context.get("threshold", trigger.condition)

        if metric_value is None:
            return False

        try:
            threshold = float(threshold_value)
        except (ValueError, TypeError):
            threshold = 0

        # Evaluate based on operator
        if operator == "greater":
            if len(condition_parts) > 1 and condition_parts[1] == "or":
                return metric_value >= threshold
            return metric_value > threshold
        elif operator == "less":
            if len(condition_parts) > 1 and condition_parts[1] == "or":
                return metric_value <= threshold
            return metric_value < threshold
        elif operator == "not":
            return metric_value != threshold
        elif operator == "equal":
            return metric_value == threshold
        else:
            # Default: treat condition as boolean key in context
            return context.get(trigger.condition, False)

    def execute_trigger(self, action: TriggerAction) -> TriggerResult:
        """Execute a trigger action.

        Args:
            action: TriggerAction to execute

        Returns:
            TriggerResult with success status and output
        """
        trigger = action.trigger
        params = action.params

        # Look up action in registry
        action_def = self._action_registry.get(trigger.action)
        if not action_def:
            return TriggerResult(
                success=False,
                action=trigger.action,
                error=f"Unknown action: {trigger.action}",
            )

        # Execute the action handler
        try:
            handler = action_def.get("handler")
            if handler:
                # Dynamic handler execution (would need to be imported/called)
                result = self._execute_handler(handler, params)
                self._log_execution(trigger, trigger.action, True, result, None)
                return TriggerResult(success=True, action=trigger.action, output=result)
            else:
                # No handler, just log
                self._log_execution(
                    trigger, trigger.action, True, {"status": "registered"}, None
                )
                return TriggerResult(
                    success=True, action=trigger.action, output={"status": "registered"}
                )
        except Exception as e:
            self._log_execution(trigger, trigger.action, False, None, str(e))
            return TriggerResult(success=False, action=trigger.action, error=str(e))

    def _execute_handler(self, handler: str, params: dict) -> Any:
        """Execute a handler by name (dynamic dispatch)."""
        # Parse handler string: "module.function" or "Class.method"
        parts = handler.rsplit(".", 1)
        if len(parts) != 2:
            return {"error": f"Invalid handler format: {handler}"}

        module_name, func_name = parts
        try:
            # Lazy import
            import importlib

            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            return func(params)
        except Exception as e:
            return {"error": f"Handler execution failed: {e}"}

    def _log_execution(
        self,
        trigger: TriggerRecord,
        action: str,
        success: bool,
        output: Any,
        error: Optional[str],
    ) -> None:
        """Log trigger execution to database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO trigger_executions 
               (trigger_id, trigger_name, action, success, output, error, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                trigger.id,
                trigger.name,
                action,
                1 if success else 0,
                str(output) if output else None,
                error,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_trigger(self, name: str) -> Optional[TriggerRecord]:
        """Get a trigger by name.

        Args:
            name: Trigger name

        Returns:
            TriggerRecord or None if not found
        """
        with self._lock:
            return self._triggers.get(name)

    def list_triggers(self, enabled_only: bool = False) -> list[TriggerRecord]:
        """List all registered triggers.

        Args:
            enabled_only: Only return enabled triggers

        Returns:
            List of TriggerRecord objects
        """
        with self._lock:
            triggers = list(self._triggers.values())
            if enabled_only:
                triggers = [t for t in triggers if t.enabled]
            return sorted(triggers, key=lambda x: x.priority, reverse=True)

    def enable_trigger(self, name: str) -> bool:
        """Enable a trigger.

        Args:
            name: Trigger name

        Returns:
            True if successful
        """
        with self._lock:
            if name not in self._triggers:
                return False
            self._triggers[name].enabled = True
            self._persist_trigger(self._triggers[name])
            return True

    def disable_trigger(self, name: str) -> bool:
        """Disable a trigger.

        Args:
            name: Trigger name

        Returns:
            True if successful
        """
        with self._lock:
            if name not in self._triggers:
                return False
            self._triggers[name].enabled = False
            self._persist_trigger(self._triggers[name])
            return True

    def _persist_trigger(self, trigger: TriggerRecord) -> None:
        """Persist trigger to database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """UPDATE triggers SET enabled = ? WHERE id = ?""",
            (1 if trigger.enabled else 0, trigger.id),
        )
        conn.commit()
        conn.close()

    def delete_trigger(self, name: str) -> bool:
        """Delete a trigger.

        Args:
            name: Trigger name

        Returns:
            True if deleted
        """
        with self._lock:
            if name not in self._triggers:
                return False
            trigger = self._triggers.pop(name)
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM triggers WHERE id = ?", (trigger.id,))
            conn.commit()
            conn.close()
            return True

    def get_execution_history(
        self,
        trigger_name: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get trigger execution history.

        Args:
            trigger_name: Optional filter by trigger name
            limit: Maximum number of records

        Returns:
            List of execution records
        """
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM trigger_executions"
        params: list[Any] = []

        if trigger_name:
            query += " WHERE trigger_name = ?"
            params.append(trigger_name)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "trigger_id": row[1],
                "trigger_name": row[2],
                "action": row[3],
                "success": bool(row[4]),
                "output": row[5],
                "error": row[6],
                "timestamp": row[7],
            }
            for row in rows
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics.

        Returns:
            Dictionary with stats
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)

            # Trigger counts
            total = conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0]
            enabled = conn.execute(
                "SELECT COUNT(*) FROM triggers WHERE enabled = 1"
            ).fetchone()[0]

            # Execution stats
            exec_stats = conn.execute(
                """SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                   FROM trigger_executions"""
            ).fetchone()

            # Recent failures
            recent_failures = conn.execute(
                """SELECT COUNT(*) FROM trigger_executions 
                   WHERE success = 0 AND timestamp > datetime('now', '-1 hour')"""
            ).fetchone()[0]

            conn.close()

            return {
                "total_triggers": total,
                "enabled_triggers": enabled,
                "disabled_triggers": total - enabled,
                "total_executions": exec_stats[0]
                if exec_stats and exec_stats[0]
                else 0,
                "successful_executions": exec_stats[1]
                if exec_stats and exec_stats[1]
                else 0,
                "failed_executions": (
                    exec_stats[0]
                    - (exec_stats[1] if exec_stats and exec_stats[1] else 0)
                )
                if exec_stats
                else 0,
                "recent_failures_1h": recent_failures,
                "by_priority": self._get_priority_distribution(),
            }

    def _get_priority_distribution(self) -> dict:
        """Get trigger count by priority."""
        priority_counts: dict[int, int] = defaultdict(int)
        for trigger in self._triggers.values():
            priority_counts[trigger.priority] += 1
        return dict(priority_counts)

    def register_action(
        self, name: str, handler: str, params: Optional[list] = None
    ) -> None:
        """Register an action in the action registry.

        Args:
            name: Action name
            handler: Handler function path (e.g., "module.function")
            params: Required parameters
        """
        with self._lock:
            self._action_registry[name] = {
                "handler": handler,
                "params": params or [],
            }

    def load_from_config(self, config: dict) -> None:
        """Load triggers and actions from config dict (like triggers.json).

        Args:
            config: Configuration dictionary with "triggers" and "action_registry"
        """
        with self._lock:
            # Load action registry
            if "action_registry" in config:
                for name, action_def in config["action_registry"].items():
                    self.register_action(
                        name=name,
                        handler=action_def.get("handler", ""),
                        params=action_def.get("params", []),
                    )

            # Load triggers
            if "triggers" in config:
                for category, trigger_list in config["triggers"].items():
                    for trigger_def in trigger_list:
                        self.register_trigger(
                            name=trigger_def["id"],
                            condition=trigger_def.get("condition", "always"),
                            action=trigger_def["action"],
                            priority={"critical": 3, "warning": 2, "info": 1}.get(
                                trigger_def.get("severity", "info"), 0
                            ),
                            enabled=True,
                            cooldown_seconds=trigger_def.get("cooldown_seconds", 60),
                            action_params=trigger_def.get("action_params", {}),
                        )

    def close(self) -> None:
        """Close the trigger system."""
        with self._lock:
            self._triggers.clear()
            self._cooldowns.clear()

    def __enter__(self) -> "TriggerSystem":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


# Global singleton
_system: Optional[TriggerSystem] = None
_system_lock = threading.Lock()


def get_system() -> TriggerSystem:
    """Get or create the global TriggerSystem instance."""
    global _system
    with _system_lock:
        if _system is None:
            _system = TriggerSystem()
        return _system


def register_trigger(
    name: str,
    condition: str,
    action: str,
    priority: int = 0,
    enabled: bool = True,
    cooldown_seconds: int = 60,
    action_params: Optional[dict] = None,
) -> TriggerRecord:
    """Convenience function to register a trigger."""
    return get_system().register_trigger(
        name=name,
        condition=condition,
        action=action,
        priority=priority,
        enabled=enabled,
        cooldown_seconds=cooldown_seconds,
        action_params=action_params,
    )


def evaluate_triggers(context: dict) -> list[TriggerAction]:
    """Convenience function to evaluate triggers."""
    return get_system().evaluate_triggers(context)


def execute_trigger(action: TriggerAction) -> TriggerResult:
    """Convenience function to execute a trigger action."""
    return get_system().execute_trigger(action)


def get_trigger(name: str) -> Optional[TriggerRecord]:
    """Convenience function to get a trigger by name."""
    return get_system().get_trigger(name)


def list_triggers(enabled_only: bool = False) -> list[TriggerRecord]:
    """Convenience function to list all triggers."""
    return get_system().list_triggers(enabled_only=enabled_only)


def enable_trigger(name: str) -> bool:
    """Convenience function to enable a trigger."""
    return get_system().enable_trigger(name)


def disable_trigger(name: str) -> bool:
    """Convenience function to disable a trigger."""
    return get_system().disable_trigger(name)


def delete_trigger(name: str) -> bool:
    """Convenience function to delete a trigger."""
    return get_system().delete_trigger(name)


def get_stats() -> dict[str, Any]:
    """Convenience function to get trigger statistics."""
    return get_system().get_stats()
