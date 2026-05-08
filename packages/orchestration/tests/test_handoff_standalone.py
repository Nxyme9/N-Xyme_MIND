#!/usr/bin/env python3
"""Standalone test for handoff primitives - bypasses package imports."""

import sys
import types

# Register stub modules BEFORE any imports to fix KeyError
telemetry_stub = types.ModuleType('packages.infrastructure.monitoring.telemetry')
telemetry_stub.get_logger = lambda name: None
sys.modules['packages.infrastructure.monitoring.telemetry'] = telemetry_stub

infrastructure_stub = types.ModuleType('packages.infrastructure')
sys.modules['packages.infrastructure'] = infrastructure_stub

# Read and exec the handoff module with proper module context
handoff_code = open('/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/handoff.py').read()

# Create module with proper __name__ and __package__
handoff = types.ModuleType('packages.orchestration.handoff')
handoff.__file__ = '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/handoff.py'
handoff.__package__ = 'packages.orchestration'
sys.modules['packages.orchestration.handoff'] = handoff

# Execute in the module's namespace
exec(compile(handoff_code, 'handoff.py', 'exec'), handoff.__dict__)

# === TESTS ===
print("=" * 60)
print("TESTING HANDOFF PRIMITIVES")
print("=" * 60)

# Test 1: HandoffRequest validation
print("\n[TEST 1] HandoffRequest validation")
try:
    request = handoff.HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"task": "implement feature"},
        reason="Implementation needed"
    )
    errors = request.validate()
    assert errors == [], f"Expected no errors, got {errors}"
    print("  PASS: Valid request passes validation")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 2: Invalid request - same agents
print("\n[TEST 2] Same source and target agent")
try:
    request = handoff.HandoffRequest(
        source_agent="hephaestus",
        target_agent="hephaestus",
        context={"task": "test"},
        reason="test"
    )
    errors = request.validate()
    assert "must be different" in str(errors)
    print("  PASS: Same agent rejected")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 3: Guardrails pass
print("\n[TEST 3] Guardrails validation")
try:
    guardrails = handoff.Guardrails()
    request = handoff.HandoffRequest("sisyphus", "hephaestus", {"task": "test"}, "reason")
    passed, errors = guardrails.check_handoff(request)
    assert passed == True
    print("  PASS: Guardrails pass for valid request")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 4: Guardrails custom rule blocks
print("\n[TEST 4] Custom guardrail rule blocks transfer")
try:
    guardrails = handoff.Guardrails()
    guardrails.add_rule("block_hephaestus", lambda r: r.target_agent != "hephaestus", "No hephaestus")
    request = handoff.HandoffRequest("sisyphus", "hephaestus", {"task": "test"}, "reason")
    passed, errors = guardrails.check_handoff(request)
    assert passed == False
    assert "No hephaestus" in errors
    print("  PASS: Custom rule blocks transfer correctly")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 5: HandoffManager executes
print("\n[TEST 5] HandoffManager execution")
try:
    manager = handoff.HandoffManager()
    request = handoff.HandoffRequest(
        source_agent="sisyphus",
        target_agent="hephaestus",
        context={"session_state": {"key": "value"}, "conversation_history": []},
        reason="Implementation needed"
    )
    response = manager.execute_handoff(request)
    assert response.success == True
    assert response.status == handoff.HandoffStatus.COMPLETED
    assert "session_state" in response.transferred_context
    print("  PASS: Handoff transfers context correctly")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 6: Guardrails block - use rule that specifically rejects hephaestus target
print("\n[TEST 6] Guardrails block transfer")
try:
    manager = handoff.HandoffManager()
    manager.guardrails.add_rule("no_hephaestus", lambda r: r.target_agent != "hephaestus", "No hephaestus transfers allowed")
    request = handoff.HandoffRequest("sisyphus", "hephaestus", {"task": "test"}, "Implementation")  # target=hephaestus triggers rule
    response = manager.execute_handoff(request)
    assert response.success == False
    assert response.status == handoff.HandoffStatus.BLOCKED
    assert response.guardrails_passed == False
    print("  PASS: Guardrails block transfer correctly")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 7: Context transfer
print("\n[TEST 7] Full context transfer")
try:
    manager = handoff.HandoffManager()
    request = handoff.HandoffRequest(
        source_agent="sisyphus",
        target_agent="oracle",
        context={
            "session_state": {"session_id": "abc123"},
            "conversation_history": [{"role": "user", "content": "Hello"}],
            "tool_access": ["read", "write"],
            "agent_state": {"step": 5},
            "additional": {"custom": "value"}
        },
        reason="Review needed"
    )
    response = manager.execute_handoff(request)
    ctx = response.transferred_context
    assert ctx["session_state"] == {"session_id": "abc123"}
    assert len(ctx["conversation_history"]) == 1
    assert ctx["tool_access"] == ["read", "write"]
    assert ctx["metadata"]["source_agent"] == "sisyphus"
    assert ctx["metadata"]["target_agent"] == "oracle"
    print("  PASS: Full context transferred with metadata")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

# Test 8: Convenience function
print("\n[TEST 8] Convenience create_handoff function")
try:
    response = handoff.create_handoff("sisyphus", "explore", {"task": "search"}, "Search")
    assert response.success == True
    print("  PASS: Convenience function works")
except Exception as e:
    print(f"  FAIL: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL 8 TESTS PASSED!")
print("=" * 60)
