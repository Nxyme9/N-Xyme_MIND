"""
Session Memory Service — Store and retrieve per-session context in Graphiti.

Each session gets a unique ID. Memories are stored with session context
so they can be retrieved later.

Usage:
    memory = SessionMemory()
    memory.store("Started working on RAG service")
    memories = memory.recall("RAG")
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class SessionMemory:
    """Per-session memory using Graphiti MCP."""

    def __init__(
        self,
        graphiti_url: str = "http://localhost:8001",
        session_id: Optional[str] = None,
    ):
        self.graphiti_url = graphiti_url
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._http_client = None
        self._knowledge_graph = None
        logger.info(f"SessionMemory: Session {self.session_id}")

    def set_knowledge_graph(self, kg) -> None:
        """Set knowledge graph for dual storage."""
        self._knowledge_graph = kg

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def store(
        self,
        text: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a memory in Graphiti."""
        client = self._get_client()

        name = f"session_{self.session_id}_{int(time.time())}"
        full_text = f"[Session {self.session_id}] {text}"
        if tags:
            full_text += f" [Tags: {', '.join(tags)}]"

        try:
            resp = client.post(
                f"{self.graphiti_url}/json-rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "graphiti_add_episode",
                    "params": {
                        "name": name,
                        "text": full_text,
                        "source": "session_memory",
                        "source_description": f"Session {self.session_id}",
                    },
                    "id": f"store_{name[:10]}",
                },
            )
            data = resp.json()
            success = data.get("result", {}).get("success", False)
            if success:
                logger.info(f"SessionMemory: Stored '{text[:50]}...'")
            return success
        except Exception as e:
            logger.error(f"SessionMemory: Store failed: {e}")
            return False

    def recall(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recall memories matching query."""
        client = self._get_client()

        try:
            resp = client.post(
                f"{self.graphiti_url}/json-rpc",
                json={
                    "jsonrpc": "2.0",
                    "method": "graphiti_search_nodes",
                    "params": {"query": query, "limit": limit},
                    "id": f"recall_{query[:10]}",
                },
            )
            data = resp.json()
            episodes = data.get("result", {}).get("episodes", [])
            logger.info(f"SessionMemory: Found {len(episodes)} memories for '{query}'")
            return episodes
        except Exception as e:
            logger.error(f"SessionMemory: Recall failed: {e}")
            return []

    def recall_session(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Recall all memories from this session."""
        return self.recall(f"Session {self.session_id}", limit=limit)

    def summarize(self, query: str) -> str:
        """Get a summary of memories matching query."""
        memories = self.recall(query, limit=5)
        if not memories:
            return "No memories found."

        texts = [m.get("text", "") for m in memories]
        return "\n".join(f"- {t[:100]}" for t in texts)

    def clear_session(self):
        """Clear this session's memories (not implemented in Graphiti)."""
        logger.warning("SessionMemory: Clear not supported by Graphiti")

    def close(self):
        """Cleanup."""
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()


def create_session_memory(session_id: Optional[str] = None) -> SessionMemory:
    """Create session memory for Catalyst."""
    return SessionMemory(
        graphiti_url="http://localhost:8001",
        session_id=session_id,
    )
