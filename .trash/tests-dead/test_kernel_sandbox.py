"""Comprehensive tests for kernel_sandbox module.

Tests cover:
- CommandInspector: destructive command detection, sh -c unwrapping, allowlist/denylist
- AuditLogger: logging, flushing, summary
- CommandFilterBackend: safe_run, check_command
- KernelSandbox: configuration, backend detection, OpenCode integration
- Convenience API: create_sandbox, is_command_safe, block_destructive
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.security.kernel_sandbox import (
    AccessMode,
    AuditEntry,
    AuditLevel,
    AuditLogger,
    BlockReason,
    CommandBlockedError,
    CommandFilterBackend,
    CommandInspector,
    DESTRUCTIVE_COMMANDS,
    DESTRUCTIVE_PATTERNS,
    KernelSandbox,
    LandlockBackend,
    SandboxBackend,
    SandboxConfig,
    SandboxError,
    SeatbeltBackend,
    SeccompBackend,
    block_destructive,
    create_sandbox,
    is_command_safe,
)


# ===================================================================
# CommandInspector Tests
# ===================================================================


class TestCommandInspector:
    """Tests for command inspection and destructive pattern detection."""

    def test_safe_command_passes(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect("ls -la /tmp")
        assert is_safe is True
        assert reason is None
        assert block_reason is None

    def test_safe_command_list_form(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect(["ls", "-la", "/tmp"])
        assert is_safe is True

    def test_blocks_rm(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect("rm -rf /")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_dd(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("dd if=/dev/zero of=/dev/sda")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_sudo(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("sudo apt update")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_docker(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("docker rm container")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_kubectl_delete(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("kubectl delete pod mypod")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_scp(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("scp file.txt user@host:/tmp")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_chmod(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("chmod 777 /etc/passwd")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_shutdown(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("shutdown now")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_reboot(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("reboot")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_mkfs(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("mkfs.ext4 /dev/sda1")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_ssh(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("ssh user@host")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_curl(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("curl https://example.com")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_wget(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("wget https://example.com/file")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_kill_9(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("kill -9 1234")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_iptables(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("iptables -A INPUT -j DROP")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_mount(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("mount /dev/sda1 /mnt")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_systemctl_stop(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("systemctl stop nginx")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_shred(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("shred -u secret.txt")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_blocks_crontab_remove(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("crontab -r")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND


class TestCommandInspectorShCWrapper:
    """Tests for sh -c wrapper detection."""

    def test_unwraps_sh_c(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect("sh -c 'rm -rf /tmp/data'")
        assert is_safe is False
        assert block_reason == BlockReason.SH_C_WRAPPER
        assert "sh -c wrapper" in reason.lower()

    def test_unwraps_bash_c(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect('bash -c "rm -rf /tmp/data"')
        assert is_safe is False
        assert block_reason == BlockReason.SH_C_WRAPPER

    def test_unwraps_zsh_c(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect('zsh -c "sudo rm -rf /"')
        assert is_safe is False
        assert block_reason == BlockReason.SH_C_WRAPPER

    def test_unwraps_nested_sh_c(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("sh -c 'sh -c \"rm -rf /\"'")
        assert is_safe is False
        assert block_reason == BlockReason.SH_C_WRAPPER

    def test_unwraps_dash_c(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect('dash -c "dd if=/dev/zero"')
        assert is_safe is False
        assert block_reason == BlockReason.SH_C_WRAPPER

    def test_safe_sh_c_passes(self):
        inspector = CommandInspector()
        is_safe, reason, block_reason = inspector.inspect("sh -c 'echo hello'")
        assert is_safe is True
        assert reason is None

    def test_sh_c_with_flags(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect('sh -x -c "rm -rf /tmp"')
        assert is_safe is False
        assert block_reason == BlockReason.SH_C_WRAPPER


class TestCommandInspectorAllowlist:
    """Tests for allowlist-based command filtering."""

    def test_allowlist_blocks_unknown(self):
        inspector = CommandInspector(allowed_commands={"ls", "cat", "echo"})
        is_safe, _, block_reason = inspector.inspect("rm -rf /tmp")
        # rm is not in allowlist, so NOT_IN_ALLOWLIST fires first
        assert is_safe is False
        assert block_reason == BlockReason.NOT_IN_ALLOWLIST

    def test_allowlist_allows_known(self):
        inspector = CommandInspector(allowed_commands={"ls", "cat", "echo"})
        is_safe, _, _ = inspector.inspect("ls -la")
        assert is_safe is True

    def test_allowlist_blocks_unlisted_safe_command(self):
        inspector = CommandInspector(allowed_commands={"ls", "cat"})
        is_safe, _, block_reason = inspector.inspect("pwd")
        assert is_safe is False
        assert block_reason == BlockReason.NOT_IN_ALLOWLIST

    def test_denylist_overrides(self):
        inspector = CommandInspector(denied_commands={"rm", "dd"})
        is_safe, _, block_reason = inspector.inspect("rm file.txt")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_empty_inspector_allows_all(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("python script.py")
        assert is_safe is True


class TestCommandInspectorPatterns:
    """Tests for regex-based destructive pattern matching."""

    def test_pattern_rm_recursive(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("rm -rf /home/user")
        assert is_safe is False
        assert block_reason in (
            BlockReason.DESTRUCTIVE_COMMAND,
            BlockReason.PATTERN_MATCH,
        )

    def test_pattern_dd_write(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect(
            "dd if=/dev/urandom of=/dev/sda bs=1M"
        )
        assert is_safe is False

    def test_pattern_mkswap(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("mkswap /dev/sda2")
        assert is_safe is False

    def test_pattern_poweroff(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("poweroff")
        assert is_safe is False

    def test_pattern_halt(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("halt -p")
        assert is_safe is False

    def test_pattern_umount(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("umount /mnt/usb")
        assert is_safe is False

    def test_pattern_killall(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("killall python")
        assert is_safe is False

    def test_pattern_pkill(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("pkill -f nginx")
        assert is_safe is False

    def test_pattern_modprobe(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("modprobe evil_module")
        assert is_safe is False

    def test_pattern_insmod(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("insmod /tmp/evil.ko")
        assert is_safe is False

    def test_pattern_rmmod(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("rmmod good_module")
        assert is_safe is False


# ===================================================================
# AuditLogger Tests
# ===================================================================


class TestAuditLogger:
    """Tests for audit logging functionality."""

    def test_log_blocked_entry(self):
        logger = AuditLogger(level=AuditLevel.BLOCKED_ONLY)
        entry = logger.log("rm -rf /", "blocked", reason="destructive")
        assert entry.command == "rm -rf /"
        assert entry.action == "blocked"
        assert entry.reason == "destructive"
        assert entry.event_id is not None
        assert entry.timestamp > 0

    def test_log_allowed_entry_all_level(self):
        logger = AuditLogger(level=AuditLevel.ALL)
        entry = logger.log("ls -la", "allowed")
        assert entry.command == "ls -la"
        assert entry.action == "allowed"

    def test_blocked_only_level_skips_allowed(self):
        logger = AuditLogger(level=AuditLevel.BLOCKED_ONLY)
        logger.log("ls -la", "allowed")
        logger.log("rm -rf /", "blocked", reason="destructive")
        entries = logger.get_entries()
        assert len(entries) == 1
        assert entries[0].action == "blocked"

    def test_none_level_logs_nothing(self):
        logger = AuditLogger(level=AuditLevel.NONE)
        logger.log("rm -rf /", "blocked", reason="test")
        assert len(logger.get_entries()) == 0

    def test_all_level_logs_everything(self):
        logger = AuditLogger(level=AuditLevel.ALL)
        logger.log("ls", "allowed")
        logger.log("rm", "blocked", reason="test")
        logger.log("cat", "allowed")
        entries = logger.get_entries()
        assert len(entries) == 3

    def test_get_blocked(self):
        logger = AuditLogger(level=AuditLevel.ALL)
        logger.log("rm -rf /", "blocked", reason="destructive")
        logger.log("ls", "allowed")
        logger.log("dd if=/dev/zero", "blocked", reason="destructive")
        blocked = logger.get_blocked()
        assert len(blocked) == 2

    def test_summary(self):
        logger = AuditLogger(level=AuditLevel.ALL)
        logger.log("ls", "allowed")
        logger.log("rm", "blocked", reason="test")
        summary = logger.summary()
        assert summary["total_events"] == 2
        assert summary["blocked"] == 1
        assert summary["allowed"] == 1
        assert "session_id" in summary

    def test_flush_writes_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            log_path = f.name

        try:
            logger = AuditLogger(log_path=log_path, level=AuditLevel.ALL)
            logger.log("rm -rf /", "blocked", reason="test")
            logger.flush()

            data = json.loads(Path(log_path).read_text())
            assert len(data) == 1
            assert data[0]["command"] == "rm -rf /"
            assert data[0]["action"] == "blocked"
        finally:
            Path(log_path).unlink(missing_ok=True)

    def test_flush_appends_to_existing_file(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            log_path = f.name

        try:
            # Write initial data
            Path(log_path).write_text('[{"existing": true}]')

            logger = AuditLogger(log_path=log_path, level=AuditLevel.ALL)
            logger.log("rm -rf /", "blocked", reason="test")
            logger.flush()

            data = json.loads(Path(log_path).read_text())
            assert len(data) == 2
            assert data[0]["existing"] is True
            assert data[1]["command"] == "rm -rf /"
        finally:
            Path(log_path).unlink(missing_ok=True)

    def test_flush_empty_entries_does_nothing(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            log_path = f.name

        try:
            logger = AuditLogger(log_path=log_path, level=AuditLevel.BLOCKED_ONLY)
            logger.log("ls", "allowed")
            logger.flush()

            # File should not exist or be empty
            assert not Path(log_path).exists() or Path(log_path).read_text() == ""
        finally:
            Path(log_path).unlink(missing_ok=True)

    def test_audit_entry_to_json(self):
        entry = AuditEntry(
            timestamp=1234567890.0,
            event_id="abc123",
            command="rm -rf /",
            action="blocked",
            reason="destructive",
            backend="command_filter",
            pid=1234,
            uid=1000,
            cwd="/tmp",
            details={"block_reason": "destructive_command"},
        )
        json_str = entry.to_json()
        data = json.loads(json_str)
        assert data["command"] == "rm -rf /"
        assert data["action"] == "blocked"
        assert data["reason"] == "destructive"

    def test_session_id_is_unique(self):
        logger1 = AuditLogger()
        logger2 = AuditLogger()
        assert logger1.summary()["session_id"] != logger2.summary()["session_id"]


# ===================================================================
# CommandFilterBackend Tests
# ===================================================================


class TestCommandFilterBackend:
    """Tests for the command filter backend."""

    def test_check_command_safe(self):
        backend = CommandFilterBackend()
        inspector = CommandInspector()
        audit = AuditLogger(level=AuditLevel.ALL)
        backend.initialize(inspector, audit)

        is_safe, error_msg = backend.check_command("ls -la")
        assert is_safe is True
        assert error_msg is None

    def test_check_command_blocked(self):
        backend = CommandFilterBackend()
        inspector = CommandInspector()
        audit = AuditLogger(level=AuditLevel.ALL)
        backend.initialize(inspector, audit)

        is_safe, error_msg = backend.check_command("rm -rf /")
        assert is_safe is False
        assert error_msg is not None
        assert "destructive" in error_msg.lower() or "blocked" in error_msg.lower()

    def test_safe_run_blocked_raises(self):
        backend = CommandFilterBackend()
        inspector = CommandInspector()
        audit = AuditLogger(level=AuditLevel.ALL)
        backend.initialize(inspector, audit)

        with pytest.raises(CommandBlockedError):
            backend.safe_run("rm -rf /")

    def test_safe_run_allowed_executes(self):
        backend = CommandFilterBackend()
        inspector = CommandInspector()
        audit = AuditLogger(level=AuditLevel.ALL)
        backend.initialize(inspector, audit)

        result = backend.safe_run(["echo", "hello"])
        assert result.returncode == 0

    def test_safe_run_string_command(self):
        backend = CommandFilterBackend()
        inspector = CommandInspector()
        audit = AuditLogger(level=AuditLevel.ALL)
        backend.initialize(inspector, audit)

        result = backend.safe_run("echo hello world")
        assert result.returncode == 0

    def test_uninitialized_backend_allows_all(self):
        backend = CommandFilterBackend()
        is_safe, error_msg = backend.check_command("rm -rf /")
        assert is_safe is True


# ===================================================================
# LandlockBackend Tests
# ===================================================================


class TestLandlockBackend:
    """Tests for the Landlock backend."""

    def test_not_available_on_non_linux(self):
        with patch("platform.system", return_value="Darwin"):
            backend = LandlockBackend()
            assert backend.available is False

    def test_available_checks_kernel_version(self):
        with patch("platform.system", return_value="Linux"):
            with patch("platform.release", return_value="5.15.0-generic"):
                backend = LandlockBackend()
                assert backend._check_kernel_version() is True

    def test_unavailable_old_kernel(self):
        with patch("platform.system", return_value="Linux"):
            with patch("platform.release", return_value="4.19.0"):
                backend = LandlockBackend()
                assert backend._check_kernel_version() is False

    def test_apply_returns_false_without_nono_py(self):
        with patch("platform.system", return_value="Linux"):
            with patch("platform.release", return_value="5.15.0"):
                backend = LandlockBackend()
                with patch.dict("sys.modules", {"nono_py": None}):
                    result = backend.apply(allow_paths=[])
                    assert result is False

    def test_apply_returns_false_if_not_available(self):
        backend = LandlockBackend()
        backend._available = False
        result = backend.apply(allow_paths=[])
        assert result is False

    def test_name_is_landlock(self):
        backend = LandlockBackend()
        assert backend.name == SandboxBackend.LANDLOCK


# ===================================================================
# SeatbeltBackend Tests
# ===================================================================


class TestSeatbeltBackend:
    """Tests for the Seatbelt backend."""

    def test_available_on_darwin(self):
        with patch("platform.system", return_value="Darwin"):
            backend = SeatbeltBackend()
            assert backend.available is True

    def test_not_available_on_linux(self):
        with patch("platform.system", return_value="Linux"):
            backend = SeatbeltBackend()
            assert backend.available is False

    def test_apply_returns_false_on_linux(self):
        backend = SeatbeltBackend()
        backend._available = False
        result = backend.apply(allow_paths=[])
        assert result is False

    def test_name_is_seatbelt(self):
        backend = SeatbeltBackend()
        assert backend.name == SandboxBackend.SEATBELT


# ===================================================================
# SeccompBackend Tests
# ===================================================================


class TestSeccompBackend:
    """Tests for the Seccomp backend."""

    def test_not_available_on_non_linux(self):
        with patch("platform.system", return_value="Darwin"):
            backend = SeccompBackend()
            assert backend.available is False

    def test_name_is_seccomp(self):
        backend = SeccompBackend()
        assert backend.name == SandboxBackend.SECCOMP

    def test_apply_returns_false_if_not_available(self):
        backend = SeccompBackend()
        backend._available = False
        result = backend.apply()
        assert result is False


# ===================================================================
# KernelSandbox Tests
# ===================================================================


class TestKernelSandbox:
    """Tests for the main KernelSandbox orchestrator."""

    def test_default_config(self):
        sandbox = KernelSandbox()
        assert sandbox.is_applied is False
        assert sandbox.active_backend == SandboxBackend.NONE

    def test_custom_config(self):
        config = SandboxConfig(
            block_network=True,
            strict_mode=False,
            audit_level=AuditLevel.ALL,
        )
        sandbox = KernelSandbox(config=config)
        assert sandbox._config.block_network is True
        assert sandbox._config.strict_mode is False

    def test_apply_returns_command_filter_fallback(self):
        sandbox = KernelSandbox()
        backend = sandbox.apply()
        # Command filter is always available
        assert backend in (
            SandboxBackend.LANDLOCK,
            SandboxBackend.SEATBELT,
            SandboxBackend.SECCOMP,
            SandboxBackend.COMMAND_FILTER,
        )
        assert sandbox.is_applied is True

    def test_detect_backend(self):
        sandbox = KernelSandbox()
        backend = sandbox.detect_backend()
        assert isinstance(backend, SandboxBackend)

    def test_check_command_blocked(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        is_safe, reason = sandbox.check_command("rm -rf /")
        assert is_safe is False
        assert reason is not None

    def test_check_command_allowed(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        is_safe, reason = sandbox.check_command("echo hello")
        assert is_safe is True

    def test_run_blocked_raises(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        with pytest.raises(CommandBlockedError):
            sandbox.run("rm -rf /")

    def test_run_allowed_executes(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        result = sandbox.run(["echo", "hello"])
        assert result.returncode == 0

    def test_add_allowed_command(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        sandbox.add_allowed_command("my-custom-cmd")
        # The command should now be in the allowlist
        assert "my-custom-cmd" in sandbox._config.allowed_commands

    def test_add_denied_command(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        sandbox.add_denied_command("evil-cmd")
        assert "evil-cmd" in sandbox._config.denied_commands

    def test_audit_summary(self):
        sandbox = KernelSandbox()
        sandbox.apply()
        sandbox.check_command("rm -rf /")
        summary = sandbox.audit_summary()
        assert "total_events" in summary
        assert "blocked" in summary
        assert "allowed" in summary

    def test_flush_audit(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            log_path = f.name

        try:
            config = SandboxConfig(audit_log_path=log_path, audit_level=AuditLevel.ALL)
            sandbox = KernelSandbox(config=config)
            sandbox.apply()
            sandbox.check_command("rm -rf /")
            sandbox.flush_audit()

            data = json.loads(Path(log_path).read_text())
            assert len(data) > 0
        finally:
            Path(log_path).unlink(missing_ok=True)

    def test_configure_updates(self):
        sandbox = KernelSandbox()
        sandbox.configure(block_network=True, strict_mode=False)
        assert sandbox._config.block_network is True
        assert sandbox._config.strict_mode is False

    def test_integrate_opencode_config_missing_file(self):
        sandbox = KernelSandbox()
        sandbox.integrate_opencode_config("/nonexistent/path/config.json")
        # Should not raise

    def test_integrate_opencode_config_valid(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(
                {
                    "permissions": {
                        "allow": ["Read", "Glob"],
                        "deny": ["Bash"],
                    }
                },
                f,
            )
            config_path = f.name

        try:
            sandbox = KernelSandbox()
            sandbox.integrate_opencode_config(config_path)
            assert "read" in sandbox._config.allowed_commands
            assert "glob" in sandbox._config.allowed_commands
            assert "bash" in sandbox._config.denied_commands
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_integrate_opencode_config_oh_my_format(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(
                {
                    "allowedTools": ["Read", "Edit"],
                    "deniedTools": ["Bash"],
                },
                f,
            )
            config_path = f.name

        try:
            sandbox = KernelSandbox()
            sandbox.integrate_opencode_config(config_path)
            assert "read" in sandbox._config.allowed_commands
            assert "edit" in sandbox._config.allowed_commands
            assert "bash" in sandbox._config.denied_commands
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_properties(self):
        sandbox = KernelSandbox()
        assert isinstance(sandbox.audit, AuditLogger)
        assert isinstance(sandbox.inspector, CommandInspector)


# ===================================================================
# Convenience API Tests
# ===================================================================


class TestConvenienceAPI:
    """Tests for the module-level convenience functions."""

    def test_is_command_safe_safe(self):
        is_safe, reason = is_command_safe("ls -la")
        assert is_safe is True
        assert reason is None

    def test_is_command_safe_unsafe(self):
        is_safe, reason = is_command_safe("rm -rf /")
        assert is_safe is False
        assert reason is not None

    def test_is_command_safe_sh_c_bypass(self):
        is_safe, reason = is_command_safe("sh -c 'rm -rf /'")
        assert is_safe is False
        assert reason is not None

    def test_block_destructive_safe(self):
        result = block_destructive("echo hello")
        assert result is True

    def test_block_destructive_unsafe(self):
        with pytest.raises(CommandBlockedError):
            block_destructive("rm -rf /")

    def test_create_sandbox(self):
        sandbox = create_sandbox(
            block_network=False,
            strict_mode=False,
            audit_level=AuditLevel.BLOCKED_ONLY,
        )
        assert sandbox.is_applied is True
        assert isinstance(sandbox, KernelSandbox)

    def test_create_sandbox_with_allowlist(self):
        sandbox = create_sandbox(
            allowed_commands={"ls", "cat", "echo"},
            strict_mode=False,
        )
        is_safe, _ = sandbox.check_command("ls")
        assert is_safe is True


# ===================================================================
# Integration Tests
# ===================================================================


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_workflow(self):
        """Test complete sandbox workflow."""
        sandbox = KernelSandbox()
        backend = sandbox.apply()

        # Safe command should work
        is_safe, _ = sandbox.check_command("echo hello")
        assert is_safe is True

        # Destructive command should be blocked
        is_safe, reason = sandbox.check_command("rm -rf /")
        assert is_safe is False
        assert reason is not None

        # sh -c bypass should be caught
        is_safe, reason = sandbox.check_command("sh -c 'rm -rf /'")
        assert is_safe is False

        # Audit should have entries
        summary = sandbox.audit_summary()
        assert summary["total_events"] > 0

    def test_allowlist_workflow(self):
        """Test allowlist-based workflow."""
        sandbox = create_sandbox(
            allowed_commands={"ls", "cat", "pwd", "echo"},
            strict_mode=False,
        )

        # Allowed commands pass
        for cmd in ["ls", "cat file.txt", "pwd", "echo hello"]:
            is_safe, _ = sandbox.check_command(cmd)
            assert is_safe is True, f"Expected {cmd} to be allowed"

        # Non-allowlisted commands blocked
        is_safe, _ = sandbox.check_command("python script.py")
        assert is_safe is False

    def test_denylist_workflow(self):
        """Test denylist-based workflow."""
        sandbox = create_sandbox(
            denied_commands={"rm", "dd", "sudo"},
            strict_mode=False,
        )

        # Denied commands blocked
        for cmd in ["rm file.txt", "dd if=/dev/zero", "sudo apt update"]:
            is_safe, _ = sandbox.check_command(cmd)
            assert is_safe is False, f"Expected {cmd} to be blocked"

        # Other commands pass
        is_safe, _ = sandbox.check_command("ls -la")
        assert is_safe is True

    def test_audit_trail_persistence(self):
        """Test that audit trail persists to disk."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            log_path = f.name

        try:
            sandbox = create_sandbox(
                audit_log_path=log_path,
                audit_level=AuditLevel.ALL,
                strict_mode=False,
            )

            # Generate some audit entries
            sandbox.check_command("rm -rf /")
            sandbox.check_command("ls -la")
            sandbox.check_command("sh -c 'dd if=/dev/zero'")

            sandbox.flush_audit()

            # Verify file contents
            data = json.loads(Path(log_path).read_text())
            blocked = [e for e in data if e["action"] == "blocked"]
            allowed = [e for e in data if e["action"] == "allowed"]

            assert len(blocked) >= 2  # rm and dd
            assert len(allowed) >= 1  # ls
        finally:
            Path(log_path).unlink(missing_ok=True)

    def test_opencode_config_integration_workflow(self):
        """Test full workflow with OpenCode config integration."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(
                {
                    "allowedTools": ["Read", "Glob", "Grep"],
                    "deniedTools": ["Bash"],
                },
                f,
            )
            config_path = f.name

        try:
            sandbox = KernelSandbox()
            sandbox.integrate_opencode_config(config_path)
            sandbox.apply()

            # Bash should be denied
            assert "bash" in sandbox._config.denied_commands

            # Read, Glob, Grep should be allowed
            assert "read" in sandbox._config.allowed_commands
            assert "glob" in sandbox._config.allowed_commands
            assert "grep" in sandbox._config.allowed_commands
        finally:
            Path(config_path).unlink(missing_ok=True)


# ===================================================================
# Edge Case Tests
# ===================================================================


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_command(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("")
        # Empty command should not crash
        assert isinstance(is_safe, bool)

    def test_whitespace_only_command(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("   ")
        assert isinstance(is_safe, bool)

    def test_command_with_many_spaces(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("ls     -la      /tmp")
        assert is_safe is True

    def test_command_with_special_chars(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("echo 'hello world'")
        assert is_safe is True

    def test_unicode_command(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("echo 'héllo wörld'")
        assert is_safe is True

    def test_very_long_command(self):
        inspector = CommandInspector()
        long_cmd = "echo " + "a" * 10000
        is_safe, _, _ = inspector.inspect(long_cmd)
        assert is_safe is True

    def test_case_insensitive_blocking(self):
        inspector = CommandInspector()
        # Should block regardless of case
        for cmd in ["RM -rf /", "Rm -rf /", "rM -rf /"]:
            is_safe, _, block_reason = inspector.inspect(cmd)
            assert is_safe is False

    def test_command_with_path_prefix(self):
        inspector = CommandInspector()
        is_safe, _, _ = inspector.inspect("/usr/bin/ls -la")
        assert is_safe is True

    def test_destructive_command_with_path_prefix(self):
        inspector = CommandInspector()
        is_safe, _, block_reason = inspector.inspect("/bin/rm -rf /")
        assert is_safe is False
        assert block_reason == BlockReason.DESTRUCTIVE_COMMAND

    def test_sandbox_error_handling(self):
        """Test that sandbox errors don't crash the application."""
        sandbox = KernelSandbox()
        # Should not raise even with default config
        sandbox.apply()
        assert sandbox.is_applied is True

    def test_multiple_applies(self):
        """Test that multiple applies don't cause issues."""
        sandbox = KernelSandbox()
        sandbox.apply()
        sandbox.apply()
        sandbox.apply()
        assert sandbox.is_applied is True

    def test_audit_logger_with_no_log_path(self):
        """Test audit logger without a log path."""
        logger = AuditLogger()
        logger.log("test", "blocked", reason="test")
        logger.flush()  # Should not raise

    def test_command_inspector_with_both_lists(self):
        """Test inspector with both allowlist and denylist."""
        inspector = CommandInspector(
            allowed_commands={"ls", "cat"},
            denied_commands={"rm"},
        )
        # rm should be blocked (explicit deny)
        is_safe, _, _ = inspector.inspect("rm file.txt")
        assert is_safe is False

        # ls should be allowed (in allowlist)
        is_safe, _, _ = inspector.inspect("ls -la")
        assert is_safe is True

        # python should be blocked (not in allowlist)
        is_safe, _, _ = inspector.inspect("python script.py")
        assert is_safe is False
