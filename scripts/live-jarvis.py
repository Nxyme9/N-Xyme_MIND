#!/usr/bin/env python3
"""
Live Jarvis - Real-time voice interaction
Listens continuously, responds with voice, sees screen
"""

import asyncio
import pyaudio
import numpy as np
from faster_whisper import WhisperModel
import edge_tts
import json
import requests
import time
import os
import tempfile
import subprocess


class LiveJarvis:
    """Real-time voice assistant with screen awareness"""

    def __init__(self):
        # Audio settings
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        self.format = pyaudio.paInt16

        # Initialize components
        self.whisper = None
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = "llama3.2:3b"

        # State
        self.listening = True
        self.speaking = False
        self.wake_word = "jarvis"

    def initialize(self):
        """Initialize all components"""
        print("Initializing Live Jarvis...")

        # Load Whisper
        print("Loading Whisper model...")
        self.whisper = WhisperModel("base", device="cpu", compute_type="int8")
        print("Whisper ready!")

        # Test Ollama
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if resp.ok:
                print("Ollama connected!")
            else:
                print("Ollama not available")
        except (requests.RequestException, OSError):
            print("Ollama connection failed")

        return True

    def listen_continuously(self):
        """Listen for voice input continuously"""
        print("Listening for 'Jarvis'...")

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )

        try:
            while self.listening:
                # Record audio chunk
                audio_data = stream.read(self.chunk_size)
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                # Check for speech (simple VAD)
                if np.max(np.abs(audio_array)) > 0.01:
                    # Record for 3 seconds
                    frames = [audio_data]
                    for _ in range(int(self.sample_rate / self.chunk_size * 3)):
                        try:
                            frame = stream.read(self.chunk_size)
                            frames.append(frame)
                        except OSError:
                            break

                    # Transcribe
                    audio_array = (
                        np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0
                    )
                    segments, _ = self.whisper.transcribe(audio_array, language="en")
                    text = " ".join([s.text for s in segments]).strip()

                    if text:
                        print(f"Heard: {text}")

                        # Check for wake word
                        if self.wake_word in text.lower():
                            print("Wake word detected!")
                            response = self.process_command(text)
                            if response:
                                self.speak(response)

                        # Check for direct commands
                        elif any(word in text.lower() for word in ["stop", "quit", "exit"]):
                            print("Stopping...")
                            self.listening = False
                            break

        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def process_command(self, text):
        """Process voice command"""
        try:
            # Remove wake word
            command = text.lower().replace(self.wake_word, "").strip()

            if not command:
                return "Yes?"

            # Send to Ollama
            messages = [
                {
                    "role": "system",
                    "content": "You are Jarvis, a helpful AI assistant. Respond in 1-2 sentences.",
                },
                {"role": "user", "content": command},
            ]

            resp = requests.post(
                f"{self.ollama_url}/v1/chat/completions",
                json={"model": self.ollama_model, "messages": messages, "max_tokens": 150},
                timeout=30,
            )

            if resp.ok:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return "Sorry, I couldn't process that."

        except Exception as e:
            print(f"Error: {e}")
            return "Something went wrong."

    def speak(self, text):
        """Convert text to speech"""
        print(f"Jarvis: {text}")

        # Use Edge TTS
        try:
            import edge_tts
            import asyncio

            async def tts():
                communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    await communicate.save(f.name)
                    # Play with system default player
                    subprocess.Popen(["start", f.name], shell=True)

            asyncio.run(tts())
        except Exception as e:
            print(f"TTS error: {e}")


if __name__ == "__main__":
    jarvis = LiveJarvis()

    if jarvis.initialize():
        print("\n=== LIVE JARVIS ACTIVE ===")
        print("Say 'Jarvis' to activate")
        print("Say 'Jarvis stop' to exit")
        print()

        jarvis.listen_continuously()
    else:
        print("Failed to initialize")
