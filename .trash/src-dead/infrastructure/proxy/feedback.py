"""Human Feedback Loop — Quality scoring from user feedback."""

import sqlite3
import os
import time
import threading
from typing import Dict, List, Optional


class FeedbackLoop:
    def __init__(self, db_path: str = "data/proxy/feedback.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, request_id TEXT,
            model TEXT, provider TEXT, rating INTEGER, comment TEXT,
            was_helpful INTEGER, response_time_ms REAL)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS model_ratings (
            model TEXT PRIMARY KEY, total_ratings INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0.0, helpful_rate REAL DEFAULT 0.0,
            avg_response_time_ms REAL DEFAULT 0.0)""")
        conn.commit()
        conn.close()

    def submit(self, request_id: str, model: str, provider: str,
               rating: int, comment: str = "", was_helpful: bool = True,
               response_time_ms: float = 0.0) -> int:
        """Submit feedback for a request."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO feedback (timestamp, request_id, model, provider, rating, comment, was_helpful, response_time_ms) VALUES (?,?,?,?,?,?,?,?)",
                (time.time(), request_id, model, provider, rating, comment, int(was_helpful), response_time_ms))
            # Update model ratings
            conn.execute("""INSERT INTO model_ratings (model, total_ratings, avg_rating, helpful_rate, avg_response_time_ms)
                VALUES (?,1,?,?,?) ON CONFLICT(model) DO UPDATE SET
                total_ratings=total_ratings+1,
                avg_rating=(avg_rating*(total_ratings-1)+?)/CAST(total_ratings AS REAL),
                helpful_rate=(helpful_rate*(total_ratings-1)+?)/CAST(total_ratings AS REAL),
                avg_response_time_ms=(avg_response_time_ms*(total_ratings-1)+?)/CAST(total_ratings AS REAL)""",
                (model, rating, int(was_helpful), response_time_ms, rating, int(was_helpful), response_time_ms))
            conn.commit()
            return 1
        finally:
            conn.close()

    def get_model_rankings(self) -> List[dict]:
        """Get models ranked by average rating."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""SELECT model, total_ratings, avg_rating, helpful_rate, avg_response_time_ms
                FROM model_ratings ORDER BY avg_rating DESC, total_ratings DESC""")
            return [{"model": r[0], "total_ratings": r[1], "avg_rating": round(r[2], 2),
                     "helpful_rate": round(r[3], 3), "avg_response_time_ms": round(r[4], 1)} for r in cursor.fetchall()]
        finally:
            conn.close()


# Global instance
feedback_loop = FeedbackLoop()
