"""Q-Learning router with SQLite outcomes for self-learning."""

from __future__ import annotations

import os
import sqlite3
import time
import random
import math
from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional

from .models import ProviderType, RotationOutcome, VPNEndpoint

logger = logging.getLogger("vpn_rotation.router")


# Q-Learning defaults
DEFAULT_ALPHA = 0.1    # Learning rate
DEFAULT_GAMMA = 0.9    # Discount factor
DEFAULT_EPSILON = 0.1  # Exploration rate


@dataclass
class RoutingDecision:
    """Represents a routing decision."""
    endpoint: VPNEndpoint
    strategy: str  # "exploit" or "explore"
    q_value: float = 0.0
    reason: str = ""


class QLearningRouter:
    """Q-Learning based routing for VPN endpoints.
    
    Combines:
    - Q-Learning for action selection (exploit vs explore)
    - Weighted selection based on latency/success
    - SQLite outcome storage for learning
    - Real-time Q-value updates
    """
    
    def __init__(
        self,
        db_path: str = "data/proxy/vpn_routing.db",
        alpha: float = DEFAULT_ALPHA,
        gamma: float = DEFAULT_GAMMA,
        epsilon: float = DEFAULT_EPSILON,
    ):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        
        # Q-table: (provider, country) -> action -> value
        self._q_table: Dict[str, Dict[str, float]] = {}
        
        # Endpoint weights (for weighted random selection)
        self._endpoint_weights: Dict[str, float] = {}
        
        # Initialize database
        self._db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database for outcomes."""
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            provider TEXT,
            host TEXT,
            port INTEGER,
            country TEXT,
            exit_ip TEXT,
            latency_ms REAL,
            success INTEGER,
            error_type TEXT,
            reward REAL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS q_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT UNIQUE,
            action TEXT,
            q_value REAL,
            updated_at REAL
        )""")
        conn.commit()
        conn.close()
    
    def _state_key(self, endpoint: VPNEndpoint) -> str:
        """Generate state key for an endpoint."""
        return f"{endpoint.provider}:{endpoint.country}"
    
    def _get_q_value(self, state: str, action: str) -> float:
        """Get Q-value for state-action pair."""
        if state not in self._q_table:
            self._q_table[state] = {}
        return self._q_table[state].get(action, 0.0)
    
    def _set_q_value(self, state: str, action: str, value: float) -> None:
        """Set Q-value for state-action pair."""
        if state not in self._q_table:
            self._q_table[state] = {}
        self._q_table[state][action] = value
    
    def select_endpoint(
        self,
        endpoints: List[VPNEndpoint],
        epsilon: Optional[float] = None,
    ) -> RoutingDecision:
        """Select an endpoint using epsilon-greeedy Q-learning.
        
        Args:
            endpoints: Available endpoints to choose from.
            epsilon: Exploration rate (uses default if None).
            
        Returns:
            RoutingDecision with selected endpoint.
        """
        if not endpoints:
            raise ValueError("No endpoints available")
        
        epsilon = epsilon if epsilon is not None else self.epsilon
        
        # Filter healthy endpoints
        candidates = [ep for ep in endpoints if ep.healthy and not ep.is_rate_limited]
        if not candidates:
            # Fallback: any healthy endpoint
            candidates = [ep for ep in endpoints if ep.healthy]
        if not candidates:
            # Last resort: any endpoint
            candidates = endpoints
        
        # Epsilon-greedy: explore with probability epsilon
        if random.random() < epsilon:
            selected = random.choice(candidates)
            return RoutingDecision(
                endpoint=selected,
                strategy="explore",
                q_value=0.0,
                reason="Random exploration",
            )
        
        # Exploit: select best Q-value
        best = candidates[0]
        best_q = float('-inf')
        best_reason = "First viable"
        
        for ep in candidates:
            state = self._state_key(ep)
            # Q-value based on latency (lower is better)
            q = self._get_q_value(state, "select")
            # Factor in latency score
            latency_score = max(0, 1.0 - (ep.latency_ms / 500.0))
            q += latency_score * 10
            
            if q > best_q:
                best_q = q
                best = ep
                best_reason = f"Best Q-value ({round(q, 2)})"
        
        # Compute final Q-value for this selection
        state = self._state_key(best)
        final_q = self._get_q_value(state, "select")
        
        return RoutingDecision(
            endpoint=best,
            strategy="exploit",
            q_value=final_q,
            reason=best_reason,
        )
    
    def update_from_outcome(self, outcome: RotationOutcome) -> None:
        """Update Q-values based on outcome.
        
        Uses TD learning: Q(s,a) += alpha * (reward + gamma * max Q(s') - Q(s,a))
        
        Args:
            outcome: The routing outcome to learn from.
        """
        ep = outcome.endpoint
        state = self._state_key(ep)
        
        # Compute reward (higher is better)
        if outcome.success:
            # Success: reward based on latency (lower = better)
            reward = 100.0 - min(100.0, outcome.latency_ms / 10)
        else:
            # Failure: negative reward
            reward = -50.0
        
        # Current Q-value
        current_q = self._get_q_value(state, "select")
        
        # TD update
        td_error = reward - current_q
        new_q = current_q + self.alpha * td_error
        self._set_q_value(state, "select", new_q)
        
        # Also update endpoint weight for weighted selection
        weight_key = f"{ep.host}:{ep.port}"
        if outcome.success:
            # Increase weight based on performance
            current = self._endpoint_weights.get(weight_key, 1.0)
            self._endpoint_weights[weight_key] = current * 1.1
        else:
            # Decrease weight on failure
            current = self._endpoint_weights.get(weight_key, 1.0)
            self._endpoint_weights[weight_key] = max(0.1, current * 0.9)
        
        # Store outcome in database
        self._store_outcome(outcome, reward)
        
        logger.debug(
            f"Updated Q-value for {state}: {current_q:.2f} -> {new_q:.2f} "
            f"(reward: {reward:.1f})"
        )
    
    def _store_outcome(self, outcome: RotationOutcome, reward: float) -> None:
        """Store outcome in SQLite database."""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT INTO outcomes 
                   (timestamp, provider, host, port, country, exit_ip, 
                    latency_ms, success, error_type, reward)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    outcome.timestamp,
                    outcome.endpoint.provider,
                    outcome.endpoint.host,
                    outcome.endpoint.port,
                    outcome.endpoint.country,
                    outcome.exit_ip,
                    outcome.latency_ms,
                    int(outcome.success),
                    outcome.error_type,
                    reward,
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_best_for_provider(self, provider: str) -> Optional[VPNEndpoint]:
        """Get best endpoint for a specific provider (from Q-values)."""
        best = None
        best_q = float('-inf')
        
        for state, actions in self._q_table.items():
            if not state.startswith(provider + ":"):
                continue
            q = actions.get("select", 0.0)
            if q > best_q:
                best_q = q
                # Return endpoint info (would need to store full endpoint)
        
        return best
    
    def get_stats(self) -> dict:
        """Get router statistics."""
        conn = sqlite3.connect(self._db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
            success = conn.execute(
                "SELECT COUNT(*) FROM outcomes WHERE success=1"
            ).fetchone()[0]
            avg_latency = conn.execute(
                "SELECT AVG(latency_ms) FROM outcomes"
            ).fetchone()[0] or 0
            states = conn.execute(
                "SELECT COUNT(DISTINCT state) FROM q_values"
            ).fetchone()[0]
        finally:
            conn.close()
        
        return {
            "total_outcomes": total,
            "success_rate": round(success / max(1, total), 3),
            "avg_latency_ms": round(avg_latency, 1),
            "states_learned": states,
            "q_table_size": len(self._q_table),
        }


class WeightedRouter:
    """Simple weighted router (no learning).
    
    Routes based on precomputed weights (latency, success rate, capacity).
    Used as fallback or for simple use cases.
    """
    
    def __init__(self):
        self._weights: Dict[str, float] = {}
    
    def select_endpoint(
        self,
        endpoints: List[VPNEndpoint],
    ) -> RoutingDecision:
        """Select endpoint using weighted random selection."""
        if not endpoints:
            raise ValueError("No endpoints available")
        
        # Filter healthy
        candidates = [ep for ep in endpoints if ep.healthy and not ep.is_rate_limited]
        if not candidates:
            candidates = [ep for ep in endpoints if ep.healthy]
        if not candidates:
            candidates = endpoints
        
        # Compute weights based on capacity
        weights = []
        for ep in candidates:
            key = f"{ep.host}:{ep.port}"
            base_weight = self._weights.get(key, 1.0)
            capacity_weight = ep.available_capacity
            latency_weight = max(0, 1.0 - (ep.latency_ms / 500.0))
            weight = base_weight * capacity_weight * (latency_weight + 0.5)
            weights.append(max(0.01, weight))
        
        # Weighted random selection
        total = sum(weights)
        r = random.random() * total
        cumulative = 0.0
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return RoutingDecision(
                    endpoint=candidates[i],
                    strategy="weighted",
                    q_value=w,
                    reason=f"Weight: {round(w, 3)}",
                )
        
        # Fallback
        return RoutingDecision(
            endpoint=candidates[-1],
            strategy="fallback",
            reason="Last candidate",
        )
    
    def update_weight(self, host: str, port: int, success: bool) -> None:
        """Update weight for an endpoint."""
        key = f"{host}:{port}"
        current = self._weights.get(key, 1.0)
        if success:
            self._weights[key] = min(10.0, current * 1.2)
        else:
            self._weights[key] = max(0.1, current * 0.8)


# Default singleton
_router: Optional[QLearningRouter] = None


def get_router() -> QLearningRouter:
    """Get or create the default QLearningRouter instance."""
    global _router
    if _router is None:
        _router = QLearningRouter()
    return _router
