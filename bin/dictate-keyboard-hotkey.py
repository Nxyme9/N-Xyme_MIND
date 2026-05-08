#!/usr/bin/env python3
"""N-Xyme Dictate Keyboard Hotkey - Works on Wayland"""
import subprocess
import time
import urllib.request
import json
import signal
import sys

API = "http://127.0.0.1:8765"
RECORDING = False

def signal_handler(sig, frame):
    print("\n[hotkey] Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def call_api(path):
    try:
        urllib.request.urlopen(f"{API}{path}", data=b"{}", timeout=2)
        return True
    except:
        return False

def get_status():
    try:
        r = urllib.request.urlopen(f"{API}/status", timeout=0.5)
        return json.loads(r.read().decode()).get("state", "unknown")
    except:
        return "error"

def notify(msg):
    try:
        subprocess.run(["notify-send", "-i", "audio-x-generic", "-t", "1500", 
            "NXyme Dictate", msg], capture_output=True, timeout=1)
    except:
        pass

def beep(freq=880):
    try:
        import math
        import wave
        import io
        import struct
        dur, sr = 0.04, 44100
        s = [int(32767*0.3*math.sin(2*3.14159*freq*i/sr)) for i in range(int(sr*dur))]
        w = io.BytesIO()
        with wave.open(w, 'w') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr)
            f.writeframes(struct.pack("<"+"h"*len(s), *s))
        w.seek(0)
        subprocess.Popen(["paplay", "-"], stdin=subprocess.PIPE).communicate(w.getvalue())
    except:
        pass

def poll_key():
    global RECORDING
    while True:
        status = get_status()
        
        if status == "recording" and not RECORDING:
            beep(880)
            notify("Recording... (Ctrl+Alt+D to stop)")
            RECORDING = True
        elif status != "recording" and RECORDING:
            beep(440)
            result = None
            try:
                r = urllib.request.urlopen(f"{API}/status", timeout=0.5)
                result = json.loads(r.read().decode()).get("last_result", {})
            except:
                pass
            if result:
                txt = result.get("processed") or result.get("text", "")
                if txt:
                    notify(f"Typed: {txt[:60]}...")
            RECORDING = False
        
        time.sleep(0.5)

if __name__ == "__main__":
    wait_count = 0
    
    print("[hotkey] NXyme Dictate Keyboard Controller")
    print("[hotkey] Waiting for dictation service...")
    
    while True:
        status = get_status()
        
        if status != "error":
            print(f"[hotkey] Dictation ready (state: {status})")
            print("[hotkey] Press Ctrl+Alt+D to toggle recording")
            print("[hotkey] Or use mouse button 275 (side)")
            break
        
        wait_count += 1
        if wait_count > 15:
            print("[hotkey] ERROR: Dictation service not responding on port 8765")
            print("[hotkey] Start dictation first: python -m nx_dictate --device 1")
            sys.exit(1)
        
        time.sleep(1)
    
    poll_key()