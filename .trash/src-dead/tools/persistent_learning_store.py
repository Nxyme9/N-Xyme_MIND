#!/usr/bin/env python3
"""Persistent Learning Store — Save/load learned tool wrapper state.

File: data/tool-learning.json

Structure:
{
  "version": 1,
  "last_updated": timestamp,
  "models": {
    "qwen2.5-coder:7b": {
      "best_tools": ["filesystem_read_text_file", "bash"],
      "failure_patterns": {"bash": ["permission denied"]},
      "success_count": 10,
      "failure_count": 3,
      "avg_latency_ms": 1500
    }
  }
}
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_PATH = Path("data/tool-learning.json")


class PersistentLearningStore:
    """Persistent storage for learned tool wrapper state."""

    def __init__(self, path: str = str(DEFAULT_PATH)):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> Dict:
        """Load existing data or create new."""
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"version": 1, "last_updated": 0, "models": {}}

    def save(self):
        """Save to disk."""
        self._data["last_updated"] = time.time()
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def update_model(self, model_name: str, learned_data: Dict):
        """Update learned data for a model."""
        if model_name not in self._data["models"]:
            self._data["models"][model_name] = {
                "best_tools": [],
                "failure_patterns": {},
                "success_count": 0,
                "failure_count": 0,
                "avg_latency_ms": 0,
            }

        model = self._data["models"][model_name]

        # Update best tools
        if "learned_tools" in learned_data:
            for tool in learned_data["learned_tools"]:
                if tool not in model["best_tools"]:
                    model["best_tools"].append(tool)

        # Update failure patterns
        if "failure_patterns" in learned_data:
            for tool, patterns in learned_data["failure_patterns"].items():
                if tool not in model["failure_patterns"]:
                    model["failure_patterns"][tool] = []
                for p in patterns:
                    if p not in model["failure_patterns"][tool]:
                        model["failure_patterns"][tool].append(p)

        # Update counts
        if "success_rate" in learned_data:
            # Estimate from success rate
            total = model["success_count"] + model["failure_count"]
            if total > 0:
                model["success_count"] = int(learned_data["success_rate"] * total)

        self.save()

    def get_model_data(self, model_name: str) -> Optional[Dict]:
        """Get learned data for a model."""
        return self._data["models"].get(model_name)

    def get_all_models(self) -> Dict:
        """Get all model data."""
        return self._data["models"]

    def clear_model(self, model_name: str):
        """Clear data for a model."""
        if model_name in self._data["models"]:
            del self._data["models"][model_name]
            self.save()


def get_learning_store(path: str = str(DEFAULT_PATH)) -> PersistentLearningStore:
    return PersistentLearningStore(path)


# Test it
if __name__ == "__main__":
    store = get_learning_store()

    # Simulate saving learned data
    test_data = {
        "learned_tools": ["filesystem_read_text_file", "bash", "grep"],
        "failure_patterns": {"bash": ["permission denied", "not found"]},
        "success_rate": 0.75,
    }

    store.update_model("qwen2.5-coder:7b", test_data)

    # Read back
    data = store.get_model_data("qwen2.5-coder:7b")
    print("✅ Persistent store working!")
    print(f"Saved data: {data}")
