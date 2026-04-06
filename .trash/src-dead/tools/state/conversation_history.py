"""Conversation History — Searchable conversation history.

Ported from ant-source-code-main/history.ts
Implements searchable conversation history with:
- Fuzzy search across conversations
- Filtering by topic/agent/time
- Integration with memory system for context-aware retrieval
- Conversation summarization and indexing

Pattern: Maintains a searchable index of all conversations, enabling
quick retrieval of past interactions and context-aware suggestions.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConversationEntry:
    """A single entry in conversation history."""

    id: str
    session_id: str
    role: str
    content: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tokens: int = 0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A complete conversation session."""

    id: str
    session_id: str
    title: str = ""
    entries: list[ConversationEntry] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Get total tokens in conversation."""
        return sum(e.tokens for e in self.entries)

    @property
    def entry_count(self) -> int:
        """Get number of entries."""
        return len(self.entries)

    def add_entry(
        self,
        role: str,
        content: str,
        tokens: int = 0,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationEntry:
        """Add an entry to the conversation."""
        import uuid

        entry = ConversationEntry(
            id=str(uuid.uuid4())[:8],
            session_id=self.session_id,
            role=role,
            content=content,
            tokens=tokens,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.entries.append(entry)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return entry

    def get_entries_by_role(self, role: str) -> list[ConversationEntry]:
        """Get all entries with a specific role."""
        return [e for e in self.entries if e.role == role]

    def get_entries_by_tag(self, tag: str) -> list[ConversationEntry]:
        """Get all entries with a specific tag."""
        return [e for e in self.entries if tag in e.tags]

    def get_entries_in_timeframe(
        self,
        start: datetime,
        end: datetime,
    ) -> list[ConversationEntry]:
        """Get entries within a time frame."""
        results = []
        for entry in self.entries:
            entry_time = datetime.fromisoformat(entry.timestamp)
            if start <= entry_time <= end:
                results.append(entry)
        return results


class ConversationHistory:
    """Searchable conversation history manager."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize conversation history.

        Args:
            storage_path: Path to store conversation data.
        """
        self.conversations: dict[str, Conversation] = {}
        self.storage_path = storage_path or Path(".sisyphus/history")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._load_conversations()

    def create_conversation(
        self,
        session_id: str,
        title: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Conversation:
        """Create a new conversation.

        Args:
            session_id: Session identifier.
            title: Conversation title.
            tags: Optional tags.
            metadata: Optional metadata.

        Returns:
            Created Conversation.
        """
        import uuid

        conv_id = str(uuid.uuid4())[:8]
        conversation = Conversation(
            id=conv_id,
            session_id=session_id,
            title=title,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.conversations[conv_id] = conversation
        self._save_conversation(conversation)
        return conversation

    def get_conversation(self, conv_id: str) -> Conversation | None:
        """Get conversation by ID."""
        return self.conversations.get(conv_id)

    def get_conversation_by_session(self, session_id: str) -> Conversation | None:
        """Get conversation by session ID."""
        for conv in self.conversations.values():
            if conv.session_id == session_id:
                return conv
        return None

    def list_conversations(
        self,
        tag: str | None = None,
        session_id: str | None = None,
        limit: int = 50,
    ) -> list[Conversation]:
        """List conversations with optional filters."""
        conversations = list(self.conversations.values())

        if tag:
            conversations = [c for c in conversations if tag in c.tags]
        if session_id:
            conversations = [c for c in conversations if c.session_id == session_id]

        # Sort by updated_at (newest first)
        conversations.sort(
            key=lambda c: c.updated_at,
            reverse=True,
        )

        return conversations[:limit]

    def search_conversations(
        self,
        query: str,
        limit: int = 20,
        fuzzy: bool = True,
    ) -> list[tuple[Conversation, float]]:
        """Search conversations by content.

        Args:
            query: Search query.
            limit: Maximum results.
            fuzzy: Enable fuzzy matching.

        Returns:
            List of (conversation, score) tuples.
        """
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for conv in self.conversations.values():
            score = 0.0

            # Search in title
            if query_lower in conv.title.lower():
                score += 10.0

            # Search in entries
            for entry in conv.entries:
                content_lower = entry.content.lower()

                if fuzzy:
                    # Fuzzy matching: count word overlaps
                    content_words = set(content_lower.split())
                    overlap = len(query_words & content_words)
                    score += overlap * 2.0

                    # Bonus for exact phrase match
                    if query_lower in content_lower:
                        score += 5.0
                else:
                    # Exact matching only
                    if query_lower in content_lower:
                        score += 5.0

            if score > 0:
                results.append((conv, score))

        # Sort by score (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def search_entries(
        self,
        query: str,
        role: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[tuple[ConversationEntry, Conversation, float]]:
        """Search individual entries across all conversations.

        Args:
            query: Search query.
            role: Filter by role.
            tag: Filter by tag.
            limit: Maximum results.

        Returns:
            List of (entry, conversation, score) tuples.
        """
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for conv in self.conversations.values():
            for entry in conv.entries:
                if role and entry.role != role:
                    continue
                if tag and tag not in entry.tags:
                    continue

                score = 0.0
                content_lower = entry.content.lower()

                # Word overlap scoring
                content_words = set(content_lower.split())
                overlap = len(query_words & content_words)
                score += overlap * 2.0

                # Exact phrase bonus
                if query_lower in content_lower:
                    score += 5.0

                # Title match bonus
                if query_lower in conv.title.lower():
                    score += 3.0

                if score > 0:
                    results.append((entry, conv, score))

        # Sort by score
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]

    def get_recent_conversations(
        self, hours: int = 24, limit: int = 10
    ) -> list[Conversation]:
        """Get conversations from the last N hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results = []

        for conv in self.conversations.values():
            updated = datetime.fromisoformat(conv.updated_at)
            if updated >= cutoff:
                results.append(conv)

        results.sort(key=lambda c: c.updated_at, reverse=True)
        return results[:limit]

    def get_conversation_stats(self) -> dict[str, Any]:
        """Get conversation statistics."""
        total_entries = sum(c.entry_count for c in self.conversations.values())
        total_tokens = sum(c.total_tokens for c in self.conversations.values())

        return {
            "total_conversations": len(self.conversations),
            "total_entries": total_entries,
            "total_tokens": total_tokens,
            "avg_entries_per_conversation": total_entries
            / max(1, len(self.conversations)),
            "avg_tokens_per_conversation": total_tokens
            / max(1, len(self.conversations)),
        }

    def _save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to storage."""
        conv_file = self.storage_path / f"{conversation.id}.json"
        data = {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "title": conversation.title,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "tags": conversation.tags,
            "metadata": conversation.metadata,
            "entries": [
                {
                    "id": e.id,
                    "session_id": e.session_id,
                    "role": e.role,
                    "content": e.content,
                    "timestamp": e.timestamp,
                    "tokens": e.tokens,
                    "tags": e.tags,
                    "metadata": e.metadata,
                }
                for e in conversation.entries
            ],
        }
        conv_file.write_text(json.dumps(data, indent=2))

    def _load_conversations(self) -> None:
        """Load conversations from storage."""
        for conv_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(conv_file.read_text())
                conversation = Conversation(
                    id=data["id"],
                    session_id=data["session_id"],
                    title=data.get("title", ""),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                )
                for entry_data in data.get("entries", []):
                    entry = ConversationEntry(
                        id=entry_data["id"],
                        session_id=entry_data["session_id"],
                        role=entry_data["role"],
                        content=entry_data["content"],
                        timestamp=entry_data.get("timestamp", ""),
                        tokens=entry_data.get("tokens", 0),
                        tags=entry_data.get("tags", []),
                        metadata=entry_data.get("metadata", {}),
                    )
                    conversation.entries.append(entry)
                self.conversations[conversation.id] = conversation
            except Exception as e:
                logger.warning(f"Failed to load conversation {conv_file}: {e}")


# Global singleton
_history = ConversationHistory()


def create_conversation(
    session_id: str,
    title: str = "",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Conversation:
    """Convenience function to create a conversation."""
    return _history.create_conversation(session_id, title, tags, metadata)


def search_conversations(
    query: str,
    limit: int = 20,
    fuzzy: bool = True,
) -> list[tuple[Conversation, float]]:
    """Convenience function to search conversations."""
    return _history.search_conversations(query, limit, fuzzy)


def search_entries(
    query: str,
    role: str | None = None,
    tag: str | None = None,
    limit: int = 50,
) -> list[tuple[ConversationEntry, Conversation, float]]:
    """Convenience function to search entries."""
    return _history.search_entries(query, role, tag, limit)
