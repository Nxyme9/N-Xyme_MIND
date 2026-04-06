"""Tests for brain system modules — import verification + basic smoke tests."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestBrainMemoryImports:
    """Verify brain memory modules import correctly."""

    def test_episodic_import(self):
        from src.brain.memory.episodic import EpisodicMemory
        assert EpisodicMemory is not None

    def test_procedural_import(self):
        from src.brain.memory.procedural import ProceduralMemory
        assert ProceduralMemory is not None

    def test_semantic_import(self):
        from src.brain.memory.semantic import SemanticMemory
        assert SemanticMemory is not None

    def test_working_import(self):
        from src.brain.memory.working import WorkingMemory
        assert WorkingMemory is not None


class TestWorkingMemory:
    """Test WorkingMemory — only module with clean, testable API."""

    def test_store_and_retrieve(self):
        from src.brain.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        wm.store("key1", "value1")
        result = wm.retrieve("key1")
        assert result is not None
        assert result.value == "value1"

    def test_capacity_limit(self):
        from src.brain.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=3)
        for i in range(10):
            wm.store(f"k{i}", i)
        assert len(wm.get_all()) <= 3

    def test_clear(self):
        from src.brain.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        wm.store("x", 1)
        wm.clear()
        assert len(wm.get_all()) == 0

    def test_decay(self):
        from src.brain.memory.working import WorkingMemory
        wm = WorkingMemory(capacity=5)
        wm.store("x", 1)
        wm.decay()


class TestBrainModuleImports:
    """Verify all brain modules import without errors."""

    def test_router_import(self):
        from src.brain.router import Router
        assert Router is not None

    def test_critic_import(self):
        from src.brain.critic import Critic
        assert Critic is not None

    def test_dual_loop_import(self):
        from src.brain.dual_loop import DualLoop
        assert DualLoop is not None

    def test_commitment_import(self):
        from src.brain.commitment import CommitmentTracker
        assert CommitmentTracker is not None

    def test_event_log_import(self):
        from src.brain.event_log import EventLog
        assert EventLog is not None

    def test_episodic_store_method_exists(self):
        from src.brain.memory.episodic import EpisodicMemory
        em = EpisodicMemory()
        assert hasattr(em, "store")

    def test_procedural_store_method_exists(self):
        from src.brain.memory.procedural import ProceduralMemory
        pm = ProceduralMemory()
        assert hasattr(pm, "store")

    def test_semantic_store_method_exists(self):
        from src.brain.memory.semantic import SemanticMemory
        sm = SemanticMemory()
        assert hasattr(sm, "store")
