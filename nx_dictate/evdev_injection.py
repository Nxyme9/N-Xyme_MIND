import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("nxyme_dictate.evdev_injection")

# Map characters to evdev key codes
KEY_CODES = {
    'a': 30, 'b': 48, 'c': 46, 'd': 32, 'e': 18, 'f': 33, 'g': 34, 'h': 35,
    'i': 23, 'j': 36, 'k': 37, 'l': 38, 'm': 50, 'n': 49, 'o': 24, 'p': 25,
    'q': 16, 'r': 19, 's': 31, 't': 20, 'u': 22, 'v': 47, 'w': 17, 'x': 45,
    'y': 21, 'z': 44, '0': 11, '1': 2, '2': 3, '3': 4, '4': 5, '5': 6,
    '6': 7, '7': 8, '8': 9, '9': 10,
    ' ': 57, '\n': 28, '\t': 15,
    '-': 12, '=': 13, '[': 26, ']': 27, ';': 39, "'": 40, '`': 41,
    '\\': 43, ',': 51, '.': 52, '/': 53,
}

SHIFT_MAP = {
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'",
    '~': '`', '<': ',', '>': '.', '?': '/',
}


def _find_ydotool_device() -> Optional[str]:
    """Find ydotoold virtual device."""
    try:
        import evdev
        devices = [evdev.InputDevice(d) for d in evdev.list_devices()]
        for d in devices:
            if 'virtual' in d.name.lower() or 'ydo' in d.name.lower():
                return d.path
    except Exception as e:
        logger.debug(f"Device search error: {e}")
    return None


def evdev_type(text: str) -> bool:
    """Type text using evdev through ydotoold virtual device."""
    if not text:
        return False
    
    device_path = _find_ydotool_device()
    if not device_path:
        logger.warning("evdev: no ydotoold device found")
        return False
    
    try:
        import evdev
        from evdev import ecodes
        
        device = evdev.InputDevice(device_path)
        device.grab()
        
        for char in text:
            key = None
            shift = char.isupper() or char in SHIFT_MAP
            
            if char.isalpha():
                key = ord(char.lower()) - ord('a') + 30
            elif char.isdigit():
                key = ord(char) - ord('0') + 2
            elif char in KEY_CODES:
                key = KEY_CODES[char]
            elif char in SHIFT_MAP:
                key = KEY_CODES.get(SHIFT_MAP[char])
                shift = True
            else:
                continue
            
            # Press key
            if shift:
                device.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 1)
            device.write(ecodes.EV_KEY, key, 1)
            device.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)
            
            # Release key
            device.write(ecodes.EV_KEY, key, 0)
            if shift:
                device.write(ecodes.EV_KEY, ecodes.KEY_LEFTSHIFT, 0)
            device.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)
            
            time.sleep(0.01)  # Small delay between keys
        
        device.ungrab()
        logger.info(f"evdev: typed {len(text)} chars")
        return True
        
    except Exception as e:
        logger.error(f"evdev type error: {e}")
        return False


def inject_with_evdev(text: str) -> bool:
    """Primary injection using evdev."""
    if not text:
        return False
    
    result = evdev_type(text.strip())
    if result:
        return True
    
    # Fallback to other methods
    return False