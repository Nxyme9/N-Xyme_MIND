"""
Macro Engine — Record and replay actions (ported from LIVE)

Records sequences of actions and replays them.

Usage:
    engine = MacroEngine()
    engine.start_recording("my_macro")
    engine.record("open_file", path="test.py")
    engine.record("run_tests")
    engine.stop_recording()
    engine.play("my_macro")
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MacroAction:
    """A recorded macro action."""

    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0  # Delay before this action


@dataclass
class Macro:
    """A recorded macro."""

    name: str
    actions: List[MacroAction] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    execution_count: int = 0


class MacroEngine:
    """Record and replay action sequences."""

    def __init__(self):
        self._macros: Dict[str, Macro] = {}
        self._recording: Optional[Macro] = None
        self._last_action_time: float = 0
        self._handlers: Dict[str, Callable] = {}
        logger.info("MacroEngine: Initialized")

    def register_handler(self, action_type: str, handler: Callable):
        """Register handler for action type."""
        self._handlers[action_type] = handler

    def start_recording(self, name: str) -> bool:
        """Start recording a macro."""
        if self._recording:
            logger.warning("MacroEngine: Already recording")
            return False

        self._recording = Macro(name=name)
        self._last_action_time = time.time()
        logger.info(f"MacroEngine: Recording '{name}'")
        return True

    def record(self, action_type: str, **params) -> bool:
        """Record an action."""
        if not self._recording:
            return False

        now = time.time()
        delay = now - self._last_action_time if self._last_action_time > 0 else 0

        action = MacroAction(
            action_type=action_type,
            params=params,
            delay=delay,
        )
        self._recording.actions.append(action)
        self._last_action_time = now
        return True

    def stop_recording(self) -> Optional[Macro]:
        """Stop recording and save macro."""
        if not self._recording:
            return None

        macro = self._recording
        self._macros[macro.name] = macro
        self._recording = None

        logger.info(f"MacroEngine: Saved '{macro.name}' ({len(macro.actions)} actions)")
        return macro

    def play(self, name: str, speed: float = 1.0) -> bool:
        """Play a recorded macro."""
        macro = self._macros.get(name)
        if not macro:
            logger.error(f"MacroEngine: Macro '{name}' not found")
            return False

        logger.info(f"MacroEngine: Playing '{name}'")
        macro.execution_count += 1

        for action in macro.actions:
            # Apply delay
            if action.delay > 0:
                time.sleep(action.delay / speed)

            # Execute action
            handler = self._handlers.get(action.action_type)
            if handler:
                try:
                    handler(**action.params)
                except Exception as e:
                    logger.error(f"MacroEngine: Action failed: {e}")
            else:
                logger.warning(f"MacroEngine: No handler for '{action.action_type}'")

        return True

    def list_macros(self) -> List[Dict]:
        """List all recorded macros."""
        return [
            {
                "name": m.name,
                "actions": len(m.actions),
                "created": m.created_at,
                "executions": m.execution_count,
            }
            for m in self._macros.values()
        ]

    def delete_macro(self, name: str) -> bool:
        """Delete a macro."""
        if name in self._macros:
            del self._macros[name]
            logger.info(f"MacroEngine: Deleted '{name}'")
            return True
        return False
