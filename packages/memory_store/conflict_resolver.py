#!/usr/bin/env python3
"""
packages.memory_store.conflict_resolver
============================
AGM (Alchourrón, Gärdenback, Makinson) belief revision for memory conflict resolution.

Handles contradictory memory updates through:
- Contraction: Remove beliefs without losing all consequences
- Revision: Add beliefs with consistency check (Levi identity)
- Expansion: Add beliefs without consistency check
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Belief Set Representation
# =============================================================================


@dataclass(frozen=True)
class BeliefSet:
    """Represents a set of propositional beliefs.

    Beliefs are stored as a frozenset of propositional formulas.
    Each formula is a string like "X is true" or "color(apple) = red".
    """

    beliefs: frozenset[str] = field(default_factory=frozenset)

    def __or__(self, other: BeliefSet) -> BeliefSet:
        """Union - add beliefs."""
        return BeliefSet(self.beliefs | other.beliefs)

    def __sub__(self, other: BeliefSet) -> BeliefSet:
        """Set difference - remove beliefs."""
        return BeliefSet(self.beliefs - other.beliefs)

    def __and__(self, other: BeliefSet) -> BeliefSet:
        """Intersection - common beliefs."""
        return BeliefSet(self.beliefs & other.beliefs)

    def __contains__(self, formula: str) -> bool:
        """Check if formula is in belief set."""
        return formula in self.beliefs

    def is_empty(self) -> bool:
        """Check if belief set is empty."""
        return len(self.beliefs) == 0

    def __len__(self) -> int:
        return len(self.beliefs)


# =============================================================================
# AGM Operations
# =============================================================================


class AGMResolver:
    """AGM belief revision operations for memory conflict resolution.

    Implements:
    - Contraction: Remove beliefs while preserving maximal subsets
    - Revision: Add beliefs with consistency check (Levi identity)
    - Expansion: Add beliefs without check
    """

    def __init__(self):
        """Initialize AGM resolver."""
        self._history: list[tuple[str, BeliefSet, BeliefSet]] = []

    def contract(self, K: BeliefSet, A: str) -> BeliefSet:
        """AGM partial meet contraction.

        Removes formula A from belief set K while preserving maximal subsets.
        Uses maxichoice contraction approach.

        Args:
            K: Current belief set
            A: Formula to remove (negation of what we want to keep)

        Returns:
            Contracted belief set
        """
        if A not in K.beliefs:
            # Formula not in beliefs, nothing to contract
            logger.debug(f"Contract: formula '{A}' not in K, returning unchanged")
            return K

        # Find maximal subsets of K that don't contain A
        candidates: list[BeliefSet] = []

        for formula in K.beliefs:
            if formula != A:
                # Check if this formula is independent of A
                test_set = BeliefSet(K.beliefs - {A})
                if not self._entails_negation(test_set, A):
                    candidates.append(test_set)

        if not candidates:
            # Nothing left after removing A
            result = BeliefSet(frozenset())
        else:
            # Use partial meet - pick the largest subset
            # Prefer sets with more elements
            max_size = max(len(c.beliefs) for c in candidates)
            largest = [c for c in candidates if len(c.beliefs) == max_size]
            result = largest[0]  # Pick first largest

        # Record history
        self._history.append(("contract", K, result))
        logger.debug(f"Contract: {K.beliefs} - '{A}' = {result.beliefs}")
        return result

    def expand(self, K: BeliefSet, A: str) -> BeliefSet:
        """AGM expansion - add belief without consistency check.

        Simple set union used when consistency check is not required.

        Args:
            K: Current belief set
            A: Formula to add

        Returns:
            Expanded belief set
        """
        if A in K.beliefs:
            return K

        result = BeliefSet(K.beliefs | {A})
        self._history.append(("expand", K, result))
        logger.debug(f"Expand: {K.beliefs} + '{A}' = {result.beliefs}")
        return result

    def revise(self, K: BeliefSet, A: str) -> BeliefSet:
        """AGM revision using Levi identity.

        K + A = (K - ¬A) + A

        First contracts the negation, then expands with the new belief.

        Args:
            K: Current belief set
            A: Formula to add (consistent with K after revision)

        Returns:
            Revised belief set
        """
        # Get negation of A
        neg_A = self._negate(A)

        # First contract the negation (K ÷ ¬A)
        K_contracted = self.contract(K, neg_A)

        # Then expand with A ((K ÷ ¬A) + A)
        result = self.expand(K_contracted, A)

        self._history.append(("revise", K, result))
        logger.debug(f"Revise: {K.beliefs} + '{A}' = {result.beliefs}")
        return result

    def _negate(self, formula: str) -> str:
        """Create negation of a formula."""
        # Simple negation patterns
        if " is true" in formula:
            return formula.replace(" is true", " is false")
        if " is false" in formula:
            return formula.replace(" is false", " is true")
        if " = " in formula and " != " not in formula:
            return formula.replace(" = ", " != ")
        if " != " in formula:
            return formula.replace(" != ", " = ")
        if "not " in formula.lower():
            return formula
        return f"NOT({formula})"

    def _entails_negation(self, K: BeliefSet, A: str) -> bool:
        """Check if K entails the negation of A.

        Simplified check - looks for explicit negation in beliefs.
        """
        neg_A = self._negate(A)
        return neg_A in K.beliefs

    def support_entails(self, K: BeliefSet, A: str) -> bool:
        """Check if belief set K entails formula A.

        Uses simple subset check - A is entailed if it's in K or implied.

        Args:
            K: Belief set to check
            A: Formula to check

        Returns:
            True if entailed
        """
        # Direct entailment
        if A in K.beliefs:
            return True

        # Check for negation - if A's negation is in K, K doesn't entail A
        neg_A = self._negate(A)
        if neg_A in K.beliefs:
            return False

        return False

    def inconsistent(self, *sets: BeliefSet) -> bool:
        """Check if belief sets are mutually inconsistent.

        Args:
            sets: Belief sets to check

        Returns:
            True if any set contradicts another
        """
        if len(sets) < 2:
            return False

        for i, Si in enumerate(sets):
            for Sj in sets[i + 1 :]:
                # Check for direct contradiction
                for formula in Si.beliefs:
                    neg = self._negate(formula)
                    if neg in Sj.beliefs:
                        logger.debug(f"Inconsistent: '{formula}' vs {Sj.beliefs}")
                        return True

        return False

    def get_history(self) -> list[tuple[str, BeliefSet, BeliefSet]]:
        """Get operation history for audit."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear operation history."""
        self._history.clear()


# =============================================================================
# Conflict Resolver for MemoryManager
# =============================================================================


@dataclass
class ConflictResolution:
    """Result of conflict resolution operation."""

    original_beliefs: BeliefSet
    resolved_beliefs: BeliefSet
    action: str  # "contract", "revise", "expand", "none"
    conflicts_detected: list[str]
    resolution_method: str


class MemoryConflictResolver:
    """Integrates AGM into MemoryManager for conflict resolution.

    Wraps AGMResolver and provides memory-specific methods.
    """

    def __init__(self):
        """Initialize conflict resolver."""
        self.agm = AGMResolver()
        self._belief_cache: dict[str, BeliefSet] = {}

    def check_conflict(
        self, memory_id: str, new_content: str, existing_memories: list[tuple[str, str]]
    ) -> list[str]:
        """Check if new memory conflicts with existing memories.

        Args:
            memory_id: ID of new memory
            new_content: Content of new memory
            existing_memories: List of (id, content) tuples

        Returns:
            List of conflicting memory IDs
        """
        new_beliefs = self._parse_content(new_content)
        conflicts = []

        for exp_id, exp_content in existing_memories:
            if exp_id == memory_id:
                continue

            exp_beliefs = self._parse_content(exp_content)

            if self.agm.inconsistent(new_beliefs, exp_beliefs):
                conflicts.append(exp_id)
                logger.debug(f"Conflict detected: '{new_content}' vs '{exp_content}'")

        return conflicts

    def resolve_conflict(
        self,
        memory_id: str,
        new_content: str,
        existing_memories: list[tuple[str, str]],
        strategy: str = "revise",
    ) -> ConflictResolution:
        """Resolve conflict between new and existing memories.

        Args:
            memory_id: ID of new memory
            new_content: Content of new memory
            existing_memories: List of (id, content) tuples
            strategy: Resolution strategy ("revise", "contract", "expand")

        Returns:
            ConflictResolution with result details
        """
        # Aggregate existing beliefs
        existing_beliefs = BeliefSet()
        for exp_id, exp_content in existing_memories:
            if exp_id != memory_id:
                existing_beliefs = existing_beliefs | self._parse_content(exp_content)

        new_beliefs = self._parse_content(new_content)

        # Check for conflicts
        conflicts = []
        for formula in new_beliefs.beliefs:
            neg = self.agm._negate(formula)
            if neg in existing_beliefs.beliefs:
                conflicts.append(formula)

        if not conflicts:
            # No conflict - just expand
            action = "none" if strategy == "expand" else "expand"
            return ConflictResolution(
                original_beliefs=existing_beliefs,
                resolved_beliefs=existing_beliefs | new_beliefs,
                action=action,
                conflicts_detected=[],
                resolution_method="no_conflict",
            )

        # Apply resolution strategy
        if strategy == "revise":
            # Use AGM revision
            resolved = existing_beliefs
            for formula in new_beliefs.beliefs:
                resolved = self.agm.revise(resolved, formula)
            method = "agm_revision"
            action = "revise"
        elif strategy == "contract":
            # Contract negation of new content
            resolved = existing_beliefs
            for formula in new_beliefs.beliefs:
                neg = self.agm._negate(formula)
                resolved = self.agm.contract(resolved, neg)
            method = "agm_contraction"
            action = "contract"
        else:
            # Expand without check
            resolved = existing_beliefs | new_beliefs
            method = "simple_expansion"
            action = "expand"

        return ConflictResolution(
            original_beliefs=existing_beliefs,
            resolved_beliefs=resolved,
            action=action,
            conflicts_detected=conflicts,
            resolution_method=method,
        )

    def _parse_content(self, content: str) -> BeliefSet:
        """Parse memory content into belief set.

        Simple parser - splits content into propositional formulas.
        """
        # Remove common phrases and split
        cleaned = content.strip()
        # Remove periods at end
        if cleaned.endswith("."):
            cleaned = cleaned[:-1]

        # Split by common delimiters
        parts = (
            cleaned.replace(", ", "|||").replace(" and ", "|||").replace(" but ", "|||")
        )
        parts = parts.split("|||")

        beliefs = frozenset(p.strip() for p in parts if p.strip())
        return BeliefSet(beliefs) if beliefs else BeliefSet(frozenset({cleaned}))

    def get_beliefs(self, memory_id: str) -> Optional[BeliefSet]:
        """Get cached beliefs for memory."""
        return self._belief_cache.get(memory_id)

    def set_beliefs(self, memory_id: str, beliefs: BeliefSet) -> None:
        """Cache beliefs for memory."""
        self._belief_cache[memory_id] = beliefs

    def clear_cache(self) -> None:
        """Clear belief cache."""
        self._belief_cache.clear()
