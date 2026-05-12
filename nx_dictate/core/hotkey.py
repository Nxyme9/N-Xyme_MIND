# N-Xyme Dictate - Global Hotkey Manager (Wayland-native)
# Uses evdev for mouse buttons, wtype/ydotool for keyboard simulation

from __future__ import annotations

import logging
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("nxyme_dictate.dictate.hotkey")

EVDEV_AVAILABLE = True
try:
    import evdev
except ImportError:
    EVDEV_AVAILABLE = False

WTYPE_AVAILABLE = True
try:
    subprocess.run(["wtype", "--help"], capture_output=True, timeout=3)
except Exception:
    WTYPE_AVAILABLE = False

YDOTOOL_AVAILABLE = True
try:
    subprocess.run(["ydotool", "--help"], capture_output=True, timeout=3)
except Exception:
    YDOTOOL_AVAILABLE = False

DEBOUNCE_MS = 150


@dataclass
class HotkeyConfig:
    record_button: str = "side"
    send_button: str = "extra"
    language_button: str = "middle"
    mode: str = "push-to-talk"


@dataclass
class HotkeyMode:
    PUSH_TO_TALK = "push-to-talk"
    TOGGLE = "toggle"
    HOLD = "hold"


class GlobalHotkey:
    def __init__(self, config: Optional[HotkeyConfig] = None):
        self._config = config or HotkeyConfig()
        self._mouse_thread = None
        self._is_active = False
        self._on_press = None
        self._on_release = None
        self._on_send_enter = None
        self._on_next_language = None
        self._pressed = False
        self._last_press_time = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._mouse_device = None

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def mode(self) -> str:
        paste_tools = []
        if WTYPE_AVAILABLE:
            paste_tools.append("wtype")
        if YDOTOOL_AVAILABLE:
            paste_tools.append("ydotool")
        tools = "/".join(paste_tools) if paste_tools else "none"
        return f"Mouse-EvDev(record={self._config.record_button}, send={self._config.send_button}, enter={tools})"

    def set_callbacks(
        self, on_press=None, on_release=None, on_send_enter=None, on_next_language=None
    ):
        self._on_press = on_press
        self._on_release = on_release
        self._on_send_enter = on_send_enter
        self._on_next_language = on_next_language

    def start(self) -> bool:
        if self._is_active:
            return True

        if EVDEV_AVAILABLE:
            if self._start_evdev_listener():
                return True
            logger.warning("EvDev mouse listener failed, hotkey not active")
            return False

        logger.warning("No hotkey backend available (evdev not installed?)")
        return False

    def _find_mouse_device(self):
        record_code = self._get_button_code(self._config.record_button)

        preferred_paths = ["/dev/input/event3", "/dev/input/event9"]
        for path in preferred_paths:
            try:
                device = evdev.InputDevice(path)
                caps = device.capabilities()
                if 0x01 in caps and record_code in caps[0x01]:
                    logger.info(f"Using mouse: {device.name} ({path})")
                    return device
                device.close()
            except Exception:
                pass

        for path in evdev.list_devices():
            try:
                device = evdev.InputDevice(path)
                caps = device.capabilities()
                if 0x01 in caps and record_code in caps[0x01]:
                    logger.info(f"Using mouse: {device.name} ({path})")
                    return device
                device.close()
            except Exception:
                pass

        return None

    def _get_button_code(self, button: str):
        return {
            "side": evdev.ecodes.BTN_SIDE,
            "extra": evdev.ecodes.BTN_EXTRA,
            "middle": evdev.ecodes.BTN_MIDDLE,
        }.get(button, evdev.ecodes.BTN_SIDE)

    def _start_evdev_listener(self) -> bool:
        device = self._find_mouse_device()
        if not device:
            logger.warning("No mouse with back/forward buttons found")
            return False

        self._mouse_device = device
        with self._lock:
            self._running = True
        self._mouse_thread = threading.Thread(target=self._evdev_loop, daemon=True)
        self._mouse_thread.start()
        self._is_active = True
        logger.info(f"EvDev listener active: {device.name}")
        return True

    def _evdev_loop(self):
        device = self._mouse_device
        record_code = self._get_button_code(self._config.record_button)
        send_code = self._get_button_code(self._config.send_button)
        lang_code = self._get_button_code(self._config.language_button)

        try:
            for event in device.read_loop():
                with self._lock:
                    if not self._running:
                        break
                if event.type != evdev.ecodes.EV_KEY:
                    continue
                if event.value == 1:
                    if event.code == record_code:
                        self._handle_press()
                    elif event.code == send_code:
                        self._handle_send_enter()
                    elif event.code == lang_code:
                        self._handle_language_switch()
                elif event.value == 0 and event.code == record_code:
                    self._handle_release()

        except OSError as e:
            if e.errno == 5:
                logger.warning("Mouse disconnected")
            else:
                logger.error(f"EvDev error: {e}")
        finally:
            with self._lock:
                self._is_active = False
                self._running = False
            if self._mouse_device:
                try:
                    self._mouse_device.close()
                except Exception:
                    pass
                self._mouse_device = None

    def _handle_press(self):
        now = time.time()
        with self._lock:
            if self._config.mode == HotkeyMode.TOGGLE:
                if self._pressed:
                    return
                self._pressed = not self._pressed
                is_toggle_on = self._pressed
            else:
                if self._pressed:
                    return
                if now - self._last_press_time < DEBOUNCE_MS / 1000.0:
                    return
                self._last_press_time = now
                self._pressed = True
                is_toggle_on = True

        logger.info(f"Hotkey press (mode={self._config.mode}, on={is_toggle_on})")
        if self._on_press and (self._config.mode != HotkeyMode.TOGGLE or is_toggle_on):
            try:
                self._on_press()
            except Exception as e:
                logger.error(f"Press callback error: {e}")

    def _handle_release(self):
        with self._lock:
            if self._config.mode == HotkeyMode.TOGGLE:
                return
            if not self._pressed:
                return
            self._pressed = False

        logger.info("Hotkey release")
        if self._on_release and self._config.mode != HotkeyMode.TOGGLE:
            try:
                self._on_release()
            except Exception as e:
                logger.error(f"Release callback error: {e}")

    def _handle_send_enter(self):
        logger.info("Send enter pressed")
        if self._on_send_enter:
            try:
                self._on_send_enter()
            except Exception as e:
                logger.error(f"Send enter callback error: {e}")
            return

        self._send_enter()

    def _send_enter(self):
        if WTYPE_AVAILABLE:
            try:
                proc = subprocess.Popen(
                    ["wtype", "-k", "Return"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                outs, errs = proc.communicate(timeout=1)
                if proc.returncode == 0:
                    logger.info("Enter sent via wtype")
                    return
                logger.warning(f"wtype failed: {errs.decode().strip()}")
            except Exception as e:
                logger.warning(f"wtype error: {e}")

        if YDOTOOL_AVAILABLE:
            try:
                proc = subprocess.Popen(
                    ["ydotool", "key", "Return"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                outs, errs = proc.communicate(timeout=1)
                if proc.returncode == 0:
                    logger.info("Enter sent via ydotool")
                    return
                logger.warning(f"ydotool failed: {errs.decode().strip()}")
            except Exception as e:
                logger.warning(f"ydotool error: {e}")

        logger.warning("No Enter-send method available")

    def _handle_language_switch(self):
        logger.info("Language switch pressed")
        if self._on_next_language:
            try:
                self._on_next_language()
            except Exception as e:
                logger.error(f"Language switch callback error: {e}")

    def stop(self):
        with self._lock:
            self._running = False
        
        # Close device BEFORE joining thread to avoid Bad file descriptor
        device = self._mouse_device
        self._mouse_device = None
        
        if device:
            try:
                device.close()
            except (OSError, Exception) as e:
                logger.debug(f"Device close error (expected): {e}")
        
        if self._mouse_thread:
            self._mouse_thread.join(timeout=5)
            self._mouse_thread = None
        
        self._is_active = False
        logger.info("Hotkey stopped")


def create_default_hotkey(on_press=None, on_release=None, on_next_language=None) -> GlobalHotkey:
    config = HotkeyConfig(record_button="side", send_button="extra", language_button="middle")
    hotkey = GlobalHotkey(config)
    hotkey.set_callbacks(
        on_press=on_press, on_release=on_release, on_next_language=on_next_language
    )
    hotkey.start()
    return hotkey
