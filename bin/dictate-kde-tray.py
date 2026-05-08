#!/usr/bin/env python3
"""
N-Xyme Dictate KDE Tray - Native KDE system tray integration
Uses KDE's StatusNotifierItem (dbus) for proper KDE Wayland integration
"""

import sys
import time
import signal
import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
sys.path.insert(0, str(PROJECT_ROOT))

VENV_PYTHON = PROJECT_ROOT / ".venv/bin/python"

class KDETrayApp:
    def __init__(self):
        self.dictation_pid = None
        self.is_recording = False
        self.session_count = 0
        self.word_count = 0
        self.dbus_conn = None
        self.status_item = None
        
    def check_dictation(self):
        result = subprocess.run(
            ["pgrep", "-f", "nx_dictate"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            if pids:
                self.dictation_pid = int(pids[0])
                return True
        return False
    
    def start_dictation(self):
        if not self.check_dictation():
            subprocess.Popen(
                [str(VENV_PYTHON), "-m", "nx_dictate", "--device", "1"],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            time.sleep(3)
            self.check_dictation()
    
    def get_status(self):
        if not self.check_dictation():
            return "stopped"
        try:
            import urllib.request
            req = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=1)
            import json
            data = json.loads(req.read().decode())
            return data.get("state", "unknown")
        except:
            return "error"
    
    def send_start(self):
        if not self.check_dictation():
            self.start_dictation()
        try:
            import urllib.request
            req = urllib.request.urlopen(
                "http://127.0.0.1:8765/start",
                data=b'{"device":1}',
                timeout=1
            )
            self.is_recording = True
            return True
        except Exception as e:
            print(f"Start error: {e}")
            return False
    
    def send_stop(self):
        if not self.check_dictation():
            return False
        try:
            import urllib.request
            req = urllib.request.urlopen(
                "http://127.0.0.1:8765/stop",
                timeout=1
            )
            self.is_recording = False
            self.session_count += 1
            return True
        except Exception as e:
            print(f"Stop error: {e}")
            return False
    
    def toggle_recording(self):
        if self.is_recording:
            self.send_stop()
        else:
            self.send_start()
    
    def register_dbus(self):
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            DBusGMainLoop(set_as_default=True)
            
            self.dbus_conn = dbus.SessionBus()
            
            bus_name = "org.kde.StatusNotifierItem"
            obj_path = "/StatusNotifierItem/NXymeDictate"
            
            if self.dbus_conn.request_name(bus_name) != dbus.RequestNameError.REPLY_EXISTING:
                obj = self.dbus_conn.get_object(bus_name)
                self.status_item = dbus.Interface(obj, "org.kde.StatusNotifierItem")
                
                self.status_item.setToolTip("N-Xyme Dictate")
                self.status_item.setStatus("Passive")
                return True
        except Exception as e:
            print(f"Dbus error: {e}")
        return False
    
    def send_notification(self, title, message):
        try:
            subprocess.run([
                "notify-send", "-i", "audio-x-generic", title, message
            ], capture_output=True)
        except:
            pass
    
    def play_beep(self, freq=880):
        try:
            import math
            import wave
            import io
            from struct import pack
            
            duration = 0.08
            sample_rate = 44100
            num_samples = int(sample_rate * duration)
            samples = [int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)]
            
            wav_data = io.BytesIO()
            with wave.open(wav_data, 'w') as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                f.writeframes(pack("<" + "h" * len(samples), *samples))
            wav_data.seek(0)
            
            subprocess.Popen(["paplay", "-"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).communicate(wav_data.getvalue())
        except:
            pass
    
    def run(self):
        self.start_dictation()
        
        print("NXyme Dictate KDE Tray")
        print(f"Dictation PID: {self.dictation_pid}")
        print("API: http://127.0.0.1:8765")
        print("\nControls:")
        print("  Click tray icon → Start/Stop recording")
        print("  Mouse button 275 → Record (hold to speak)")
        print("\nStatus: Ready")
        
        while True:
            status = self.get_status()
            
            if status == "recording" and not self.is_recording:
                self.is_recording = True
                self.play_beep(880)
                self.send_notification("NXyme Dictate", "Recording started")
            
            elif status != "recording" and self.is_recording:
                self.is_recording = False
                self.play_beep(440)
                self.send_notification("NXyme Dictate", "Recording stopped")
            
            time.sleep(0.5)

def main():
    app = KDETrayApp()
    
    def signal_handler(sig, frame):
        print("\nShutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app.run()

if __name__ == "__main__":
    main()