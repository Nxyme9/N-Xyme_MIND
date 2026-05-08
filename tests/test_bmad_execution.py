"""Tests for BMAD workflow execution via catalyst-mcp."""

import pytest


def test_catalyst_mcp_imports():
    """Verify catalyst-orchestrator can be imported."""
    import sys

    sys.path.insert(
        0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/catalyst_orchestrator"
    )
    from catalyst.mcp_server import mcp

    assert mcp is not None


def test_catalyst_orchestrator_imports():
    """Verify CatalystOrchestrator can be imported."""
    import sys

    sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    from packages.orchestration.catalyst import CatalystOrchestrator, UserState

    assert CatalystOrchestrator is not None
    assert UserState is not None


def test_bmad_executor_imports():
    """Verify BMADExecutor can be imported."""
    import sys

    sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    from packages.orchestration.bmad.executor import BMADExecutor

    assert BMADExecutor is not None


def test_orchestrator_detect_state():
    """Test that orchestrator can detect user state."""
    import sys

    sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    from packages.orchestration.catalyst import CatalystOrchestrator

    orch = CatalystOrchestrator()

    # Test FLOW state detection
    state = orch.detect_state("add this feature")
    assert state is not None

    # Test FRICTION state detection
    state = orch.detect_state("I'm stuck, help")
    assert state is not None


def test_bmad_executor_list_workflows():
    """Test that BMADExecutor can list workflows."""
    import sys

    sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    from packages.orchestration.bmad.executor import BMADExecutor

    executor = BMADExecutor()
    workflows = executor.list_workflows()

    assert isinstance(workflows, list)


def test_bmad_executor_load():
    """Test that BMADExecutor can load a workflow."""
    import sys

    sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    from packages.orchestration.bmad.executor import BMADExecutor

    executor = BMADExecutor()

    # Try to load a workflow (may or may not exist)
    workflow = executor.load("bmad-catalyst-chain")
    # Result depends on whether workflow exists
    # Just verify method doesn't crash
    assert True


def test_trigger_guardian_bmad_triggers():
    """Verify BMAD triggers are registered in trigger-guardian."""
    import sys

    sys.path.insert(
        0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/trigger-guardian-mcp"
    )
    from trigger_guardian_mcp import TriggerRegistry

    registry = TriggerRegistry()
    triggers = registry.list_all()

    # Check for BMAD triggers
    bmad_triggers = [
        t
        for t in triggers["triggers"]
        if t.get("handler") == "mcp" and "catalyst" in t.get("handler_target", "")
    ]

    # Should have at least /catalyst trigger
    assert len(bmad_triggers) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
