"""Procedural memory for learned skills and patterns."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProductionRule:
    rule_id: str
    name: str
    condition: str
    action: str
    success_count: int = 0
    failure_count: int = 0
    activation: float = 1.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5


# Query-type strategy rules: which strategies to use for different query types
QUERY_TYPE_STRATEGIES: dict[str, list[str]] = {
    "code_search": ["semantic_first", "rrf_fusion"],
    "concept_lookup": ["rrf_fusion", "semantic_first"],
    "fact_lookup": ["semantic_first"],
    "historical": ["rrf_fusion"],
    "general": ["rrf_fusion", "semantic_first"],
}


class ProceduralMemory:
    DB_PATH = "context/memory/file_registry.db"

    def __init__(self, storage_path: str = "data/procedural_memory.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.rules: dict[str, ProductionRule] = {}
        self._load()
        self._init_strategy_db()

    def store(
        self, rule_id: str, name: str, condition: str, action: str
    ) -> ProductionRule:
        rule = ProductionRule(
            rule_id=rule_id, name=name, condition=condition, action=action
        )
        self.rules[rule_id] = rule
        self._save()
        return rule

    def find_matching(self, context: str) -> list:
        context_lower = context.lower()
        matches = []
        for rule in self.rules.values():
            if rule.condition.lower() in context_lower:
                matches.append(rule)
        return sorted(
            matches, key=lambda r: r.success_rate * r.activation, reverse=True
        )

    def record_success(self, rule_id: str):
        if rule_id in self.rules:
            self.rules[rule_id].success_count += 1
            self.rules[rule_id].activation = min(
                1.0, self.rules[rule_id].activation + 0.1
            )
            self._save()

    def record_failure(self, rule_id: str):
        if rule_id in self.rules:
            self.rules[rule_id].failure_count += 1
            self.rules[rule_id].activation = max(
                0.0, self.rules[rule_id].activation - 0.2
            )
            self._save()

    def _load(self):
        if self.storage_path.exists():
            data = json.loads(self.storage_path.read_text())
            for rid, rdata in data.items():
                self.rules[rid] = ProductionRule(**rdata)

    def _save(self):
        data = {
            rid: {
                "rule_id": r.rule_id,
                "name": r.name,
                "condition": r.condition,
                "action": r.action,
                "success_count": r.success_count,
                "failure_count": r.failure_count,
                "activation": r.activation,
            }
            for rid, r in self.rules.items()
        }
        self.storage_path.write_text(json.dumps(data, indent=2))

    def _init_strategy_db(self):
        """Initialize the strategy_performance table in SQLite."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                success INTEGER DEFAULT 0,
                failure INTEGER DEFAULT 0,
                avg_latency_ms REAL,
                last_evaluated TEXT,
                UNIQUE(query_type, strategy)
            )
        """)
        conn.commit()
        conn.close()

    def record_strategy_result(
        self,
        query_type: str,
        strategy: str,
        success: bool,
        latency_ms: Optional[float] = None,
    ):
        """Record the result of a strategy execution for a query type."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Check if record exists
        cursor.execute(
            "SELECT success, failure, avg_latency_ms FROM strategy_performance WHERE query_type = ? AND strategy = ?",
            (query_type, strategy),
        )
        row = cursor.fetchone()

        if row:
            old_success, old_failure, old_avg = row
            new_success = old_success + (1 if success else 0)
            new_failure = old_failure + (0 if success else 1)

            # Update avg latency
            if latency_ms is not None:
                if old_avg is not None:
                    new_avg = (old_avg + latency_ms) / 2
                else:
                    new_avg = latency_ms
            else:
                new_avg = old_avg

            cursor.execute(
                """
                UPDATE strategy_performance
                SET success = ?, failure = ?, avg_latency_ms = ?, last_evaluated = ?
                WHERE query_type = ? AND strategy = ?
            """,
                (new_success, new_failure, new_avg, now, query_type, strategy),
            )
        else:
            # Insert new record
            cursor.execute(
                """
                INSERT INTO strategy_performance (query_type, strategy, success, failure, avg_latency_ms, last_evaluated)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    query_type,
                    strategy,
                    1 if success else 0,
                    0 if success else 1,
                    latency_ms,
                    now,
                ),
            )

        conn.commit()
        conn.close()

    def get_strategy_success_rate(self, query_type: str, strategy: str) -> float:
        """Get the success rate (0.0-1.0) for a specific query type and strategy."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT success, failure FROM strategy_performance WHERE query_type = ? AND strategy = ?",
            (query_type, strategy),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return 0.5  # Default neutral rate for unknown combinations

        success, failure = row
        total = success + failure
        return success / total if total > 0 else 0.5

    def get_best_strategy(self, query_type: str) -> Optional[str]:
        """Return the strategy with the highest success rate for the given query type."""
        strategies = QUERY_TYPE_STRATEGIES.get(
            query_type, ["semantic_first", "rrf_fusion"]
        )

        best_strategy = None
        best_rate = -1.0

        for strategy in strategies:
            rate = self.get_strategy_success_rate(query_type, strategy)
            if rate > best_rate:
                best_rate = rate
                best_strategy = strategy

        return best_strategy

    def get_strategy_stats(self) -> dict:
        """Return performance statistics per query type and strategy."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT query_type, strategy, success, failure, avg_latency_ms, last_evaluated
            FROM strategy_performance
            ORDER BY query_type, strategy
        """)
        rows = cursor.fetchall()
        conn.close()

        stats = {}
        for row in rows:
            query_type, strategy, success, failure, avg_latency, last_eval = row
            total = success + failure
            rate = success / total if total > 0 else 0.5

            if query_type not in stats:
                stats[query_type] = {}

            stats[query_type][strategy] = {
                "success": success,
                "failure": failure,
                "success_rate": rate,
                "avg_latency_ms": avg_latency,
                "last_evaluated": last_eval,
            }

        return stats
