#!/usr/bin/env python3
"""
ECHO JARVIS - Your Personal AI Companion
OFF by default. Say "Jarvis on" to activate.
"""

import asyncio
import subprocess
import shlex
import json
import os
import re
import sys
import time
import wave
import io
import tempfile
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Callable

import pyaudio
import logging
import requests
import numpy as np

# ─── CONFIG ──────────────────────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2:3b-instruct-q4_K_M"
PIPER_MODEL_DIR = "C:/00_AI_Models/TTS/piper"
PIPER_MODEL = "en_US-lessac-medium.onnx"
SESSION_DIR = Path("C:/Users/N-Xyme/.local/share/opencode/storage/session_diff")

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import GRAPHITI_RPC_URL as GRAPHITI_URL, OLLAMA_URL
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_RPC_URL", "http://localhost:8001/json-rpc")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


# ─── STATES ──────────────────────────────────────────────────────────────────
class EchoState(Enum):
    OFF = auto()
    SILENT = auto()
    NARRATOR = auto()
    FRIEND = auto()
    DELEGATE = auto()


# ─── PERSONALITY ─────────────────────────────────────────────────────────────
class PersonalityManager:
    """Manages Jarvis personality presets."""

    def __init__(self, config_path: str = "configs/jarvis/personalities.json"):
        self.config_path = Path(config_path)
        self.personalities = self._load()
        self.current = "butler"

    def _load(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path) as f:
                return json.load(f)
        return {}

    def set_personality(self, name: str) -> bool:
        if name in self.personalities:
            self.current = name
            return True
        return False

    def get_system_prompt(self) -> str:
        return self.personalities.get(self.current, {}).get("system_prompt", "")

    def get_greeting(self) -> str:
        return self.personalities.get(self.current, {}).get("greeting", "Hello.")

    def get_name(self) -> str:
        return self.personalities.get(self.current, {}).get("name", "Jarvis")

    def get_voice(self) -> str:
        return self.personalities.get(self.current, {}).get("voice", "en_US-lessac-medium")

    def list_personalities(self) -> list:
        return list(self.personalities.keys())


# ─── SAFETY ──────────────────────────────────────────────────────────────────
DESTRUCTIVE_PATTERNS = [
    r"\bgit push\b",
    r"\bgit commit\b",
    r"\bdelete\b",
    r"\brm\b",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\binstall\b",
    r"\bdocker\b",
    r"\bcurl\b",
    r"\bwget\b",
    r"\bchmod\b",
    r"\bsudo\b",
]


class SafetyGuard:
    def __init__(self):
        self.action_count = []
        self.speech_count = []
        self.MAX_ACTIONS_PER_MIN = 5
        self.MAX_SPEECHES_PER_MIN = 3

    def is_destructive(self, text: str) -> bool:
        return any(re.search(p, text, re.IGNORECASE) for p in DESTRUCTIVE_PATTERNS)

    def check_rate(self, action_type: str = "action") -> bool:
        now = time.time()
        counts = self.action_count if action_type == "action" else self.speech_count
        limit = self.MAX_ACTIONS_PER_MIN if action_type == "action" else self.MAX_SPEECHES_PER_MIN
        # Clean old entries
        counts[:] = [t for t in counts if now - t < 60]
        if len(counts) >= limit:
            return False
        counts.append(now)
        return True


# ─── PIPER TTS ───────────────────────────────────────────────────────────────
class PiperTTS:
    def __init__(self):
        from piper import PiperVoice

        model_path = os.path.join(PIPER_MODEL_DIR, PIPER_MODEL)
        self.voice = PiperVoice.load(model_path)
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_playing = False
        self.should_stop = False

    def speak(self, text: str):
        """Generate and play speech. ~190ms total."""
        if not text or self.should_stop:
            return

        self.is_playing = True
        self.should_stop = False

        # Generate WAV in memory
        buf = io.BytesIO()
        with wave.open(buf, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            self.voice.synthesize(text, wf)

        # Play
        buf.seek(0)
        wf = wave.open(buf, "rb")
        self.stream = self.p.open(
            format=self.p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )

        data = wf.readframes(1024)
        while data and not self.should_stop:
            self.stream.write(data)
            data = wf.readframes(1024)

        self.stream.stop_stream()
        self.stream.close()
        wf.close()
        self.is_playing = False

    def stop(self):
        """Immediately stop playback (barge-in)."""
        self.should_stop = True
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logging.error(f"Error stopping PiperTTS: {e}")
        self.is_playing = False

    def cleanup(self):
        self.p.terminate()


# ─── ECHO BRAIN ──────────────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    EchoState.SILENT: "You are Echo. Stay silent. Do not respond.",
    EchoState.NARRATOR: """You are Echo, a narrator. Comment on what the user is doing.
Keep comments to ONE short sentence (5-10 words). Be observational, not chatty.
Only comment on: errors, completions, interesting patterns. Stay silent 90% of the time.""",
    EchoState.FRIEND: """You are Echo, a casual friend. Respond naturally to what the user says.
Keep responses to 1-2 sentences. Be warm but concise. Use humor when appropriate.
You understand ADHD and are supportive without being preachy.""",
    EchoState.DELEGATE: """You are Echo, a delegation assistant. Help route the user's requests.
When they say "tell X to do Y", confirm which session/agent you're routing to.
Keep confirmations to one sentence.""",
}


class EchoBrain:
    def __init__(self):
        self.conversation = []

    def think(self, user_text: str, state: EchoState, personality_system: str = "") -> str:
        """Generate response using Ollama."""
        if state == EchoState.SILENT:
            return ""

        system = SYSTEM_PROMPTS.get(state, SYSTEM_PROMPTS[EchoState.FRIEND])
        messages = []
        if personality_system:
            messages.append({"role": "system", "content": personality_system})
        messages.append({"role": "system", "content": system})
        messages.extend(self.conversation[-6:])
        messages.append({"role": "user", "content": user_text})

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
                timeout=15,
            )
            data = resp.json()
            reply = data.get("message", {}).get("content", "").strip()
            self.conversation.append({"role": "user", "content": user_text})
            self.conversation.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"Hmm, couldn't think. {e}"


# ─── DELEGATION ──────────────────────────────────────────────────────────────
DELEGATION_PATTERNS = [
    (r"tell (?:the )?(\w+) (?:chat|session|agent) to (.+)", "inject"),
    (r"ask (\w+) about (.+)", "query"),
    (r"check if (.+) is (?:running|working|up)", "check"),
    (r"what(?:'s| is) the (.+) (?:status|state)", "status"),
]


def parse_delegation(text: str) -> Optional[dict]:
    """Parse voice command for delegation. Pattern-first, no LLM."""
    for pattern, action_type in DELEGATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return {
                "type": action_type,
                "target": match.group(1),
                "command": match.group(2) if match.lastindex >= 2 else "",
            }
    return None


# ─── MAIN ECHO ───────────────────────────────────────────────────────────────
class EchoJarvis:
    def __init__(self):
        self.state = EchoState.OFF
        self.tts = None
        self.brain = EchoBrain()
        self.safety = SafetyGuard()
        self.personality = PersonalityManager()
        self.pending_confirmation = None
        self.running = True

        # Wake words
        self.WAKE_ON = [r"\bjarvis on\b", r"\bjarvis wake up\b", r"\bjarvis activate\b"]
        self.WAKE_OFF = [
            r"\bjarvis off\b",
            r"\bjarvis sleep\b",
            r"\bjarvis shut up\b",
            r"\bjarvis stop\b",
        ]
        self.WAKE_KILL = [
            r"\bjarvis emergency\b",
            r"\bjarvis kill\b",
            r"\bjarvis shutdown\b",
        ]
        self.MODE_SWITCH = {
            r"\bjarvis silent\b": EchoState.SILENT,
            r"\bjarvis narrate\b": EchoState.NARRATOR,
            r"\bjarvis friend\b": EchoState.FRIEND,
            r"\bjarvis delegate\b": EchoState.DELEGATE,
        }

    def init_tts(self):
        """Lazy load TTS (takes a second)."""
        if self.tts is None:
            print("Loading Piper TTS...")
            self.tts = PiperTTS()
            print("TTS ready!")

    def speak(self, text: str):
        """Speak with safety checks."""
        if self.state == EchoState.OFF or self.state == EchoState.SILENT:
            return
        if not self.safety.check_rate("speech"):
            return
        self.init_tts()
        print(f"Echo: {text}")
        self.tts.speak(text)

    def handle_command(self, text: str) -> bool:
        """
        Handle voice commands. Returns True if command was handled.
        """
        text_lower = text.lower().strip()

        # ── KILL SWITCH (always works) ──
        for pattern in self.WAKE_KILL:
            if re.search(pattern, text_lower):
                self.state = EchoState.OFF
                if self.tts:
                    self.tts.stop()
                print("EMERGENCY STOP - Echo killed")
                return True

        # ── OFF (always works) ──
        for pattern in self.WAKE_OFF:
            if re.search(pattern, text_lower):
                self.state = EchoState.OFF
                self.speak("Going silent. Say Jarvis on to reactivate.")
                print("Echo: OFF")
                return True

        # ── ON (only when off) ──
        if self.state == EchoState.OFF:
            for pattern in self.WAKE_ON:
                if re.search(pattern, text_lower):
                    self.state = EchoState.FRIEND
                    self.speak("I'm here. What do you need?")
                    print("Echo: ON (friend mode)")
                    return True
            return False  # Off and not a wake word = ignore

        # ── MODE SWITCH ──
        for pattern, mode in self.MODE_SWITCH.items():
            if re.search(pattern, text_lower):
                self.state = mode
                self.speak(f"{mode.name.lower()} mode.")
                print(f"Echo: {mode.name}")
                return True

        # ── PERSONALITY SWITCH ──
        be_match = re.search(r"\bbe\s+(?:a\s+)?(\w+)", text_lower)
        if be_match:
            target = be_match.group(1)
            if self.personality.set_personality(target):
                self.speak(self.personality.get_greeting())
                return True
            # Also try by name (Gags, Doc, Coach, etc.)
            for p in self.personality.list_personalities():
                if self.personality.personalities[p]["name"].lower() == target.lower():
                    self.personality.set_personality(p)
                    self.speak(self.personality.get_greeting())
                    return True

        # ── STATUS ──
        if re.search(r"\bjarvis status\b", text_lower):
            self.speak(f"I'm in {self.state.name.lower()} mode.")
            return True

        # ── WHAT DID YOU DO ──
        if re.search(r"\bwhat did you do\b", text_lower):
            self.speak("I've been listening. Nothing executed yet.")
            return True

        return False

    def process_input(self, text: str):
        """Main processing loop for voice input."""
        if not text or len(text) < 3:
            return

        print(f"You: {text}")

        # 1. Check for commands (wake word, mode, etc.)
        if self.handle_command(text):
            return

        # 2. If OFF, ignore everything
        if self.state == EchoState.OFF:
            return

        # 3. Check for pending confirmation
        if self.pending_confirmation:
            if re.search(r"\b(confirm|yes|go ahead|do it)\b", text, re.IGNORECASE):
                action = self.pending_confirmation
                self.pending_confirmation = None
                # Show what will be executed (best-effort)
                self.speak(
                    f"Confirmed. Executing: {action.get('description', action.get('raw', action.get('command', '')))}"
                )
                # Execute the action or delegation command
                try:
                    # Only execute if this is a real shell action (has 'raw')
                    if isinstance(action, dict) and "raw" in action:
                        raw_cmd = action.get("raw")
                        if not raw_cmd:
                            self.speak("No command to execute.")
                            print("[LOG] No executable command found in confirmed action.")
                        else:
                            result = subprocess.run(
                                shlex.split(raw_cmd),
                                shell=False,
                                capture_output=True,
                                text=True,
                            )
                            out = (result.stdout or "") + (result.stderr or "")
                            ret = result.returncode
                            print(f"[LOG] Executed: {raw_cmd} RC={ret}\nOutput:\n{out[:500]}")
                            first_line = out.splitlines()[0] if out else ""
                            self.speak(f"Command finished with return code {ret}. {first_line}")
                    else:
                        self.speak("Confirmed action is delegation; no shell execution.")
                        print(f"[LOG] Confirmed action is delegation; no shell execution: {action}")
                except Exception as e:
                    self.speak(f"Error executing action: {e}")
                    print(f"[LOG] Action execution error: {e}")
                return
            elif re.search(r"\b(cancel|no|stop|don't)\b", text, re.IGNORECASE):
                self.pending_confirmation = None
                self.speak("Cancelled.")
                return

        # 4. Check for delegation
        delegation = parse_delegation(text)
        if delegation:
            if self.safety.is_destructive(delegation["command"]):
                self.pending_confirmation = delegation
                self.speak(f"This will: {delegation['command']}. Say confirm or cancel.")
                return
            else:
                self.speak(f"Routing to {delegation['target']}: {delegation['command']}")
                # Attempt to inject the command into the target OpenCode session
                try:
                    session_id = delegation.get("target", "")
                    cmd = delegation.get("command", "")
                    if not session_id or not cmd:
                        self.speak("Insufficient delegation details for injection.")
                    else:
                        payload = {"session_id": session_id, "command": cmd}
                        resp = requests.post(f"{GRAPHITI_URL}/inject", json=payload, timeout=5)
                        if resp.ok:
                            self.speak(f"Delegation injected into session {session_id}.")
                            print(f"[LOG] Delegation injected: session={session_id}, cmd={cmd}")
                        else:
                            self.speak("Failed to inject delegation into session.")
                            print(f"[LOG] Injection failed: {resp.status_code} {resp.text}")
                except Exception as e:
                    self.speak(f"Error injecting delegation: {e}")
                    print(f"[LOG] Injection error: {e}")
                return

        # 5. Check for destructive actions
        if self.safety.is_destructive(text):
            self.pending_confirmation = {"description": text, "raw": text}
            self.speak(f"This looks destructive. Say confirm or cancel.")
            return

        # 6. Normal conversation (brain thinks)
        if not self.safety.check_rate("action"):
            self.speak("I'm doing too much. Give me a moment.")
            return

        response = self.brain.think(text, self.state, self.personality.get_system_prompt())
        if response:
            self.speak(response)

    def run_interactive(self):
        """Interactive text mode (for testing without mic)."""
        print("=" * 50)
        print("  ECHO JARVIS - Interactive Mode")
        print("  Type 'quit' to exit")
        print("  Say 'Jarvis on' to activate")
        print("=" * 50)

        while self.running:
            try:
                text = input("\nYou: ").strip()
                if text.lower() in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                self.process_input(text)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    def run_voice(self):
        """Voice mode with microphone."""
        print("=" * 50)
        print("  ECHO JARVIS - Voice Mode")
        print("  Say 'Jarvis on' to activate")
        print("  Ctrl+C to exit")
        print("=" * 50)

        # Import Whisper
        from faster_whisper import WhisperModel
        import sounddevice as sd

        print("Loading Whisper...")
        whisper = WhisperModel("base", device="cpu", compute_type="int8")
        print("Whisper ready!")

        SAMPLE_RATE = 16000
        RECORD_SECONDS = 5

        while self.running:
            try:
                # Record
                print(f"\nListening ({RECORD_SECONDS}s)...")
                audio = sd.rec(
                    int(RECORD_SECONDS * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()

                # Transcribe
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                    with wave.open(f, "w") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(SAMPLE_RATE)
                        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

                segments, _ = whisper.transcribe(temp_path, beam_size=5)
                text = " ".join([s.text for s in segments]).strip()
                os.unlink(temp_path)

                if text:
                    self.process_input(text)

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    echo = EchoJarvis()

    if "--voice" in sys.argv:
        echo.run_voice()
    else:
        echo.run_interactive()
