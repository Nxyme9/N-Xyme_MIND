#!/usr/bin/env python3
"""Learning Engine Bridge — connects task completion to outcome logging, cross-session transfer, and ML."""
import json, os, time, threading
from datetime import datetime

DB_PATH = os.path.expanduser("~/N-Xyme_CODE/N-Xyme_MIND/data/learning/outcomes/log.jsonl")
LEARNING_ENGINE_PATH = os.path.expanduser("~/N-Xyme_CODE/N-Xyme_MIND/archive/data_chaos/data_chaos/packages/learning_engine")

class LearningBridge:
    """Wires task completion → outcome logging → cross-session transfer → ML adaptation."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    def log_outcome(self, agent: str, task: str, success: bool, latency_ms: float = 0,
                    quality_score: float = None, task_type: str = None):
        """Log a task outcome. Called after every task completion."""
        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "agent": agent,
            "task": task[:200],
            "task_type": task_type or "general",
            "success": success,
            "latency_ms": latency_ms,
            "quality_score": quality_score,
            "context": {}
        }
        
        with self._lock:
            with open(DB_PATH, 'a') as f:
                f.write(json.dumps(entry) + '
')
        
        return entry
    
    def get_stats(self):
        """Get aggregate stats from all logged outcomes."""
        outcomes = []
        if os.path.exists(DB_PATH):
            with open(DB_PATH) as f:
                for line in f:
                    if line.strip():
                        outcomes.append(json.loads(line))
        
        stats = {"total": len(outcomes), "agents": {}}
        for o in outcomes:
            agent = o.get("agent", "unknown")
            if agent not in stats["agents"]:
                stats["agents"][agent] = {"total": 0, "successes": 0, "failures": 0}
            stats["agents"][agent]["total"] += 1
            if o.get("success"):
                stats["agents"][agent]["successes"] += 1
            else:
                stats["agents"][agent]["failures"] += 1
        
        for a in stats["agents"]:
            s = stats["agents"][a]
            s["success_rate"] = round(s["successes"] / max(s["total"], 1), 3)
        
        return stats

# Singleton
bridge = LearningBridge()

if __name__ == "__main__":
    # Test
    b = LearningBridge()
    b.log_outcome("hephaestus", "implement auth module", True, 1234, 0.95, "implementation")
    b.log_outcome("momus", "review auth code", True, 567, 0.88, "review")
    b.log_outcome("sisyphus", "delegate parallel tasks", False, 0, None, "delegation")
    print(b.get_stats())
