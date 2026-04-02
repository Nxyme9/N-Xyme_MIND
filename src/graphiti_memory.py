#!/usr/bin/env python3
"""Graphiti Memory — Helper for episodic memory operations"""

import logging
import requests
from typing import List, Optional

logger = logging.getLogger("graphiti-memory")

GRAPHITI_URL = "http://localhost:8001/json-rpc"


def search_memory(query: str, max_results: int = 5) -> List[dict]:
    try:
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_hybrid_search",
                "params": {"query": query, "max_results": max_results},
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("result", {}).get("episodes", [])
    except Exception as e:
        logger.warning(f"Graphiti search failed: {e}")
        return []


def store_episode(name: str, text: str, group_id: str = "chain-runs") -> bool:
    try:
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_add_episode",
                "params": {
                    "name": name,
                    "text": text,
                    "source": "chain-orchestrator",
                    "group_id": group_id,
                },
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("result", {}).get("success", False)
    except Exception as e:
        logger.warning(f"Graphiti store failed: {e}")
        return False


def get_recent_episodes(group_id: str = "chain-runs", last_n: int = 5) -> List[dict]:
    try:
        resp = requests.post(
            GRAPHITI_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "graphiti_get_episodes",
                "params": {"group_id": group_id, "last_n": last_n},
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json().get("result", {}).get("episodes", [])
    except Exception as e:
        logger.warning(f"Graphiti get failed: {e}")
        return []
