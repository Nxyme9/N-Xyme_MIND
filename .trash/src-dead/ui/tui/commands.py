"""Command registry for TUI dashboard actions.

This module provides a Command dataclass and CommandRegistry class for managing
dashboard commands in the Textual TUI framework.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Command:
    """Represents a dashboard command.
    
    Attributes:
        id: Unique identifier for the command.
        name: Display name of the command.
        description: Human-readable description of what the command does.
        callback: Callable to execute when the command is invoked.
        shortcut: Optional keyboard shortcut for quick access.
    """
    id: str
    name: str
    description: str
    callback: Callable
    shortcut: str | None = None


class CommandRegistry:
    """Registry for managing dashboard commands.
    
    Provides methods to register, unregister, and retrieve commands
    by ID or keyboard shortcut.
    """
    
    def __init__(self) -> None:
        """Initialize an empty command registry."""
        self._commands: dict[str, Command] = {}
    
    def register(self, command: Command) -> None:
        """Register a command in the registry.
        
        Args:
            command: The Command instance to register.
            
        Raises:
            ValueError: If a command with the same ID is already registered.
        """
        if command.id in self._commands:
            raise ValueError(f"Command with id '{command.id}' is already registered")
        self._commands[command.id] = command
    
    def unregister(self, command_id: str) -> bool:
        """Unregister a command from the registry.
        
        Args:
            command_id: The unique identifier of the command to unregister.
            
        Returns:
            True if the command was unregistered, False if it wasn't found.
        """
        if command_id in self._commands:
            del self._commands[command_id]
            return True
        return False
    
    def get(self, command_id: str) -> Command | None:
        """Retrieve a command by its ID.
        
        Args:
            command_id: The unique identifier of the command.
            
        Returns:
            The Command if found, None otherwise.
        """
        return self._commands.get(command_id)
    
    def get_by_shortcut(self, key: str) -> Command | None:
        """Retrieve a command by its keyboard shortcut.
        
        Args:
            key: The keyboard shortcut to search for.
            
        Returns:
            The Command if found, None otherwise.
        """
        for command in self._commands.values():
            if command.shortcut == key:
                return command
        return None
    
    def get_all(self) -> list[Command]:
        """Get all registered commands.
        
        Returns:
            A list of all registered Command objects.
        """
        return list(self._commands.values())
