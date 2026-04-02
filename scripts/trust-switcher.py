#!/usr/bin/env python3
"""
N-Xyme Trust-Based Auto-Switching (L0 Manual Mode)
Intercepts model calls and logs decisions for trust building.
Starts at L0: Always prompts, never auto-switches.
"""

import json
import logging
import os
import time
import requests
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import (
        GRAPHITI_RPC_URL as GRAPHITI_URL,
        OLLAMA_URL,
        TOOLBRIDGE_URL,
    )
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    TOOLBRIDGE_URL = os.getenv("TOOLBRIDGE_URL", "http://localhost:3100")
CATALYST_DIR = Path(__file__).parent.parent.resolve()
DECISIONS_LOG = CATALYST_DIR / "data" / "switch-decisions.jsonl"

# Ensure data dir exists
(CATALYST_DIR / "data").mkdir(parents=True, exist_ok=True)

# Model capabilities (what each model is good at)
MODEL_CAPABILITIES = {
    "llama3.2:3b-instruct-q4_K_M": {
        "speed": "fast",
        "quality": "medium",
        "tool_calling": True,
        "best_for": ["quick_tasks", "simple_qa"],
    },
    "llama3.1:8b": {
        "speed": "medium",
        "quality": "good",
        "tool_calling": True,
        "best_for": ["general", "coding"],
    },
    "qwen2.5-coder:7b": {
        "speed": "medium",
        "quality": "good",
        "tool_calling": "via_toolbridge",
        "best_for": ["coding", "refactoring"],
    },
    "qwen2.5-coder:14b-instruct-q4_0": {
        "speed": "slow",
        "quality": "excellent",
        "tool_calling": "via_toolbridge",
        "best_for": ["complex_coding", "architecture"],
    },
    "deepseek-r1:14b": {
        "speed": "slow",
        "quality": "excellent",
        "tool_calling": False,
        "best_for": ["reasoning", "analysis"],
    },
    "deepseek-coder-v2:16b": {
        "speed": "slow",
        "quality": "excellent",
        "tool_calling": False,
        "best_for": ["coding", "debugging"],
    },
    "qwen3:8b": {
        "speed": "medium",
        "quality": "good",
        "tool_calling": "via_toolbridge",
        "best_for": ["general", "multilingual"],
    },
}

# Free API models (via OpenCode Zen)
FREE_API_MODELS = {
    "mimo-v2-pro-free": {
        "speed": "fast",
        "quality": "excellent",
        "tool_calling": True,
        "best_for": ["complex", "architecture"],
    },
    "minimax-m2.5-free": {
        "speed": "fast",
        "quality": "excellent",
        "tool_calling": True,
        "best_for": ["general", "coding"],
    },
    "mimo-v2-omni-free": {
        "speed": "fast",
        "quality": "excellent",
        "tool_calling": True,
        "best_for": ["multimodal", "general"],
    },
    "mimo-v2-flash-free": {
        "speed": "very_fast",
        "quality": "good",
        "tool_calling": True,
        "best_for": ["quick_tasks"],
    },
}


class TrustSwitcher:
    # Cleanup counter
    _cleanup_counter = 0
    CLEANUP_INTERVAL = 20  # Run cleanup every 20 decisions

    def __init__(self):
        self.trust_level = "L0"  # Start at manual
        self.decision_count = 0
        self.approval_count = 0
        self.rejection_count = 0
        print(f"[Trust Switcher] Initialized at {self.trust_level} (Manual)")

    def now(self):
        return datetime.now().isoformat()

    def analyze_task(self, task_description):
        """Analyze task and recommend best model."""
        task_lower = task_description.lower()

        # Simple keyword matching (can be enhanced with LLM)
        if any(w in task_lower for w in ["quick", "simple", "fast", "one word", "yes/no"]):
            return {
                "complexity": "low",
                "recommended": "llama3.2:3b-instruct-q4_K_M",
                "reason": "Fast model for simple task",
            }

        if any(w in task_lower for w in ["code", "implement", "function", "class", "debug", "fix"]):
            if any(w in task_lower for w in ["complex", "architecture", "system", "design"]):
                return {
                    "complexity": "high",
                    "recommended": "qwen2.5-coder:14b-instruct-q4_0",
                    "reason": "Best coder for complex tasks",
                }
            return {
                "complexity": "medium",
                "recommended": "qwen2.5-coder:7b",
                "reason": "Good coder for standard tasks",
            }

        if any(w in task_lower for w in ["reason", "analyze", "think", "evaluate", "compare"]):
            return {
                "complexity": "high",
                "recommended": "deepseek-r1:14b",
                "reason": "Best reasoning model",
            }

        if any(w in task_lower for w in ["tool", "function call", "api", "mcp"]):
            return {
                "complexity": "medium",
                "recommended": "llama3.1:8b",
                "reason": "Native tool calling support",
            }

        # Default
        return {
            "complexity": "unknown",
            "recommended": "llama3.2:3b-instruct-q4_K_M",
            "reason": "Default fast model",
        }

    def log_decision(self, decision):
        """Log decision for trust tracking with periodic cleanup."""
        try:
            DECISIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(DECISIONS_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision) + "\n")

            # Periodic cleanup
            TrustSwitcher._cleanup_counter += 1
            if TrustSwitcher._cleanup_counter >= TrustSwitcher.CLEANUP_INTERVAL:
                TrustSwitcher._cleanup_counter = 0
                try:
                    import sys as _sys

                    _sys.path.insert(0, str(CATALYST_DIR))
                    from packages.auto_capture.src.data_retention import cleanup_jsonl_file

                    cleanup_jsonl_file(DECISIONS_LOG)
                except (ImportError, Exception) as e:
                    logger.debug(f"data_retention not available or cleanup failed: {e}")
        except Exception as e:
            logging.error(f"Error logging decision: {e}")

    def store_in_graphiti(self, decision):
        """Store decision in Graphiti for learning."""
        try:
            content = f"Model switch decision: {decision['current_model']} -> {decision['recommended_model']}. Reason: {decision['reason']}. User response: {decision['user_response']}. Outcome: {decision.get('outcome', 'pending')}"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "graphiti_add_episode",
                    "arguments": {
                        "name": f"switch-decision-{decision['id']}",
                        "episode_body": content,
                        "source": "trust-switcher",
                        "source_description": f"L0 manual decision at {self.now()}",
                    },
                },
            }
            requests.post(GRAPHITI_URL, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Error storing decision in Graphiti: {e}")

    def prompt_user(self, analysis, current_model):
        """L0: Always prompt user for approval."""
        self.decision_count += 1

        decision = {
            "id": f"dec-{self.decision_count}",
            "timestamp": self.now(),
            "trust_level": self.trust_level,
            "current_model": current_model,
            "recommended_model": analysis["recommended"],
            "reason": analysis["reason"],
            "complexity": analysis["complexity"],
            "user_response": None,
            "outcome": "pending",
        }

        print(f"\n{'=' * 60}")
        print(f"  MODEL SWITCH RECOMMENDATION (L0: Manual)")
        print(f"{'=' * 60}")
        print(f"  Current:  {current_model}")
        print(f"  Suggest:  {analysis['recommended']}")
        print(f"  Reason:   {analysis['reason']}")
        print(f"  Task:     {analysis['complexity']} complexity")
        print(f"{'=' * 60}")
        print(f"  [1] Approve switch")
        print(f"  [2] Keep current model")
        print(f"  [3] Choose different model")
        print(f"{'=' * 60}")

        # Log the prompt
        self.log_decision(decision)

        return decision

    def record_response(self, decision_id, response, outcome="pending"):
        """Record user response for trust building."""
        decision = {
            "id": decision_id,
            "timestamp": self.now(),
            "user_response": response,
            "outcome": outcome,
            "trust_level": self.trust_level,
        }

        if response == "approved":
            self.approval_count += 1
        elif response == "rejected":
            self.rejection_count += 1

        # Calculate trust score
        total = self.approval_count + self.rejection_count
        trust_score = self.approval_count / total if total > 0 else 0

        print(f"\n[Trust] Score: {trust_score:.1%} ({self.approval_count}/{total})")

        # Check for level promotion
        if self.trust_level == "L0" and total >= 20 and trust_score >= 0.8:
            print(f"[Trust] Ready to promote to L1 (Suggested)")
            print(f"[Trust] Run: trust-switcher promote")

        self.log_decision(decision)
        self.store_in_graphiti(decision)

        return trust_score

    def get_status(self):
        """Get current trust status."""
        total = self.approval_count + self.rejection_count
        trust_score = self.approval_count / total if total > 0 else 0

        return {
            "trust_level": self.trust_level,
            "decision_count": self.decision_count,
            "approval_count": self.approval_count,
            "rejection_count": self.rejection_count,
            "trust_score": trust_score,
            "ready_for_promotion": self.trust_level == "L0" and total >= 20 and trust_score >= 0.8,
        }


def main():
    import sys

    switcher = TrustSwitcher()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python trust-switcher.py analyze 'task description'")
        print("  python trust-switcher.py status")
        print("  python trust-switcher.py record <decision_id> <approved|rejected> [outcome]")
        return

    cmd = sys.argv[1]

    if cmd == "analyze":
        task = sys.argv[2] if len(sys.argv) > 2 else "general task"
        analysis = switcher.analyze_task(task)
        decision = switcher.prompt_user(analysis, "llama3.2:3b-instruct-q4_K_M")
        print(f"\nDecision ID: {decision['id']}")

    elif cmd == "status":
        status = switcher.get_status()
        print(json.dumps(status, indent=2))

    elif cmd == "record":
        decision_id = sys.argv[2]
        response = sys.argv[3]
        outcome = sys.argv[4] if len(sys.argv) > 4 else "pending"
        score = switcher.record_response(decision_id, response, outcome)
        print(f"Trust score: {score:.1%}")


if __name__ == "__main__":
    main()
