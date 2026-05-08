#!/usr/bin/env python3
import sys
import signal
import time
import subprocess
from pathlib import Path

PROJECT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
sys.path.insert(0, str(PROJECT))

print("[TRAY] Starting NXyme Dictate Tray...", flush=True)

def get_status():
    try:
        import urllib.request
        import json
        r = urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=0.5)
        return json.loads(r.read().decode())
    except:
        return {"state": "error"}

def start_recording():
    try:
        import urllib.request
        import json
        urllib.request.urlopen("http://127.0.0.1:8765/start", 
            data=json.dumps({"device":1}).encode(), timeout=2)
        notify("NXyme Dictate", "Recording started")
    except Exception as e:
        print(f"Start error: {e}")

def stop_recording():
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8765/stop", timeout=2)
        notify("NXyme Dictate", "Recording stopped")
    except Exception as e:
        print(f"Stop error: {e}")

def notify(title, msg):
    try:
        subprocess.run(["notify-send", "-i", "audio-x-generic", "-t", "2000", title, msg],
            capture_output=True, timeout=1)
    except:
        pass

def beep(freq=880):
    try:
        import math
        import wave
        import io
        import struct
        import subprocess
        dur, sr = 0.05, 44100
        s = [int(32767*0.4*math.sin(2*math.pi*freq*i/sr)) for i in range(int(sr*dur))]
        w = io.BytesIO()
        with wave.open(w, 'w') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
            f.writeframes(struct.pack("<"+"h"*len(s), *s))
        w.seek(0)
        subprocess.Popen(["paplay", "-"], stdin=subprocess.PIPE).communicate(w.getvalue())
    except:
        pass

def check_dictation():
    r = subprocess.run(["pgrep", "-f", "nx_dictate"], capture_output=True)
    return r.returncode == 0

def ensure_dictation():
    if not check_dictation():
        print("[TRAY] Starting dictation daemon...", flush=True)
        venv = PROJECT / ".venv/bin/python"
        subprocess.Popen([str(venv), "-m", "nx_dictate.__main__", 
            "--device", "1", "--model", "distil-large-v3", "--language", "en", "--no-ui", "--fast"],
            cwd=str(PROJECT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)

def ensure_ydotool():
    r = subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True)
    if r.returncode != 0:
        print("[TRAY] Starting ydotool...", flush=True)
        subprocess.Popen(["ydotoold"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)

def signal_handler(sig, frame):
    print("\n[TRAY] Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    ensure_dictation()
    ensure_ydotool()
    
    is_recording = False
    last_state = ""
    
    print("[TRAY] Monitoring status...", flush=True)
    print("[TRAY] API: http://127.0.0.1:8765", flush=True)
    print("[TRAY] Controls:", flush=True)
    print("  - Mouse button 275 to toggle recording", flush=True)
    print("  - Or use the HTTP API directly", flush=True)
    
    while True:
        status = get_status()
        state = status.get("state", "unknown")
        
        if state != last_state:
            print(f"[TRAY] State: {state}", flush=True)
            
            if state == "recording" and not is_recording:
                beep(880)
                notify("NXyme Dictate", "🎤 Recording...")
                is_recording = True
            elif state != "recording" and is_recording:
                beep(440)
                result = status.get("last_result", {})
                txt = result.get("processed") or result.get("text", "")
                if txt:
                    notify("NXyme Dictate", f"Typed: {txt[:50]}...")
                is_recording = False
            
            last_state = state
        
        time.sleep(0.5)

if __name__ == "__main__":
    main()