"""
MCP server exposing Bitwig Studio and Scarlett 2i2 controls as tools.

Provides these MCP tools:
  - bitwig_add_clip(name, bpm, key, track_index, length_bars)
  - bitwig_play()
  - bitwig_stop()
  - bitwig_pause()
  - bitwig_record()
  - bitwig_set_tempo(bpm)
  - bitwig_create_track(name, type, index)
  - bitwig_delete_track(track_index)
  - bitwig_rename_track(track_index, new_name)
  - bitwig_set_track_volume(track_index, volume)
  - bitwig_launch_clip(track_index, clip_index)
  - scarlett_set_gain(channel, gain_db)
  - scarlett_set_monitor_mix(direct, playback)
  - get_audio_state()
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP
from pythonosc import udp_client

from bitwig_client import BitwigClient, BitwigConnectionError, BitwigOscError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path | None = None) -> dict:
    """Load YAML config, falling back to defaults if the file is missing."""
    config_path = path or DEFAULT_CONFIG_PATH
    defaults = {
        "bitwig": {
            "host": "127.0.0.1",
            "send_port": 8000,
            "receive_port": 9000,
            "timeout": 2.0,
        },
        "scarlett_2i2": {
            "input_gain_db": 0.0,
            "monitor_direct": 0.5,
            "monitor_playback": 0.5,
            "sample_rate": 48000,
            "buffer_size": 256,
        },
    }
    if config_path.exists():
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        # Deep merge
        for section, values in user_config.items():
            if section in defaults and isinstance(values, dict):
                defaults[section].update(values)
            else:
                defaults[section] = values
    return defaults


# ---------------------------------------------------------------------------
# Singleton Bitwig client
# ---------------------------------------------------------------------------

_config = load_config()
_bitwig: BitwigClient | None = None


def get_bitwig() -> BitwigClient:
    """Return the shared Bitwig client, connecting on first use."""
    global _bitwig
    if _bitwig is None:
        bw_cfg = _config.get("bitwig", {})
        _bitwig = BitwigClient(
            host=bw_cfg.get("host", "127.0.0.1"),
            send_port=bw_cfg.get("send_port", 8000),
            receive_port=bw_cfg.get("receive_port", 9000),
            timeout=bw_cfg.get("timeout", 2.0),
        )
        _bitwig.connect()
    return _bitwig


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "nx-audio-bridge",
    description="Bridge OpenCode to Bitwig Studio and Scarlett 2i2",
)


def _handle_error(operation: str, exc: Exception) -> dict:
    """Format an error response for MCP tools."""
    logger.error("%s failed: %s", operation, exc, exc_info=True)
    if isinstance(exc, BitwigConnectionError):
        return {"success": False, "error": f"Connection error: {exc}"}
    if isinstance(exc, BitwigOscError):
        return {"success": False, "error": f"OSC error: {exc}"}
    if isinstance(exc, ValueError):
        return {"success": False, "error": f"Invalid argument: {exc}"}
    return {"success": False, "error": str(exc)}


# ========================
# Transport tools
# ========================


@mcp.tool()
def bitwig_play() -> dict:
    """Start playback in Bitwig."""
    try:
        result = get_bitwig().play()
        return {"success": True, "action": "play", "response": result}
    except Exception as exc:
        return _handle_error("play", exc)


@mcp.tool()
def bitwig_stop() -> dict:
    """Stop playback in Bitwig."""
    try:
        result = get_bitwig().stop()
        return {"success": True, "action": "stop", "response": result}
    except Exception as exc:
        return _handle_error("stop", exc)


@mcp.tool()
def bitwig_pause() -> dict:
    """Pause (toggle) playback in Bitwig."""
    try:
        result = get_bitwig().pause()
        return {"success": True, "action": "pause", "response": result}
    except Exception as exc:
        return _handle_error("pause", exc)


@mcp.tool()
def bitwig_record() -> dict:
    """Toggle recording in Bitwig."""
    try:
        result = get_bitwig().record()
        return {"success": True, "action": "record", "response": result}
    except Exception as exc:
        return _handle_error("record", exc)


@mcp.tool()
def bitwig_set_tempo(bpm: float) -> dict:
    """
    Set the project tempo.

    Args:
        bpm: Tempo in beats per minute (20-999).
    """
    try:
        result = get_bitwig().set_tempo(bpm)
        return {"success": True, "action": "set_tempo", "bpm": bpm, "response": result}
    except Exception as exc:
        return _handle_error("set_tempo", exc)


# ========================
# Track tools
# ========================


@mcp.tool()
def bitwig_create_track(name: str, type: str = "audio", index: int = -1) -> dict:
    """
    Create a new track in the Bitwig project.

    Args:
        name: Display name for the track.
        type: Track type - one of: audio, midi, instrument, hybrid.
        index: Insert position (-1 = append to end).
    """
    try:
        result = get_bitwig().create_track(name, type, index)
        return {
            "success": True,
            "action": "create_track",
            "name": name,
            "type": type,
            "response": result,
        }
    except Exception as exc:
        return _handle_error("create_track", exc)


@mcp.tool()
def bitwig_delete_track(track_index: int) -> dict:
    """
    Delete a track by its zero-based index.

    Args:
        track_index: Zero-based index of the track to delete.
    """
    try:
        result = get_bitwig().delete_track(track_index)
        return {"success": True, "action": "delete_track", "track_index": track_index, "response": result}
    except Exception as exc:
        return _handle_error("delete_track", exc)


@mcp.tool()
def bitwig_rename_track(track_index: int, new_name: str) -> dict:
    """
    Rename an existing track.

    Args:
        track_index: Zero-based track index.
        new_name: New display name.
    """
    try:
        result = get_bitwig().rename_track(track_index, new_name)
        return {"success": True, "action": "rename_track", "response": result}
    except Exception as exc:
        return _handle_error("rename_track", exc)


@mcp.tool()
def bitwig_set_track_volume(track_index: int, volume: float) -> dict:
    """
    Set track volume.

    Args:
        track_index: Zero-based track index.
        volume: Volume level (0.0 to 1.0).
    """
    try:
        result = get_bitwig().set_track_volume(track_index, volume)
        return {"success": True, "action": "set_track_volume", "response": result}
    except Exception as exc:
        return _handle_error("set_track_volume", exc)


# ========================
# Clip tools
# ========================


@mcp.tool()
def bitwig_add_clip(
    name: str,
    bpm: float = 120.0,
    key: str = "C",
    track_index: int = 0,
    length_bars: int = 4,
) -> dict:
    """
    Add a new clip to a track.

    Args:
        name: Clip display name.
        bpm: Tempo for the clip (20-999).
        key: Musical key (e.g. "C", "Am", "F#m").
        track_index: Zero-based track index to place the clip in.
        length_bars: Clip length in bars.
    """
    try:
        result = get_bitwig().add_clip(name, track_index, bpm, key, length_bars)
        return {
            "success": True,
            "action": "add_clip",
            "name": name,
            "bpm": bpm,
            "key": key,
            "response": result,
        }
    except Exception as exc:
        return _handle_error("add_clip", exc)


@mcp.tool()
def bitwig_launch_clip(track_index: int, clip_index: int) -> dict:
    """
    Launch a specific clip.

    Args:
        track_index: Zero-based track index.
        clip_index: Zero-based clip slot index.
    """
    try:
        result = get_bitwig().launch_clip(track_index, clip_index)
        return {"success": True, "action": "launch_clip", "response": result}
    except Exception as exc:
        return _handle_error("launch_clip", exc)


# ========================
# Scarlett 2i2 tools
# ========================


@mcp.tool()
def scarlett_set_gain(channel: int = 0, gain_db: float = 0.0) -> dict:
    """
    Set Scarlett 2i2 input gain via Bitwig's input mixer.

    Note: For hardware-level gain control, use the Scarlett Control app
    or `amixer`. This applies a software gain offset in Bitwig.

    Args:
        channel: Input channel (0 or 1 for Scarlett 2i2).
        gain_db: Gain in decibels (typically -60 to +12).
    """
    try:
        result = get_bitwig().set_input_gain(channel, gain_db)
        return {
            "success": True,
            "action": "scarlett_set_gain",
            "channel": channel,
            "gain_db": gain_db,
            "response": result,
        }
    except Exception as exc:
        return _handle_error("scarlett_set_gain", exc)


@mcp.tool()
def scarlett_set_monitor_mix(direct: float = 0.5, playback: float = 0.5) -> dict:
    """
    Set the Scarlett 2i2 direct monitor mix ratio.

    Args:
        direct: Direct input level (0.0 to 1.0).
        playback: DAW playback level (0.0 to 1.0).
    """
    try:
        result = get_bitwig().set_monitor_mix(direct, playback)
        return {
            "success": True,
            "action": "scarlett_set_monitor_mix",
            "direct": direct,
            "playback": playback,
            "response": result,
        }
    except Exception as exc:
        return _handle_error("scarlett_set_monitor_mix", exc)


# ========================
# State query
# ========================


@mcp.tool()
def get_audio_state() -> dict:
    """Return the current Bitwig project state."""
    try:
        state = get_bitwig().get_project_state()
        return {
            "success": True,
            "project_name": state.project_name,
            "tempo": state.tempo,
            "time_signature": f"{state.time_signature_numerator}/{state.time_signature_denominator}",
            "is_playing": state.is_playing,
            "tracks": [asdict(t) for t in state.tracks],
        }
    except Exception as exc:
        return _handle_error("get_audio_state", exc)


# ========================
# Entry point
# ========================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="nx-audio-bridge MCP server")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to config.yaml",
    )
    args = parser.parse_args()

    _config = load_config(args.config)
    logger.info("nx-audio-bridge MCP server starting")
    logger.info("Bitwig: %s:%s", _config["bitwig"]["host"], _config["bitwig"]["send_port"])

    mcp.run()
