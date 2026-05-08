"""
Agent Prompt Builder — Phase 2.4: Pre-Agent Prompt Construction.

Builds enhanced prompts by injecting fingerprint context and memory context
before agent dispatch. Works WITH FingerprintActivator and PreAgentMemoryInjector.

Usage:
    from packages.orchestration.agent_prompt import AgentPromptBuilder

    builder = AgentPromptBuilder()
    enhanced = builder.build_prompt(
        base_prompt="Implement JWT auth middleware",
        agent_type="hephaestus",
        current_task="Add JWT authentication to REST API"
    )
    print(enhanced)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

MAX_INJECTION_TOKENS = 500
TOKENS_PER_CHAR = 0.25


# ============================================================================
# Result Dataclass
# ============================================================================


@dataclass
class AgentPromptResult:
    """Result of building an enhanced agent prompt."""

    enhanced_prompt: str
    injection_source: str  # "fingerprint", "memory", "both", "none"
    tokens_injected: int
    within_budget: bool
    fingerprint_context: str = ""
    memory_context: str = ""


# ============================================================================
# AgentPromptBuilder
# ============================================================================


class AgentPromptBuilder:
    """Builds enhanced prompts with injected context.

    Implements Phase 2.4 - combines fingerprint and memory context
    injection to build optimal prompts for agent dispatch.

    Features:
        - Uses FingerprintActivator for session context (Phase 1.5)
        - Uses PreAgentMemoryInjector for memory context (Phase 1.4)
        - Enforces 500 token budget for injections
        - Prioritizes sources and combines intelligently

    Attributes:
        MAX_INJECTION_TOKENS: Maximum tokens allowed for injected context.
    """

    MAX_INJECTION_TOKENS = MAX_INJECTION_TOKENS

    def __init__(self, max_tokens: int = MAX_INJECTION_TOKENS) -> None:
        """Initialize builder with optional token budget override.

        Args:
            max_tokens: Maximum tokens for injected context (default: 500).
        """
        self.max_tokens = max_tokens
        self._fingerprint_activator = None
        self._memory_injector = None
        logger.debug(f"AgentPromptBuilder initialized with max_tokens={max_tokens}")

    @property
    def fingerprint_activator(self) -> Any:
        """Lazy-load FingerprintActivator."""
        if self._fingerprint_activator is None:
            try:
                from packages.orchestration.fingerprint_activator import (
                    FingerprintActivator,
                )

                self._fingerprint_activator = FingerprintActivator()
            except ImportError as e:
                logger.warning(f"FingerprintActivator not available: {e}")
                return None
        return self._fingerprint_activator

    @property
    def memory_injector(self) -> Any:
        """Lazy-load PreAgentMemoryInjector."""
        if self._memory_injector is None:
            try:
                from packages.orchestration.memory_injector import (
                    PreAgentMemoryInjector,
                )

                self._memory_injector = PreAgentMemoryInjector(
                    max_tokens=self.max_tokens
                )
            except ImportError as e:
                logger.warning(f"PreAgentMemoryInjector not available: {e}")
                return None
        return self._memory_injector

    def build_prompt(
        self,
        base_prompt: str,
        agent_type: str,
        current_task: str,
    ) -> str:
        """Build enhanced prompt with fingerprint + memory injection.

        Performs:
        1. Get fingerprint context from FingerprintActivator (Phase 1.5)
        2. Get memory context from PreAgentMemoryInjector (Phase 1.4)
        3. Combine and inject into base prompt
        4. Enforce token budget (500 tokens max)
        5. Return enhanced prompt

        Args:
            base_prompt: The base prompt to enhance.
            agent_type: Target agent type (e.g., "hephaestus", "oracle").
            current_task: Current task description for context matching.

        Returns:
            Enhanced prompt with injected context.
        """
        result = self._build_with_injection(
            base_prompt=base_prompt,
            agent_type=agent_type,
            current_task=current_task,
        )
        return result.enhanced_prompt

    def _build_with_injection(
        self,
        base_prompt: str,
        agent_type: str,
        current_task: str,
    ) -> AgentPromptResult:
        """Internal method to build prompt with full result details.

        Args:
            base_prompt: Base prompt text.
            agent_type: Target agent type.
            current_task: Task description.

        Returns:
            AgentPromptResult with all details.
        """
        fingerprint_context = ""
        memory_context = ""
        injection_source = "none"
        total_tokens = 0

        # Step 1: Get fingerprint context (Phase 1.5)
        fp_result = self._get_fingerprint_context(current_task)
        if fp_result:
            fingerprint_context = fp_result.get("session_context", "")
            if fingerprint_context:
                injection_source = "fingerprint"
                total_tokens += self._estimate_tokens(fingerprint_context)
                logger.debug(f"Fingerprint context: {len(fingerprint_context)} chars")

        # Step 2: Get memory context (Phase 1.4) - check budget first
        remaining_budget = self.max_tokens - total_tokens
        if remaining_budget > 50:  # Only if meaningful budget left
            mem_result = self._get_memory_context(
                agent_type, current_task, remaining_budget
            )
            if mem_result:
                memory_context = mem_result
                if injection_source == "none":
                    injection_source = "memory"
                elif fingerprint_context and memory_context:
                    injection_source = "both"
                total_tokens += self._estimate_tokens(memory_context)
                logger.debug(f"Memory context: {len(memory_context)} chars")

        # Step 3: Combine injections
        injections = self._combine_injections(fingerprint_context, memory_context)

        # Step 4: Enforce token budget
        combined = self._enforce_budget(injections)

        # Step 5: Build final prompt
        final_prompt = self._build_final_prompt(base_prompt, combined, injection_source)

        final_tokens = self._estimate_tokens(combined)

        return AgentPromptResult(
            enhanced_prompt=final_prompt,
            injection_source=injection_source,
            tokens_injected=final_tokens,
            within_budget=final_tokens <= self.max_tokens,
            fingerprint_context=fingerprint_context,
            memory_context=memory_context,
        )

    def _get_fingerprint_context(self, task: str) -> Dict[str, Any]:
        """Get fingerprint context for task.

        Args:
            task: Task description.

        Returns:
            Dict with session_context and user_preferences.
        """
        activator = self.fingerprint_activator
        if activator is None:
            logger.debug("FingerprintActivator not available")
            return {}

        try:
            result = activator.before_task(task)
            if result.get("status") in ("success", "partial"):
                logger.debug(f"Fingerprint context retrieved for: {task[:30]}...")
                return result
        except Exception as e:
            logger.warning(f"Fingerprint context error: {e}")

        return {}

    def _get_memory_context(self, agent: str, task: str, budget: int) -> str:
        """Get memory context for task.

        Args:
            agent: Target agent type.
            task: Task description.
            budget: Remaining token budget.

        Returns:
            Formatted memory context or empty string.
        """
        injector = self.memory_injector
        if injector is None:
            logger.debug("PreAgentMemoryInjector not available")
            return ""

        try:
            # Adjust budget for memory injector
            adjusted_budget = min(budget, self.max_tokens)
            injector.max_tokens = adjusted_budget

            result = injector.inject(agent=agent, task=task)
            if result:
                logger.debug(f"Memory context retrieved: {len(result)} chars")
                return result
        except Exception as e:
            logger.warning(f"Memory context error: {e}")

        return ""

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0
        return int(len(text) * TOKENS_PER_CHAR)

    def _combine_injections(self, fingerprint: str, memory: str) -> str:
        """Combine fingerprint and memory injections.

        Args:
            fingerprint: Fingerprint context text.
            memory: Memory context text.

        Returns:
            Combined injection text.
        """
        parts: List[str] = []

        if fingerprint:
            parts.append(fingerprint)
        if memory:
            parts.append(memory)

        if not parts:
            return ""

        return "\n\n".join(parts)

    def _enforce_budget(self, injection: str) -> str:
        """Enforce token budget on injection text.

        Args:
            injection: Injection text to trim.

        Returns:
            Trimmed injection text within budget.
        """
        if not injection:
            return ""

        estimated = self._estimate_tokens(injection)
        if estimated <= self.max_tokens:
            return injection

        # Trim to fit budget
        max_chars = int(self.max_tokens / TOKENS_PER_CHAR)
        if max_chars > 100:
            trimmed = injection[:max_chars] + "\n[truncated to fit token budget]"
            logger.debug(f"Injection trimmed: {len(injection)} -> {len(trimmed)} chars")
            return trimmed

        return ""

    def _build_final_prompt(self, base_prompt: str, injection: str, source: str) -> str:
        """Build final enhanced prompt.

        Args:
            base_prompt: Original base prompt.
            injection: Combined injection text.
            source: Source identifier.

        Returns:
            Final enhanced prompt.
        """
        if not injection:
            return base_prompt

        # Build header
        header_lines = [
            "<!-- INJECTED CONTEXT (Phase 2.4) -->",
            f"Source: {source}",
            f"Context-Tokens: {self._estimate_tokens(injection)}/{self.max_tokens}",
            "",
        ]

        header = "\n".join(header_lines)

        return f"{header}\n{injection}\n\n<!-- BASE PROMPT -->\n{base_prompt}"

    def build_result(
        self,
        base_prompt: str,
        agent_type: str,
        current_task: str,
    ) -> AgentPromptResult:
        """Build prompt and return full result details.

        Convenience method when you need all result details.

        Args:
            base_prompt: Base prompt text.
            agent_type: Target agent type.
            current_task: Task description.

        Returns:
            AgentPromptResult with all details.
        """
        return self._build_with_injection(
            base_prompt=base_prompt,
            agent_type=agent_type,
            current_task=current_task,
        )


# ============================================================================
# Convenience Functions
# ============================================================================


def build_agent_prompt(base_prompt: str, agent_type: str, current_task: str) -> str:
    """Convenience function to build enhanced agent prompt.

    Args:
        base_prompt: Base prompt to enhance.
        agent_type: Target agent type.
        current_task: Current task description.

    Returns:
        Enhanced prompt with injected context.
    """
    builder = AgentPromptBuilder()
    return builder.build_prompt(
        base_prompt=base_prompt,
        agent_type=agent_type,
        current_task=current_task,
    )


def build_agent_prompt_with_result(
    base_prompt: str, agent_type: str, current_task: str
) -> AgentPromptResult:
    """Convenience function to build prompt with full result.

    Args:
        base_prompt: Base prompt to enhance.
        agent_type: Target agent type.
        current_task: Current task description.

    Returns:
        AgentPromptResult with all details.
    """
    builder = AgentPromptBuilder()
    return builder.build_result(
        base_prompt=base_prompt,
        agent_type=agent_type,
        current_task=current_task,
    )


# ============================================================================
# CLI (for testing)
# ============================================================================


if __name__ == "__main__":
    import sys

    # Default test
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "implement JWT authentication"

    base_prompt = "Create auth middleware for Express.js API"
    agent_type = "hephaestus"

    builder = AgentPromptBuilder()
    result = builder.build_result(
        base_prompt=base_prompt,
        agent_type=agent_type,
        current_task=task,
    )

    print(f"Task: {task}")
    print(f"Source: {result.injection_source}")
    print(f"Tokens: {result.tokens_injected}/{result.within_budget}")
    print(f"\n{'=' * 60}")
    print(f"Enhanced Prompt:\n{result.enhanced_prompt}")
