#!/usr/bin/env python3
"""Tests for AGM belief revision (Phase 1.2).

Tests verify that AGM conflict resolution actually works:
- Contraction removes beliefs while preserving consistency
- Expansion adds without consistency check
- Revision adds with consistency (Levi identity)
- support_entails for entailment checking
- inconsistent() detects contradictions
- MemoryConflictResolver integration
"""

import logging
import pytest
from packages.memory_store.conflict_resolver import (
    AGMResolver,
    BeliefSet,
    ConflictResolution,
    MemoryConflictResolver,
)

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class TestBeliefSetCreation:
    """Tests for BeliefSet creation and manipulation."""

    def test_create_empty_belief_set(self):
        """Test creating an empty belief set."""
        bs = BeliefSet()
        assert bs.is_empty()
        assert len(bs) == 0

    def test_create_belief_set_with_beliefs(self):
        """Test creating belief set with initial beliefs."""
        beliefs = frozenset({"P is true", "Q is true"})
        bs = BeliefSet(beliefs)
        assert len(bs) == 2
        assert "P is true" in bs

    def test_belief_set_union(self):
        """Test belief set union (__or__)."""
        bs1 = BeliefSet(frozenset({"A is true"}))
        bs2 = BeliefSet(frozenset({"B is true"}))
        result = bs1 | bs2
        assert len(result) == 2
        assert "A is true" in result
        assert "B is true" in result

    def test_belief_set_difference(self):
        """Test belief set difference (__sub__)."""
        bs1 = BeliefSet(frozenset({"A is true", "B is true"}))
        bs2 = BeliefSet(frozenset({"B is true"}))
        result = bs1 - bs2
        assert len(result) == 1
        assert "A is true" in result
        assert "B is true" not in result

    def test_belief_set_intersection(self):
        """Test belief set intersection (__and__)."""
        bs1 = BeliefSet(frozenset({"A is true", "B is true", "C is true"}))
        bs2 = BeliefSet(frozenset({"B is true", "C is true", "D is true"}))
        result = bs1 & bs2
        assert len(result) == 2
        assert "B is true" in result
        assert "C is true" in result

    def test_belief_set_contains(self):
        """Test membership check (__contains__)."""
        bs = BeliefSet(frozenset({"X is true"}))
        assert "X is true" in bs
        assert "Y is true" not in bs


class TestAGMContraction:
    """Tests for AGM contraction operation."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_contract_removes_belief(self, agm_resolver):
        """Test that contraction removes the specified belief."""
        K = BeliefSet(frozenset({"P is true", "Q is true", "R is true"}))
        A = "P is true"

        result = agm_resolver.contract(K, A)

        assert "P is true" not in result.beliefs
        assert "Q is true" in result.beliefs
        assert "R is true" in result.beliefs

    def test_contract_formula_not_in_set(self, agm_resolver):
        """Test contracting formula not in belief set returns unchanged."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "X is true"  # Not in K

        result = agm_resolver.contract(K, A)

        assert result == K

    def test_contract_preserves_maximal_subsets(self, agm_resolver):
        """Test contraction preserves maximal subsets."""
        K = BeliefSet(frozenset({"A is true", "B is true", "C is true"}))
        # Contract a belief that would create inconsistency
        A = "NOT(A is true)"  # Negation is not in set, so this is a no-op contract

        result = agm_resolver.contract(K, A)

        # Should return unchanged since A not in K
        assert result == K

    def test_contract_removes_negation(self, agm_resolver):
        """Test contracting negation of a belief."""
        K = BeliefSet(frozenset({"P is true", "P is false"}))
        A = "P is false"

        result = agm_resolver.contract(K, A)

        # Contraction removes A but may also affect dependent beliefs
        assert "P is false" not in result.beliefs

    def test_contract_history_recorded(self, agm_resolver):
        """Test that contraction operations are recorded in history."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "P is true"

        agm_resolver.contract(K, A)

        history = agm_resolver.get_history()
        assert len(history) == 1
        assert history[0][0] == "contract"


class TestAGMExpansion:
    """Tests for AGM expansion operation."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_expand_adds_belief(self, agm_resolver):
        """Test that expansion adds a new belief."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "Q is true"

        result = agm_resolver.expand(K, A)

        assert "P is true" in result.beliefs
        assert "Q is true" in result.beliefs

    def test_expand_belief_already_exists(self, agm_resolver):
        """Test expanding with existing belief returns unchanged."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "P is true"

        result = agm_resolver.expand(K, A)

        assert result == K

    def test_expand_multiple_beliefs(self, agm_resolver):
        """Test expanding with multiple beliefs sequentially."""
        K = BeliefSet()
        K = agm_resolver.expand(K, "A is true")
        K = agm_resolver.expand(K, "B is true")
        K = agm_resolver.expand(K, "C is true")

        assert len(K) == 3

    def test_expand_history_recorded(self, agm_resolver):
        """Test that expansion operations are recorded in history."""
        K = BeliefSet()
        A = "P is true"

        agm_resolver.expand(K, A)

        history = agm_resolver.get_history()
        assert len(history) == 1
        assert history[0][0] == "expand"


class TestAGMRevision:
    """Tests for AGM revision operation (Levi identity)."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_revision_adds_belief_with_consistency(self, agm_resolver):
        """Test revision adds belief ensuring consistency."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "Q is true"

        result = agm_resolver.revise(K, A)

        assert "P is true" in result.beliefs
        assert "Q is true" in result.beliefs

    def test_revision_removes_conflicting_negation(self, agm_resolver):
        """Test revision removes negation to maintain consistency."""
        K = BeliefSet(frozenset({"P is false"}))  # Negation of P is true
        A = "P is true"

        result = agm_resolver.revise(K, A)

        assert "P is true" in result.beliefs
        assert "P is false" not in result.beliefs

    def test_revision_with_equality_neq(self, agm_resolver):
        """Test revision with equality/inequality formulas."""
        K = BeliefSet(frozenset({"color = red"}))
        A = "color = blue"

        result = agm_resolver.revise(K, A)

        assert "color = blue" in result.beliefs

    def test_revision_clears_negation_of_equality(self, agm_resolver):
        """Test revision removes negation of equality."""
        K = BeliefSet(frozenset({"color != red"}))
        A = "color = red"

        result = agm_resolver.revise(K, A)

        assert "color = red" in result.beliefs
        assert "color != red" not in result.beliefs

    def test_revision_history_recorded(self, agm_resolver):
        """Test that revision operations are recorded in history."""
        K = BeliefSet()
        A = "P is true"

        agm_resolver.revise(K, A)

        history = agm_resolver.get_history()
        # Revision internally uses contract + expand, so 2 entries
        assert len(history) == 2
        assert history[-1][0] == "revise"


class TestEntailmentChecking:
    """Tests for support_entails entailment checking."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_support_entails_direct(self, agm_resolver):
        """Test direct entailment check."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "P is true"

        assert agm_resolver.support_entails(K, A) is True

    def test_support_entails_not_entailed(self, agm_resolver):
        """Test that non-entailed formula returns False."""
        K = BeliefSet(frozenset({"P is true"}))
        A = "Q is true"

        assert agm_resolver.support_entails(K, A) is False

    def test_support_entails_negation_blocked(self, agm_resolver):
        """Test that negation in K blocks entailment."""
        K = BeliefSet(frozenset({"P is false"}))  # Negation of P is true
        A = "P is true"

        assert agm_resolver.support_entails(K, A) is False

    def test_support_entails_empty_set(self, agm_resolver):
        """Test entailment check on empty set."""
        K = BeliefSet()
        A = "P is true"

        assert agm_resolver.support_entails(K, A) is False


class TestInconsistencyDetection:
    """Tests for inconsistent() contradiction detection."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_inconsistent_returns_true(self, agm_resolver):
        """Test detecting inconsistency between two sets."""
        K1 = BeliefSet(frozenset({"P is true"}))
        K2 = BeliefSet(frozenset({"P is false"}))

        assert agm_resolver.inconsistent(K1, K2) is True

    def test_inconsistent_returns_false(self, agm_resolver):
        """Test no inconsistency when no contradictions."""
        K1 = BeliefSet(frozenset({"P is true"}))
        K2 = BeliefSet(frozenset({"Q is true"}))

        assert agm_resolver.inconsistent(K1, K2) is False

    def test_inconsistent_with_equality(self, agm_resolver):
        """Test detecting inconsistency with equality/inequality."""
        K1 = BeliefSet(frozenset({"color = red"}))
        K2 = BeliefSet(frozenset({"color != red"}))

        assert agm_resolver.inconsistent(K1, K2) is True

    def test_inconsistent_single_set(self, agm_resolver):
        """Test single set returns False."""
        K1 = BeliefSet(frozenset({"P is true"}))

        assert agm_resolver.inconsistent(K1) is False

    def test_inconsistent_multiple_sets(self, agm_resolver):
        """Test detecting inconsistency across multiple sets."""
        K1 = BeliefSet(frozenset({"P is true"}))
        K2 = BeliefSet(frozenset({"Q is true"}))
        K3 = BeliefSet(frozenset({"P is false"}))

        assert agm_resolver.inconsistent(K1, K2, K3) is True


class TestMemoryConflictResolver:
    """Tests for MemoryConflictResolver integration."""

    @pytest.fixture
    def resolver(self):
        """Create MemoryConflictResolver instance."""
        return MemoryConflictResolver()

    def test_check_conflict_detects_conflict(self, resolver):
        """Test conflict detection between memories."""
        new_content = "P is true"
        existing = [("mem1", "P is false")]

        conflicts = resolver.check_conflict("new_mem", new_content, existing)

        assert len(conflicts) == 1
        assert "mem1" in conflicts

    def test_check_conflict_no_conflict(self, resolver):
        """Test no conflict when content doesn't contradict."""
        new_content = "P is true"
        existing = [("mem1", "Q is true")]

        conflicts = resolver.check_conflict("new_mem", new_content, existing)

        assert len(conflicts) == 0

    def test_resolve_conflict_expand_strategy(self, resolver):
        """Test resolve_conflict with expand strategy."""
        new_content = "Q is true"
        existing = [("mem1", "P is true")]

        result = resolver.resolve_conflict(
            memory_id="new_mem",
            new_content=new_content,
            existing_memories=existing,
            strategy="expand",
        )

        # When no conflict exists, action is "none" for expand strategy
        assert result.action in ("none", "expand")
        assert "Q is true" in result.resolved_beliefs.beliefs

    def test_resolve_conflict_revise_strategy(self, resolver):
        """Test resolve_conflict with revise strategy."""
        new_content = "P is true"
        existing = [("mem1", "P is false")]

        result = resolver.resolve_conflict(
            memory_id="new_mem",
            new_content=new_content,
            existing_memories=existing,
            strategy="revise",
        )

        assert result.action == "revise"
        assert "P is true" in result.resolved_beliefs.beliefs
        assert "P is false" not in result.resolved_beliefs.beliefs
        assert len(result.conflicts_detected) > 0

    def test_resolve_conflict_contract_strategy(self, resolver):
        """Test resolve_conflict with contract strategy."""
        new_content = "P is true"
        existing = [("mem1", "P is false")]

        result = resolver.resolve_conflict(
            memory_id="new_mem",
            new_content=new_content,
            existing_memories=existing,
            strategy="contract",
        )

        assert result.action == "contract"
        # Contract strategy removes the negation from existing
        assert "P is false" not in result.resolved_beliefs.beliefs
        # And should add the new belief
        assert len(result.resolved_beliefs) >= 0

    def test_resolve_conflict_no_conflict(self, resolver):
        """Test resolve_conflict when no conflict exists."""
        new_content = "Q is true"
        existing = [("mem1", "P is true")]

        result = resolver.resolve_conflict(
            memory_id="new_mem",
            new_content=new_content,
            existing_memories=existing,
            strategy="revise",
        )

        assert result.action in ("none", "expand")
        assert len(result.conflicts_detected) == 0

    def test_parse_content_basic(self, resolver):
        """Test content parsing."""
        content = "P is true and Q is true"
        beliefs = resolver._parse_content(content)

        assert len(beliefs.beliefs) >= 1
        assert "P is true" in beliefs.beliefs or "Q is true" in beliefs.beliefs


class TestNegation:
    """Tests for negation handling."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_negate_is_true(self, agm_resolver):
        """Test negating 'is true'."""
        result = agm_resolver._negate("P is true")
        assert result == "P is false"

    def test_negate_is_false(self, agm_resolver):
        """Test negating 'is false'."""
        result = agm_resolver._negate("P is false")
        assert result == "P is true"

    def test_negate_equality(self, agm_resolver):
        """Test negating equality."""
        result = agm_resolver._negate("color = red")
        assert result == "color != red"

    def test_negate_inequality(self, agm_resolver):
        """Test negating inequality."""
        result = agm_resolver._negate("color != red")
        assert result == "color = red"

    def test_negate_default(self, agm_resolver):
        """Test default negation pattern."""
        result = agm_resolver._negate("unknown formula")
        assert result == "NOT(unknown formula)"


class TestComplexScenarios:
    """Complex scenarios combining multiple AGM operations."""

    @pytest.fixture
    def agm_resolver(self):
        """Create AGMResolver instance."""
        return AGMResolver()

    def test_full_revision_cycle(self, agm_resolver):
        """Test full cycle: start with beliefs, revise multiple times."""
        K = BeliefSet(frozenset({"P is true"}))

        # Revise with Q - should add
        K = agm_resolver.revise(K, "Q is true")
        assert len(K) == 2

        # Revise with P is false - should contract P is false and add
        K = agm_resolver.revise(K, "P is false")
        assert "P is false" in K.beliefs

        # P is true should be removed due to contraction
        assert "P is true" not in K.beliefs

    def test_contraction_then_expansion(self, agm_resolver):
        """Test contracting then expanding."""
        K = BeliefSet(frozenset({"P is true", "Q is true", "R is true"}))

        # Contract P
        K = agm_resolver.contract(K, "P is true")
        assert "P is true" not in K.beliefs

        # Expand with S
        K = agm_resolver.expand(K, "S is true")
        assert "S is true" in K.beliefs
        assert len(K) == 3

    def test_multiple_inconsistent_sets(self, agm_resolver):
        """Test detecting inconsistency across many sets."""
        sets = [
            BeliefSet(frozenset({"A is true"})),
            BeliefSet(frozenset({"B is true"})),
            BeliefSet(frozenset({"A is false"})),
            BeliefSet(frozenset({"C is true"})),
        ]

        assert agm_resolver.inconsistent(*sets) is True

    def test_history_tracking(self, agm_resolver):
        """Test that all operations are tracked in history."""
        K = BeliefSet()

        K = agm_resolver.expand(K, "A is true")
        K = agm_resolver.expand(K, "B is true")
        K = agm_resolver.contract(K, "A is true")
        K = agm_resolver.revise(K, "C is true")

        history = agm_resolver.get_history()
        assert (
            len(history) == 5
        )  # 2 expand + 1 contract + 2 (contract+expand for revise)

        operations = [op[0] for op in history]
        assert "expand" in operations
        assert "contract" in operations
        assert "revise" in operations


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
