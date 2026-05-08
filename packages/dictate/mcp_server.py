#!/usr/bin/env python3
"""
Dictate MCP Server - Exposes voice-to-text as MCP tools.

PRIMARY: Uses frankenstein_engine's direct pywhispercpp (NO daemon!)
FALLBACK: Uses existing dictate daemon via Unix socket (dictate --serve).

Add to opencode.json:
    "dictate": {
      "type": "local",
      "command": ["python3", "-m", "packages.dictate.mcp_server"],
      "environment": {"PYTHONPATH": "."}
    }
"""

import os
import socket
import threading
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger("dictate_mcp")

mcp = FastMCP("N-Xyme Dictate")

# Dictate socket path (fallback only)
SOCK_PATH = os.path.expanduser("~/.local/share/dictate/dictate.sock")

# Try frankenstein_engine first
_frankenstein_whisper = None


def _store_to_memory(content: str, kind: str = "episodic") -> bool:
    """Store content to memory store for learning.

    Args:
        content: Text to store
        kind: Memory type (episodic, semantic, etc.)

    Returns:
        True if stored successfully
    """
    try:
        from packages.memory_store.mcp_server import memory_write

        result = memory_write(
            content=content, kind=kind, scope="session", tags=["voice", "dictate"]
        )
        return result.get("success", False)
    except Exception as e:
        logger.warning(f"Could not store to memory: {e}")
        return False


def _get_frankenstein_whisper():
    """Lazy-load frankenstein whisper client."""
    global _frankenstein_whisper
    if _frankenstein_whisper is None:
        try:
            from frankenstein_engine.engine.whisper import WhisperClient

            _frankenstein_whisper = WhisperClient()
            logger.info("Loaded frankenstein whisper (direct pywhispercpp)")
        except Exception as e:
            logger.warning(f"Could not load frankenstein whisper: {e}")
    return _frankenstein_whisper


class DictateClient:
    """Client for interacting with dictate daemon via Unix socket."""

    def __init__(self, sock_path: str = SOCK_PATH):
        self.sock_path = sock_path
        self._lock = threading.Lock()

    def transcribe(self, text: str = "") -> Dict[str, Any]:
        """Send transcribe request.

        PRIMARY: Try frankenstein direct whisper (pywhispercpp)
        FALLBACK: Use Unix socket daemon

        This requires audio input from microphone. If no daemon is running,
        we need a different approach - this is for FILE transcription.
        """
        # First try frankenstein client (direct pywhispercpp)
        frankenstein = _get_frankenstein_whisper()
        if frankenstein:
            # frankenstein needs an audio FILE, not microphone
            # For live dictation, we need the daemon or a different approach
            # This is here for future file-based transcription
            logger.info("Frankenstein whisper available for file transcription")

        with self._lock:
            try:
                import json as json_mod

                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect(self.sock_path)

                # Send request - use json.dumps for proper JSON format
                request = {"action": "transcribe", "text": text}
                sock.sendall((json_mod.dumps(request) + "\n").encode())
                sock.shutdown(socket.SHUT_WR)

                # Read response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\n" in chunk:
                        break

                sock.close()

                # Parse response
                result = response.decode().strip()
                if result:
                    try:
                        resp_data = json_mod.loads(result)
                        return {
                            "status": "success",
                            "result": resp_data.get("text", result),
                        }
                    except (json.JSONDecodeError, ValueError, KeyError):
                        return {"status": "success", "result": result}
                return {"status": "success", "result": ""}

            except socket.timeout:
                return {"status": "error", "error": "Timeout waiting for transcription"}
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error": f"Dictate socket not found: {self.sock_path}",
                }
            except ConnectionRefusedError:
                return {
                    "status": "error",
                    "error": "Dictate daemon not running. Run: dictate --serve",
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

    def transcribe_file(
        self, audio_path: str, initial_prompt: str = ""
    ) -> Dict[str, Any]:
        """Transcribe an audio FILE using frankenstein direct whisper.

        Args:
            audio_path: Path to audio file (wav, mp3, etc.)
            initial_prompt: Optional vocabulary hints

        Returns:
            Dict with transcription result
        """
        frankenstein = _get_frankenstein_whisper()
        if frankenstein is None:
            return {
                "status": "error",
                "error": "Frankenstein whisper not available",
            }

        try:
            text = frankenstein.transcribe(audio_path, initial_prompt=initial_prompt)
            return {"status": "success", "result": text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def status(self) -> Dict[str, Any]:
        """Check if dictate daemon is running."""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(self.sock_path)
            sock.sendall(b'{"action": "status"}\n')
            response = sock.recv(1024)
            sock.close()
            return {"status": "running", "daemon": "connected"}
        except Exception as e:
            return {"status": "stopped", "daemon": str(e)}

    def stop_recording(self) -> Dict[str, Any]:
        """Stop current recording immediately."""
        try:
            stop_flag = os.path.expanduser("~/.local/share/dictate/stop")
            Path(stop_flag).touch()
            return {"status": "success", "action": "stop_flag_created"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global client instance
_client: Optional[DictateClient] = None


def get_client() -> DictateClient:
    global _client
    if _client is None:
        _client = DictateClient()
    return _client


@mcp.tool()
def dictate_status() -> Dict[str, Any]:
    """Check if dictate daemon is running and ready.

    Returns:
        Dict with daemon status
    """
    client = get_client()
    return client.status()


@mcp.tool()
def dictate_transcribe(text: str = "", store_memory: bool = False) -> Dict[str, Any]:
    """Transcribe voice input from MICROPHONE.

    The dictate daemon must be running (dictate --serve).
    Press RIGHT CTRL to record, release to transcribe.
    Use this tool after you've finished recording.

    For AUDIO FILE transcription, use dictate_transcribe_file instead.

    Args:
        text: Optional context text for vocabulary hints
        store_memory: If True, store transcription to memory store for learning

    Returns:
        Dict with transcription result
    """
    client = get_client()
    result = client.transcribe(text)

    # Optionally store to memory for learning
    if store_memory and result.get("status") == "success":
        _store_to_memory(result.get("result", ""), "voice_input")

    return result


@mcp.tool()
def dictate_transcribe_file(
    audio_path: str, initial_prompt: str = "", store_memory: bool = False
) -> Dict[str, Any]:
    """Transcribe an AUDIO FILE using direct pywhispercpp.

    Uses frankenstein_engine's direct whisper (pywhispercpp) - NO HTTP, NO daemon!
    Supports vocabulary hints via initial_prompt for better accuracy.

    For MICROPHONE transcription, use dictate_transcribe instead.

    Args:
        audio_path: Path to audio file (wav, mp3, m4a, flac, etc.)
        initial_prompt: Optional prompt with vocabulary hints
        store_memory: If True, store transcription to memory store for learning

    Returns:
        Dict with transcription result
    """
    client = get_client()
    result = client.transcribe_file(audio_path, initial_prompt=initial_prompt)

    # Optionally store to memory for learning
    if store_memory and result.get("status") == "success":
        _store_to_memory(result.get("result", ""), "audio_file")

    return result


@mcp.tool()
def dictate_stop() -> Dict[str, Any]:
    """Stop current recording immediately.

    Use this if you started recording but want to cancel.

    Returns:
        Dict with stop result
    """
    client = get_client()
    return client.stop_recording()


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger.info("Starting Dictate MCP Server...")
    mcp.run()
