"""Hindsight Retriever — Query session memories via Hindsight MCP.

This retriever integrates with the Hindsight MCP server (hindsight_mcp.py)
to provide session memory search capabilities as part of the memory_core
retrieval pipeline.

Supports:
- Session memory recall via Hindsight's multi-strategy retrieval
- Graceful fallback if Hindsight is unavailable
- Integration with RRF fusion in TEMPRRetriever
"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Default bank ID for session memories
DEFAULT_BANK_ID = "default"


class HindsightRetriever:
    """Retriever for Hindsight session memory via MCP.

    Queries Hindsight for session-based memories using its multi-strategy
    recall (semantic, keyword, graph, temporal).
    """

    def __init__(
        self,
        bank_id: str = DEFAULT_BANK_ID,
        base_url: str = "http://localhost:8888",
        api_key: Optional[str] = None,
    ):
        """Initialize Hindsight retriever.

        Args:
            bank_id: Hindsight bank ID to query (default: "default")
            base_url: Hindsight API base URL
            api_key: Optional API key for Hindsight Cloud
        """
        self.bank_id = bank_id
        self.base_url = base_url
        self.api_key = api_key or os.environ.get("HINDSIGHT_API_KEY")
        self._client = None
        self._available = False

    def _get_client(self):
        """Lazy-load Hindsight client.

        Tries to import hindsight_client and create client instance.
        Returns None if unavailable.
        """
        if self._client is not None:
            return self._client

        # Try to import hindsight_client
        try:
            from hindsight_client import Hindsight

            self._client = Hindsight(
                base_url=self.base_url,
                api_key=self.api_key,
            )
            self._available = True
            logger.info(f"HindsightRetriever: Connected to {self.base_url}")
            return self._client

        except ImportError:
            logger.warning(
                "HindsightRetriever: hindsight_client not installed. "
                "Run: pip install hindsight-client"
            )
            self._available = False
            return None
        except Exception as e:
            logger.warning(f"HindsightRetriever: Failed to connect: {e}")
            self._available = False
            return None

    def is_available(self) -> bool:
        """Check if Hindsight is available.

        Returns:
            True if Hindsight client is connected and operational
        """
        if not self._available:
            self._get_client()
        return self._available

    def get_capabilities(self) -> List[str]:
        """Get retriever capabilities.

        Returns:
            List of capability strings
        """
        return ["semantic", "keyword", "graph", "temporal", "session_memory"]

    def search(
        self,
        query: str,
        top_k: int = 10,
        tier: Optional[str] = None,
        **kwargs,
    ) -> List[dict]:
        """Search Hindsight for session memories.

        Args:
            query: Search query text
            top_k: Number of results to return
            tier: Memory tier filter (not used for Hindsight, for API compatibility)
            **kwargs: Additional options (budget, types, max_tokens, etc.)

        Returns:
            List of result dicts with id, content, score, source
        """
        client = self._get_client()
        if client is None:
            logger.debug("HindsightRetriever: Skipping - not available")
            return []

        try:
            # Build recall options
            recall_options = {
                "bank_id": self.bank_id,
                "query": query,
            }

            # Add optional parameters if provided
            if "budget" in kwargs:
                recall_options["budget"] = kwargs["budget"]
            if "types" in kwargs:
                recall_options["types"] = kwargs["types"]
            if "max_tokens" in kwargs:
                recall_options["max_tokens"] = kwargs["max_tokens"]
            if kwargs.get("include_chunks", False):
                recall_options["include_chunks"] = True

            # Execute recall
            response = client.recall(**recall_options)

            # Convert RecallResult to dict format
            results = []
            for i, result in enumerate(response.results[:top_k]):
                results.append(
                    {
                        "id": getattr(result, "id", f"hindsight_{i}"),
                        "content": getattr(result, "text", str(result)),
                        "score": getattr(result, "score", 1.0 / (i + 1)),
                        "source": "hindsight",
                        "metadata": {
                            "type": getattr(result, "type", "observation"),
                            "bank_id": self.bank_id,
                        },
                    }
                )

            logger.info(f"HindsightRetriever: {len(results)} results for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.warning(f"HindsightRetriever: Search failed: {e}")
            return []

    def get_stats(self) -> dict:
        """Get Hindsight memory statistics.

        Returns:
            Dict with memory stats or empty dict if unavailable
        """
        client = self._get_client()
        if client is None:
            return {"available": False}

        try:
            # Try to get bank info
            if hasattr(client, "get_bank"):
                bank = client.get_bank(self.bank_id)
                return {
                    "available": True,
                    "bank_id": self.bank_id,
                    "memory_count": getattr(bank, "memory_count", 0),
                }
            return {"available": True, "bank_id": self.bank_id}
        except Exception as e:
            logger.warning(f"HindsightRetriever: Failed to get stats: {e}")
            return {"available": False, "error": str(e)}


# Module-level convenience function
def get_hindsight_retriever(
    bank_id: str = DEFAULT_BANK_ID,
    **kwargs,
) -> HindsightRetriever:
    """Get a HindsightRetriever instance.

    Args:
        bank_id: Hindsight bank ID
        **kwargs: Additional options passed to HindsightRetriever

    Returns:
        HindsightRetriever instance
    """
    return HindsightRetriever(bank_id=bank_id, **kwargs)


__all__ = ["HindsightRetriever", "get_hindsight_retriever"]
