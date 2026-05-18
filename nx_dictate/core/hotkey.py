"""Global hotkey — supports toggle (F8) and hold-to-talk (RIGHT CTRL)."""

import threading
from typing import Callable, Optional

from pynput import keyboard

from nx_dictate.config import HotkeyConfig

# Virtual key codes for "right ctrl"
VK_RCONTROL = 0xA3


class GlobalHotkey:
    """Global hotkey listener — toggle OR hold-to-talk mode."""

    def __init__(self, config: HotkeyConfig, on_toggle: Callable, on_hold_start: Optional[Callable] = None, on_hold_end: Optional[Callable] = None):
        self.config = config
        self.on_toggle = on_toggle
        self.on_hold_start = on_hold_start
        self.on_hold_end = on_hold_end
        self._listener: Optional[keyboard.Listener] = None
        self._running = False
        self._pressed_keys = set()
        self._hold_key_pressed = False

    @property
    def is_hold_mode(self) -> bool:
        return self.config.hold_key is not None

    @property
    def _toggle_key_code(self):
        """Map toggle key name to key object."""
        key = self.config.toggle_key.lower()
        _TOGGLE_MAP = {
            "f5": keyboard.KeyCode.from_vk(0x74),
            "f6": keyboard.KeyCode.from_vk(0x75),
            "f7": keyboard.KeyCode.from_vk(0x76),
            "f8": keyboard.KeyCode.from_vk(0x77),
            "f9": keyboard.KeyCode.from_vk(0x78),
            "f10": keyboard.KeyCode.from_vk(0x79),
            "f11": keyboard.KeyCode.from_vk(0x7A),
            "f12": keyboard.KeyCode.from_vk(0x7B),
            "ctrl+alt+d": {keyboard.Key.ctrl, keyboard.Key.alt, keyboard.KeyCode.from_char('d')},
        }
        return _TOGGLE_MAP.get(key, keyboard.KeyCode.from_vk(0x77))

    @property
    def _hold_key_code(self):
        """Get hold key object."""
        key = self.config.hold_key.lower() if self.config.hold_key else ""
        _HOLD_MAP = {
            "right ctrl": keyboard.KeyCode.from_vk(VK_RCONTROL),
            "right alt": keyboard.KeyCode.from_vk(0xB8),
            "left ctrl": keyboard.Key.ctrl,
            "left alt": keyboard.Key.alt,
            "right shift": keyboard.KeyCode.from_vk(0xB6),
            "caps lock": keyboard.Key.caps_lock,
        }
        return _HOLD_MAP.get(key, keyboard.KeyCode.from_vk(VK_RCONTROL))

    def start(self) -> None:
        """Start listening for hotkey."""
        self._running = True
        toggle_target = self._toggle_key_code
        hold_target = self._hold_key_code if self.is_hold_mode else None

        def on_press(k):
            self._pressed_keys.add(k)

            # Toggle mode
            if not self.is_hold_mode:
                if isinstance(toggle_target, set):
                    if toggle_target.issubset(self._pressed_keys):
                        self.on_toggle()
                elif k == toggle_target:
                    self.on_toggle()

            # Hold-to-talk mode
            if self.is_hold_mode and hold_target is not None:
                if k == hold_target and not self._hold_key_pressed:
                    self._hold_key_pressed = True
                    if self.on_hold_start:
                        self.on_hold_start()

        def on_release(k):
            self._pressed_keys.discard(k)

            # Hold-to-talk release
            if self.is_hold_mode and hold_target is not None:
                if k == hold_target and self._hold_key_pressed:
                    self._hold_key_pressed = False
                    if self.on_hold_end:
                        self.on_hold_end()

            if k == keyboard.Key.esc and not self.is_hold_mode:
                return False

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    @property
    def is_running(self) -> bool:
        return self._running and self._listener is not None


class EvdevHotkey:
    """Alternative hotkey using evdev (for Wayland fallback)."""

    def __init__(self, config: HotkeyConfig, on_toggle: Callable, on_hold_start: Optional[Callable] = None, on_hold_end: Optional[Callable] = None):
        self.config = config
        self.on_toggle = on_toggle
        self.on_hold_start = on_hold_start
        self.on_hold_end = on_hold_end
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._hold_key_pressed = False

    @property
    def is_hold_mode(self) -> bool:
        return self.config.hold_key is not None

    def start(self) -> None:
        """Start evdev hotkey listener."""
        try:
            import evdev
            from evdev import ecodes
        except ImportError:
            raise RuntimeError("evdev not installed. Install with: pip install evdev")

        self._running = True

        def listen():
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            keyboard_dev = None
            game_keyboard = None
            for dev in devices:
                if ecodes.EV_KEY in dev.capabilities():
                    name = dev.name.lower()
                    # Skip mouse-integrated keypads — they don't have right Ctrl
                    if "mouse" in name:
                        game_keyboard = dev
                        continue
                    if "keyboard" in name:
                        keyboard_dev = dev
                        break
            
            # Prefer real keyboard; fallback to first device with keys
            if keyboard_dev is None:
                keyboard_dev = game_keyboard or devices[-1] if devices else None

            if keyboard_dev is None:
                return

            _TOGGLE_MAP = {
                "f5": ecodes.KEY_F5, "f6": ecodes.KEY_F6, "f7": ecodes.KEY_F7,
                "f8": ecodes.KEY_F8, "f9": ecodes.KEY_F9, "f10": ecodes.KEY_F10,
                "f11": ecodes.KEY_F11, "f12": ecodes.KEY_F12,
            }
            _HOLD_MAP = {
                "right ctrl": ecodes.KEY_RIGHTCTRL,
                "right alt": ecodes.KEY_RIGHTALT,
                "left ctrl": ecodes.KEY_LEFTCTRL,
                "left alt": ecodes.KEY_LEFTALT,
                "right shift": ecodes.KEY_RIGHTSHIFT,
                "caps lock": ecodes.KEY_CAPSLOCK,
            }

            toggle_code = _TOGGLE_MAP.get(self.config.toggle_key.lower(), ecodes.KEY_F8)
            hold_code = _HOLD_MAP.get(self.config.hold_key.lower(), None) if self.is_hold_mode else None

            for event in keyboard_dev.read_loop():
                if not self._running:
                    break
                if event.type != ecodes.EV_KEY:
                    continue

                if event.value == 1:  # Pressed
                    if not self.is_hold_mode and event.code == toggle_code:
                        self.on_toggle()
                    if self.is_hold_mode and hold_code is not None:
                        if event.code == hold_code and not self._hold_key_pressed:
                            self._hold_key_pressed = True
                            if self.on_hold_start:
                                self.on_hold_start()

                elif event.value == 0:  # Released
                    if self.is_hold_mode and hold_code is not None:
                        if event.code == hold_code and self._hold_key_pressed:
                            self._hold_key_pressed = False
                            if self.on_hold_end:
                                self.on_hold_end()

        self._thread = threading.Thread(target=listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop evdev listener."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
