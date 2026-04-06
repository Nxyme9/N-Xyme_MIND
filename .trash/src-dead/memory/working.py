"""Working memory for active context."""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

@dataclass
class MemoryItem:
    key: str
    value: str
    timestamp: str
    activation: float = 1.0
    access_count: int = 0

class WorkingMemory:
    def __init__(self, capacity: int = 7):
        self.capacity = capacity
        self.items: dict[str, MemoryItem] = {}

    def store(self, key: str, value: str) -> MemoryItem:
        if len(self.items) >= self.capacity:
            self._evict_lowest_activation()
        item = MemoryItem(key=key, value=value, timestamp=datetime.now(timezone.utc).isoformat())
        self.items[key] = item
        return item

    def retrieve(self, key: str) -> Optional[MemoryItem]:
        if key in self.items:
            item = self.items[key]
            item.access_count += 1
            item.activation = min(1.0, item.activation + 0.1)
            return item
        return None

    def get_all(self) -> list:
        return list(self.items.values())

    def decay(self, rate: float = 0.1):
        for item in self.items.values():
            item.activation = max(0.0, item.activation - rate)

    def _evict_lowest_activation(self):
        if not self.items:
            return
        lowest_key = min(self.items.keys(), key=lambda k: self.items[k].activation)
        del self.items[lowest_key]

    def clear(self):
        self.items.clear()
