"""
Real Tests — Orchestration gap modules.

Tests for: teams, sandbox, oauth, streaming, transport (ported from Claude Code)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.orchestration import teams as teams_module
from packages.orchestration import sandbox as sandbox_module
from packages.orchestration import oauth as oauth_module
from packages.orchestration import streaming as streaming_module
from packages.orchestration import transport as transport_module


class TestTeams(unittest.TestCase):
    """Test Multi-Agent Teams module."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "teams.json"
        self.registry = teams_module.TeamRegistry(self.storage_path)

    def tearDown(self):
        if self.storage_path.exists():
            self.storage_path.unlink()
        Path(self.temp_dir).rmdir()

    def test_create_team(self):
        """Test team creation."""
        team = self.registry.create_team(
            name="test-team",
            description="Test team",
            lead_agent_type="researcher",
        )
        self.assertEqual(team.name, "test-team")
        self.assertEqual(team.description, "Test team")
        self.assertEqual(team.lead_agent_type, "researcher")
        self.assertEqual(team.status, "active")

    def test_get_team(self):
        """Test getting a team."""
        self.registry.create_team("test-team")
        team = self.registry.get_team("test-team")
        self.assertIsNotNone(team)
        self.assertEqual(team.name, "test-team")

    def test_delete_team(self):
        """Test deleting a team."""
        self.registry.create_team("test-team")
        result = self.registry.delete_team("test-team")
        self.assertTrue(result)
        self.assertIsNone(self.registry.get_team("test-team"))

    def test_add_member(self):
        """Test adding team member."""
        self.registry.create_team("test-team")
        result = self.registry.add_member("test-team", "agent-001")
        self.assertTrue(result)
        team = self.registry.get_team("test-team")
        self.assertIn("agent-001", team.members)

    def test_remove_member(self):
        """Test removing team member."""
        self.registry.create_team("test-team")
        self.registry.add_member("test-team", "agent-001")
        result = self.registry.remove_member("test-team", "agent-001")
        self.assertTrue(result)
        team = self.registry.get_team("test-team")
        self.assertNotIn("agent-001", team.members)

    def test_list_teams(self):
        """Test listing teams."""
        self.registry.create_team("team-1")
        self.registry.create_team("team-2")
        team_list = self.registry.list_teams()
        self.assertEqual(len(team_list), 2)

    def test_update_team(self):
        """Test updating team."""
        self.registry.create_team("test-team")
        result = self.registry.update_team("test-team", description="Updated")
        self.assertTrue(result)
        team = self.registry.get_team("test-team")
        self.assertEqual(team.description, "Updated")


class TestSandbox(unittest.TestCase):
    """Test Sandboxing module."""

    def test_sandbox_config(self):
        """Test sandbox config creation."""
        config = sandbox_module.SandboxConfig(
            enabled=True,
            max_memory_mb=1024,
        )
        self.assertTrue(config.enabled)
        self.assertEqual(config.max_memory_mb, 1024)

    def test_sandbox_creation(self):
        """Test sandbox creation."""
        sandbox = sandbox_module.Sandbox()
        self.assertFalse(sandbox.is_active())

    def test_enable_disable(self):
        """Test enabling/disabling sandbox."""
        sandbox = sandbox_module.Sandbox()
        sandbox.enable()
        self.assertTrue(sandbox.is_active())

        sandbox.disable()
        self.assertFalse(sandbox.is_active())

    def test_check_path_allowed(self):
        """Test path checking."""
        sandbox = sandbox_module.Sandbox()
        sandbox.config.allowed_paths = ["/home"]
        result = sandbox.check_path("/home/user")
        self.assertTrue(result)

    def test_check_path_denied(self):
        """Test path denial."""
        sandbox = sandbox_module.Sandbox()
        sandbox.config.denied_paths = ["/etc"]
        sandbox.enable()
        result = sandbox.check_path("/etc/passwd")
        self.assertFalse(result)

    def test_sandbox_disabled_allows(self):
        """Test disabled sandbox allows all paths."""
        sandbox = sandbox_module.Sandbox()
        result = sandbox.check_path("/any/path")
        self.assertTrue(result)

    def test_run_command_disabled(self):
        """Test running command when disabled."""
        sandbox = sandbox_module.Sandbox()
        result = sandbox.run_command(["echo", "test"])
        self.assertTrue(result["success"])


class TestOAuth(unittest.TestCase):
    """Test OAuth module."""

    def test_generate_code_verifier(self):
        """Test PKCE code verifier generation."""
        verifier = oauth_module.generate_code_verifier()
        self.assertIsInstance(verifier, str)
        self.assertGreaterEqual(len(verifier), 32)

    def test_generate_code_challenge(self):
        """Test PKCE code challenge generation."""
        verifier = "test verifier"
        challenge = oauth_module.generate_code_challenge(verifier)
        self.assertIsInstance(challenge, str)
        self.assertTrue(len(challenge) > 0)

    def test_generate_state(self):
        """Test state generation."""
        state = oauth_module.generate_state()
        self.assertIsInstance(state, str)
        self.assertGreaterEqual(len(state), 16)

    def test_parse_scopes(self):
        """Test scope parsing."""
        scopes = oauth_module.parse_scopes("read:user write:organization")
        self.assertIn("read:user", scopes)
        self.assertIn("write:organization", scopes)

    def test_parse_empty_scopes(self):
        """Test empty scope parsing."""
        scopes = oauth_module.parse_scopes("")
        self.assertEqual(scopes, [])

    def test_oauth_tokens_dataclass(self):
        """Test OAuthTokens dataclass."""
        tokens = oauth_module.OAuthTokens(
            access_token="access",
            refresh_token="refresh",
            expires_at=1000.0,
            scopes=["read:user"],
        )
        self.assertEqual(tokens.access_token, "access")
        self.assertEqual(tokens.scopes, ["read:user"])


class TestStreaming(unittest.TestCase):
    """Test Streaming module."""

    def test_tool_status_enum(self):
        """Test ToolStatus enum."""
        self.assertEqual(streaming_module.ToolStatus.QUEUED, "queued")
        self.assertEqual(streaming_module.ToolStatus.EXECUTING, "executing")
        self.assertEqual(streaming_module.ToolStatus.COMPLETED, "completed")

    def test_tracked_tool_creation(self):
        """Test TrackedTool creation."""
        tool = streaming_module.TrackedTool(
            id="tool-001",
            block={"name": "test"},
            assistant_message={"uuid": "msg-001"},
        )
        self.assertEqual(tool.id, "tool-001")
        self.assertEqual(tool.status, streaming_module.ToolStatus.QUEUED)

    def test_message_update(self):
        """Test MessageUpdate."""
        update = streaming_module.MessageUpdate(
            message={"type": "test"},
        )
        self.assertIsNotNone(update.message)

    def test_streaming_executor_creation(self):
        """Test StreamingToolExecutor creation."""
        executor = streaming_module.StreamingToolExecutor(
            tool_definitions=[],
            can_use_tool=lambda x: True,
            tool_use_context={},
        )
        self.assertEqual(executor.tools, [])
        self.assertFalse(executor.has_errored)
        self.assertFalse(executor.discarded)

    def test_add_tool_not_found(self):
        """Test adding tool not in definitions."""
        executor = streaming_module.StreamingToolExecutor(
            tool_definitions=[],
            can_use_tool=lambda x: x == "found",
            tool_use_context={},
        )
        block = {"name": "missing", "id": "1", "input": {}}
        executor.add_tool(block, {"uuid": "msg-001"})

        self.assertEqual(len(executor.tools), 1)
        self.assertEqual(executor.tools[0].status, streaming_module.ToolStatus.COMPLETED)

    def test_discard(self):
        """Test discard."""
        executor = streaming_module.StreamingToolExecutor(
            tool_definitions=[],
            can_use_tool=lambda x: True,
            tool_use_context={},
        )
        executor.discard()
        self.assertTrue(executor.discarded)


class TestTransport(unittest.TestCase):
    """Test Transport module."""

    def test_transport_state_enum(self):
        """Test TransportState enum."""
        self.assertEqual(transport_module.TransportState.IDLE, "idle")
        self.assertEqual(transport_module.TransportState.CONNECTED, "connected")
        self.assertEqual(transport_module.TransportState.RECONNECTING, "reconnecting")

    def test_transport_options(self):
        """Test TransportOptions."""
        opts = transport_module.TransportOptions(
            auto_reconnect=False,
            is_bridge=True,
        )
        self.assertFalse(opts.auto_reconnect)
        self.assertTrue(opts.is_bridge)

    def test_circular_buffer(self):
        """Test CircularBuffer."""
        buf = transport_module.CircularBuffer(max_size=3)
        buf.push("a")
        buf.push("b")
        buf.push("c")
        items = buf.get_all()
        self.assertEqual(len(items), 3)
        self.assertIn("a", items)
        self.assertIn("b", items)

    def test_circular_buffer_overflow(self):
        """Test buffer overflow."""
        buf = transport_module.CircularBuffer(max_size=2)
        for i in range(5):
            buf.push(str(i))
        items = buf.get_all()
        self.assertEqual(len(items), 2)

    def test_websocket_transport_creation(self):
        """Test WebSocketTransport creation."""
        transport = transport_module.WebSocketTransport(
            url="ws://localhost:8080",
            headers={"Authorization": "Bearer test"},
        )
        self.assertEqual(transport.url, "ws://localhost:8080")
        self.assertEqual(transport.state, transport_module.TransportState.IDLE)

    def test_http_transport_creation(self):
        """Test HTTPTransport creation."""
        transport = transport_module.HTTPTransport(
            base_url="http://localhost:8080",
            headers={"Authorization": "Bearer test"},
        )
        self.assertEqual(transport.base_url, "http://localhost:8080")

    def test_create_transport_websocket(self):
        """Test create_transport for WebSocket."""
        transport = transport_module.create_transport("ws://localhost:8080")
        self.assertIsInstance(transport, transport_module.WebSocketTransport)

    def test_create_transport_http(self):
        """Test create_transport for HTTP."""
        transport = transport_module.create_transport("http://localhost:8080")
        self.assertIsInstance(transport, transport_module.HTTPTransport)

    def test_is_connected(self):
        """Test is_connected."""
        transport = transport_module.WebSocketTransport("ws://localhost:8080")
        self.assertFalse(transport.is_connected())
        transport.state = transport_module.TransportState.CONNECTED
        self.assertTrue(transport.is_connected())


def run_tests():
    """Run all tests with coverage."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestTeams))
    suite.addTests(loader.loadTestsFromTestCase(TestSandbox))
    suite.addTests(loader.loadTestsFromTestCase(TestOAuth))
    suite.addTests(loader.loadTestsFromTestCase(TestStreaming))
    suite.addTests(loader.loadTestsFromTestCase(TestTransport))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)