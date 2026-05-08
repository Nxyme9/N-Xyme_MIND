"""
Plugin System — Dynamic extension loading for N-Xyme MIND.

Ported from: types/plugin.ts, utils/plugins/*.ts (Claude Code)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import subprocess
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PluginComponent(str, Enum):
    COMMANDS = "commands"
    AGENTS = "agents"
    SKILLS = "skills"
    HOOKS = "hooks"
    OUTPUT_STYLES = "output-styles"
    MCP = "mcp"
    LSP = "lsp"


class PluginSource(str, Enum):
    BUILTIN = "builtin"
    MARKETPLACE = "marketplace"
    LOCAL = "local"
    SESSION = "session"
    NPM = "npm"


class PluginErrorType(str, Enum):
    GENERIC_ERROR = "generic-error"
    PLUGIN_NOT_FOUND = "plugin-not-found"
    PATH_NOT_FOUND = "path-not-found"
    GIT_AUTH_FAILED = "git-auth-failed"
    GIT_TIMEOUT = "git-timeout"
    NETWORK_ERROR = "network-error"
    MANIFEST_PARSE_ERROR = "manifest-parse-error"
    MANIFEST_VALIDATION_ERROR = "manifest-validation-error"
    MARKETPLACE_NOT_FOUND = "marketplace-not-found"
    MARKETPLACE_LOAD_FAILED = "marketplace-load-failed"
    MCP_CONFIG_INVALID = "mcp-config-invalid"
    HOOK_LOAD_FAILED = "hook-load-failed"
    COMPONENT_LOAD_FAILED = "component-load-failed"


@dataclass
class PluginAuthor:
    name: str
    email: Optional[str] = None
    url: Optional[str] = None


@dataclass
class PluginManifest:
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    author: Optional[PluginAuthor] = None
    repository: Optional[str] = None
    license: str = "MIT"
    homepage: Optional[str] = None
    commands: dict = field(default_factory=dict)
    commands_paths: list[str] = field(default_factory=list)
    agents: dict = field(default_factory=dict)
    agents_paths: list[str] = field(default_factory=list)
    skills: dict = field(default_factory=dict)
    skills_paths: list[str] = field(default_factory=list)
    hooks: dict = field(default_factory=dict)
    hooks_config: dict = field(default_factory=dict)
    mcp_servers: dict = field(default_factory=dict)
    lsp_servers: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    is_available: Optional[Callable[[], bool]] = None


@dataclass
class LoadedPlugin:
    name: str
    manifest: PluginManifest
    path: Path
    source: PluginSource
    repository: str
    enabled: bool = True
    is_builtin: bool = False
    sha: Optional[str] = None
    commands_path: Optional[Path] = None
    agents_path: Optional[Path] = None
    skills_path: Optional[Path] = None
    hooks_config: dict = field(default_factory=dict)
    mcp_servers: dict = field(default_factory=dict)
    lsp_servers: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)
    loaded_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class PluginError:
    type: PluginErrorType
    source: str
    plugin: Optional[str] = None
    message: str = ""
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        base = f"[{self.type.value}] {self.source}"
        if self.plugin:
            base += f" ({self.plugin})"
        if self.message:
            base += f": {self.message}"
        return base


@dataclass
class PluginLoadResult:
    success: bool
    plugin: Optional[LoadedPlugin] = None
    errors: list[PluginError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PluginRepository:
    url: str
    branch: str = "main"
    last_updated: Optional[str] = None
    commit_sha: Optional[str] = None


@dataclass
class MarketplacedPluginEntry:
    plugin_id: str
    name: str
    description: str
    version: str
    author: PluginAuthor
    repository: PluginRepository
    downloads: int = 0
    rating: float = 0.0
    tags: list[str] = field(default_factory=list)
    is_official: bool = False
    auto_update: bool = True


class PluginPolicy:
    """Plugin security policy enforcement."""

    OFFICIAL_MARKETPLACE_NAMES = {
        "claude-code-marketplace",
        "claude-code-plugins",
        "claude-plugins-official",
        "anthropic-marketplace",
        "anthropic-plugins",
        "agent-skills",
        "life-sciences",
        "knowledge-work-plugins",
    }

    NO_AUTO_UPDATE_OFFICIAL = {"knowledge-work-plugins"}

    BLOCKED_NAME_PATTERN = __import__("re").compile(
        r"(?:official[^a-z0-9]*(anthropic|claude)|(?:anthropic|claude)[^a-z0-9]*official|^(?:anthropic|claude)[^a-z0-9]*(marketplace|plugins|official))",
        __import__("re").I,
    )

    @classmethod
    def is_blocked_name(cls, name: str) -> bool:
        normalized = name.lower()
        if normalized in cls.OFFICIAL_MARKETPLACE_NAMES:
            return False
        return bool(cls.BLOCKED_NAME_PATTERN.search(name))

    @classmethod
    def is_auto_update_enabled(cls, marketplace: str, entry: dict) -> bool:
        normalized = marketplace.lower()
        return entry.get("autoUpdate", normalized in cls.OFFICIAL_MARKETPLACE_NAMES and normalized not in cls.NO_AUTO_UPDATE_OFFICIAL)


class PluginDirectoryManager:
    """Manages plugin directory paths."""

    DEFAULT_PLUGINS_DIR = Path.home() / ".config" / "nxyme" / "plugins"
    DEFAULT_CACHE_DIR = DEFAULT_PLUGINS_DIR / "cache"
    DEFAULT_SEED_DIRS: list[Path] = []

    def __init__(self, plugins_dir: Optional[Path] = None, cache_dir: Optional[Path] = None):
        self._plugins_dir = plugins_dir or self.DEFAULT_PLUGINS_DIR
        self._cache_dir = cache_dir or self.DEFAULT_CACHE_DIR

    @property
    def plugins_dir(self) -> Path:
        return self._plugins_dir

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def get_plugin_path(self, plugin_name: str, marketplace: str = "local") -> Path:
        safe_marketplace = "".join(c if c.isalnum() or c in "-_" else "-" for c in marketplace)
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in plugin_name)
        return self._plugins_dir / safe_marketplace / safe_name

    def get_cache_path(self, plugin_id: str, version: str) -> Path:
        safe_marketplace, safe_name = self._parse_plugin_id(plugin_id)
        safe_version = "".join(c if c.isalnum() or c in "-_." else "-" for c in version)
        return self._cache_dir / safe_marketplace / safe_name / safe_version

    def ensure_directories(self) -> None:
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _parse_plugin_id(self, plugin_id: str) -> tuple[str, str]:
        if "@" in plugin_id:
            parts = plugin_id.rsplit("@", 1)
            return parts[1], parts[0]
        return "local", plugin_id


class PluginManifestLoader:
    """Loads and validates plugin manifests."""

    REQUIRED_FIELDS = {"name", "version"}
    VALID_COMPONENTS = {"commands", "agents", "skills", "hooks", "mcp-servers", "lsp-servers"}

    @classmethod
    def load(cls, path: Path) -> Optional[PluginManifest]:
        if not path.exists():
            return None

        try:
            if path.suffix == ".json":
                data = json.loads(path.read_text())
            elif path.suffix in {".yaml", ".yml"}:
                data = {"yaml_placeholder": True}
            else:
                return None
            return cls._parse_manifest(data)
        except Exception as e:
            logger.error(f"Failed to load manifest {path}: {e}")
            return None

    @classmethod
    def _parse_manifest(cls, data: dict) -> Optional[PluginManifest]:
        for field in cls.REQUIRED_FIELDS:
            if field not in data:
                logger.warning(f"Manifest missing required field: {field}")
                return None

        author = None
        if author_data := data.get("author"):
            author = PluginAuthor(
                name=author_data.get("name", "Unknown"),
                email=author_data.get("email"),
                url=author_data.get("url"),
            )

        return PluginManifest(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description"),
            author=author,
            repository=data.get("repository"),
            license=data.get("license", "MIT"),
            homepage=data.get("homepage"),
            commands=data.get("commands", {}),
            commands_paths=data.get("commandsPaths", []),
            agents=data.get("agents", {}),
            agents_paths=data.get("agentsPaths", []),
            skills=data.get("skills", {}),
            skills_paths=data.get("skillsPaths", []),
            hooks=data.get("hooks", {}),
            hooks_config=data.get("hooksConfig", {}),
            mcp_servers=data.get("mcpServers", {}),
            lsp_servers=data.get("lspServers", {}),
            settings=data.get("settings", {}),
            dependencies=data.get("dependencies", []),
        )

    @classmethod
    def _parse_simple_yaml(cls, path: Path) -> dict:
        content = path.read_text()
        result = {}
        current_key = None
        current_values = []

        for line in content.split("\n"):
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue

            if ":" in stripped:
                if current_key:
                    result[current_key] = "\n".join(current_values) if current_values else True
                key, _, value = stripped.partition(": ")
                current_key = key.strip()
                current_values = [value.strip()] if value.strip() else []
            else:
                current_values.append(stripped)

        if current_key:
            result[current_key] = "\n".join(current_values) if current_values else True

        return result


class PluginLoader:
    """Discovers, loads, and validates plugins."""

    def __init__(
        self,
        dir_manager: Optional[PluginDirectoryManager] = None,
        max_workers: int = 4,
    ):
        self._dir_manager = dir_manager or PluginDirectoryManager()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._loaded_plugins: dict[str, LoadedPlugin] = {}
        self._plugin_futures: dict[str, asyncio.Future] = {}
        self._lock = threading.Lock()

    async def discover_plugins(self, sources: list[PluginSource] = None) -> list[PluginLoadResult]:
        sources = sources or [PluginSource.LOCAL, PluginSource.MARKETPLACE]
        results = []

        if PluginSource.LOCAL in sources:
            results.extend(await self._discover_local_plugins())

        if PluginSource.MARKETPLACE in sources:
            results.extend(await self._discover_marketplace_plugins())

        return results

    async def _discover_local_plugins(self) -> list[PluginLoadResult]:
        results = []
        plugins_dir = self._dir_manager.plugins_dir

        if not plugins_dir.exists():
            return results

        for marketplace_dir in plugins_dir.iterdir():
            if not marketplace_dir.is_dir():
                continue

            for plugin_dir in marketplace_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue

                manifest_path = plugin_dir / "plugin.json"
                if not manifest_path.exists():
                    manifest_path = plugin_dir / "plugin.yaml"

                if manifest_path.exists():
                    result = await self._load_plugin_dir(plugin_dir, manifest_path, marketplace_dir.name)
                    results.append(result)

        return results

    async def _discover_marketplace_plugins(self) -> list[PluginLoadResult]:
        return []

    async def _load_plugin_dir(self, path: Path, manifest_path: Path, marketplace: str) -> PluginLoadResult:
        manifest = PluginManifestLoader.load(manifest_path)
        if not manifest:
            return PluginLoadResult(
                success=False,
                errors=[PluginError(
                    type=PluginErrorType.MANIFEST_PARSE_ERROR,
                    source="local",
                    plugin=path.name,
                    message=f"Failed to parse manifest: {manifest_path}",
                )],
            )

        plugin = LoadedPlugin(
            name=manifest.name,
            manifest=manifest,
            path=path,
            source=PluginSource.LOCAL,
            repository=marketplace,
            commands_path=path / "commands" if (path / "commands").exists() else None,
            agents_path=path / "agents" if (path / "agents").exists() else None,
            skills_path=path / "skills" if (path / "skills").exists() else None,
            hooks_config=manifest.hooks_config,
            mcp_servers=manifest.mcp_servers,
            lsp_servers=manifest.lsp_servers,
            settings=manifest.settings,
        )

        with self._lock:
            self._loaded_plugins[plugin.name] = plugin

        return PluginLoadResult(success=True, plugin=plugin)

    async def load_plugin(self, plugin_id: str, source: PluginSource = PluginSource.LOCAL) -> PluginLoadResult:
        with self._lock:
            if plugin_id in self._loaded_plugins:
                return PluginLoadResult(
                    success=True,
                    plugin=self._loaded_plugins[plugin_id],
                )

        if source == PluginSource.LOCAL:
            return await self._load_from_directory(plugin_id)

        return PluginLoadResult(
            success=False,
            errors=[PluginError(
                type=PluginErrorType.PLUGIN_NOT_FOUND,
                source=source.value,
                plugin=plugin_id,
                message="Plugin not found",
            )],
        )

    async def _load_from_directory(self, plugin_id: str) -> PluginLoadResult:
        parts = plugin_id.rsplit("@", 1)
        name = parts[0]
        marketplace = parts[1] if len(parts) > 1 else "local"

        plugin_path = self._dir_manager.get_plugin_path(name, marketplace)
        manifest_paths = [plugin_path / "plugin.json", plugin_path / "plugin.yaml"]

        for manifest_path in manifest_paths:
            if manifest_path.exists():
                return await self._load_plugin_dir(plugin_path, manifest_path, marketplace)

        return PluginLoadResult(
            success=False,
            errors=[PluginError(
                type=PluginErrorType.PATH_NOT_FOUND,
                source="local",
                plugin=plugin_id,
                path=str(plugin_path),
            )],
        )

    async def load_from_git(self, plugin_id: str, git_url: str, branch: str = "main") -> PluginLoadResult:
        cache_path = self._dir_manager.get_cache_path(plugin_id, branch)

        if not cache_path.exists():
            try:
                result = subprocess.run(
                    ["git", "clone", "--branch", branch, "--depth", "1", git_url, str(cache_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    return PluginLoadResult(
                        success=False,
                        errors=[PluginError(
                            type=PluginErrorType.GIT_TIMEOUT,
                            source="git",
                            plugin=plugin_id,
                            gitUrl=git_url,
                            message=result.stderr,
                        )],
                    )
            except subprocess.TimeoutExpired:
                return PluginLoadResult(
                    success=False,
                    errors=[PluginError(
                        type=PluginErrorType.GIT_TIMEOUT,
                        source="git",
                        plugin=plugin_id,
                        gitUrl=git_url,
                        operation="clone",
                    )],
                )
            except Exception as e:
                return PluginLoadResult(
                    success=False,
                    errors=[PluginError(
                        type=PluginErrorType.NETWORK_ERROR,
                        source="git",
                        plugin=plugin_id,
                        url=git_url,
                        message=str(e),
                    )],
                )

        result = await self._load_plugin_dir(cache_path, cache_path / "plugin.json", "git")
        if result.success and result.plugin:
            result.plugin.sha = self._get_git_sha(cache_path)

        return result

    def _get_git_sha(self, path: Path) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def get_loaded_plugin(self, name: str) -> Optional[LoadedPlugin]:
        return self._loaded_plugins.get(name)

    def list_loaded_plugins(self) -> list[LoadedPlugin]:
        return list(self._loaded_plugins.values())

    def unload_plugin(self, name: str) -> bool:
        with self._lock:
            if name in self._loaded_plugins:
                del self._loaded_plugins[name]
                return True
        return False


class PluginManager:
    """High-level plugin management with enable/disable, caching, updates."""

    def __init__(self, loader: Optional[PluginLoader] = None):
        self._loader = loader or PluginLoader()
        self._enabled: set[str] = set()
        self._disabled: set[str] = set()
        self._settings_path = Path.home() / ".config" / "nxyme" / "plugins.json"

    async def initialize(self) -> None:
        self._loader._dir_manager.ensure_directories()
        await self._load_settings()
        await self._loader.discover_plugins()

    async def _load_settings(self) -> None:
        if self._settings_path.exists():
            try:
                data = json.loads(self._settings_path.read_text())
                self._enabled = set(data.get("enabled", []))
                self._disabled = set(data.get("disabled", []))
            except Exception as e:
                logger.warning(f"Failed to load plugin settings: {e}")

    async def _save_settings(self) -> None:
        data = {
            "enabled": list(self._enabled),
            "disabled": list(self._disabled),
        }
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        self._settings_path.write_text(json.dumps(data, indent=2))

    async def enable_plugin(self, name: str) -> bool:
        result = await self._loader.load_plugin(name)
        if result.success:
            self._enabled.add(name)
            self._disabled.discard(name)
            await self._save_settings()
            return True
        return False

    async def disable_plugin(self, name: str) -> bool:
        if name in self._loaded_plugins:
            self._disabled.add(name)
            self._enabled.discard(name)
            await self._save_settings()
            return True
        return False

    def is_enabled(self, name: str) -> bool:
        if name in self._disabled:
            return False
        if name in self._enabled:
            return True
        plugin = self._loader.get_loaded_plugin(name)
        return plugin.is_builtin if plugin else True

    def list_enabled(self) -> list[LoadedPlugin]:
        return [p for p in self._loader.list_loaded_plugins() if self.is_enabled(p.name)]

    def list_disabled(self) -> list[LoadedPlugin]:
        return [p for p in self._loader.list_loaded_plugins() if not self.is_enabled(p.name)]

    @property
    def _loaded_plugins(self) -> dict:
        return self._loader._loaded_plugins


class BuiltinPluginRegistry:
    """Registry for built-in plugins that ship with the CLI."""

    _builtins: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, plugin_class: type) -> None:
        cls._builtins[name] = plugin_class

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        return cls._builtins.get(name)

    @classmethod
    def list_all(cls) -> list[str]:
        return list(cls._builtins.keys())

    @classmethod
    def is_builtin(cls, name: str) -> bool:
        return name in cls._builtins


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> Optional[PluginManager]:
    return _plugin_manager


async def init_plugin_system(
    plugins_dir: Optional[Path] = None,
    cache_dir: Optional[Path] = None,
) -> PluginManager:
    global _plugin_manager

    dir_manager = PluginDirectoryManager(plugins_dir, cache_dir)
    loader = PluginLoader(dir_manager)
    _plugin_manager = PluginManager(loader)

    await _plugin_manager.initialize()
    return _plugin_manager


__all__ = [
    "PluginComponent",
    "PluginSource",
    "PluginErrorType",
    "PluginAuthor",
    "PluginManifest",
    "LoadedPlugin",
    "PluginError",
    "PluginLoadResult",
    "PluginRepository",
    "MarketplacedPluginEntry",
    "PluginPolicy",
    "PluginDirectoryManager",
    "PluginManifestLoader",
    "PluginLoader",
    "PluginManager",
    "BuiltinPluginRegistry",
    "get_plugin_manager",
    "init_plugin_system",
]