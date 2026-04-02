#!/usr/bin/env python3
"""Jarvis Voice Wrapper - Handles non-interactive startup"""
import subprocess
import sys
import os

def start_jarvis_voice():
    """Start Jarvis voice mode properly"""
    print("Starting Jarvis voice assistant...")
    
    # Create a pseudo-terminal for Jarvis
    proc = subprocess.Popen(
        [sys.executable, 'D:/01_CODING/00_N-Xyme_CATALYST/scripts/echo-jarvis.py', '--voice'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Send a newline to prevent EOF
    proc.stdin.write("
")
    proc.stdin.flush()
    
    print("Jarvis starting...")
    print("Loading Whisper model (30-60 seconds)...")
    print("Then say 'Jarvis on' to activate")
    
    return proc

if __name__ == "__main__":
    proc = start_jarvis_voice()
    
    # Keep running
    try:
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print(f"JARVIS: {line.strip()}")
    except KeyboardInterrupt:
        print("
Stopping Jarvis...")
        proc.terminate()
