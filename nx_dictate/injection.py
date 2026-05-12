from __future__ import annotations

import logging
import os
import subprocess
import time
import threading
from pathlib import Path

logger = logging.getLogger("nxyme_dictate.text_injection")

UINPUT_AVAILABLE = True
try:
    from evdev import UInput
    import fcntl
    import array
    UINPUT_AVAILABLE = True
except Exception:
    UINPUT_AVAILABLE = False
    logger.debug("UInput not available (requires evdev + input group)")

_uinput_keyboard = None
_uinput_initialized = False

def _get_uinput_keyboard():
    global _uinput_keyboard, _uinput_initialized
    if _uinput_initialized:
        return _uinput_keyboard
    
    if not UINPUT_AVAILABLE:
        return None
    
    try:
        from .uinput_keyboard import create_uinput_keyboard
        _uinput_keyboard = create_uinput_keyboard()
        _uinput_initialized = True
        if _uinput_keyboard and _uinput_keyboard.is_available:
            logger.info("UInput keyboard initialized successfully")
        return _uinput_keyboard
    except Exception as e:
        logger.warning(f"Failed to create UInput keyboard: {e}")
        _uinput_initialized = True
        return None

# Check for evdev injection (most reliable on Wayland via ydotoold)
try:
    from .evdev_injection import inject_with_evdev
    EVDEV_INJECTION_AVAILABLE = True
except Exception:
    EVDEV_INJECTION_AVAILABLE = False
    logger.debug("evdev injection not available")

logger = logging.getLogger("nxyme_dictate.text_injection")

# pynput for direct keyboard injection (works in Wayland without compositor support)
PYNPUT_AVAILABLE = True
try:
    from pynput import keyboard
except Exception as e:
    PYNPUT_AVAILABLE = False
    logger.warning(f"pynput not available: {e}")

WL_CLIPBOARD_AVAILABLE = True
try:
    subprocess.run(["wl-copy", "--version"], capture_output=True, check=True, timeout=5)
except (subprocess.SubprocessError, FileNotFoundError):
    WL_CLIPBOARD_AVAILABLE = False

WTYPE_AVAILABLE = True
try:
    subprocess.run(["wtype", "--version"], capture_output=True, timeout=5)
except (subprocess.SubprocessError, FileNotFoundError):
    WTYPE_AVAILABLE = False

YDOTOOL_AVAILABLE = True
try:
    subprocess.run(["ydotool", "--version"], capture_output=True, timeout=5)
except (subprocess.SubprocessError, FileNotFoundError):
    YDOTOOL_AVAILABLE = False

# Auto-start ydotoold if ydotool is available but daemon not running
_ydotoold_started = False
def _ensure_ydotoold() -> bool:
    global _ydotoold_started
    if _ydotoold_started:
        return True
    try:
        result = subprocess.run(["ydotool", "info"], capture_output=True, timeout=1)
        if result.returncode == 0:
            _ydotoold_started = True
            logger.info("ydotoold already running")
            return True
    except:
        pass
    
    logger.info("Attempting to start ydotoold...")
    try:
        proc = subprocess.Popen(
            ["ydotoold"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(10):
            time.sleep(0.3)
            try:
                result = subprocess.run(["ydotool", "info"], capture_output=True, timeout=1)
                if result.returncode == 0:
                    _ydotoold_started = True
                    logger.info("Successfully started ydotoold")
                    return True
            except:
                continue
        proc.kill()
    except Exception as e:
        logger.debug(f"Failed to start ydotoold: {e}")
    
    logger.warning("Could not start ydotoold - your compositor may not support virtual keyboard")
    return False

DOTOOL_AVAILABLE = True
try:
    subprocess.run(["dotool", "--help"], capture_output=True, timeout=5)
except (subprocess.SubprocessError, FileNotFoundError):
    DOTOOL_AVAILABLE = False

# XDOTOOL_AVAILABLE - X11 tool (works in XWayland with DISPLAY=:0)
XDOTOOL_AVAILABLE = True
try:
    subprocess.run(["xdotool", "--version"], capture_output=True, timeout=5)
except (subprocess.SubprocessError, FileNotFoundError):
    XDOTOOL_AVAILABLE = False


def _get_safe_env() -> dict:
    env = {}
    if path := os.environ.get("PATH"):
        env["PATH"] = path
    if wd := os.environ.get("WAYLAND_DISPLAY"):
        env["WAYLAND_DISPLAY"] = wd
    if xdg := os.environ.get("XDG_RUNTIME_DIR"):
        env["XDG_RUNTIME_DIR"] = xdg
    # CRITICAL: ydotoold socket location for text injection
    if yd := os.environ.get("YDOTOOL_SOCKET"):
        env["YDOTOOL_SOCKET"] = yd
    elif xdg:
        # Auto-detect socket in XDG_RUNTIME_DIR
        socket_path = Path(xdg) / ".ydotool_socket"
        if socket_path.exists():
            env["YDOTOOL_SOCKET"] = str(socket_path)
    env["LANG"] = os.environ.get("LANG", "en_US.UTF-8")
    return env


def _wl_copy(text: str, timeout: float = 1.5, retries: int = 3) -> bool:
    if not text:
        return False
    safe_env = _get_safe_env()
    for attempt in range(retries):
        try:
            proc = subprocess.Popen(
                ["wl-copy"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=safe_env,
            )
            proc.communicate(input=text.encode("utf-8"), timeout=timeout)
            proc.wait()
            if proc.returncode == 0:
                return True
            logger.warning(f"wl-copy attempt {attempt + 1} returned {proc.returncode}")
        except OSError as e:
            logger.warning(f"wl-copy attempt {attempt + 1} error: {e}")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            logger.warning(f"wl-copy attempt {attempt + 1} timed out")
        if attempt < retries - 1:
            time.sleep(0.1 * (2**attempt))
    return False


def _uinput_type(text: str) -> bool:
    if not text:
        return False
    keyboard = _get_uinput_keyboard()
    if keyboard and keyboard.is_available:
        try:
            return keyboard.type_text(text)
        except Exception as e:
            logger.warning(f"UInput type failed: {e}")
    return False


def _wtype_type(text: str) -> bool:
    if not WTYPE_AVAILABLE or not text:
        return False
    safe_env = _get_safe_env()
    try:
        proc = subprocess.Popen(
            ["wtype", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=safe_env,
        )
        proc.wait(timeout=3)
        return proc.returncode == 0
    except Exception as e:
        logger.debug(f"wtype type failed: {e}")
        return False


def _wtype_paste() -> bool:
    if not WTYPE_AVAILABLE:
        return False
    safe_env = _get_safe_env()
    try:
        proc = subprocess.Popen(
            ["wtype", "-k", "V"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=safe_env,
        )
        outs, errs = proc.communicate(timeout=1.5)
        if proc.returncode == 0:
            return True
        logger.warning(f"wtype paste failed: {errs.decode().strip()}")
    except Exception as e:
        logger.debug(f"wtype paste error: {e}")
    return False


def _ydotool_type(text: str) -> bool:
    if not YDOTOOL_AVAILABLE or not text:
        return False
    if not _ensure_ydotoold():
        return False
    try:
        proc = subprocess.Popen(
            ["ydotool", "type", "--file", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=_get_safe_env(),
        )
        proc.communicate(input=text.encode("utf-8"), timeout=3)
        proc.wait(timeout=1)
        if proc.returncode == 0:
            logger.info(f"Direct type via ydotool: {len(text)} chars")
            return True
    except Exception as e:
        logger.debug(f"ydotool type error: {e}")
    return False


def _dotool_type(text: str) -> bool:
    if not DOTOOL_AVAILABLE or not text:
        return False
    try:
        proc = subprocess.Popen(
            ["dotool"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=text.encode("utf-8"), timeout=3)
        return proc.returncode == 0
    except Exception as e:
        logger.debug(f"dotool failed: {e}")
        return False


def _ydotool_paste() -> bool:
    """Paste using ydotool Ctrl+V key combo."""
    if not YDOTOOL_AVAILABLE:
        return False
    try:
        proc = subprocess.Popen(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=1.5)
        return proc.returncode == 0
    except Exception as e:
        logger.debug(f"ydotool paste error: {e}")
        return False


def _xdotool_paste() -> bool:
    if not os.environ.get("DISPLAY"):
        return False
    try:
        proc = subprocess.Popen(
            ["xdotool", "key", "ctrl+v"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=1.5)
        return proc.returncode == 0
    except Exception as e:
        logger.debug(f"xdotool paste error: {e}")
        return False


def _xdotool_type(text: str) -> bool:
    """Type text using xdotool (works in XWayland with DISPLAY=:0)."""
    if not XDOTOOL_AVAILABLE or not text or not os.environ.get("DISPLAY"):
        return False
    try:
        proc = subprocess.Popen(
            ["xdotool", "type", "--", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=3)
        if proc.returncode == 0:
            logger.info(f"xdotool typed: {len(text)}")
            return True
    except Exception as e:
        logger.debug(f"xdotool type error: {e}")
    return False


_pynput_kb = None
_pynput_lock = threading.Lock()


def _pynput_type(text: str) -> bool:
    global _pynput_kb
    if not PYNPUT_AVAILABLE or not text:
        return False

    # pynput fundamentally doesn't work well on Wayland - it may report success but nothing happens
    # Only use as last resort
    if os.environ.get("WAYLAND_DISPLAY"):
        logger.debug("pynput: skipping on Wayland (unreliable)")
        return False

    try:
        if _pynput_kb is None:
            _pynput_kb = keyboard.Controller()
            logger.info(f"pynput keyboard created")

        # Test with a single character first
        try:
            test_char = text[0] if text else 'x'
            _pynput_kb.press(test_char)
            _pynput_kb.release(test_char)
            logger.info(f"pynput test char sent")
        except Exception as test_e:
            logger.warning(f"pynput test char failed: {test_e}")
            return False

        with _pynput_lock:
            _pynput_kb.type(text)
        logger.info(f"Text typed via pynput: {len(text)} chars")
        return True
    except Exception as e:
        logger.warning(f"pynput type error: {e}")
        import traceback
        logger.warning(f"pynput traceback: {traceback.format_exc()}")
        return False


def type_text_direct(text: str) -> bool:
    if not text:
        logger.debug("type_text_direct: empty text, skipping")
        return False
    
    logger.info(f"type_text_direct: attempting to type {len(text)} chars")
    
    # Try xdotool FIRST on XWayland (DISPLAY=:0 means X11 compatibility)
    if XDOTOOL_AVAILABLE:
        logger.info("type_text_direct: trying xdotool (XWayland)...")
        if _xdotool_type(text):
            logger.info(f"Text typed via xdotool: {len(text)} chars")
            return True
        logger.warning("xdotool failed")
    
    # Try evdev first (works via ydotoold virtual device)
    if EVDEV_INJECTION_AVAILABLE:
        logger.info("type_text_direct: trying evdev (via ydotoold)...")
        if inject_with_evdev(text):
            logger.info(f"Text typed via evdev: {len(text)} chars")
            return True
        logger.warning("evdev failed")
    
    if YDOTOOL_AVAILABLE:
        logger.info("type_text_direct: trying ydotool...")
        if _ydotool_type(text):
            logger.info(f"Text typed via ydotool: {len(text)} chars")
            return True
        logger.warning("ydotool failed")

    if PYNPUT_AVAILABLE:
        logger.info("type_text_direct: trying pynput...")
        if _pynput_type(text):
            return True
        logger.warning("pynput failed")

    if DOTOOL_AVAILABLE:
        logger.debug("type_text_direct: trying dotool (KDE Wayland)...")
        if _dotool_type(text):
            logger.info(f"Text typed via dotool: {len(text)} chars")
            return True
        logger.debug("dotool failed")

    if WTYPE_AVAILABLE:
        logger.debug("type_text_direct: trying wtype (Wayland)...")
        if _wtype_type(text):
            logger.info(f"Text typed via wtype: {len(text)} chars")
            return True
        logger.debug("wtype failed")
    
    if YDOTOOL_AVAILABLE:
        logger.debug("type_text_direct: trying ydotool...")
        if _ydotool_type(text):
            logger.info(f"Text typed via ydotool: {len(text)} chars")
            return True
        logger.debug("ydotool failed")
    
    logger.warning(f"type_text_direct: ALL methods failed for {len(text)} chars")
    return False


def copy_and_paste(text: str) -> bool:
    if not text:
        logger.debug("copy_and_paste: empty text, skipping")
        return False
    
    logger.info(f"copy_and_paste: processing {len(text)} chars")
    
    is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    
    # PRIMARY on Wayland: UInput keyboard (works without compositor protocol!)
    if is_wayland and UINPUT_AVAILABLE:
        logger.info("copy_and_paste: trying UInput keyboard (Wayland native)...")
        if _uinput_type(text):
            logger.info(f"Text typed via UInput ({len(text)} chars)")
            return True
        logger.warning("UInput keyboard failed")
    
    # Wayland: try wtype as backup
    if is_wayland and WTYPE_AVAILABLE:
        logger.info("copy_and_paste: trying wtype (Wayland)...")
        if _wtype_type(text):
            logger.info(f"Text typed via wtype ({len(text)} chars)")
            return True
        logger.warning("wtype failed")
    
    # PRIMARY: Try ydotool (works in Wayland with daemon)
    if YDOTOOL_AVAILABLE:
        logger.info("copy_and_paste: trying ydotool...")
        if _ydotool_type(text):
            logger.info(f"Text typed via ydotool ({len(text)} chars)")
            return True
        logger.warning("ydotool failed")
    
    # Try pynput only on non-Wayland
    if PYNPUT_AVAILABLE and not is_wayland:
        logger.info("copy_and_paste: trying pynput...")
        if _pynput_type(text):
            logger.info(f"Text typed via pynput ({len(text)} chars)")
            return True
        logger.warning("pynput failed")
    
    # Clipboard fallback
    if not WL_CLIPBOARD_AVAILABLE:
        logger.warning("wl-copy not available - clipboard copy will fail")
    else:
        logger.debug("copy_and_paste: copying to clipboard via wl-copy...")
        if not _wl_copy(text):
            logger.error("Failed to copy text to clipboard")
            return False
        logger.info(f"Text copied to clipboard ({len(text)} chars)")
        logger.info("PASTING IN 1 SECOND - FOCUS YOUR TEXT FIELD NOW!")
        time.sleep(1.0)
    
    # Try paste with longer timeout for focus switching
    if YDOTOOL_AVAILABLE:
        logger.debug("copy_and_paste: trying ydotool paste with delay...")
        time.sleep(0.15)
        if _ydotool_paste():
            logger.info("Text pasted via ydotool Ctrl+V")
            return True
        logger.debug("ydotool paste failed")
    
    if WTYPE_AVAILABLE:
        logger.debug("copy_and_paste: trying wtype paste...")
        if _wtype_paste():
            logger.info("Text pasted via wtype")
            return True
        logger.debug("wtype paste failed")

    if _xdotool_paste():
        logger.info("Text pasted via xdotool")
        return True
    
    logger.warning("Paste failed - text on clipboard, paste manually")
    return True


def get_backend() -> str:
    methods = []
    if PYNPUT_AVAILABLE:
        methods.append("pynput")
    if WTYPE_AVAILABLE:
        methods.append("wtype")
    if YDOTOOL_AVAILABLE:
        methods.append("ydotool")
    if DOTOOL_AVAILABLE:
        methods.append("dotool")
    if os.environ.get("DISPLAY"):
        methods.append("xdotool")

    if WL_CLIPBOARD_AVAILABLE and methods:
        return f"wl-clipboard + {'/'.join(methods)}"
    elif methods:
        return f"pynput-primary + {'/'.join(methods)}"
    return "none"


def send_key_combo(keys: list[str]) -> bool:
    if not YDOTOOL_AVAILABLE:
        return False
    try:
        proc = subprocess.Popen(
            ["ydotool", "key"] + keys,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.wait(timeout=1.0)
        return proc.returncode == 0
    except Exception as e:
        logger.debug(f"ydotool key combo error: {e}")
        return False


def execute_special_action(action: str) -> bool:
    if action == "delete_backspace":
        return send_key_combo(["14:1", "14:0"])
    elif action == "newline_twice":
        success = send_key_combo(["28:1", "28:0"])
        if success:
            time.sleep(0.05)
            success = send_key_combo(["28:1", "28:0"])
        return success
    return False
