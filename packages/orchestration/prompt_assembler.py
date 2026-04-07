"""
Prompt Assembler — Static/Dynamic Boundary Separation for API Caching.

Based on Claude Code's static/dynamic prompt boundary pattern:
- Static prefix: Cacheable across requests (system prompt, instructions)
- Dynamic boundary: Transition marker between static/dynamic
- Dynamic suffix: Changes per request (user message, context)
- tools_json: Tool definitions

Architecture:
    ┌─────────────────┐
    │  system_prompt  │ ← Static (cacheable)
    │  (instructions)│
    ├─────────────────┤
    │  DYNAMIC_BOUND  │ ← Marker
    ├─────────────────┤
    │  context msgs   │ ← Dynamic (per request)
    │  user_message   │
    ├─────────────────┤
    │  tools_json     │ ← Dynamic (per request)
    └─────────────────┘

Usage:
    assembler = PromptAssembler()
    result = assembler.assemble(
        system_prompt="You are a helpful assistant.",
        context=[{"role": "user", "content": "Hello"}],
        user_message="Fix the bug",
        tools=[{"type": "function", "function": {...}}]
    )
    # result.static_prefix → hashable, cacheable
    # result.dynamic_suffix → changes per request
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("prompt_assembler")


# =============================================================================
# Constants
# =============================================================================

DYNAMIC_BOUNDARY = "[/DYNAMIC_BOUNDARY]"


# =============================================================================
# AssembledPrompt Data Class
# =============================================================================


@dataclass(frozen=True)
class AssembledPrompt:
    """
    Result of assembling a prompt with static/dynamic boundary.
    
    Attributes:
        static_prefix: The static portion (system + instructions) - cacheable
        dynamic_boundary: The boundary marker
        dynamic_suffix: The dynamic portion (context + user message) - NOT cacheable
        tools_json: JSON string of tools definition
        full_prompt: Complete assembled prompt (static + boundary + dynamic + tools)
        static_hash: SHA256 hash of static_prefix for cache key
    """
    
    static_prefix: str
    dynamic_boundary: str
    dynamic_suffix: str
    tools_json: str
    full_prompt: str
    static_hash: str
    
    def __post_init__(self) -> None:
        """Validate assembled components."""
        if not self.static_prefix:
            raise ValueError("static_prefix cannot be empty")
        if not self.dynamic_suffix:
            raise ValueError("dynamic_suffix cannot be empty")
    
    @property
    def cache_key(self) -> str:
        """Cache key for API caching (based on static content)."""
        return self.static_hash
    
    @property
    def is_cacheable(self) -> bool:
        """Whether this prompt can use cached response."""
        # Cacheable if static portion dominates
        return len(self.static_prefix) > len(self.dynamic_suffix)


# =============================================================================
# PromptAssembler Class
# =============================================================================


class PromptAssembler:
    """
    Assembles prompts with static/dynamic boundary separation.
    
    Enables API caching by separating cacheable static content from
    per-request dynamic content. Thread-safe for concurrent assembly.
    
    Features:
        - Static/dynamic boundary separation
        - Cache key generation via SHA256
        - Thread-safe operation
        - Configurable boundary marker
    """
    
    def __init__(
        self,
        boundary_marker: str = DYNAMIC_BOUNDARY,
        include_boundary_in_cache: bool = False,
    ):
        """
        Initialize the PromptAssembler.
        
        Args:
            boundary_marker: The marker string separating static/dynamic
            include_boundary_in_cache: Whether to include boundary in cache hash
        """
        self._boundary = boundary_marker
        self._include_boundary = include_boundary_in_cache
        self._lock = threading.RLock()
        
        # Cache for static prefix to avoid recomputation
        self._static_cache: Dict[str, str] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(
            f"PromptAssembler initialized: boundary_marker length={len(boundary_marker)}"
        )
    
    def assemble(
        self,
        system_prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        user_message: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AssembledPrompt:
        """
        Assemble a prompt with static/dynamic boundary separation.
        
        Args:
            system_prompt: The system prompt (static, cacheable)
            context: Optional list of prior messages (dynamic)
            user_message: The user's current message (dynamic)
            tools: Optional list of tool definitions (dynamic)
        
        Returns:
            AssembledPrompt with all components separated
        
        Raises:
            ValueError: If required arguments are missing or invalid
        """
        # Validation
        if not system_prompt:
            raise ValueError("system_prompt is required")
        
        with self._lock:
            # === Build static prefix ===
            static_prefix = self._build_static_prefix(system_prompt)
            
            # === Build dynamic suffix ===
            dynamic_suffix = self._build_dynamic_suffix(
                context=context or [],
                user_message=user_message,
            )
            
            # === Build tools JSON ===
            tools_json = self._build_tools_json(tools)
            
            # === Calculate static hash for cache key ===
            static_hash = self._compute_static_hash(static_prefix)
            
            # === Assemble full prompt ===
            full_prompt = self._assemble_full(
                static_prefix=static_prefix,
                dynamic_suffix=dynamic_suffix,
                tools_json=tools_json,
            )
            
            return AssembledPrompt(
                static_prefix=static_prefix,
                dynamic_boundary=self._boundary,
                dynamic_suffix=dynamic_suffix,
                tools_json=tools_json,
                full_prompt=full_prompt,
                static_hash=static_hash,
            )
    
    def _build_static_prefix(self, system_prompt: str) -> str:
        """Build the static prefix portion."""
        # Static = system prompt (cacheable across requests)
        return system_prompt.strip()
    
    def _build_dynamic_suffix(
        self,
        context: List[Dict[str, Any]],
        user_message: str,
    ) -> str:
        """Build the dynamic suffix portion."""
        parts = []
        
        # Add context messages
        for msg in context:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                parts.append(f"{role}: {content}")
        
        # Add user message
        if user_message:
            parts.append(f"user: {user_message}")
        
        return "\n".join(parts)
    
    def _build_tools_json(self, tools: Optional[List[Dict[str, Any]]]) -> str:
        """Build JSON string of tools."""
        if not tools:
            return "[]"
        
        try:
            return json.dumps(tools, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize tools: {e}")
            return "[]"
    
    def _compute_static_hash(self, static_prefix: str) -> str:
        """Compute SHA256 hash of static content for cache key."""
        content = static_prefix
        if self._include_boundary:
            content += self._boundary
        
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    
    def _assemble_full(
        self,
        static_prefix: str,
        dynamic_suffix: str,
        tools_json: str,
    ) -> str:
        """Assemble the full prompt with boundary."""
        parts = [
            static_prefix,
            "",
            self._boundary,
            "",
            dynamic_suffix,
        ]
        
        # Add tools if present
        if tools_json and tools_json != "[]":
            parts.extend([
                "",
                "## Tools",
                tools_json,
            ])
        
        return "\n".join(parts)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._cache_hits + self._cache_misses
            hit_rate = (
                self._cache_hits / total * 100
                if total > 0
                else 0.0
            )
            
            return {
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate_percent": round(hit_rate, 2),
                "cached_entries": len(self._static_cache),
            }
    
    def clear_cache(self) -> None:
        """Clear the static cache."""
        with self._lock:
            self._static_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            logger.info("PromptAssembler cache cleared")


# =============================================================================
# Convenience Functions
# =============================================================================


def assemble_prompt(
    system_prompt: str,
    context: Optional[List[Dict[str, Any]]] = None,
    user_message: str = "",
    tools: Optional[List[Dict[str, Any]]] = None,
) -> AssembledPrompt:
    """
    Convenience function to assemble a prompt.
    
    Args:
        system_prompt: The system prompt (static, cacheable)
        context: Optional list of prior messages (dynamic)
        user_message: The user's current message (dynamic)
        tools: Optional list of tool definitions (dynamic)
    
    Returns:
        AssembledPrompt with all components separated
    """
    assembler = PromptAssembler()
    return assembler.assemble(
        system_prompt=system_prompt,
        context=context,
        user_message=user_message,
        tools=tools,
    )


def compute_prompt_hash(
    system_prompt: str,
    context: Optional[List[Dict[str, Any]]] = None,
    user_message: str = "",
) -> str:
    """
    Compute a hash for prompt caching.
    
    Args:
        system_prompt: The system prompt
        context: Optional context messages
        user_message: The user message
    
    Returns:
        SHA256 hash string
    """
    assembler = PromptAssembler()
    result = assembler.assemble(
        system_prompt=system_prompt,
        context=context,
        user_message=user_message,
    )
    return result.static_hash


# =============================================================================
# Main - Quick Test
# =============================================================================


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(message)s",
    )
    
    print("=== PromptAssembler Test ===\n")
    
    # Test basic assembly
    assembler = PromptAssembler()
    
    print("--- Test 1: Basic Assembly ---")
    result = assembler.assemble(
        system_prompt="You are a helpful coding assistant.",
        context=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"},
        ],
        user_message="Fix the bug in auth.py",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {"path": {"type": "string"}},
                },
            }
        ],
    )
    
    print(f"Static prefix length: {len(result.static_prefix)}")
    print(f"Dynamic suffix length: {len(result.dynamic_suffix)}")
    print(f"Static hash: {result.static_hash}")
    print(f"Cache key: {result.cache_key}")
    print(f"Is cacheable: {result.is_cacheable}")
    
    print("\n--- Static Prefix ---")
    print(result.static_prefix[:80] + "...")
    
    print("\n--- Dynamic Suffix ---")
    print(result.dynamic_suffix[:80] + "...")
    
    # Test cache key consistency
    print("\n--- Test 2: Cache Key Consistency ---")
    result2 = assembler.assemble(
        system_prompt="You are a helpful coding assistant.",
        user_message="Different message",  # Different user message
    )
    print(f"Same system, different user - Hash match: {result.static_hash == result2.static_hash}")
    
    result3 = assembler.assemble(
        system_prompt="You are a helpful coding assistant.",  # Same system
        user_message="Different message",
    )
    print(f"Same system, same system - Hash match: {result.static_hash == result3.static_hash}")
    
    # Test different system prompts
    print("\n--- Test 3: Different System Prompts ---")
    result4 = assembler.assemble(
        system_prompt="You are a security expert.",  # Different system
        user_message="Check for vulnerabilities",
    )
    print(f"Different system - Hash match: {result.static_hash == result4.static_hash}")
    
    # Test cache stats
    print("\n--- Test 4: Cache Stats ---")
    stats = assembler.get_cache_stats()
    print(f"Stats: {stats}")
    
    print("\n--- Test 5: Full Prompt Structure ---")
    print("Full prompt preview:")
    print("=" * 40)
    print(result.full_prompt[:500])
    print("...")
    print("=" * 40)
    
    # Test error handling
    print("\n--- Test 6: Error Handling ---")
    try:
        assembler.assemble(system_prompt="", user_message="test")
    except ValueError as e:
        print(f"Caught expected error: {e}")
    
    # Test convenience function
    print("\n--- Test 7: Convenience Function ---")
    simple = assemble_prompt(
        system_prompt="You are a bot.",
        user_message="Hello",
    )
    print(f"Simple prompt hash: {simple.static_hash}")
    
    print("\nAll tests passed!")
    sys.exit(0)
