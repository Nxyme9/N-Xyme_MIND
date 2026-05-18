#!/usr/bin/env python3
"""Unified Memory + Learning + Consciousness bridge.
Every task completion feeds ALL three systems simultaneously."""
import json, os, time, threading
from datetime import datetime

ROOT = os.path.expanduser("~/N-Xyme_CODE/N-Xyme_MIND")
OUTCOMES_FILE = os.path.join(ROOT, "data/learning/outcomes/log.jsonl")
CONSCIOUSNESS_DIR = os.path.join(ROOT, "data/memory/consciousness")

class UnifiedBridge:
    """One connection: task outcome → memory + learning + consciousness."""
    
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
        os.makedirs(os.path.dirname(OUTCOMES_FILE), exist_ok=True)
        os.makedirs(CONSCIOUSNESS_DIR, exist_ok=True)
    
    def record(self, agent: str, task: str, success: bool, latency_ms: float = 0,
               quality: float = None, task_type: str = None):
        """Record task outcome → feeds ALL three systems simultaneously."""
        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "agent": agent,
            "task": task[:200],
            "task_type": task_type or "general",
            "success": success,
            "latency_ms": latency_ms,
            "quality_score": quality
        }
        
        # 1. MEMORY — store as searchable memory entry
        mem_path = os.path.join(ROOT, "data/memory/holographic-memory.json")
        try:
            mems = json.load(open(mem_path)) if os.path.exists(mem_path) else []
            mems.append({
                "id": f"outcome_{int(entry['timestamp'])}",
                "content": f"[{agent}] {task[:100]} → {'✅' if success else '❌'} ({latency_ms}ms)",
                "category": f"agent:{agent}",
                "timestamp": entry["timestamp"],
                "tags": ["outcome", agent, "success" if success else "failure"]
            })
            json.dump(mems, open(mem_path, 'w'), indent=2)
        except:
            pass
        
        # 2. LEARNING — log to outcomes file
        os.makedirs(os.path.dirname(OUTCOMES_FILE), exist_ok=True)
        with open(OUTCOMES_FILE, 'a') as f:
            f.write(json.dumps(entry) + chr(10))
        
        # 3. CONSCIOUSNESS — update agent identity
        agent_file = os.path.join(CONSCIOUSNESS_DIR, f"{agent}.json")
        identity = json.load(open(agent_file)) if os.path.exists(agent_file) else {
            "agent": agent, "created_at": time.time(), "outcomes": [],
            "total_tasks": 0, "successes": 0, "failures": 0
        }
        identity["total_tasks"] += 1
        if success: identity["successes"] += 1
        else: identity["failures"] += 1
        identity["outcomes"].append(entry)
        if len(identity["outcomes"]) > 100:
            identity["outcomes"] = identity["outcomes"][-100:]
        json.dump(identity, open(agent_file, 'w'), indent=2)
        
        return {
            "agent": agent,
            "total_tasks": identity["total_tasks"],
            "success_rate": round(identity["successes"] / max(identity["total_tasks"], 1), 3),
            "stored_in": ["memory", "learning", "consciousness"]
        }

bridge = UnifiedBridge()
