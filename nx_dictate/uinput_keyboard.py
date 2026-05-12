#!/usr/bin/env python3
"""UInput virtual keyboard for text injection on Wayland."""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger("nxyme_dictate.uinput_keyboard")

EVIOCSREP = (2 << 30) | (8 << 16) | (ord("E") << 8) | 0x03

try:
    import evdev
    from evdev import UInput, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    UInput = None
    ecodes = None
    logger.warning("evdev not available, UInput keyboard will not work")

_CHAR_TO_KEY = {}
_KEYBOARD_KEYS = []

if EVDEV_AVAILABLE:
    for _code, _key in [
        (ecodes.KEY_1, ("1", "!")),
        (ecodes.KEY_2, ("2", "@")),
        (ecodes.KEY_3, ("3", "#")),
        (ecodes.KEY_4, ("4", "$")),
        (ecodes.KEY_5, ("5", "%")),
        (ecodes.KEY_6, ("6", "^")),
        (ecodes.KEY_7, ("7", "&")),
        (ecodes.KEY_8, ("8", "*")),
        (ecodes.KEY_9, ("9", "(")),
        (ecodes.KEY_0, ("0", ")")),
        (ecodes.KEY_MINUS, ("-", "_")),
        (ecodes.KEY_EQUAL, ("=", "+")),
        (ecodes.KEY_LEFTBRACE, ("[", "{")),
        (ecodes.KEY_RIGHTBRACE, ("]", "}")),
        (ecodes.KEY_BACKSLASH, ("\\", "|")),
        (ecodes.KEY_SEMICOLON, (";", ":")),
        (ecodes.KEY_APOSTROPHE, ("'", '"')),
        (ecodes.KEY_COMMA, (",", "<")),
        (ecodes.KEY_DOT, (".", ">")),
        (ecodes.KEY_SLASH, ("/", "?")),
        (ecodes.KEY_GRAVE, ("`", "~")),
    ]:
        _CHAR_TO_KEY[_key[0]] = (_code, False)
        _CHAR_TO_KEY[_key[1]] = (_code, True)

    for _i, _c in enumerate("abcdefghijklmnopqrstuvwxyz"):
        _CHAR_TO_KEY[_c] = (getattr(ecodes, f"KEY_{_c.upper()}"), False)

    for _i, _c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
        _CHAR_TO_KEY[_c] = (getattr(ecodes, f"KEY_{_c}"), True)

    _CHAR_TO_KEY[" "] = (ecodes.KEY_SPACE, False)
    _CHAR_TO_KEY["\n"] = (ecodes.KEY_ENTER, False)
    _CHAR_TO_KEY["\t"] = (ecodes.KEY_TAB, False)

    _KEYBOARD_KEYS = [
        ecodes.KEY_ESC,
        *range(ecodes.KEY_1, ecodes.KEY_EQUAL + 1),
        ecodes.KEY_BACKSPACE, ecodes.KEY_TAB,
        *range(ecodes.KEY_Q, ecodes.KEY_RIGHTBRACE + 1),
        ecodes.KEY_ENTER, ecodes.KEY_LEFTCTRL,
        *range(ecodes.KEY_A, ecodes.KEY_GRAVE + 1),
        ecodes.KEY_LEFTSHIFT, ecodes.KEY_BACKSLASH,
        *range(ecodes.KEY_Z, ecodes.KEY_SLASH + 1),
        ecodes.KEY_RIGHTSHIFT, ecodes.KEY_KPASTERISK,
        ecodes.KEY_LEFTALT, ecodes.KEY_SPACE,
        ecodes.KEY_CAPSLOCK,
        *range(ecodes.KEY_F1, ecodes.KEY_F10 + 1),
        ecodes.KEY_NUMLOCK, ecodes.KEY_SCROLLLOCK,
        *range(ecodes.KEY_KP7, ecodes.KEY_KPDOT + 1),
        ecodes.KEY_F11, ecodes.KEY_F12,
        ecodes.KEY_RIGHTCTRL, ecodes.KEY_RIGHTALT,
        ecodes.KEY_HOME, ecodes.KEY_UP,
        ecodes.KEY_PAGEUP, ecodes.KEY_LEFT,
        ecodes.KEY_RIGHT, ecodes.KEY_END,
        ecodes.KEY_DOWN, ecodes.KEY_PAGEDOWN,
        ecodes.KEY_INSERT, ecodes.KEY_DELETE,
        ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA,
        ecodes.KEY_KPENTER,
        ecodes.KEY_V,
    ]


class UInputKeyboard:
    def __init__(self, name: str = "nxyme-dictate"):
        self._ui = None
        self._device_path = None
        self._initialize(name)

    def _initialize(self, name: str):
        if not EVDEV_AVAILABLE:
            logger.error("evdev not available")
            return

        try:
            import fcntl
            import array

            self._ui = UInput(
                {ecodes.EV_KEY: list(set(_KEYBOARD_KEYS))},
                name=name,
            )
            self._device_path = self._ui.device.path
            
            time.sleep(0.3)
            
            try:
                fd = os.open(self._device_path, os.O_RDWR)
                try:
                    fcntl.ioctl(fd, EVIOCSREP, array.array("i", [0, 0]))
                finally:
                    os.close(fd)
            except OSError as e:
                logger.warning("Could not disable key repeat: %s", e)
            
            logger.info("UInput keyboard created: %s", self._device_path)
        except Exception as e:
            logger.error("Failed to create UInput keyboard: %s", e)
            self._ui = None

    def type_text(self, text: str) -> bool:
        if not self._ui or not text:
            return False

        try:
            self._release_stuck_keys([
                ecodes.KEY_SPACE,
                ecodes.KEY_LEFTCTRL,
                ecodes.KEY_LEFTSHIFT,
                ecodes.KEY_LEFTMETA,
            ])
            time.sleep(0.02)

            for c in text:
                if c in _CHAR_TO_KEY:
                    keycode, need_shift = _CHAR_TO_KEY[c]
                elif c.isspace():
                    keycode, need_shift = ecodes.KEY_SPACE, False
                elif c == "\t":
                    keycode, need_shift = ecodes.KEY_TAB, False
                elif c == "\n":
                    keycode, need_shift = ecodes.KEY_ENTER, False
                else:
                    continue

                if keycode == ecodes.KEY_SPACE:
                    self._ui.write(ecodes.EV_KEY, ecodes.KEY_SPACE, 0)
                    self._ui.syn()
                    time.sleep(0.005)

                if need_shift:
                    self._ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
                
                self._ui.write(ecodes.EV_KEY, keycode, 1)
                self._ui.write(ecodes.EV_KEY, keycode, 0)
                
                if need_shift:
                    self._ui.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
                
                self._ui.syn()
                time.sleep(0.006)

            self._release_stuck_keys([
                ecodes.KEY_LEFTSHIFT,
                ecodes.KEY_LEFTCTRL,
                ecodes.KEY_SPACE,
            ])
            
            logger.info("Typed %d chars via UInput", len(text))
            return True

        except Exception as e:
            logger.error("UInput typing failed: %s", e)
            return False

    def _release_stuck_keys(self, keys: list):
        if not self._ui:
            return
        for key in keys:
            self._ui.write(ecodes.EV_KEY, key, 0)
        self._ui.syn()

    def close(self):
        if self._ui:
            self._ui.close()
            self._ui = None

    @property
    def is_available(self) -> bool:
        return self._ui is not None


def create_uinput_keyboard() -> Optional[UInputKeyboard]:
    if not EVDEV_AVAILABLE:
        logger.warning("Cannot create UInput keyboard: evdev not available")
        return None
    try:
        return UInputKeyboard()
    except Exception as e:
        logger.error("Failed to create UInput keyboard: %s", e)
        return None