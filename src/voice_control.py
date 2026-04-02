"""Voice Control — Voice command system"""

import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class VoiceControl:
    def __init__(self):
        self._commands: Dict[str, Callable] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, command: str, handler: Callable, aliases: List[str] = None):
        self._commands[command] = handler
        if aliases:
            for alias in aliases:
                self._aliases[alias] = command

    def process(self, text: str) -> Optional[str]:
        text_lower = text.lower().strip()
        command = self._aliases.get(text_lower, text_lower)
        handler = self._commands.get(command)
        if handler:
            try:
                result = handler()
                return str(result) if result else f"Executed: {command}"
            except Exception as e:
                return f"Error: {e}"
        return None

    def list_commands(self) -> List[str]:
        return list(self._commands.keys())
