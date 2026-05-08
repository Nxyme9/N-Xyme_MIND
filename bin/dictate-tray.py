#!/usr/bin/env python3
"""
N-Xyme Dictate Tray - KDE Plasma native system tray
Uses pydbus for proper KDE StatusNotifierItem integration
"""

import sys
import time
import signal
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
sys.path.insert(0, str(PROJECT_ROOT))

def log(msg):
    print(f"[tray] {msg}", flush=True)

class TrayApp:
    def __init__(self):
        self.dictation_pid = None
        self.is_recording = False
        self.proxy = None
        
    def check_dictation(self):
        result = subprocess.run(
            ["pgrep", "-af", "nx_dictate"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "nx_dictate" in line and "--no-ui" not in line:
                    pid = int(line.split()[0])
                    self.dictation_pid = pid
                    return True
        return False
    
    def start_dictation(self):
        if not self.check_dictation():
            venv_python = PROJECT_ROOT / ".venv/bin/python"
            subprocess.Popen(
                [str(venv_python), "-m", "nx_dictate", "--device", "1"],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(4)
            return self.check_dictation()
        return True
    
    def get_status(self):
        try:
            import urllib.request
            import json
            req = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=1)
            data = json.loads(req.read().decode())
            return data.get("state", "unknown")
        except:
            return "error"
    
    def send_start(self):
        try:
            import urllib.request
            import json
            req = urllib.request.urlopen(
                "http://127.0.0.1:8765/start",
                data=json.dumps({"device":1}).encode(),
                timeout=2
            )
            self.is_recording = True
            self.play_beep(880)
            self.notify("NXyme Dictate", "Recording started")
            return True
        except Exception as e:
            log(f"Start error: {e}")
            return False
    
    def send_stop(self):
        try:
            import urllib.request
            req = urllib.request.urlopen("http://127.0.0.1:8765/stop", timeout=2)
            self.is_recording = False
            self.play_beep(440)
            self.notify("NXyme Dictate", "Recording stopped")
            return True
        except Exception as e:
            log(f"Stop error: {e}")
            return False
    
    def play_beep(self, freq=880):
        try:
            import math
            import wave
            import io
            from struct import pack
            
            duration = 0.06
            sample_rate = 44100
            num_samples = int(sample_rate * duration)
            samples = [int(32767 * 0.4 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)]
            
            wav_data = io.BytesIO()
            with wave.open(wav_data, 'w') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                f.writeframes(pack("<" + "h" * len(samples), *samples))
            wav_data.seek(0)
            
            subprocess.Popen(
                ["paplay", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            ).communicate(wav_data.getvalue())
        except:
            pass
    
    def notify(self, title, message):
        try:
            subprocess.run([
                "notify-send", "-i", "audio-x-generic", "-t", "2000", title, message
            ], capture_output=True, timeout=1)
        except:
            pass
    
    def setup_kde_tray(self):
        try:
            from pydbus import SessionBus
            
            bus = SessionBus()
            
            self.proxy = bus.get(
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierItem"
            )
            
            log("KDE StatusNotifier available")
            return True
        except ImportError:
            log("pydbus not available, using fallback")
        except Exception as e:
            log(f"KDE setup error: {e}")
        
        return False
    
    def run(self):
        log("Starting N-Xyme Dictate Tray...")
        
        self.start_dictation()
        self.setup_kde_tray()
        
        log(f"Dictation: PID {self.dictation_pid}")
        log("API: http://127.0.0.1:8765")
        log("Controls: Click to toggle, or use mouse button 275")
        log("Status: Ready")
        
        last_state = None
        
        while True:
            status = self.get_status()
            
            if status != last_state:
                log(f"State: {status}")
                last_state = status
            
            time.sleep(0.3)

def main():
    def signal_handler(sig, frame):
        print("\n[tray] Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app = TrayApp()
    app.run()

if __name__ == "__main__":
    main()