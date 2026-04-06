"""Learning Engine — Stores routing outcomes, improves routing over time."""

import os
import sqlite3
import time
from typing import Optional


class LearningEngine:
    def __init__(self, db_path: str = "data/proxy/routing_outcomes.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, prompt_hash INTEGER,
            categories TEXT, complexity TEXT, selected_model TEXT, selected_provider TEXT,
            selected_ip TEXT, input_tokens INTEGER, output_tokens INTEGER,
            latency_ms REAL, success INTEGER, error_type TEXT, quality_score REAL, cost REAL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS model_performance (
            model TEXT PRIMARY KEY, total_requests INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0, avg_latency_ms REAL DEFAULT 0.0,
            avg_quality_score REAL DEFAULT 0.0, total_cost REAL DEFAULT 0.0, last_updated REAL)""")
        conn.commit()
        conn.close()

    def record_outcome(self, prompt_hash: int, categories: str, complexity: str,
                       model: str, provider: str, ip: str, input_tokens: int,
                       output_tokens: int, latency_ms: float, success: bool,
                       error_type: str = "", quality_score: float = 0.0, cost: float = 0.0) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO outcomes VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), prompt_hash, categories, complexity, model, provider, ip,
                 input_tokens, output_tokens, latency_ms, int(success), error_type, quality_score, cost))
            now = time.time()
            # 7 columns in INSERT, 7 placeholders in VALUES, 1 in UPDATE = 8 total params
            # VALUES: model, total_requests, successful_requests, avg_latency_ms, avg_quality_score, total_cost, last_updated
            conn.execute("""INSERT INTO model_performance 
                (model, total_requests, successful_requests, avg_latency_ms, avg_quality_score, total_cost, last_updated)
                VALUES (?,?,?,?,?,?,?) 
                ON CONFLICT(model) DO UPDATE SET
                total_requests=total_requests+1, 
                successful_requests=successful_requests+excluded.successful_requests,
                avg_latency_ms=(avg_latency_ms*(total_requests-1)+excluded.avg_latency_ms)/CAST(total_requests AS REAL),
                avg_quality_score=(avg_quality_score*(total_requests-1)+excluded.avg_quality_score)/CAST(total_requests AS REAL),
                total_cost=total_cost+excluded.total_cost, 
                last_updated=?""",
                (model, 1, int(success), latency_ms, quality_score, cost, now, now))
            conn.commit()
        finally:
            conn.close()

    def get_best_model_for(self, categories: str = "", complexity: str = "", min_quality: float = 0.7) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""SELECT model, CAST(successful_requests AS REAL)/NULLIF(total_requests,0) as success_rate,
                avg_latency_ms, avg_quality_score FROM model_performance
                WHERE total_requests >= 5 ORDER BY avg_quality_score DESC, avg_latency_ms ASC LIMIT 10""")
            results = cursor.fetchall()
        finally:
            conn.close()
        if not results: return None
        qualified = [(r[0], r[2]) for r in results if r[3] and r[3] >= min_quality]
        return qualified[0][0] if qualified else (results[0][0] if results else None)

    def get_stats(self) -> dict:
        conn = sqlite3.connect(self.db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
            success = conn.execute("SELECT COUNT(*) FROM outcomes WHERE success=1").fetchone()[0]
            avg_latency = conn.execute("SELECT AVG(latency_ms) FROM outcomes").fetchone()[0] or 0
            models = conn.execute("SELECT COUNT(DISTINCT model) FROM model_performance").fetchone()[0]
        finally:
            conn.close()
        return {"total_requests": total, "success_rate": round(success/total, 3) if total > 0 else 0,
            "avg_latency_ms": round(avg_latency, 1), "models_tracked": models}

learning_engine = LearningEngine()
