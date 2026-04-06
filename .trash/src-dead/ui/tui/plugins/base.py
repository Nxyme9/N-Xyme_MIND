"""Base plugin classes and plugin manager."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass
class PluginMetadata:
    """Metadata for a plugin.

    Attributes:
        id: Unique identifier for the plugin.
        name: Human-readable name of the plugin.
        version: Version string of the plugin.
        author: Author of the plugin.
        description: Description of the plugin's functionality.
    """

    id: str
    name: str
    version: str
    author: str
    description: str


class Plugin(ABC):
    """Base class for all TUI dashboard plugins.

    Plugins must inherit from this class and implement the abstract methods.

    Attributes:
        app: Reference to the application instance.
        config: Plugin configuration dictionary.
    """

    def __init__(self, app: Any, config: dict[str, Any] | None = None) -> None:
        """Initialize the plugin.

        Args:
            app: Reference to the application instance.
            config: Optional configuration dictionary for the plugin.
        """
        self.app = app
        self.config = config or {}

    @abstractmethod
    def on_load(self) -> None:
        """Called when the plugin is loaded.

        Use this method to initialize plugin resources and setup.
        """
        ...

    @abstractmethod
    def on_unload(self) -> None:
        """Called when the plugin is unloaded.

        Use this method to cleanup resources and teardown.
        """
        ...

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get the plugin metadata.

        Returns:
            PluginMetadata instance containing plugin information.
        """
        ...


class PluginManager:
    """Manager for registering and managing plugins.

    This class handles plugin lifecycle including registration,
    unregistration, and retrieval.
    """

    def __init__(self) -> None:
        """Initialize the plugin manager."""
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin.

        Args:
            plugin: The plugin instance to register.

        Raises:
            ValueError: If a plugin with the same ID is already registered.
        """
        metadata = plugin.get_metadata()
        if metadata.id in self._plugins:
            raise ValueError(f"Plugin with id '{metadata.id}' is already registered")
        self._plugins[metadata.id] = plugin
        plugin.on_load()

    def unregister(self, plugin_id: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_id: The ID of the plugin to unregister.

        Raises:
            KeyError: If no plugin with the given ID is registered.
        """
        plugin = self._plugins.pop(plugin_id)
        plugin.on_unload()

    def get(self, plugin_id: str) -> Plugin | None:
        """Get a plugin by its ID.

        Args:
            plugin_id: The ID of the plugin to retrieve.

        Returns:
            The plugin instance if found, None otherwise.
        """
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[PluginMetadata]:
        """List metadata for all registered plugins.

        Returns:
            List of PluginMetadata for all registered plugins.
        """
        return [plugin.get_metadata() for plugin in self._plugins.values()]
