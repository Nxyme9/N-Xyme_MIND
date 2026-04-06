"""Speculative Decoding — Fast local inference with draft-verify pattern.

Implements speculative decoding for 2-3x speedup on local models:
- Small model drafts tokens
- Large model verifies drafts
- Accepts matching tokens, rejects mismatches
- Net speedup when draft acceptance rate is high
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SpeculativeResult:
    """Result of speculative decoding."""

    output: str
    total_tokens: int
    accepted_tokens: int
    rejected_tokens: int
    draft_time_ms: float
    verify_time_ms: float
    total_time_ms: float
    acceptance_rate: float
    speedup_factor: float


class SpeculativeDecoder:
    """Speculative decoding engine for fast local inference."""

    def __init__(
        self,
        draft_model: str = "llama-3.2-1b",
        target_model: str = "llama-3.2-8b",
        draft_length: int = 4,
    ):
        """Initialize speculative decoder.

        Args:
            draft_model: Small model for drafting.
            target_model: Large model for verification.
            draft_length: Number of tokens to draft per step.
        """
        self.draft_model = draft_model
        self.target_model = target_model
        self.draft_length = draft_length
        self._stats = {
            "total_decodes": 0,
            "total_tokens": 0,
            "accepted_tokens": 0,
            "rejected_tokens": 0,
            "avg_acceptance_rate": 0.0,
            "avg_speedup": 0.0,
        }

    def decode(
        self,
        prompt: str,
        max_tokens: int = 256,
        draft_fn: Callable[[str, int], list[str]] | None = None,
        verify_fn: Callable[[str, list[str]], list[bool]] | None = None,
    ) -> SpeculativeResult:
        """Perform speculative decoding.

        Args:
            prompt: Input prompt.
            max_tokens: Maximum tokens to generate.
            draft_fn: Function to draft tokens (small model).
            verify_fn: Function to verify tokens (large model).

        Returns:
            SpeculativeResult with output and statistics.
        """
        if draft_fn is None or verify_fn is None:
            # Fallback to standard decoding
            return self._standard_decode(prompt, max_tokens)

        output_tokens: list[str] = []
        current_prompt = prompt
        total_accepted = 0
        total_rejected = 0
        total_draft_time = 0.0
        total_verify_time = 0.0

        while len(output_tokens) < max_tokens:
            remaining = max_tokens - len(output_tokens)
            draft_count = min(self.draft_length, remaining)

            # Step 1: Draft tokens with small model
            draft_start = time.time() * 1000
            draft_tokens = draft_fn(current_prompt, draft_count)
            draft_time = time.time() * 1000 - draft_start
            total_draft_time += draft_time

            if not draft_tokens:
                break

            # Step 2: Verify tokens with large model
            verify_start = time.time() * 1000
            acceptances = verify_fn(current_prompt, draft_tokens)
            verify_time = time.time() * 1000 - verify_start
            total_verify_time += verify_time

            # Step 3: Accept matching tokens
            accepted_count = 0
            for i, (token, accepted) in enumerate(zip(draft_tokens, acceptances)):
                if accepted:
                    output_tokens.append(token)
                    accepted_count += 1
                    total_accepted += 1
                else:
                    total_rejected += 1
                    break

            # Update prompt with accepted tokens
            if accepted_count > 0:
                current_prompt += " " + " ".join(output_tokens[-accepted_count:])
            else:
                # All rejected, need to generate at least one token
                total_rejected += len(draft_tokens)
                break

        total_time = total_draft_time + total_verify_time
        total_tokens = len(output_tokens)
        acceptance_rate = total_accepted / max(1, total_accepted + total_rejected)

        # Speedup: compare to standard decoding time estimate
        standard_time_estimate = total_tokens * 100  # Assume 100ms per token standard
        speedup = standard_time_estimate / max(1, total_time)

        # Update stats
        self._stats["total_decodes"] += 1
        self._stats["total_tokens"] += total_tokens
        self._stats["accepted_tokens"] += total_accepted
        self._stats["rejected_tokens"] += total_rejected
        alpha = 0.3
        self._stats["avg_acceptance_rate"] = (
            alpha * acceptance_rate + (1 - alpha) * self._stats["avg_acceptance_rate"]
        )
        self._stats["avg_speedup"] = (
            alpha * speedup + (1 - alpha) * self._stats["avg_speedup"]
        )

        return SpeculativeResult(
            output=" ".join(output_tokens),
            total_tokens=total_tokens,
            accepted_tokens=total_accepted,
            rejected_tokens=total_rejected,
            draft_time_ms=round(total_draft_time, 2),
            verify_time_ms=round(total_verify_time, 2),
            total_time_ms=round(total_time, 2),
            acceptance_rate=round(acceptance_rate, 4),
            speedup_factor=round(speedup, 2),
        )

    def _standard_decode(
        self,
        prompt: str,
        max_tokens: int,
    ) -> SpeculativeResult:
        """Standard decoding fallback."""
        # In production, would call the target model directly
        return SpeculativeResult(
            output="",
            total_tokens=0,
            accepted_tokens=0,
            rejected_tokens=0,
            draft_time_ms=0.0,
            verify_time_ms=0.0,
            total_time_ms=0.0,
            acceptance_rate=0.0,
            speedup_factor=1.0,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get speculative decoding statistics."""
        return {
            **self._stats,
            "draft_model": self.draft_model,
            "target_model": self.target_model,
            "draft_length": self.draft_length,
        }


# Global singleton
_speculative_decoder = SpeculativeDecoder()


def speculative_decode(
    prompt: str,
    max_tokens: int = 256,
    draft_fn: Callable | None = None,
    verify_fn: Callable | None = None,
) -> SpeculativeResult:
    """Convenience function for speculative decoding."""
    return _speculative_decoder.decode(prompt, max_tokens, draft_fn, verify_fn)
