"""
Correction buffer — logs and manages routing corrections.
Story 4.1: Every correction persisted to JSONL, buffer count tracked.

Usage:
    from hot.collector import CorrectionBuffer
    
    buffer = CorrectionBuffer("data/corrections.jsonl")
    buffer.add("query text", "wrong_tool", "correct_tool", source="user", confidence=0.8)
    print(f"Total corrections: {buffer.count}")
    corrections = buffer.load_since(timestamp)
"""

import json
import os
import time
import threading
from typing import Optional


class CorrectionBuffer:
    """
    Thread-safe correction logging buffer.
    Persists corrections to JSONL, tracks count for retrain trigger.
    """
    
    def __init__(self, path: str = "data/corrections.jsonl"):
        """
        Initialize correction buffer.
        
        Args:
            path: Path to JSONL file for corrections
        """
        self.path = path
        self._count = 0
        self._lock = threading.Lock()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    
    def add(
        self,
        query: str,
        wrong_tool: str,
        correct_tool: str,
        source: str = "user",
        confidence: float = 0.0
    ) -> None:
        """
        Log a correction entry. Thread-safe, minimal overhead.
        
        Args:
            query: The user's query that was misrouted
            wrong_tool: The tool that was incorrectly selected
            correct_tool: The correct tool that should have been selected
            source: Source of correction ("user", "audit", "hebbian")
            confidence: Confidence score of the correction (0.0-1.0)
        """
        entry = {
            "query": query,
            "wrong_tool": wrong_tool,
            "correct_tool": correct_tool,
            "timestamp": time.time(),
            "source": source,
            "confidence": confidence
        }
        
        with self._lock:
            with open(self.path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self._count += 1
    
    @property
    def count(self) -> int:
        """Number of corrections since last retrain (reset)."""
        with self._lock:
            return self._count
    
    def load_since(self, since_timestamp: float = 0) -> list[dict]:
        """
        Load all corrections after a given timestamp.
        
        Args:
            since_timestamp: Unix timestamp to load corrections after
            
        Returns:
            List of correction dictionaries
        """
        entries = []
        
        if not os.path.exists(self.path):
            return entries
        
        with self._lock:
            with open(self.path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("timestamp", 0) > since_timestamp:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        return entries
    
    def load_recent(self, n: int = 100) -> list[dict]:
        """
        Load the n most recent corrections.
        
        Args:
            n: Number of recent corrections to load
            
        Returns:
            List of correction dictionaries (most recent first)
        """
        entries = []
        
        if not os.path.exists(self.path):
            return entries
        
        with self._lock:
            # Read all and take last n
            with open(self.path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line.strip())
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        return entries[-n:]
    
    def reset_count(self) -> None:
        """Reset the correction count after retrain completes."""
        with self._lock:
            self._count = 0
    
    def get_statistics(self) -> dict:
        """
        Get correction statistics.
        
        Returns:
            Dictionary with correction counts by source and tool pair
        """
        corrections = self.load_since(0)  # Load all
        
        stats = {
            "total": len(corrections),
            "by_source": {},
            "by_tool_pair": {},
            "avg_confidence": 0.0
        }
        
        if not corrections:
            return stats
        
        confidences = []
        
        for c in corrections:
            # By source
            source = c.get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
            
            # By tool pair
            pair = (c.get("wrong_tool", ""), c.get("correct_tool", ""))
            if pair != ("", ""):
                pair_key = f"{pair[0]} -> {pair[1]}"
                stats["by_tool_pair"][pair_key] = stats["by_tool_pair"].get(pair_key, 0) + 1
            
            # Confidence
            conf = c.get("confidence", 0.0)
            if conf > 0:
                confidences.append(conf)
        
        if confidences:
            stats["avg_confidence"] = sum(confidences) / len(confidences)
        
        return stats
    
    def clear(self) -> None:
        """Clear all corrections and reset count."""
        with self._lock:
            self._count = 0
            if os.path.exists(self.path):
                os.remove(self.path)


# Convenience function for quick testing
def test_collector():
    """Test the correction buffer."""
    import tempfile
    
    # Use temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        path = f.name
    
    buffer = CorrectionBuffer(path)
    
    # Add some corrections
    buffer.add("How do I save to memory?", "session_start", "memory_write", source="user", confidence=0.95)
    buffer.add("What's in memory?", "session_status", "memory_read", source="audit", confidence=0.9)
    buffer.add("test query", "wrong", "correct", source="hebbian", confidence=0.8)
    
    print(f"Correction count: {buffer.count}")
    
    # Load corrections
    corrections = buffer.load_since(0)
    print(f"Loaded {len(corrections)} corrections")
    
    for c in corrections:
        print(f"  {c['wrong_tool']} -> {c['correct_tool']}: {c['query'][:30]}...")
    
    # Get stats
    stats = buffer.get_statistics()
    print(f"Stats: {stats}")
    
    # Cleanup
    buffer.clear()
    os.unlink(path)
    
    print("Collector test passed!")


if __name__ == "__main__":
    test_collector()