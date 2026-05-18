"""Voice command system — command registry with aliases, vocabulary support."""

import logging
import re
from typing import Callable, Dict, List, Optional

from nx_dictate.config import CommandConfig

logger = logging.getLogger(__name__)


class VoiceCommandRecognizer:
    """Command registry with aliases. Ported from CATALYST voice_control.py pattern."""

    def __init__(self, config: CommandConfig) -> None:
        self.config = config
        self._handlers: Dict[str, Callable] = {}
        self._aliases: Dict[str, str] = {}
        self._command_map = {k.lower(): v for k, v in config.commands.items()}

        # Register built-in commands as handlers
        for cmd_name, action in self._command_map.items():
            self._register_cmd(cmd_name, action)

    def _register_cmd(self, name: str, action: str) -> None:
        """Register a built-in command action."""
        def _make_handler(a):
            return lambda: a
        self.register(name, _make_handler(action), aliases=[name])

    def register(self, command: str, handler: Callable, aliases: Optional[List[str]] = None) -> None:
        """Register a command with optional aliases."""
        self._handlers[command.lower()] = handler
        if aliases:
            for alias in aliases:
                self._aliases[alias.lower()] = command.lower()

    def recognize(self, text: str) -> Optional[str]:
        """Check if text matches a command. Returns action string or None."""
        if not self.config.enabled:
            return None

        text_lower = text.lower().strip()
        command_text = self._extract_command_text(text_lower)
        if command_text is None:
            return None

        # Try aliases first
        resolved = self._aliases.get(command_text)
        if resolved:
            return self._command_map.get(resolved)

        # Try direct command match
        for cmd, action in self._command_map.items():
            if cmd in command_text:
                return action

        # Try handler registry
        handler = self._handlers.get(command_text)
        if handler:
            result = handler()
            return str(result) if result else f"Executed: {command_text}"

        return None

    def is_command(self, text: str) -> bool:
        """Check if text contains a trigger phrase."""
        if not self.config.enabled:
            return False
        if self.config.trigger_phrase:
            return self.config.trigger_phrase.lower() in text.lower()
        return any(cmd.lower() in text.lower() for cmd in self._command_map)

    def _extract_command_text(self, text: str) -> Optional[str]:
        """Extract command text after trigger phrase."""
        if not self.config.trigger_phrase:
            return text
        pattern = rf"{re.escape(self.config.trigger_phrase)}\s*(.+)"
        match = re.match(pattern, text)
        return match.group(1).strip() if match else None

    def build_initial_prompt(self) -> str:
        """Build Whisper initial_prompt from vocabulary for better term recognition."""
        if not self.config.vocabulary:
            return ""
        return ", ".join(self.config.vocabulary) + "."

    def list_commands(self) -> List[str]:
        """List all registered commands."""
        return list(self._command_map.keys())
