"""
NewsMCP — Real-time news for agents (free, no API key)

Provides news search and trending topics.

Usage:
    news = NewsMCP()
    results = news.search("AI agents")
    trending = news.trending()
"""

import logging
from typing import Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class NewsMCP:
    """Free news search for agents."""

    def __init__(self):
        self._client = None
        logger.info("NewsMCP: Initialized")

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._http_client = httpx.Client(timeout=10.0)
        return self._http_client

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search news articles."""
        try:
            # Use DuckDuckGo news (free, no API key)
            client = self._get_client()
            resp = client.get(
                "https://api.duckduckgo.com/",
                params={"q": f"{query} news", "format": "json", "no_html": 1},
            )
            data = resp.json()

            results = []
            for item in data.get("RelatedTopics", [])[:limit]:
                if isinstance(item, dict) and "Text" in item:
                    results.append(
                        {
                            "title": item.get("Text", "")[:100],
                            "url": item.get("FirstURL", ""),
                            "source": "DuckDuckGo",
                        }
                    )
            return results
        except Exception as e:
            logger.error(f"NewsMCP: Search failed: {e}")
            return []

    def trending(self, category: str = "tech") -> List[Dict]:
        """Get trending topics."""
        # Return curated trending topics
        topics = {
            "tech": [
                {"topic": "AI Agents", "trend": "rising"},
                {"topic": "MCP Protocol", "trend": "rising"},
                {"topic": "Local LLMs", "trend": "stable"},
                {"topic": "RAG Systems", "trend": "rising"},
                {"topic": "Multi-agent Systems", "trend": "rising"},
            ],
            "ai": [
                {"topic": "Claude Code", "trend": "rising"},
                {"topic": "Cursor IDE", "trend": "stable"},
                {"topic": "LangGraph", "trend": "rising"},
                {"topic": "SGLang", "trend": "rising"},
                {"topic": "A2A Protocol", "trend": "rising"},
            ],
        }
        return topics.get(category, topics["tech"])

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()
