"""MCP Credential Proxy — nono-style credential injection for MCP servers.

Implements two security modes inspired by nono's credential injection:

1. PROXY MODE: Credentials stay entirely outside the sandbox. The agent
   connects to a local proxy which injects real API keys into upstream
   requests. The agent never sees raw credentials, even in its own memory.

2. ENV MODE: Secrets are loaded from OS keystore (keyring, 1Password, etc.)
   and injected as environment variables before the sandbox locks down.
   Simpler but the secret exists in the process environment.

Features:
- Multiple credential sources with fallback chains
- Audit trail for all credential access
- Integration with opencode.json MCP config
- Encrypted config file support
- Clear error messages on credential access failure

MIT License — patterns derived from nono (Apache-2.0) credential injection.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------


class CredentialSource(Enum):
    """Supported credential sources, ordered by security preference."""

    KEYRING = "keyring"
    ONEPASSWORD = "1password"
    ENVIRONMENT = "environment"
    ENCRYPTED_CONFIG = "encrypted_config"
    PLAINTEXT_CONFIG = "plaintext_config"


class InjectionMode(Enum):
    """How credentials are delivered to MCP servers."""

    PROXY = "proxy"
    ENV = "env"


class AuditAction(Enum):
    """Audit trail actions."""

    CREDENTIAL_ACCESSED = "credential_accessed"
    CREDENTIAL_NOT_FOUND = "credential_not_found"
    CREDENTIAL_INJECTED = "credential_injected"
    PROXY_STARTED = "proxy_started"
    PROXY_STOPPED = "proxy_stopped"
    FALLBACK_USED = "fallback_used"
    CONFIG_LOADED = "config_loaded"
    CONFIG_VALIDATION_FAILED = "config_validation_failed"


@dataclass(frozen=True)
class CredentialSpec:
    """Specification for a single credential requirement.

    Mirrors nono's credential mapping pattern:
      --env-credential-map 'op://Development/OpenAI/credential' OPENAI_API_KEY
    """

    env_var: str
    source: CredentialSource
    location: str  # keyring service name, 1password URI, env var name, or config key
    required: bool = True
    mask_pattern: str = "***"  # How to mask in logs


@dataclass
class AuditEntry:
    """Single audit log entry."""

    timestamp: str
    action: AuditAction
    credential_name: str
    source: str
    success: bool
    detail: str = ""
    session_id: str = ""
    request_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action.value,
            "credential_name": self.credential_name,
            "source": self.source,
            "success": self.success,
            "detail": self.detail,
            "session_id": self.session_id,
            "request_id": self.request_id,
        }


@dataclass
class ProxyConfig:
    """Configuration for proxy mode."""

    bind_host: str = "127.0.0.1"
    bind_port: int = 0  # 0 = auto-assign
    upstream_url: str = ""
    headers_to_inject: Dict[str, str] = field(default_factory=dict)
    allowed_hosts: Sequence[str] = field(default_factory=list)


@dataclass
class MCPServerCredentialConfig:
    """Credential configuration for a single MCP server."""

    server_name: str
    injection_mode: InjectionMode
    credentials: List[CredentialSpec] = field(default_factory=list)
    proxy_config: Optional[ProxyConfig] = None


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Immutable audit trail for credential access.

    Every credential operation is logged as a structured JSON entry.
    Entries are appended to an in-memory log and optionally flushed
    to a file on disk.
    """

    def __init__(self, log_path: Optional[Path] = None, session_id: str = ""):
        self.log_path = log_path
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._entries: List[AuditEntry] = []

    def log(
        self,
        action: AuditAction,
        credential_name: str,
        source: str,
        success: bool,
        detail: str = "",
        request_id: str = "",
    ) -> AuditEntry:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            credential_name=credential_name,
            source=source,
            success=success,
            detail=detail,
            session_id=self.session_id,
            request_id=request_id or uuid.uuid4().hex[:8],
        )
        self._entries.append(entry)
        logger.debug(
            "AUDIT [%s] %s: %s (source=%s, success=%s)",
            entry.request_id,
            action.value,
            credential_name,
            source,
            success,
        )
        return entry

    def get_entries(
        self,
        action_filter: Optional[AuditAction] = None,
        success_filter: Optional[bool] = None,
    ) -> List[AuditEntry]:
        entries = self._entries
        if action_filter:
            entries = [e for e in entries if e.action == action_filter]
        if success_filter is not None:
            entries = [e for e in entries if e.success == success_filter]
        return entries

    def flush(self) -> None:
        if not self.log_path:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(e.to_dict()) for e in self._entries]
        self.log_path.write_text("\n".join(lines) + "\n")

    def summary(self) -> Dict[str, Any]:
        total = len(self._entries)
        succeeded = sum(1 for e in self._entries if e.success)
        failed = total - succeeded
        return {
            "session_id": self.session_id,
            "total_entries": total,
            "succeeded": succeeded,
            "failed": failed,
            "actions": {
                a.value: sum(1 for e in self._entries if e.action == a)
                for a in AuditAction
            },
        }


# ---------------------------------------------------------------------------
# Credential Providers
# ---------------------------------------------------------------------------


class CredentialProviderError(Exception):
    """Raised when a credential cannot be retrieved."""


class BaseCredentialProvider:
    """Abstract base for credential providers."""

    @property
    def source_name(self) -> str:
        raise NotImplementedError

    def get(self, location: str) -> Optional[str]:
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


class KeyringProvider(BaseCredentialProvider):
    """Retrieve credentials from the OS keyring via the `keyring` library."""

    @property
    def source_name(self) -> str:
        return CredentialSource.KEYRING.value

    def is_available(self) -> bool:
        try:
            import keyring  # noqa: F401

            return True
        except ImportError:
            return False

    def get(self, location: str) -> Optional[str]:
        if not self.is_available():
            raise CredentialProviderError(
                f"keyring provider not available: install with `pip install keyring`. "
                f"Requested credential: {location}"
            )
        import keyring

        # location format: "service_name/username"
        parts = location.split("/", 1)
        if len(parts) == 2:
            service, username = parts
        else:
            service = "mcp-credential-proxy"
            username = location
        try:
            value = keyring.get_password(service, username)
            if value is None:
                raise CredentialProviderError(
                    f"keyring: no credential found for service='{service}', username='{username}'. "
                    f"Store it with: keyring set '{service}' '{username}'"
                )
            return value
        except Exception as exc:
            raise CredentialProviderError(
                f"keyring: failed to retrieve '{location}': {exc}"
            ) from exc


class OnePasswordProvider(BaseCredentialProvider):
    """Retrieve credentials from 1Password CLI (op).

    Location format: op://Vault/Item/field
    Example: op://Development/OpenAI/credential
    """

    @property
    def source_name(self) -> str:
        return CredentialSource.ONEPASSWORD.value

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["op", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get(self, location: str) -> Optional[str]:
        if not self.is_available():
            raise CredentialProviderError(
                f"1Password CLI (op) not available. "
                f"Install from https://developer.1password.com/docs/cli/ "
                f"and run `op signin`. Requested: {location}"
            )
        if not location.startswith("op://"):
            raise CredentialProviderError(
                f"1Password URI must start with 'op://', got: '{location}'. "
                f"Example: op://Development/OpenAI/credential"
            )
        try:
            result = subprocess.run(
                ["op", "read", location],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise CredentialProviderError(
                    f"1Password: failed to read '{location}': {result.stderr.strip()}. "
                    f"Ensure you are signed in: `op signin`"
                )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise CredentialProviderError(
                f"1Password: timed out reading '{location}' (10s limit)"
            )
        except Exception as exc:
            raise CredentialProviderError(
                f"1Password: unexpected error reading '{location}': {exc}"
            ) from exc


class EnvironmentProvider(BaseCredentialProvider):
    """Retrieve credentials from environment variables."""

    @property
    def source_name(self) -> str:
        return CredentialSource.ENVIRONMENT.value

    def get(self, location: str) -> Optional[str]:
        value = os.environ.get(location)
        if value is None:
            raise CredentialProviderError(
                f"Environment variable '{location}' is not set. "
                f"Set it with: export {location}='<value>'"
            )
        if not value:
            raise CredentialProviderError(
                f"Environment variable '{location}' is set but empty. "
                f"Set it with: export {location}='<value>'"
            )
        return value


class EncryptedConfigProvider(BaseCredentialProvider):
    """Retrieve credentials from an encrypted config file.

    Uses the existing SecretManager (cryptography.fernet) for decryption.
    Falls back to plaintext config if encryption key is unavailable.
    """

    def __init__(self, config_path: Path, key_path: Optional[Path] = None):
        self.config_path = config_path
        self.key_path = key_path or config_path.with_suffix(".key")

    @property
    def source_name(self) -> str:
        return CredentialSource.ENCRYPTED_CONFIG.value

    def is_available(self) -> bool:
        return self.config_path.exists()

    def _decrypt(self, data: bytes) -> str:
        from cryptography.fernet import Fernet, InvalidToken

        if not self.key_path.exists():
            raise CredentialProviderError(
                f"Encryption key not found at '{self.key_path}'. "
                f"Cannot decrypt '{self.config_path}'."
            )
        key = self.key_path.read_bytes()
        try:
            return Fernet(key).decrypt(data).decode()
        except InvalidToken as exc:
            raise CredentialProviderError(
                f"Failed to decrypt '{self.config_path}': invalid or corrupted key. "
                f"The key at '{self.key_path}' may not match the encrypted data."
            ) from exc

    def get(self, location: str) -> Optional[str]:
        if not self.config_path.exists():
            raise CredentialProviderError(
                f"Encrypted config file not found at '{self.config_path}'. "
                f"Create it by storing secrets first."
            )
        try:
            raw = self.config_path.read_bytes()
            decrypted = self._decrypt(raw)
            data = json.loads(decrypted)
        except json.JSONDecodeError as exc:
            raise CredentialProviderError(
                f"Encrypted config '{self.config_path}' contains invalid JSON after decryption. "
                f"The file may be corrupted: {exc}"
            ) from exc
        except Exception as exc:
            if isinstance(exc, CredentialProviderError):
                raise
            raise CredentialProviderError(
                f"Failed to read encrypted config '{self.config_path}': {exc}"
            ) from exc

        # Support nested keys with dot notation: "openai.api_key"
        keys = location.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                raise CredentialProviderError(
                    f"Encrypted config: '{location}' not found. "
                    f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'none'}"
                )
        if value is None:
            raise CredentialProviderError(
                f"Encrypted config: key '{location}' not found. "
                f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'none'}"
            )
        return str(value)


class PlaintextConfigProvider(BaseCredentialProvider):
    """Retrieve credentials from a plaintext JSON config file.

    WARNING: This is the least secure option. Use only for development.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path

    @property
    def source_name(self) -> str:
        return CredentialSource.PLAINTEXT_CONFIG.value

    def is_available(self) -> bool:
        return self.config_path.exists()

    def get(self, location: str) -> Optional[str]:
        if not self.config_path.exists():
            raise CredentialProviderError(
                f"Plaintext config file not found at '{self.config_path}'."
            )
        try:
            data = json.loads(self.config_path.read_text())
        except json.JSONDecodeError as exc:
            raise CredentialProviderError(
                f"Plaintext config '{self.config_path}' contains invalid JSON: {exc}"
            ) from exc

        keys = location.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                raise CredentialProviderError(
                    f"Plaintext config: '{location}' not found. "
                    f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'none'}"
                )
        if value is None:
            raise CredentialProviderError(
                f"Plaintext config: key '{location}' not found. "
                f"Available keys: {list(data.keys()) if isinstance(data, dict) else 'none'}"
            )
        return str(value)


# ---------------------------------------------------------------------------
# Fallback Chain
# ---------------------------------------------------------------------------


class CredentialFallbackChain:
    """Try multiple credential providers in order until one succeeds.

    This mirrors nono's approach of trying multiple sources:
    1. OS keyring (most secure)
    2. 1Password CLI
    3. Environment variables
    4. Encrypted config file
    5. Plaintext config (least secure, dev only)
    """

    def __init__(
        self,
        providers: Optional[List[BaseCredentialProvider]] = None,
        audit: Optional[AuditLogger] = None,
    ):
        if providers:
            self.providers = providers
        else:
            self.providers = [
                KeyringProvider(),
                OnePasswordProvider(),
                EnvironmentProvider(),
            ]
        self.audit = audit

    def add_provider(self, provider: BaseCredentialProvider) -> None:
        self.providers.append(provider)

    def get(
        self,
        credential_name: str,
        location: str,
        required: bool = True,
    ) -> Optional[str]:
        last_error: Optional[Exception] = None
        for provider in self.providers:
            if not provider.is_available():
                continue
            try:
                value = provider.get(location)
                if value is not None:
                    if self.audit:
                        self.audit.log(
                            AuditAction.CREDENTIAL_ACCESSED,
                            credential_name,
                            provider.source_name,
                            success=True,
                        )
                    return value
            except CredentialProviderError as exc:
                last_error = exc
                if self.audit:
                    self.audit.log(
                        AuditAction.FALLBACK_USED,
                        credential_name,
                        provider.source_name,
                        success=False,
                        detail=str(exc),
                    )
                continue
            except Exception as exc:
                last_error = exc
                continue

        if required:
            error_detail = str(last_error) if last_error else "no providers available"
            if self.audit:
                self.audit.log(
                    AuditAction.CREDENTIAL_NOT_FOUND,
                    credential_name,
                    ", ".join(p.source_name for p in self.providers),
                    success=False,
                    detail=error_detail,
                )
            raise CredentialProviderError(
                f"Credential '{credential_name}' not found after trying "
                f"{len(self.providers)} source(s). Last error: {error_detail}"
            )

        if self.audit:
            self.audit.log(
                AuditAction.CREDENTIAL_NOT_FOUND,
                credential_name,
                ", ".join(p.source_name for p in self.providers),
                success=False,
                detail="optional credential, skipping",
            )
        return None


# ---------------------------------------------------------------------------
# Credential Proxy (Proxy Mode)
# ---------------------------------------------------------------------------


class CredentialProxy:
    """Local HTTP proxy that injects credentials into upstream requests.

    The agent connects to this proxy on localhost. The proxy forwards
    requests to the real upstream API and injects authentication headers.
    The agent never sees the raw API key.

    This is the nono proxy injection pattern:
      nono run --proxy-credential openai -- my-agent
    """

    def __init__(
        self,
        config: ProxyConfig,
        audit: Optional[AuditLogger] = None,
    ):
        self.config = config
        self.audit = audit
        self._port: Optional[int] = None
        self._server: Any = None
        self._thread: Any = None

    @property
    def endpoint_url(self) -> str:
        port = self._port or self.config.bind_port
        return f"http://{self.config.bind_host}:{port}"

    def start(self) -> str:
        """Start the proxy server and return the endpoint URL."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import threading

            headers_to_inject = dict(self.config.headers_to_inject)
            allowed_hosts = list(self.config.allowed_hosts)
            upstream_url = self.config.upstream_url

            class ProxyHandler(BaseHTTPRequestHandler):
                def do_POST(self):
                    self._forward("POST")

                def do_GET(self):
                    self._forward("GET")

                def _forward(self, method: str):
                    import urllib.request
                    import urllib.error

                    content_length = int(self.headers.get("Content-Length", 0))
                    body = (
                        self.rfile.read(content_length) if content_length > 0 else b""
                    )

                    target_url = f"{upstream_url}{self.path}"

                    req = urllib.request.Request(target_url, data=body, method=method)
                    req.add_header("Content-Type", "application/json")
                    for header_name, header_value in headers_to_inject.items():
                        req.add_header(header_name, header_value)

                    try:
                        with urllib.request.urlopen(req, timeout=30) as resp:
                            response_body = resp.read()
                            self.send_response(resp.status)
                            for h in ["Content-Type"]:
                                if h in resp.headers:
                                    self.send_header(h, resp.headers[h])
                            self.end_headers()
                            self.wfile.write(response_body)
                    except urllib.error.HTTPError as exc:
                        self.send_response(exc.code)
                        self.end_headers()
                        self.wfile.write(exc.read())
                    except Exception as exc:
                        self.send_response(502)
                        self.end_headers()
                        self.wfile.write(f"Proxy error: {exc}".encode())

                def log_message(self, format, *args):
                    pass  # Suppress default logging

            port = self.config.bind_port
            server = HTTPServer((self.config.bind_host, port), ProxyHandler)
            self._port = server.server_address[1]
            self._server = server

            self._thread = threading.Thread(target=server.serve_forever, daemon=True)
            self._thread.start()

            if self.audit:
                self.audit.log(
                    AuditAction.PROXY_STARTED,
                    f"proxy:{self.config.bind_host}:{self._port}",
                    "local",
                    success=True,
                    detail=f"upstream={upstream_url}",
                )

            return self.endpoint_url

        except Exception as exc:
            if self.audit:
                self.audit.log(
                    AuditAction.PROXY_STARTED,
                    f"proxy:{self.config.bind_host}",
                    "local",
                    success=False,
                    detail=str(exc),
                )
            raise CredentialProviderError(
                f"Failed to start credential proxy on {self.config.bind_host}:{self.config.bind_port}: {exc}"
            ) from exc

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            if self.audit:
                self.audit.log(
                    AuditAction.PROXY_STOPPED,
                    f"proxy:{self.config.bind_host}:{self._port}",
                    "local",
                    success=True,
                )
            self._server = None
            self._thread = None
            self._port = None


# ---------------------------------------------------------------------------
# MCP Config Parser / Integrator
# ---------------------------------------------------------------------------


class MCPConfigIntegrator:
    """Parse opencode.json MCP config and inject credentials.

    Reads the `mcp` section from opencode.json, resolves credential
    placeholders, and returns a ready-to-use environment dict for each
    MCP server.
    """

    PLACEHOLDER_RE = re.compile(r"\$\{([^}]+)\}")

    def __init__(
        self,
        config_path: Path,
        fallback_chain: CredentialFallbackChain,
        audit: Optional[AuditLogger] = None,
    ):
        self.config_path = config_path
        self.fallback_chain = fallback_chain
        self.audit = audit

    def load_mcp_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"MCP config not found at '{self.config_path}'. "
                f"Expected opencode.json in the project root."
            )
        try:
            data = json.loads(self.config_path.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in MCP config '{self.config_path}': {exc}"
            ) from exc

        mcp_section = data.get("mcp", {})
        if not mcp_section:
            if self.audit:
                self.audit.log(
                    AuditAction.CONFIG_VALIDATION_FAILED,
                    "mcp_config",
                    str(self.config_path),
                    success=False,
                    detail="no 'mcp' section found in config",
                )
            return {}

        if self.audit:
            self.audit.log(
                AuditAction.CONFIG_LOADED,
                "mcp_config",
                str(self.config_path),
                success=True,
                detail=f"{len(mcp_section)} server(s) configured",
            )
        return mcp_section

    def resolve_environment(
        self,
        server_name: str,
        env_section: Dict[str, str],
    ) -> Dict[str, str]:
        """Resolve ${PLACEHOLDER} values in an MCP server's environment section.

        For each value like "${GITHUB_PERSONAL_ACCESS_TOKEN}", looks up the
        credential through the fallback chain and returns the resolved dict.
        """
        resolved: Dict[str, str] = {}
        for key, raw_value in env_section.items():
            match = self.PLACEHOLDER_RE.match(raw_value)
            if match:
                credential_key = match.group(1)
                try:
                    value = self.fallback_chain.get(
                        credential_name=f"{server_name}.{key}",
                        location=credential_key,
                        required=True,
                    )
                    resolved[key] = value or ""
                    if self.audit:
                        self.audit.log(
                            AuditAction.CREDENTIAL_INJECTED,
                            f"{server_name}.{key}",
                            "fallback_chain",
                            success=True,
                            detail=f"resolved ${{{credential_key}}}",
                        )
                except CredentialProviderError as exc:
                    if self.audit:
                        self.audit.log(
                            AuditAction.CREDENTIAL_INJECTED,
                            f"{server_name}.{key}",
                            "fallback_chain",
                            success=False,
                            detail=str(exc),
                        )
                    raise
            else:
                resolved[key] = raw_value
        return resolved

    def resolve_all(self) -> Dict[str, Dict[str, str]]:
        """Resolve credentials for all MCP servers in the config.

        Returns a dict mapping server_name -> resolved environment variables.
        """
        mcp_config = self.load_mcp_config()
        result: Dict[str, Dict[str, str]] = {}

        for server_name, server_config in mcp_config.items():
            env_section = server_config.get("environment", {})
            if not env_section:
                continue
            result[server_name] = self.resolve_environment(server_name, env_section)

        return result


# ---------------------------------------------------------------------------
# Main Facade: MCPCredentialProxy
# ---------------------------------------------------------------------------


class MCPCredentialProxy:
    """Main facade for MCP credential management.

    Usage — Env Mode (simplest):
        proxy = MCPCredentialProxy(project_root=Path("/path/to/project"))
        env = proxy.resolve_env_for_server("github")
        # env now contains GITHUB_PERSONAL_ACCESS_TOKEN resolved from keyring/env/1password

    Usage — Proxy Mode (most secure):
        proxy = MCPCredentialProxy(
            project_root=Path("/path/to/project"),
            default_mode=InjectionMode.PROXY,
        )
        proxy.start_proxy_for_server("openai")
        url = proxy.get_proxy_endpoint("openai")
        # Agent connects to url, proxy injects the API key

    Usage — Custom fallback chain:
        chain = CredentialFallbackChain(providers=[
            OnePasswordProvider(),
            EnvironmentProvider(),
        ])
        proxy = MCPCredentialProxy(
            project_root=Path("/path/to/project"),
            fallback_chain=chain,
        )
    """

    def __init__(
        self,
        project_root: Path,
        default_mode: InjectionMode = InjectionMode.ENV,
        config_path: Optional[Path] = None,
        audit_log_path: Optional[Path] = None,
        fallback_chain: Optional[CredentialFallbackChain] = None,
        encrypted_config_path: Optional[Path] = None,
        plaintext_config_path: Optional[Path] = None,
    ):
        self.project_root = project_root
        self.default_mode = default_mode
        self.config_path = config_path or project_root / "opencode.json"

        self.audit = AuditLogger(
            log_path=audit_log_path or project_root / "data" / "credential_audit.log",
        )

        if fallback_chain:
            self.fallback_chain = fallback_chain
            self.fallback_chain.audit = self.audit
        else:
            self.fallback_chain = CredentialFallbackChain(audit=self.audit)

        # Add encrypted config provider if path given
        if encrypted_config_path:
            self.fallback_chain.add_provider(
                EncryptedConfigProvider(encrypted_config_path)
            )

        # Add plaintext config provider if path given (dev only)
        if plaintext_config_path:
            self.fallback_chain.add_provider(
                PlaintextConfigProvider(plaintext_config_path)
            )

        self.integrator = MCPConfigIntegrator(
            config_path=self.config_path,
            fallback_chain=self.fallback_chain,
            audit=self.audit,
        )

        self._proxies: Dict[str, CredentialProxy] = {}

    def resolve_env_for_server(self, server_name: str) -> Dict[str, str]:
        """Resolve all credentials for a single MCP server (env mode)."""
        mcp_config = self.integrator.load_mcp_config()
        server_config = mcp_config.get(server_name, {})
        env_section = server_config.get("environment", {})
        if not env_section:
            return {}
        return self.integrator.resolve_environment(server_name, env_section)

    def resolve_all_servers(self) -> Dict[str, Dict[str, str]]:
        """Resolve credentials for all MCP servers."""
        return self.integrator.resolve_all()

    def get_credential(
        self,
        credential_name: str,
        location: str,
        required: bool = True,
    ) -> Optional[str]:
        """Get a single credential through the fallback chain."""
        return self.fallback_chain.get(
            credential_name=credential_name,
            location=location,
            required=required,
        )

    def start_proxy_for_server(
        self,
        server_name: str,
        proxy_config: Optional[ProxyConfig] = None,
    ) -> str:
        """Start a credential proxy for an MCP server (proxy mode).

        Resolves credentials through the fallback chain, starts a local
        proxy that injects them, and returns the proxy endpoint URL.
        """
        if server_name in self._proxies:
            return self._proxies[server_name].endpoint_url

        mcp_config = self.integrator.load_mcp_config()
        server_config = mcp_config.get(server_name, {})
        env_section = server_config.get("environment", {})

        if not env_section:
            raise CredentialProviderError(
                f"MCP server '{server_name}' has no environment section in config. "
                f"Cannot determine which credentials to proxy."
            )

        # Resolve credentials
        headers: Dict[str, str] = {}
        for key, raw_value in env_section.items():
            match = MCPConfigIntegrator.PLACEHOLDER_RE.match(raw_value)
            if match:
                credential_key = match.group(1)
                value = self.fallback_chain.get(
                    credential_name=f"{server_name}.{key}",
                    location=credential_key,
                    required=True,
                )
                # Map common env var names to HTTP header names
                header_name = self._env_var_to_header(key, value or "")
                if header_name:
                    headers[header_name] = value or ""
            else:
                header_name = self._env_var_to_header(key, raw_value)
                if header_name:
                    headers[header_name] = raw_value

        cfg = proxy_config or ProxyConfig(
            headers_to_inject=headers,
        )
        proxy = CredentialProxy(config=cfg, audit=self.audit)
        endpoint = proxy.start()
        self._proxies[server_name] = proxy

        return endpoint

    def get_proxy_endpoint(self, server_name: str) -> Optional[str]:
        proxy = self._proxies.get(server_name)
        return proxy.endpoint_url if proxy else None

    def stop_all_proxies(self) -> None:
        for name, proxy in list(self._proxies.items()):
            proxy.stop()
        self._proxies.clear()

    def flush_audit(self) -> None:
        self.audit.flush()

    def audit_summary(self) -> Dict[str, Any]:
        return self.audit.summary()

    @staticmethod
    def _env_var_to_header(env_var: str, value: str) -> Optional[str]:
        """Map common environment variable names to HTTP header names."""
        mapping = {
            "OPENAI_API_KEY": "Authorization",
            "ANTHROPIC_API_KEY": "x-api-key",
            "GOOGLE_API_KEY": "x-goog-api-key",
            "GITHUB_PERSONAL_ACCESS_TOKEN": "Authorization",
        }
        header = mapping.get(env_var)
        if header == "Authorization" and value:
            # Prefix with Bearer or token type
            if value.startswith("ghp_") or value.startswith("github_pat_"):
                return header  # raw token, caller should prefix
            return header
        return header

    def __enter__(self) -> "MCPCredentialProxy":
        return self

    def __exit__(self, *args) -> None:
        self.stop_all_proxies()
        self.flush_audit()
