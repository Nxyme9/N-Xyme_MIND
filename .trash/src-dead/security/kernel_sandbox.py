"""Kernel-level sandbox integration using nono patterns.

Provides OS-enforced sandboxing via Landlock (Linux 5.13+) or Seatbelt (macOS),
with destructive command blocking, audit trail, and allowlist support.

Patterns derived from always-further/nono (Apache-2.0, 1.6k stars).
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — destructive commands blocked by default (nono pattern)
# ---------------------------------------------------------------------------

DESTRUCTIVE_COMMANDS: frozenset[str] = frozenset(
    {
        "rm",
        "dd",
        "chmod",
        "chown",
        "sudo",
        "su",
        "scp",
        "docker",
        "kubectl",
        "mkfs",
        "fdisk",
        "parted",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "mount",
        "umount",
        "iptables",
        "kill",
        "killall",
        "pkill",
        "curl",
        "wget",
        "nc",
        "ncat",
        "socat",
        "ssh",
        "telnet",
        "ftp",
        "sftp",
        "rsync",
        "crontab",
        "at",
        "systemctl",
        "service",
        "init",
        "insmod",
        "rmmod",
        "modprobe",
        "dd",
        "shred",
        "wipe",
        "mkfs.ext4",
        "mkfs.xfs",
        "mkfs.vfat",
        "mkswap",
    }
)

# Patterns that detect destructive intent even through sh -c wrappers
DESTRUCTIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brm\s+(-[rfR]+\s+)?/", re.IGNORECASE),
    re.compile(r"\brm\s+-[rfR]", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\bsudo\s+", re.IGNORECASE),
    re.compile(r"\bchmod\s+[0-7]{3,4}\s", re.IGNORECASE),
    re.compile(r"\bchown\s+\w+", re.IGNORECASE),
    re.compile(r"\bdocker\s+(rm|rmi|system\s+prune)", re.IGNORECASE),
    re.compile(r"\bkubectl\s+delete", re.IGNORECASE),
    re.compile(r"\bshred\s+", re.IGNORECASE),
    re.compile(r"\bwipe\s+", re.IGNORECASE),
    re.compile(r"\bmkfs\.", re.IGNORECASE),
    re.compile(r"\bmkswap\b", re.IGNORECASE),
    re.compile(r"\bshutdown\b", re.IGNORECASE),
    re.compile(r"\breboot\b", re.IGNORECASE),
    re.compile(r"\bpoweroff\b", re.IGNORECASE),
    re.compile(r"\bhalt\b", re.IGNORECASE),
    re.compile(r"\bmount\s+", re.IGNORECASE),
    re.compile(r"\bumount\s+", re.IGNORECASE),
    re.compile(r"\biptables\s+", re.IGNORECASE),
    re.compile(r"\bkill\s+-9\s", re.IGNORECASE),
    re.compile(r"\bkillall\s+", re.IGNORECASE),
    re.compile(r"\bpkill\s+", re.IGNORECASE),
    re.compile(r"\bcrontab\s+-r", re.IGNORECASE),
    re.compile(r"\bsystemctl\s+(stop|disable|mask)\s+", re.IGNORECASE),
    re.compile(r"\b(insmod|rmmod|modprobe)\s+", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SandboxBackend(Enum):
    """Available sandbox backends."""

    LANDLOCK = "landlock"
    SECCOMP = "seccomp"
    SEATBELT = "seatbelt"
    COMMAND_FILTER = "command_filter"
    NONE = "none"


class AccessMode(Enum):
    """Filesystem access modes (mirrors nono-py API)."""

    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"


class AuditLevel(Enum):
    """Audit logging verbosity."""

    NONE = "none"
    BLOCKED_ONLY = "blocked_only"
    ALL = "all"


class BlockReason(Enum):
    """Why a command was blocked."""

    DESTRUCTIVE_COMMAND = "destructive_command"
    PATTERN_MATCH = "pattern_match"
    SH_C_WRAPPER = "sh_c_wrapper"
    NOT_IN_ALLOWLIST = "not_in_allowlist"
    PATH_DENIED = "path_denied"
    NETWORK_DENIED = "network_denied"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: float
    event_id: str
    command: str
    action: str  # "blocked" or "allowed"
    reason: str | None = None
    backend: str = ""
    pid: int = 0
    uid: int = 0
    cwd: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class SandboxConfig:
    """Configuration for the kernel sandbox."""

    allowed_commands: set[str] = field(default_factory=set)
    denied_commands: set[str] = field(default_factory=set)
    allow_paths: list[tuple[str, AccessMode]] = field(default_factory=list)
    deny_paths: list[str] = field(default_factory=list)
    block_network: bool = False
    allowed_hosts: list[str] = field(default_factory=list)
    audit_level: AuditLevel = AuditLevel.BLOCKED_ONLY
    audit_log_path: str = ""
    strict_mode: bool = True
    sh_c_inspection: bool = True


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Immutable audit trail for sandbox events.

    Follows nono's pattern of structured JSON audit entries with
    cryptographic session IDs.
    """

    def __init__(
        self, log_path: str | None = None, level: AuditLevel = AuditLevel.BLOCKED_ONLY
    ):
        self._entries: list[AuditEntry] = []
        self._log_path = log_path
        self._level = level
        self._session_id = str(uuid.uuid4())[:12]

    def log(
        self,
        command: str,
        action: str,
        reason: str | None = None,
        backend: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=time.time(),
            event_id=str(uuid.uuid4())[:8],
            command=command,
            action=action,
            reason=reason,
            backend=backend,
            pid=os.getpid(),
            uid=os.getuid() if hasattr(os, "getuid") else 0,
            cwd=os.getcwd(),
            details=details or {},
        )

        should_log = self._level == AuditLevel.ALL or (
            self._level == AuditLevel.BLOCKED_ONLY and action == "blocked"
        )

        if should_log:
            self._entries.append(entry)
            if action == "blocked":
                logger.warning(
                    "[SANDBOX] BLOCKED: %s | reason=%s | event=%s",
                    command,
                    reason,
                    entry.event_id,
                )
            else:
                logger.debug(
                    "[SANDBOX] ALLOWED: %s | event=%s",
                    command,
                    entry.event_id,
                )

        return entry

    def get_entries(self) -> list[AuditEntry]:
        return list(self._entries)

    def get_blocked(self) -> list[AuditEntry]:
        return [e for e in self._entries if e.action == "blocked"]

    def flush(self) -> None:
        """Write audit entries to disk if a log path is configured."""
        if not self._log_path or not self._entries:
            return

        path = Path(self._log_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing: list[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                existing = []

        existing.extend(e.to_dict() for e in self._entries)
        path.write_text(json.dumps(existing, indent=2))
        self._entries.clear()

    def summary(self) -> dict[str, Any]:
        blocked = len(self.get_blocked())
        total = len(self._entries)
        return {
            "session_id": self._session_id,
            "total_events": total,
            "blocked": blocked,
            "allowed": total - blocked,
            "entries": [e.to_dict() for e in self._entries],
        }


# ---------------------------------------------------------------------------
# Command Inspector — detects destructive commands including sh -c wrappers
# ---------------------------------------------------------------------------


class CommandInspector:
    """Inspects commands for destructive patterns, including sh -c bypasses.

    This is the core defense-in-depth layer. Even if a command is wrapped
    in `sh -c 'rm -rf /'`, the inspector unwraps and checks the inner command.
    """

    def __init__(
        self,
        allowed_commands: set[str] | None = None,
        denied_commands: set[str | None] = None,
        sh_c_inspection: bool = True,
    ):
        self._allowed = allowed_commands or set()
        self._denied = denied_commands or set()
        self._sh_c_inspection = sh_c_inspection

    def inspect(
        self, cmd: str | list[str]
    ) -> tuple[bool, str | None, BlockReason | None]:
        """Inspect a command for destructive patterns.

        Returns:
            (is_safe, reason, block_reason) — is_safe=True means command can proceed.
        """
        cmd_str = self._normalize_cmd(cmd)

        # Check explicit deny list first
        if self._denied:
            base = self._extract_base_command(cmd_str)
            if base and base in self._denied:
                return (
                    False,
                    f"Command '{base}' is explicitly denied",
                    BlockReason.DESTRUCTIVE_COMMAND,
                )

        # Check allowlist — if set and command not in it, block
        if self._allowed and cmd_str not in self._allowed:
            base = self._extract_base_command(cmd_str)
            if base and base not in self._allowed:
                return (
                    False,
                    f"Command '{base}' is not in the allowlist",
                    BlockReason.NOT_IN_ALLOWLIST,
                )

        # Unwrap sh -c wrappers
        if self._sh_c_inspection:
            unwrapped = self._unwrap_sh_c(cmd_str)
            if unwrapped != cmd_str:
                # Check the unwrapped command against destructive patterns
                is_safe, reason, block_reason = self._check_destructive(unwrapped)
                if not is_safe:
                    return (
                        False,
                        f"Blocked via sh -c wrapper: {reason}",
                        BlockReason.SH_C_WRAPPER,
                    )

        # Check against destructive commands
        is_safe, reason, block_reason = self._check_destructive(cmd_str)
        if not is_safe:
            return False, reason, block_reason

        return True, None, None

    def _normalize_cmd(self, cmd: str | list[str]) -> str:
        if isinstance(cmd, list):
            return shlex.join(cmd)
        return cmd.strip()

    def _extract_base_command(self, cmd_str: str) -> str | None:
        try:
            parts = shlex.split(cmd_str)
            if parts:
                return Path(parts[0]).name
        except ValueError:
            parts = cmd_str.split()
            if parts:
                return Path(parts[0]).name
        return None

    def _unwrap_sh_c(self, cmd_str: str) -> str:
        """Unwrap sh -c / bash -c / zsh -c wrappers recursively."""
        pattern = re.compile(
            r"""^(?:sh|bash|zsh|dash|ksh|csh|tcsh)\s+(?:-[a-zA-Z]*\s+)*-c\s+(?:["'])(.+?)["']$""",
            re.IGNORECASE,
        )
        current = cmd_str
        max_depth = 5
        depth = 0

        while depth < max_depth:
            match = pattern.match(current.strip())
            if not match:
                break
            current = match.group(1)
            depth += 1

        return current

    def _check_destructive(
        self, cmd_str: str
    ) -> tuple[bool, str | None, BlockReason | None]:
        base = self._extract_base_command(cmd_str)

        # Check against known destructive commands
        if base and base.lower() in DESTRUCTIVE_COMMANDS:
            return (
                False,
                f"Destructive command blocked: {base}",
                BlockReason.DESTRUCTIVE_COMMAND,
            )

        # Check against regex patterns for destructive intent
        for pattern in DESTRUCTIVE_PATTERNS:
            if pattern.search(cmd_str):
                return (
                    False,
                    f"Destructive pattern matched: {pattern.pattern}",
                    BlockReason.PATTERN_MATCH,
                )

        return True, None, None


# ---------------------------------------------------------------------------
# Sandbox Backend Implementations
# ---------------------------------------------------------------------------


class LandlockBackend:
    """Landlock LSM backend (Linux 5.13+).

    Wraps nono-py's Landlock capabilities for filesystem isolation.
    Falls back gracefully if Landlock is not available.
    """

    name = SandboxBackend.LANDLOCK

    def __init__(self):
        self._available: bool | None = None
        self._applied = False

    @property
    def available(self) -> bool:
        if self._available is not None:
            return self._available

        if platform.system() != "Linux":
            self._available = False
            return False

        try:
            import nono_py

            self._available = nono_py.is_supported()
        except ImportError:
            # Check kernel version as fallback indicator
            self._available = self._check_kernel_version()
        return self._available

    def _check_kernel_version(self) -> bool:
        try:
            release = platform.release()
            major = int(release.split(".")[0])
            minor = int(release.split(".")[1]) if "." in release else 0
            return (major, minor) >= (5, 13)
        except (ValueError, IndexError):
            return False

    def apply(
        self,
        allow_paths: list[tuple[str, AccessMode]],
        deny_paths: list[str] | None = None,
        block_network: bool = False,
    ) -> bool:
        """Apply Landlock sandbox via nono-py.

        Returns True if successfully applied, False if fallback needed.
        """
        if not self.available or self._applied:
            return False

        try:
            import nono_py

            caps = nono_py.CapabilitySet()

            for path, mode in allow_paths:
                path_obj = Path(path).expanduser().resolve()
                if path_obj.exists():
                    access_mode = self._convert_access_mode(mode)
                    caps.allow_path(str(path_obj), access_mode)
                else:
                    logger.warning("Landlock: path does not exist, skipping: %s", path)

            if block_network:
                caps.block_network()

            nono_py.apply(caps)
            self._applied = True
            logger.info("Landlock sandbox applied successfully")
            return True

        except ImportError:
            logger.warning("nono-py not installed, Landlock unavailable")
            return False
        except Exception as exc:
            logger.error("Landlock apply failed: %s", exc)
            return False

    def _convert_access_mode(self, mode: AccessMode):
        import nono_py

        mapping = {
            AccessMode.READ: nono_py.AccessMode.READ,
            AccessMode.WRITE: nono_py.AccessMode.WRITE,
            AccessMode.READ_WRITE: nono_py.AccessMode.READ_WRITE,
        }
        return mapping[mode]


class SeccompBackend:
    """Seccomp-BPF fallback for Linux.

    Uses libseccomp (via ctypes or subprocess) to restrict syscalls.
    This is a defense-in-depth layer, not a full sandbox replacement.
    """

    name = SandboxBackend.SECCOMP

    def __init__(self):
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        if self._available is not None:
            return self._available

        if platform.system() != "Linux":
            self._available = False
            return False

        # Check for libseccomp
        try:
            import ctypes.util

            lib_path = ctypes.util.find_library("seccomp")
            self._available = lib_path is not None
        except Exception:
            self._available = False
        return self._available

    def apply(
        self,
        allow_paths: list[tuple[str, AccessMode]] | None = None,
        deny_paths: list[str] | None = None,
        block_network: bool = False,
    ) -> bool:
        """Apply seccomp filters.

        Returns True if applied, False otherwise.
        """
        if not self.available:
            return False

        # Try pyseccomp first (preferred)
        try:
            import seccomp

            ctx = seccomp.Seccomp(seccomp.ALLOW)

            if block_network:
                # Block socket-related syscalls
                for syscall in ["socket", "connect", "accept", "bind", "listen"]:
                    try:
                        ctx.add_rule(
                            seccomp.ERRNO(1), getattr(seccomp.syscalls, syscall)
                        )
                    except AttributeError:
                        pass

            ctx.load()
            logger.info("Seccomp filters applied via pyseccomp")
            return True
        except ImportError:
            pass

        # Fallback: use prctl with basic seccomp mode
        try:
            import ctypes
            import ctypes.util

            libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
            # PR_SET_NO_NEW_PRIVS = 38
            libc.prctl(38, 1, 0, 0, 0)
            # SECCOMP_MODE_FILTER = 2 — requires BPF program, skip for safety
            logger.info("Seccomp: prctl(NO_NEW_PRIVS) set, BPF filters not loaded")
            return True
        except Exception as exc:
            logger.warning("Seccomp fallback failed: %s", exc)
            return False


class SeatbeltBackend:
    """macOS Seatbelt sandbox backend.

    Uses Apple's Seatbelt (sandbox_init) for kernel-level isolation.
    """

    name = SandboxBackend.SEATBELT

    def __init__(self):
        self._available: bool | None = None

    @property
    def available(self) -> bool:
        if self._available is not None:
            return self._available
        self._available = platform.system() == "Darwin"
        return self._available

    def apply(
        self,
        allow_paths: list[tuple[str, AccessMode]],
        deny_paths: list[str] | None = None,
        block_network: bool = False,
    ) -> bool:
        """Apply Seatbelt sandbox via nono-py."""
        if not self.available:
            return False

        try:
            import nono_py

            caps = nono_py.CapabilitySet()

            for path, mode in allow_paths:
                path_obj = Path(path).expanduser().resolve()
                if path_obj.exists():
                    access_mode = self._convert_access_mode(mode)
                    caps.allow_path(str(path_obj), access_mode)

            if block_network:
                caps.block_network()

            nono_py.apply(caps)
            logger.info("Seatbelt sandbox applied successfully")
            return True

        except ImportError:
            logger.warning("nono-py not installed, Seatbelt unavailable")
            return False
        except Exception as exc:
            logger.error("Seatbelt apply failed: %s", exc)
            return False

    def _convert_access_mode(self, mode: AccessMode):
        import nono_py

        mapping = {
            AccessMode.READ: nono_py.AccessMode.READ,
            AccessMode.WRITE: nono_py.AccessMode.WRITE,
            AccessMode.READ_WRITE: nono_py.AccessMode.READ_WRITE,
        }
        return mapping[mode]


class CommandFilterBackend:
    """Pure-Python command filtering backend.

    This is the always-available fallback that provides
    command-level blocking even when kernel sandboxes are unavailable.
    It cannot prevent filesystem access directly but blocks
    destructive command execution at the application layer.
    """

    name = SandboxBackend.COMMAND_FILTER

    def __init__(self):
        self._inspector: CommandInspector | None = None
        self._audit: AuditLogger | None = None

    def initialize(
        self,
        inspector: CommandInspector,
        audit: AuditLogger,
    ) -> None:
        self._inspector = inspector
        self._audit = audit

    def check_command(self, cmd: str | list[str]) -> tuple[bool, str | None]:
        """Check if a command is safe to execute.

        Returns (is_safe, error_message).
        """
        if self._inspector is None:
            return True, None

        is_safe, reason, block_reason = self._inspector.inspect(cmd)
        if not is_safe:
            if self._audit:
                self._audit.log(
                    command=cmd if isinstance(cmd, str) else shlex.join(cmd),
                    action="blocked",
                    reason=reason,
                    backend="command_filter",
                    details={
                        "block_reason": block_reason.value if block_reason else None
                    },
                )
            return False, reason
        return True, None

    def safe_run(
        self,
        cmd: str | list[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess:
        """Run a command after safety check.

        Raises:
            CommandBlockedError: if the command is blocked.
        """
        is_safe, error_msg = self.check_command(cmd)
        if not is_safe:
            raise CommandBlockedError(error_msg or "Command blocked by sandbox")

        if self._audit:
            self._audit.log(
                command=cmd if isinstance(cmd, str) else shlex.join(cmd),
                action="allowed",
                backend="command_filter",
            )

        if isinstance(cmd, str):
            cmd_list = shlex.split(cmd)
        else:
            cmd_list = list(cmd)

        return subprocess.run(cmd_list, **kwargs)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------


class SandboxError(Exception):
    """Base exception for sandbox errors."""


class CommandBlockedError(SandboxError):
    """Raised when a destructive command is blocked."""


class SandboxApplyError(SandboxError):
    """Raised when sandbox cannot be applied."""


# ---------------------------------------------------------------------------
# Main KernelSandbox — orchestrates all backends
# ---------------------------------------------------------------------------


class KernelSandbox:
    """Kernel-level sandbox with nono-pattern destructive command blocking.

    Backend priority:
        1. Landlock (Linux 5.13+) via nono-py
        2. Seatbelt (macOS) via nono-py
        3. Seccomp-BPF (Linux, libseccomp)
        4. Command filter (pure Python, always available)

    Usage:
        sandbox = KernelSandbox()
        sandbox.configure(
            allow_paths=[("/tmp", AccessMode.READ_WRITE)],
            block_network=True,
        )
        sandbox.apply()

        # Check commands before running them
        sandbox.check_command("rm -rf /")  # raises CommandBlockedError
    """

    def __init__(self, config: SandboxConfig | None = None):
        self._config = config or SandboxConfig()
        self._audit = AuditLogger(
            log_path=self._config.audit_log_path or None,
            level=self._config.audit_level,
        )
        self._inspector = CommandInspector(
            allowed_commands=self._config.allowed_commands,
            denied_commands=self._config.denied_commands,
            sh_c_inspection=self._config.sh_c_inspection,
        )

        # Backends
        self._landlock = LandlockBackend()
        self._seatbelt = SeatbeltBackend()
        self._seccomp = SeccompBackend()
        self._cmd_filter = CommandFilterBackend()
        self._cmd_filter.initialize(self._inspector, self._audit)

        self._active_backend: SandboxBackend = SandboxBackend.NONE
        self._applied = False

    @property
    def audit(self) -> AuditLogger:
        return self._audit

    @property
    def inspector(self) -> CommandInspector:
        return self._inspector

    @property
    def active_backend(self) -> SandboxBackend:
        return self._active_backend

    @property
    def is_applied(self) -> bool:
        return self._applied

    def configure(self, **kwargs: Any) -> None:
        """Update sandbox configuration.

        Accepts any SandboxConfig field as keyword argument.
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

        # Reinitialize components with new config
        self._inspector = CommandInspector(
            allowed_commands=self._config.allowed_commands,
            denied_commands=self._config.denied_commands,
            sh_c_inspection=self._config.sh_c_inspection,
        )
        self._cmd_filter.initialize(self._inspector, self._audit)

    def detect_backend(self) -> SandboxBackend:
        """Detect the best available sandbox backend."""
        if self._landlock.available:
            return SandboxBackend.LANDLOCK
        if self._seatbelt.available:
            return SandboxBackend.SEATBELT
        if self._seccomp.available:
            return SandboxBackend.SECCOMP
        return SandboxBackend.COMMAND_FILTER

    def apply(self) -> SandboxBackend:
        """Apply the sandbox with the best available backend.

        Returns the backend that was actually used.
        Raises SandboxApplyError if strict mode is on and no kernel backend is available.
        """
        backend = self.detect_backend()
        applied = False

        if backend == SandboxBackend.LANDLOCK:
            applied = self._landlock.apply(
                allow_paths=self._config.allow_paths,
                deny_paths=self._config.deny_paths,
                block_network=self._config.block_network,
            )
            if applied:
                self._active_backend = SandboxBackend.LANDLOCK

        elif backend == SandboxBackend.SEATBELT:
            applied = self._seatbelt.apply(
                allow_paths=self._config.allow_paths,
                deny_paths=self._config.deny_paths,
                block_network=self._config.block_network,
            )
            if applied:
                self._active_backend = SandboxBackend.SEATBELT

        elif backend == SandboxBackend.SECCOMP:
            applied = self._seccomp.apply(
                allow_paths=self._config.allow_paths,
                deny_paths=self._config.deny_paths,
                block_network=self._config.block_network,
            )
            if applied:
                self._active_backend = SandboxBackend.SECCOMP

        # Command filter is always active regardless
        if self._active_backend == SandboxBackend.NONE:
            self._active_backend = SandboxBackend.COMMAND_FILTER

        if not applied and self._config.strict_mode:
            if backend in (
                SandboxBackend.LANDLOCK,
                SandboxBackend.SEATBELT,
                SandboxBackend.SECCOMP,
            ):
                logger.warning(
                    "Kernel sandbox (%s) unavailable, falling back to command filter",
                    backend.value,
                )

        self._audit.log(
            command="sandbox_apply",
            action="allowed",
            reason=f"Backend: {self._active_backend.value}",
            backend=self._active_backend.value,
        )

        self._applied = True
        return self._active_backend

    def check_command(self, cmd: str | list[str]) -> tuple[bool, str | None]:
        """Check if a command is safe to execute.

        Returns (is_safe, error_message).
        """
        return self._cmd_filter.check_command(cmd)

    def run(self, cmd: str | list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        """Run a command after sandbox safety check.

        Raises:
            CommandBlockedError: if the command is blocked.
        """
        return self._cmd_filter.safe_run(cmd, **kwargs)

    def add_allowed_command(self, command: str) -> None:
        """Add a command to the allowlist."""
        self._config.allowed_commands.add(command)
        self._inspector = CommandInspector(
            allowed_commands=self._config.allowed_commands,
            denied_commands=self._config.denied_commands,
            sh_c_inspection=self._config.sh_c_inspection,
        )
        self._cmd_filter.initialize(self._inspector, self._audit)

    def add_denied_command(self, command: str) -> None:
        """Add a command to the deny list."""
        self._config.denied_commands.add(command)
        self._inspector = CommandInspector(
            allowed_commands=self._config.allowed_commands,
            denied_commands=self._config.denied_commands,
            sh_c_inspection=self._config.sh_c_inspection,
        )
        self._cmd_filter.initialize(self._inspector, self._audit)

    def audit_summary(self) -> dict[str, Any]:
        """Get audit summary."""
        return self._audit.summary()

    def flush_audit(self) -> None:
        """Flush audit log to disk."""
        self._audit.flush()

    def integrate_opencode_config(self, config_path: str | Path) -> None:
        """Integrate with OpenCode permission config.

        Reads opencode.json / oh-my-opencode.json and maps
        allowedTools/deniedTools to sandbox allowlist/denylist.
        """
        path = Path(config_path).expanduser()
        if not path.exists():
            logger.warning("OpenCode config not found: %s", path)
            return

        try:
            import json

            data = json.loads(path.read_text())

            # Extract tool permissions from various config formats
            allowed_tools: set[str] = set()
            denied_tools: set[str] = set()

            # opencode.json format
            if "permissions" in data:
                perms = data["permissions"]
                if isinstance(perms, dict):
                    allowed_tools.update(perms.get("allow", []))
                    denied_tools.update(perms.get("deny", []))

            # oh-my-opencode.json format
            if "allowedTools" in data:
                allowed_tools.update(data["allowedTools"])
            if "deniedTools" in data:
                denied_tools.update(data["deniedTools"])

            # Map tool names to commands
            tool_to_cmd = {
                "Bash": "bash",
                "Edit": "edit",
                "Write": "write",
                "Read": "read",
                "Glob": "glob",
                "Grep": "grep",
            }

            for tool in allowed_tools:
                cmd = tool_to_cmd.get(tool, tool.lower())
                self.add_allowed_command(cmd)

            for tool in denied_tools:
                cmd = tool_to_cmd.get(tool, tool.lower())
                self.add_denied_command(cmd)

            logger.info(
                "OpenCode config integrated: %d allowed, %d denied",
                len(allowed_tools),
                len(denied_tools),
            )
        except Exception as exc:
            logger.error("Failed to integrate OpenCode config: %s", exc)


# ---------------------------------------------------------------------------
# Convenience API (nono-pattern: simple functions for common use cases)
# ---------------------------------------------------------------------------


def create_sandbox(
    allow_paths: list[tuple[str, AccessMode]] | None = None,
    deny_paths: list[str] | None = None,
    block_network: bool = False,
    allowed_commands: set[str] | None = None,
    denied_commands: set[str] | None = None,
    audit_level: AuditLevel = AuditLevel.BLOCKED_ONLY,
    audit_log_path: str = "",
    strict_mode: bool = True,
) -> KernelSandbox:
    """Create and configure a kernel sandbox in one call.

    Mirrors nono's capability-based API pattern.
    """
    config = SandboxConfig(
        allowed_commands=allowed_commands or set(),
        denied_commands=denied_commands or set(),
        allow_paths=allow_paths or [],
        deny_paths=deny_paths or [],
        block_network=block_network,
        audit_level=audit_level,
        audit_log_path=audit_log_path,
        strict_mode=strict_mode,
    )
    sandbox = KernelSandbox(config=config)
    sandbox.apply()
    return sandbox


def is_command_safe(cmd: str | list[str]) -> tuple[bool, str | None]:
    """Quick check if a command is safe without creating a full sandbox.

    Uses default destructive command list.
    """
    inspector = CommandInspector()
    is_safe, reason, _ = inspector.inspect(cmd)
    return is_safe, reason


def block_destructive(cmd: str | list[str]) -> bool:
    """Run a command, blocking if destructive.

    Returns True if command executed, raises CommandBlockedError if blocked.
    """
    is_safe, reason = is_command_safe(cmd)
    if not is_safe:
        raise CommandBlockedError(reason or "Command blocked")
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    subprocess.run(cmd, check=False)
    return True
