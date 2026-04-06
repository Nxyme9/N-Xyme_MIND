"""LLM-based memory relevance selection — adapted from Claude Code's pattern.

Scans memory files, formats a manifest, and uses an LLM to select
the most relevant memories for a given query (up to 5).
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Set, Any, Dict

from src.memory.memory_files import (
    MemoryFile,
    format_memory_manifest,
    scan_memory_files,
)

logger = logging.getLogger(__name__)

# System prompt for memory selection (adapted from Claude Code)
SELECT_MEMORIES_SYSTEM_PROMPT = """You are selecting memories that will be useful as context for processing a user's query. You will be given the user's query and a list of available memory files with their filenames and descriptions.

Return a list of filenames for the memories that will clearly be useful (up to 5). Only include memories that you are certain will be helpful based on their name and description.
- If you are unsure if a memory will be useful, do not include it. Be selective and discerning.
- If there are no memories that would clearly be useful, return an empty list.
- Return ONLY a JSON array of filenames, nothing else.

Example response:
["user_profile.md", "project_goals.md"]
"""


def select_relevant_memories(
    query: str,
    memories: List[MemoryFile],
    model: str = "nomic-embed-text",
    max_results: int = 5,
) -> List[str]:
    """Use LLM to select relevant memory filenames.

    Args:
        query: User query to find relevant memories for
        memories: List of available memory files
        model: Ollama model to use for selection
        max_results: Maximum number of memories to select

    Returns:
        List of selected filenames
    """
    if not memories:
        return []

    # Format manifest for LLM
    manifest = format_memory_manifest(memories)

    user_prompt = (
        f"User query: {query}\n\n"
        f"Available memories:\n{manifest}\n\n"
        f"Return up to {max_results} filenames as a JSON array."
    )

    try:
        import httpx

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": f"{SELECT_MEMORIES_SYSTEM_PROMPT}\n\n{user_prompt}",
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")

            # Parse JSON response
            try:
                selected = json.loads(response_text)
                if isinstance(selected, list):
                    # Validate filenames exist
                    valid_filenames = {m.filename for m in memories}
                    return [f for f in selected if f in valid_filenames][:max_results]
            except json.JSONDecodeError:
                # Fallback: extract filenames from text
                import re

                filenames = re.findall(r"[\w-]+\.md", response_text)
                valid_filenames = {m.filename for m in memories}
                return [f for f in filenames if f in valid_filenames][:max_results]

    except Exception as e:
        logger.warning(f"LLM memory selection failed: {e}")
        # Fallback: return most recent memories
        return [m.filename for m in memories[:max_results]]

    return []  # type: ignore[unreachable]


def find_relevant_memories(
    query: str,
    memory_dir: str,
    max_results: int = 5,
    already_surfaced: Optional[Set[str]] = None,
) -> List[MemoryFile]:
    """Find memory files relevant to a query.

    Scans memory directory, filters out already-surfaced files,
    and uses LLM to select the most relevant ones.

    Args:
        query: User query
        memory_dir: Path to memory directory
        max_results: Maximum memories to return
        already_surfaced: Set of filenames already shown to user

    Returns:
        List of relevant MemoryFile objects
    """
    already = already_surfaced or set()

    # Scan memory files
    memories = scan_memory_files(memory_dir)

    # Filter out already-surfaced
    memories = [m for m in memories if m.filename not in already]

    if not memories:
        return []

    # Select relevant memories via LLM
    selected_filenames = select_relevant_memories(
        query, memories, max_results=max_results
    )

    # Map filenames back to MemoryFile objects
    by_filename = {m.filename: m for m in memories}
    selected = [by_filename[f] for f in selected_filenames if f in by_filename]

    return selected


def get_memory_context_for_query(
    query: str,
    memory_dir: str,
    max_results: int = 5,
) -> str:
    """Get formatted memory context for a query.

    Returns a text block of relevant memories to inject into the system prompt.

    Args:
        query: User query
        memory_dir: Path to memory directory
        max_results: Maximum memories to include

    Returns:
        Formatted text block of relevant memories
    """
    memories = find_relevant_memories(query, memory_dir, max_results)

    if not memories:
        return ""

    sections = []
    for m in memories:
        tag = f"[{m.memory_type.value}] " if m.memory_type else ""
        sections.append(f"## {tag}{m.filename}\n\n{m.content}")

    return "\n\n---\n\n".join(sections)
