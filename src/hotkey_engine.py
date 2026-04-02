"""
Hotkey Engine — Global hotkeys even when unfocused (ported from LIVE)

Registers system-wide keyboard shortcuts.

Usage:
    engine = HotkeyEngine()
    engine.register("ctrl+shift+r", lambda: print("Pressed!"))
    engine.start()
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Check if pynput available
PYNPUT_AVAILABLE = False
try:
    from pynput import keyboard

    PYNPUT_AVAILABLE = True
except ImportError:
    logger.warning("pynput not installed. Run: pip install pynput")


@dataclass
class HotkeyBinding:
    """A hotkey binding."""

    key_combo: str
    callback: Callable
    description: str = ""
    enabled: bool = True
    triggered_count: int = 0
    last_triggered: float = 0.0


class HotkeyEngine:
    """Global hotkey engine."""

    def __init__(self):
        self._bindings: Dict[str, HotkeyBinding] = {}
        self._listener: Optional[keyboard.Listener] = None
        self._pressed_keys: set = set()
        self._running = False
        logger.info(
            f"HotkeyEngine: Initialized (pynput={'available' if PYNPUT_AVAILABLE else 'missing'})"
        )

    def register(
        self,
        key_combo: str,
        callback: Callable,
        description: str = "",
    ) -> bool:
        """Register a hotkey."""
        if not PYNPUT_AVAILABLE:
            logger.error("HotkeyEngine: Cannot register - pynput not available")
            return False

        normalized = self._normalize_combo(key_combo)
        self._bindings[normalized] = HotkeyBinding(
            key_combo=normalized,
            callback=callback,
            description=description,
        )
        logger.info(f"HotkeyEngine: Registered '{key_combo}'")
        return True

    def unregister(self, key_combo: str) -> bool:
        """Unregister a hotkey."""
        normalized = self._normalize_combo(key_combo)
        if normalized in self._bindings:
            del self._bindings[normalized]
            logger.info(f"HotkeyEngine: Unregistered '{key_combo}'")
            return True
        return False

    def start(self) -> bool:
        """Start listening for hotkeys."""
        if not PYNPUT_AVAILABLE:
            logger.error("HotkeyEngine: Cannot start - pynput not available")
            return False

        if self._running:
            return True

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        self._running = True
        logger.info("HotkeyEngine: Started")
        return True

    def stop(self):
        """Stop listening."""
        if self._listener:
            self._listener.stop()
            self._running = False
            logger.info("HotkeyEngine: Stopped")

    def _on_press(self, key):
        """Handle key press."""
        try:
            key_str = self._key_to_string(key)
            self._pressed_keys.add(key_str)
            self._check_hotkeys()
        except Exception as e:
            logger.debug(f"HotkeyEngine: Press error: {e}")

    def _on_release(self, key):
        """Handle key release."""
        try:
            key_str = self._key_to_string(key)
            self._pressed_keys.discard(key_str)
        except Exception:
            pass

    def _check_hotkeys(self):
        """Check if current key combo matches any binding."""
        current = "+".join(sorted(self._pressed_keys))
        binding = self._bindings.get(current)
        if binding and binding.enabled:
            binding.triggered_count += 1
            binding.last_triggered = time.time()
            try:
                binding.callback()
            except Exception as e:
                logger.error(f"HotkeyEngine: Callback error: {e}")

    def _key_to_string(self, key) -> str:
        """Convert key to string."""
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        elif hasattr(key, "name"):
            name = key.name.lower()
            if name in ("ctrl_l", "ctrl_r"):
                return "ctrl"
            elif name in ("shift_l", "shift_r"):
                return "shift"
            elif name in ("alt_l", "alt_r"):
                return "alt"
            return name
        return str(key)

    def _normalize_combo(self, combo: str) -> str:
        """Normalize key combo string."""
        parts = [p.strip().lower() for p in combo.split("+")]
        return "+".join(sorted(parts))

    def get_bindings(self) -> List[Dict]:
        """Get all registered bindings."""
        return [
            {
                "key_combo": b.key_combo,
                "description": b.description,
                "enabled": b.enabled,
                "triggered_count": b.triggered_count,
            }
            for b in self._bindings.values()
        ]
