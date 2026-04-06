"""Learning Engine — Stores routing outcomes, improves routing over time with error-based avoidance."""

import os
import sqlite3
import time
from typing import Optional, Set
from collections import defaultdict


class LearningEngine:
    def __init__(self, db_path: str = "data/proxy/routing_outcomes.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()
        # Cache of models to avoid based on errors
        self._auto_avoid_cache: Set[str] = set()
        self._error_counts: dict = defaultdict(lambda: defaultdict(int))

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, prompt_hash INTEGER,
            categories TEXT, complexity TEXT, selected_model TEXT, selected_provider TEXT,
            selected_ip TEXT, input_tokens INTEGER, output_tokens INTEGER,
            latency_ms REAL, success INTEGER, error_type TEXT, quality_score REAL, cost REAL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS model_performance (
            model TEXT PRIMARY KEY, total_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0, failed_requests INTEGER DEFAULT 0,
            avg_latency_ms REAL DEFAULT 0.0, avg_quality_score REAL DEFAULT 0.0, 
            total_cost REAL DEFAULT 0.0, rate_limit_count INTEGER DEFAULT 0,
            timeout_count INTEGER DEFAULT 0, other_error_count INTEGER DEFAULT 0,
            last_updated REAL)""")
        conn.commit()
        conn.close()

    def record_outcome(
        self,
        prompt_hash: int,
        categories: str,
        complexity: str,
        model: str,
        provider: str,
        ip: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        error_type: str = "",
        quality_score: float = 0.0,
        cost: float = 0.0,
    ) -> None:

        conn = sqlite3.connect(self.db_path)
        try:
            # Record outcome
            conn.execute(
                "INSERT INTO outcomes VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    time.time(),
                    prompt_hash,
                    categories,
                    complexity,
                    model,
                    provider,
                    ip,
                    input_tokens,
                    output_tokens,
                    latency_ms,
                    int(success),
                    error_type,
                    quality_score,
                    cost,
                ),
            )

            now = time.time()

            # Count errors by type for auto-avoidance
            is_failure = not success
            rate_limit = 1 if error_type and "rate_limit" in error_type.lower() else 0
            timeout = (
                1
                if error_type
                and (
                    "timeout" in error_type.lower() or "timed_out" in error_type.lower()
                )
                else 0
            )
            other_error = 1 if is_failure and not rate_limit and not timeout else 0

            # Update model performance with error tracking
            conn.execute(
                """INSERT INTO model_performance 
                (model, total_requests, successful_requests, failed_requests, avg_latency_ms, 
                 avg_quality_score, total_cost, rate_limit_count, timeout_count, other_error_count, last_updated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?) 
                ON CONFLICT(model) DO UPDATE SET
                total_requests=total_requests+1, 
                successful_requests=successful_requests+excluded.successful_requests,
                failed_requests=failed_requests+excluded.failed_requests,
                avg_latency_ms=(avg_latency_ms*(total_requests-1)+excluded.avg_latency_ms)/CAST(total_requests AS REAL),
                avg_quality_score=(avg_quality_score*(total_requests-1)+excluded.avg_quality_score)/CAST(total_requests AS REAL),
                total_cost=total_cost+excluded.total_cost,
                rate_limit_count=rate_limit_count+excluded.rate_limit_count,
                timeout_count=timeout_count+excluded.timeout_count,
                other_error_count=other_error_count+excluded.other_error_count,
                last_updated=?""",
                (
                    model,
                    1,
                    int(success),
                    int(is_failure),
                    latency_ms,
                    quality_score,
                    cost,
                    rate_limit,
                    timeout,
                    other_error,
                    now,
                    now,
                ),
            )

            conn.commit()

            # Update auto-avoid cache
            self._update_auto_avoid(conn)

        finally:
            conn.close()

    def _update_auto_avoid(self, conn):
        """Auto-avoid models with high failure rates or too many rate limits."""
        # Threshold: if >30% failures or >3 rate limits in last 20 requests, avoid the model
        cursor = conn.execute("""SELECT model, total_requests, failed_requests, 
            CAST(failed_requests AS REAL)/NULLIF(total_requests,0) as fail_rate,
            rate_limit_count, timeout_count
            FROM model_performance 
            WHERE total_requests >= 5""")

        self._auto_avoid_cache = set()
        for row in cursor.fetchall():
            model, total, failed, fail_rate, rate_limits, timeouts = row
            # Avoid if: >30% failure rate OR >3 rate limits OR >3 timeouts
            if fail_rate and fail_rate > 0.30:
                self._auto_avoid_cache.add(model)
            elif rate_limits and rate_limits > 3:
                self._auto_avoid_cache.add(model)
            elif timeouts and timeouts > 3:
                self._auto_avoid_cache.add(model)

    def get_auto_avoid_models(self) -> Set[str]:
        """Get models that should be automatically avoided due to errors."""
        return self._auto_avoid_cache

    def get_best_model_for(
        self,
        categories: str = "",
        complexity: str = "",
        min_quality: float = 0.7,
        avoid_models: set = None,
    ) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            # First, get models that are NOT in auto-avoid
            auto_avoid = self.get_auto_avoid_models()
            if avoid_models:
                auto_avoid = auto_avoid.union(avoid_models)

            avoid_clause = (
                f"AND model NOT IN ({','.join(['?'] * len(auto_avoid))})"
                if auto_avoid
                else ""
            )
            params = list(auto_avoid) if auto_avoid else []

            cursor = conn.execute(
                f"""SELECT model, CAST(successful_requests AS REAL)/NULLIF(total_requests,0) as success_rate,
                avg_latency_ms, avg_quality_score FROM model_performance
                WHERE total_requests >= 3 {avoid_clause}
                ORDER BY avg_quality_score DESC, avg_latency_ms ASC LIMIT 10""",
                params,
            )
            results = cursor.fetchall()
        finally:
            conn.close()

        if not results:
            return None
        qualified = [(r[0], r[2]) for r in results if r[3] and r[3] >= min_quality]
        return qualified[0][0] if qualified else (results[0][0] if results else None)

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
            success = conn.execute(
                "SELECT COUNT(*) FROM outcomes WHERE success=1"
            ).fetchone()[0]
            avg_latency = (
                conn.execute("SELECT AVG(latency_ms) FROM outcomes").fetchone()[0] or 0
            )
            models = conn.execute(
                "SELECT COUNT(DISTINCT model) FROM model_performance"
            ).fetchone()[0]
            auto_avoid = len(self.get_auto_avoid_models())
        finally:
            conn.close()
        return {
            "total_requests": total,
            "success_rate": round(success / total, 3) if total > 0 else 0,
            "avg_latency_ms": round(avg_latency, 1),
            "models_tracked": models,
            "auto_avoid_count": auto_avoid,
            "auto_avoid_models": list(self._auto_avoid_cache),
        }


learning_engine = LearningEngine()
