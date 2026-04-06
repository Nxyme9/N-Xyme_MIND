"""Session context management — Working, Episodic, and Procedural memory.

Provides unified session context with three memory systems:
- Working: Active context items with activation decay
- Episodic: Experience storage via Graphiti
- Procedural: Learned skills and patterns
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# For episodic memory - Graphiti integration
GRAPHITI_URL = "http://localhost:8001/json-rpc"

# Query-type strategy rules
QUERY_TYPE_STRATEGIES: dict[str, list[str]] = {
    "code_search": ["semantic_first", "rrf_fusion"],
    "concept_lookup": ["rrf_fusion", "semantic_first"],
    "fact_lookup": ["semantic_first"],
    "historical": ["rrf_fusion"],
    "general": ["rrf_fusion", "semantic_first"],
}


# ============== Working Memory ==============


@dataclass
class MemoryItem:
    """A single item in working memory."""

    key: str
    value: str
    timestamp: str
    activation: float = 1.0
    access_count: int = 0


class WorkingMemory:
    """Working memory for active context with capacity limit and activation decay."""

    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.items: dict[str, MemoryItem] = {}

    def store(self, key: str, value: str) -> MemoryItem:
        """Store a new item, evicting lowest activation if at capacity."""
        if len(self.items) >= self.capacity:
            self._evict_lowest_activation()
        item = MemoryItem(
            key=key,
            value=value,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.items[key] = item
        return item

    def retrieve(self, key: str) -> Optional[MemoryItem]:
        """Retrieve and update activation on access."""
        if key in self.items:
            item = self.items[key]
            item.access_count += 1
            item.activation = min(1.0, item.activation + 0.1)
            return item
        return None

    def get_all(self) -> list:
        """Get all items."""
        return list(self.items.values())

    def decay(self, rate: float = 0.1):
        """Apply decay to all activation values."""
        for item in self.items.values():
            item.activation = max(0.0, item.activation - rate)

    def _evict_lowest_activation(self):
        """Remove the item with lowest activation."""
        if not self.items:
            return
        lowest_key = min(self.items.keys(), key=lambda k: self.items[k].activation)
        del self.items[lowest_key]

    def clear(self):
        """Clear all items."""
        self.items.clear()


# ============== Episodic Memory ==============


class EpisodicMemory:
    """Episodic memory for experiences and events via Graphiti."""

    def __init__(self, group_id: str = "brain-memory"):
        self.group_id = group_id

    def store(self, name: str, text: str) -> bool:
        """Store an episodic memory."""
        try:
            import requests

            resp = requests.post(
                GRAPHITI_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "graphiti_add_episode",
                    "params": {
                        "name": name,
                        "text": text,
                        "source": "brain",
                        "group_id": self.group_id,
                    },
                },
                timeout=5,
            )
            return resp.json().get("result", {}).get("success", False)
        except Exception:
            return False

    def search(self, query: str, max_results: int = 5) -> list:
        """Search episodic memories."""
        try:
            import requests

            resp = requests.post(
                GRAPHITI_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "graphiti_hybrid_search",
                    "params": {"query": query, "max_results": max_results},
                },
                timeout=5,
            )
            return resp.json().get("result", {}).get("episodes", [])
        except Exception:
            return []

    def get_recent(self, last_n: int = 5) -> list:
        """Get recent episodic memories."""
        try:
            import requests

            resp = requests.post(
                GRAPHITI_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "graphiti_get_episodes",
                    "params": {"group_id": self.group_id, "last_n": last_n},
                },
                timeout=5,
            )
            return resp.json().get("result", {}).get("episodes", [])
        except Exception:
            return []


# ============== Procedural Memory ==============


@dataclass
class ProductionRule:
    """A learned production rule."""

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


class ProceduralMemory:
    """Procedural memory for learned skills and patterns."""

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
        """Store a new production rule."""
        rule = ProductionRule(
            rule_id=rule_id, name=name, condition=condition, action=action
        )
        self.rules[rule_id] = rule
        self._save()
        return rule

    def find_matching(self, context: str) -> list:
        """Find rules matching the given context."""
        context_lower = context.lower()
        matches = []
        for rule in self.rules.values():
            if rule.condition.lower() in context_lower:
                matches.append(rule)
        return sorted(
            matches, key=lambda r: r.success_rate * r.activation, reverse=True
        )

    def record_success(self, rule_id: str):
        """Record successful rule application."""
        if rule_id in self.rules:
            self.rules[rule_id].success_count += 1
            self.rules[rule_id].activation = min(
                1.0, self.rules[rule_id].activation + 0.1
            )
            self._save()

    def record_failure(self, rule_id: str):
        """Record failed rule application."""
        if rule_id in self.rules:
            self.rules[rule_id].failure_count += 1
            self.rules[rule_id].activation = max(
                0.0, self.rules[rule_id].activation - 0.2
            )
            self._save()

    def _load(self):
        """Load rules from storage."""
        if self.storage_path.exists():
            data = json.loads(self.storage_path.read_text())
            for rid, rdata in data.items():
                self.rules[rid] = ProductionRule(**rdata)

    def _save(self):
        """Save rules to storage."""
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
        """Initialize strategy_performance table."""
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
        """Record strategy execution result."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute(
            "SELECT success, failure, avg_latency_ms FROM strategy_performance WHERE query_type = ? AND strategy = ?",
            (query_type, strategy),
        )
        row = cursor.fetchone()

        if row:
            old_success, old_failure, old_avg = row
            new_success = old_success + (1 if success else 0)
            new_failure = old_failure + (0 if success else 1)

            if latency_ms is not None:
                if old_avg is not None:
                    new_avg = (old_avg + latency_ms) / 2
                else:
                    new_avg = latency_ms
            else:
                new_avg = old_avg

            cursor.execute(
                """UPDATE strategy_performance
                SET success = ?, failure = ?, avg_latency_ms = ?, last_evaluated = ?
                WHERE query_type = ? AND strategy = ?""",
                (new_success, new_failure, new_avg, now, query_type, strategy),
            )
        else:
            cursor.execute(
                """INSERT INTO strategy_performance
                (query_type, strategy, success, failure, avg_latency_ms, last_evaluated)
                VALUES (?, ?, ?, ?, ?, ?)""",
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
        """Get success rate for query type + strategy."""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT success, failure FROM strategy_performance WHERE query_type = ? AND strategy = ?",
            (query_type, strategy),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return 0.5

        success, failure = row
        total = success + failure
        return success / total if total > 0 else 0.5

    def get_best_strategy(self, query_type: str) -> Optional[str]:
        """Get best strategy for query type."""
        strategies = QUERY_TYPE_STRATEGIES.get(query_type, ["semantic_first", "rrf_fusion"])

        best_strategy = None
        best_rate = -1.0

        for strategy in strategies:
            rate = self.get_strategy_success_rate(query_type, strategy)
            if rate > best_rate:
                best_rate = rate
                best_strategy = strategy

        return best_strategy

    def get_strategy_stats(self) -> dict:
        """Get all strategy performance stats."""
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


# ============== Unified Session Context ==============


class SessionContext:
    """Unified session context combining all memory types."""

    def __init__(self):
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()

    def store_working(self, key: str, value: str) -> MemoryItem:
        """Store in working memory."""
        return self.working.store(key, value)

    def retrieve_working(self, key: str) -> Optional[MemoryItem]:
        """Retrieve from working memory."""
        return self.working.retrieve(key)

    def store_episodic(self, name: str, text: str) -> bool:
        """Store episodic memory."""
        return self.episodic.store(name, text)

    def search_episodic(self, query: str, max_results: int = 5) -> list:
        """Search episodic memories."""
        return self.episodic.search(query, max_results)

    def store_procedural(
        self, rule_id: str, name: str, condition: str, action: str
    ) -> ProductionRule:
        """Store procedural rule."""
        return self.procedural.store(rule_id, name, condition, action)

    def find_procedural(self, context: str) -> list:
        """Find procedural rules matching context."""
        return self.procedural.find_matching(context)

    def decay_working(self, rate: float = 0.1):
        """Apply decay to working memory."""
        self.working.decay(rate)