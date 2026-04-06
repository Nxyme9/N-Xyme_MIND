"""Episodic memory for experiences and events."""
import requests
from typing import Optional
from datetime import datetime

GRAPHITI_URL = "http://localhost:8001/json-rpc"

class EpisodicMemory:
    def __init__(self, group_id: str = "brain-memory"):
        self.group_id = group_id

    def store(self, name: str, text: str) -> bool:
        try:
            resp = requests.post(GRAPHITI_URL, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "graphiti_add_episode",
                "params": {"name": name, "text": text, "source": "brain", "group_id": self.group_id}
            }, timeout=5)
            return resp.json().get("result", {}).get("success", False)
        except Exception:
            return False

    def search(self, query: str, max_results: int = 5) -> list:
        try:
            resp = requests.post(GRAPHITI_URL, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "graphiti_hybrid_search",
                "params": {"query": query, "max_results": max_results}
            }, timeout=5)
            return resp.json().get("result", {}).get("episodes", [])
        except Exception:
            return []

    def get_recent(self, last_n: int = 5) -> list:
        try:
            resp = requests.post(GRAPHITI_URL, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "graphiti_get_episodes",
                "params": {"group_id": self.group_id, "last_n": last_n}
            }, timeout=5)
            return resp.json().get("result", {}).get("episodes", [])
        except Exception:
            return []
