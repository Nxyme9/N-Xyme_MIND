"""Routing Weight Optimizer — Uses learning system to optimize routing decisions over time."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("routing-optimizer")


@dataclass
class AgentWeights:
    """Routing weights for a specific agent."""
    success_rate: float = 0.5  # EMA of success rate
    avg_latency_ms: float = 0.0  # EMA of latency
    total_tasks: int = 0
    success_count: int = 0
    failure_count: int = 0
    by_level: Dict[int, Dict[str, float]] = field(default_factory=dict)  # level -> {success_rate, avg_latency}


@dataclass
class RoutingRecommendation:
    """Optimized routing recommendation."""
    recommended_agent: str
    confidence: float
    reason: str
    weights: Dict[str, AgentWeights]


class RoutingWeightOptimizer:
    """Optimizes routing weights based on delegation outcomes with JSON persistence."""
    
    def __init__(self, alpha: float = 0.1, persist_path: Optional[str] = None):
        """
        Args:
            alpha: Learning rate for exponential moving average (0.0-1.0)
            persist_path: Path to JSON file for persistence (default: .sisyphus/routing-weights.json)
        """
        self._alpha = alpha
        self._weights: Dict[str, AgentWeights] = {}
        self._initialized = False
        
        # Setup persistence
        if persist_path is None:
            project_root = Path(__file__).parent.parent.parent
            persist_path = str(project_root / ".sisyphus" / "routing-weights.json")
        self._persist_path = persist_path
        
        # Load existing weights from disk
        self._load_weights()

    def _load_weights(self) -> None:
        """Load weights from JSON file on startup."""
        try:
            path = Path(self._persist_path)
            if path.exists():
                with open(path, 'r') as f:
                    data = json.load(f)
                for agent_name, agent_data in data.items():
                    weights = AgentWeights(
                        success_rate=agent_data.get('success_rate', 0.5),
                        avg_latency_ms=agent_data.get('avg_latency_ms', 0.0),
                        total_tasks=agent_data.get('total_tasks', 0),
                        success_count=agent_data.get('success_count', 0),
                        failure_count=agent_data.get('failure_count', 0),
                        by_level=agent_data.get('by_level', {})
                    )
                    self._weights[agent_name] = weights
                self._initialized = True
                logging.getLogger("routing-optimizer").info(f"Loaded weights for {len(self._weights)} agents from {self._persist_path}")
        except Exception as e:
            logging.getLogger("routing-optimizer").warning(f"Failed to load weights: {e}")

    def _persist_weights(self) -> None:
        """Save weights to JSON file."""
        try:
            path = Path(self._persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for agent_name, weights in self._weights.items():
                data[agent_name] = {
                    'success_rate': weights.success_rate,
                    'avg_latency_ms': weights.avg_latency_ms,
                    'total_tasks': weights.total_tasks,
                    'success_count': weights.success_count,
                    'failure_count': weights.failure_count,
                    'by_level': weights.by_level
                }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.getLogger("routing-optimizer").warning(f"Failed to persist weights: {e}")
    
    def _initialize_default_weights(self) -> None:
        """Initialize default weights for all agents."""
        default_agents = [
            "hephaestus", "sisyphus-junior", "explore", "librarian",
            "oracle", "momus", "prometheus", "metis", "atlas"
        ]
        for agent in default_agents:
            self._weights[agent] = AgentWeights()
        self._initialized = True
    
    def update_weights(
        self,
        agent: str,
        level: int,
        success: bool,
        latency_ms: float = 0
    ) -> None:
        """Update routing weights based on delegation outcome."""
        if not self._initialized:
            self._initialize_default_weights()
        
        if agent not in self._weights:
            self._weights[agent] = AgentWeights()
        
        weights = self._weights[agent]
        weights.total_tasks += 1
        
        if success:
            weights.success_count += 1
        else:
            weights.failure_count += 1
        
        # Update EMA of success rate
        current_success_rate = 1.0 if success else 0.0
        weights.success_rate = (
            self._alpha * current_success_rate + (1 - self._alpha) * weights.success_rate
        )
        
        # Update EMA of latency
        if latency_ms > 0:
            if weights.avg_latency_ms == 0:
                weights.avg_latency_ms = latency_ms
            else:
                weights.avg_latency_ms = (
                    self._alpha * latency_ms + (1 - self._alpha) * weights.avg_latency_ms
                )
        
        # Update per-level weights
        if level not in weights.by_level:
            weights.by_level[level] = {"success_rate": 0.5, "avg_latency_ms": 0.0}
        
        level_weights = weights.by_level[level]
        level_success_rate = 1.0 if success else 0.0
        level_weights["success_rate"] = (
            self._alpha * level_success_rate + (1 - self._alpha) * level_weights["success_rate"]
        )
        
        if latency_ms > 0:
            if level_weights["avg_latency_ms"] == 0:
                level_weights["avg_latency_ms"] = latency_ms
            else:
                level_weights["avg_latency_ms"] = (
                    self._alpha * latency_ms + (1 - self._alpha) * level_weights["avg_latency_ms"]
                )
        
        logger.debug(f"Updated weights for {agent} (L{level}): success={success}, latency={latency_ms:.0f}ms")
        
        # Persist weights to disk after each update
        self._persist_weights()
    
    def get_optimal_agent(self, task_description: str, level: int) -> RoutingRecommendation:
        """Get optimal agent for a task based on learned weights."""
        if not self._initialized:
            self._initialize_default_weights()
        
        if not self._weights:
            return RoutingRecommendation(
                recommended_agent="hephaestus",
                confidence=0.5,
                reason="No weights available, using default",
                weights=self._weights
            )
        
        # Score agents based on weights
        agent_scores: List[Tuple[str, float, str]] = []
        
        for agent, weights in self._weights.items():
            if weights.total_tasks == 0:
                continue
            
            # Get level-specific weights if available
            if level in weights.by_level:
                level_success_rate = weights.by_level[level]["success_rate"]
                level_latency = weights.by_level[level]["avg_latency_ms"]
            else:
                level_success_rate = weights.success_rate
                level_latency = weights.avg_latency_ms
            
            # Calculate score: success_rate * (1 - normalized_latency)
            # Lower latency is better, higher success rate is better
            normalized_latency = min(level_latency / 10000.0, 1.0)  # Cap at 10s
            score = level_success_rate * (1 - normalized_latency * 0.3)  # Latency has 30% weight
            
            reason = f"Success rate: {level_success_rate:.0%}, Avg latency: {level_latency:.0f}ms"
            agent_scores.append((agent, score, reason))
        
        if not agent_scores:
            return RoutingRecommendation(
                recommended_agent="hephaestus",
                confidence=0.5,
                reason="No agent data available, using default",
                weights=self._weights
            )
        
        # Sort by score descending
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        best_agent, best_score, best_reason = agent_scores[0]
        
        # Confidence based on data amount and score
        data_confidence = min(sum(w.total_tasks for w in self._weights.values()) / 100.0, 1.0)
        confidence = best_score * 0.7 + data_confidence * 0.3
        
        return RoutingRecommendation(
            recommended_agent=best_agent,
            confidence=confidence,
            reason=best_reason,
            weights=self._weights
        )
    
    def get_routing_weights(self) -> Dict[str, Dict[str, Any]]:
        """Get current routing weights."""
        if not self._initialized:
            self._initialize_default_weights()
        
        result = {}
        for agent, weights in self._weights.items():
            result[agent] = {
                "success_rate": weights.success_rate,
                "avg_latency_ms": weights.avg_latency_ms,
                "total_tasks": weights.total_tasks,
                "success_count": weights.success_count,
                "failure_count": weights.failure_count,
                "by_level": weights.by_level
            }
        return result
    
    def reset_weights(self) -> None:
        """Reset all weights to defaults."""
        self._weights.clear()
        self._initialized = False
        self._initialize_default_weights()


# Global instance
_routing_optimizer: Optional[RoutingWeightOptimizer] = None

def get_routing_optimizer(alpha: float = 0.1) -> RoutingWeightOptimizer:
    """Get or create the global routing optimizer."""
    global _routing_optimizer
    if _routing_optimizer is None:
        _routing_optimizer = RoutingWeightOptimizer(alpha)
    return _routing_optimizer
