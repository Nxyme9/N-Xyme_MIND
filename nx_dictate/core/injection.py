"""Multi-backend text injection (xdotool, wtype, ydotool, clipboard)."""

import subprocess
import time
from typing import Optional

from nx_dictate.config import Backend, InjectionConfig


def inject_text(text: str, config: InjectionConfig) -> bool:
    """Inject text using configured backend."""
    if not text:
        return True

    backend = config.backend
    if backend == Backend.XDOTOOL:
        return _inject_xdotool(text, config)
    elif backend == Backend.WTYPE:
        return _inject_wtype(text, config)
    elif backend == Backend.YDOOTOOL:
        return _inject_ydotool(text, config)
    elif backend == Backend.CLIPBOARD:
        return _inject_clipboard(text, config)
    return False


def _inject_xdotool(text: str, config: InjectionConfig) -> bool:
    """Inject text using xdotool."""
    try:
        chunks = [text[i:i + config.chunk_size] for i in range(0, len(text), config.chunk_size)]
        for chunk in chunks:
            escaped = chunk.replace("\\", "\\\\").replace("'", "'\\''")
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", str(config.delay_ms), escaped],
                check=True,
                capture_output=True,
                timeout=5.0,
            )
            if config.delay_ms > 0:
                time.sleep(config.delay_ms / 1000.0)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _inject_wtype(text: str, config: InjectionConfig) -> bool:
    """Inject text using wtype (Wayland)."""
    try:
        subprocess.run(
            ["wtype", text],
            check=True,
            capture_output=True,
            timeout=5.0,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _inject_ydotool(text: str, config: InjectionConfig) -> bool:
    """Inject text using ydotool."""
    try:
        for char in text:
            subprocess.run(
                ["ydotool", "type", char],
                check=True,
                capture_output=True,
                timeout=5.0,
            )
            if config.delay_ms > 0:
                time.sleep(config.delay_ms / 1000.0)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _inject_clipboard(text: str, config: InjectionConfig) -> bool:
    """Inject text via clipboard (paste)."""
    try:
        subprocess.run(
            ["wl-copy", text],
            check=True,
            capture_output=True,
            timeout=5.0,
        )
        time.sleep(0.05)
        subprocess.run(
            ["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
            check=True,
            capture_output=True,
            timeout=5.0,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        try:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode(),
                check=True,
                capture_output=True,
                timeout=5.0,
            )
            time.sleep(0.05)
            subprocess.run(
                ["xdotool", "key", "ctrl+v"],
                check=True,
                capture_output=True,
                timeout=5.0,
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False


def inject_key_combo(combo: str) -> bool:
    """Inject key combination (e.g., 'ctrl+a', 'ctrl+shift+z')."""
    keys = combo.split("+")
    try:
        if _has_display_server("wayland"):
            modifiers = [k for k in keys if k.lower() in ("ctrl", "alt", "shift", "super")]
            main_key = [k for k in keys if k.lower() not in ("ctrl", "alt", "shift", "super")][0]

            press_args = []
            for m in modifiers:
                press_args.extend(["-M", m.lower()])
            press_args.append(main_key.lower())

            subprocess.run(["wtype"] + press_args, check=True, capture_output=True, timeout=5.0)
        else:
            xdotool_combo = "+".join(k.lower() for k in keys)
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", xdotool_combo],
                check=True,
                capture_output=True,
                timeout=5.0,
            )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def _has_display_server(server: str) -> bool:
    """Check if running under specified display server."""
    return server in subprocess.run(
        ["bash", "-c", "echo $XDG_SESSION_TYPE"],
        capture_output=True,
        text=True,
        timeout=5.0,
    ).stdout.strip().lower()
