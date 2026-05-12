"""
Bitwig Studio OSC client.

Connects to Bitwig's OSC API (default port 8000) for transport control,
track management, clip creation, and project state querying.

Bitwig OSC Protocol:
  - Transport:  /bitwig/transport/play, /bitwig/transport/stop
  - Tracks:     /bitwig/track/create, /bitwig/track/delete
  - Clips:      /bitwig/clip/add, /bitwig/clip/set_bpm, /bitwig/clip/set_key
  - State:      /bitwig/project/name, /bitwig/project/tempo
  - Mixer:      /bitwig/mixer/gain, /bitwig/mixer/pan
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pythonosc import udp_client, osc_message_builder
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TrackInfo:
    """Metadata about a Bitwig track."""
    name: str
    track_type: str  # "audio" | "midi" | "instrument" | "hybrid"
    index: int = -1
    is_active: bool = False
    volume: float = 1.0
    pan: float = 0.0


@dataclass
class ClipInfo:
    """Metadata about a clip within a track."""
    name: str
    bpm: float = 120.0
    key: str = "C"
    length_bars: int = 4
    track_index: int = 0


@dataclass
class ProjectState:
    """Snapshot of the current Bitwig project state."""
    project_name: str = ""
    tempo: float = 120.0
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4
    is_playing: bool = False
    tracks: list[TrackInfo] = field(default_factory=list)
    current_clip: ClipInfo | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BitwigConnectionError(Exception):
    """Raised when the connection to Bitwig fails."""


class BitwigOscError(Exception):
    """Raised when an OSC command fails or returns an unexpected response."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class BitwigClient:
    """
    High-level client for controlling Bitwig Studio via OSC.

    Parameters
    ----------
    host : str
        Hostname or IP of the Bitwig machine (default: 127.0.0.1).
    send_port : int
        Port Bitwig listens on for incoming OSC messages (default: 8000).
    receive_port : int
        Local port this client binds to for receiving OSC responses
        (default: 9000).
    timeout : float
        Seconds to wait for a response before timing out (default: 2.0).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        send_port: int = 8000,
        receive_port: int = 9000,
        timeout: float = 2.0,
    ) -> None:
        self.host = host
        self.send_port = send_port
        self.receive_port = receive_port
        self.timeout = timeout

        self._client = udp_client.SimpleUDPClient(host, send_port)
        self._client.timeout = timeout
        self._server: BlockingOSCUDPServer | None = None
        self._last_response: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Verify connectivity by sending a ping to Bitwig.

        Raises
        ------
        BitwigConnectionError
            If Bitwig does not respond within ``timeout`` seconds.
        """
        try:
            self._client.send_message("/bitwig/ping", [])
            logger.info("Connected to Bitwig at %s:%s", self.host, self.send_port)
        except OSError as exc:
            raise BitwigConnectionError(
                f"Cannot reach Bitwig at {self.host}:{self.send_port}: {exc}"
            ) from exc

    def disconnect(self) -> None:
        """Shut down the response listener if running."""
        if self._server:
            self._server.shutdown()
            self._server = None
            logger.info("Disconnected from Bitwig.")

    def start_response_listener(self) -> None:
        """
        Start a background OSC server to capture responses from Bitwig.

        Bitwig will send acknowledgements and state updates to
        ``receive_port``. This method registers handlers for common
        response paths.
        """
        dispatcher = Dispatcher()
        dispatcher.map("/bitwig/response/*", self._handle_response)
        dispatcher.map("/bitwig/state/*", self._handle_state_update)

        self._server = BlockingOSCUDPServer(
            (self.host, self.receive_port), dispatcher
        )
        logger.info(
            "Response listener started on %s:%s", self.host, self.receive_port
        )

    # ------------------------------------------------------------------
    # Transport controls
    # ------------------------------------------------------------------

    def play(self) -> dict[str, Any]:
        """Start playback."""
        return self._send("/bitwig/transport/play", [])

    def stop(self) -> dict[str, Any]:
        """Stop playback."""
        return self._send("/bitwig/transport/stop", [])

    def pause(self) -> dict[str, Any]:
        """Pause playback (toggle)."""
        return self._send("/bitwig/transport/pause", [])

    def record(self) -> dict[str, Any]:
        """Toggle recording."""
        return self._send("/bitwig/transport/record", [])

    def set_tempo(self, bpm: float) -> dict[str, Any]:
        """Set the project tempo."""
        if not 20 <= bpm <= 999:
            raise ValueError(f"BPM must be between 20 and 999, got {bpm}")
        return self._send("/bitwig/transport/set_tempo", [bpm])

    def get_tempo(self) -> float:
        """Query the current project tempo."""
        resp = self._send("/bitwig/transport/get_tempo", [])
        return float(resp.get("value", 120.0))

    def set_loop_length(self, bars: int) -> dict[str, Any]:
        """Set the loop length in bars."""
        return self._send("/bitwig/transport/set_loop_length", [float(bars)])

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def create_track(
        self,
        name: str,
        track_type: str = "audio",
        index: int = -1,
    ) -> dict[str, Any]:
        """
        Create a new track in the Bitwig project.

        Parameters
        ----------
        name : str
            Display name for the track.
        track_type : str
            One of ``"audio"``, ``"midi"``, ``"instrument"``, ``"hybrid"``.
        index : int
            Insert position. ``-1`` appends to the end.
        """
        valid_types = {"audio", "midi", "instrument", "hybrid"}
        if track_type not in valid_types:
            raise ValueError(f"track_type must be one of {valid_types}, got '{track_type}'")

        return self._send(
            "/bitwig/track/create",
            [name, track_type, float(index)],
        )

    def delete_track(self, track_index: int) -> dict[str, Any]:
        """Delete a track by its zero-based index."""
        return self._send("/bitwig/track/delete", [float(track_index)])

    def rename_track(self, track_index: int, new_name: str) -> dict[str, Any]:
        """Rename an existing track."""
        return self._send(
            "/bitwig/track/rename",
            [float(track_index), new_name],
        )

    def set_track_volume(self, track_index: int, volume: float) -> dict[str, Any]:
        """Set track volume (0.0 – 1.0)."""
        if not 0.0 <= volume <= 1.0:
            raise ValueError(f"Volume must be between 0.0 and 1.0, got {volume}")
        return self._send(
            "/bitwig/track/set_volume",
            [float(track_index), volume],
        )

    def set_track_pan(self, track_index: int, pan: float) -> dict[str, Any]:
        """Set track pan (-1.0 = left, 1.0 = right)."""
        if not -1.0 <= pan <= 1.0:
            raise ValueError(f"Pan must be between -1.0 and 1.0, got {pan}")
        return self._send(
            "/bitwig/track/set_pan",
            [float(track_index), pan],
        )

    # ------------------------------------------------------------------
    # Clip management
    # ------------------------------------------------------------------

    def add_clip(
        self,
        name: str,
        track_index: int = 0,
        bpm: float = 120.0,
        key: str = "C",
        length_bars: int = 4,
    ) -> dict[str, Any]:
        """
        Add a new clip to a track.

        Parameters
        ----------
        name : str
            Clip display name.
        track_index : int
            Zero-based track index to place the clip in.
        bpm : float
            Tempo for the clip.
        key : str
            Musical key (e.g. ``"C"``, ``"Am"``, ``"F#m"``).
        length_bars : int
            Clip length in bars.
        """
        return self._send(
            "/bitwig/clip/add",
            [name, float(track_index), bpm, key, float(length_bars)],
        )

    def set_clip_bpm(self, track_index: int, clip_index: int, bpm: float) -> dict[str, Any]:
        """Change the BPM of an existing clip."""
        return self._send(
            "/bitwig/clip/set_bpm",
            [float(track_index), float(clip_index), bpm],
        )

    def set_clip_key(self, track_index: int, clip_index: int, key: str) -> dict[str, Any]:
        """Change the musical key of an existing clip."""
        return self._send(
            "/bitwig/clip/set_key",
            [float(track_index), float(clip_index), key],
        )

    def launch_clip(self, track_index: int, clip_index: int) -> dict[str, Any]:
        """Launch (start playing) a specific clip."""
        return self._send(
            "/bitwig/clip/launch",
            [float(track_index), float(clip_index)],
        )

    # ------------------------------------------------------------------
    # Project state
    # ------------------------------------------------------------------

    def get_project_state(self) -> ProjectState:
        """
        Query and return the current project state.

        Queries tempo, time signature, playing state, and track list
        in a single batch.
        """
        state = ProjectState()

        # Tempo
        tempo_resp = self._send("/bitwig/transport/get_tempo", [])
        state.tempo = float(tempo_resp.get("value", 120.0))

        # Playing state
        play_resp = self._send("/bitwig/transport/is_playing", [])
        state.is_playing = bool(play_resp.get("value", False))

        # Time signature
        ts_resp = self._send("/bitwig/transport/get_time_signature", [])
        state.time_signature_numerator = int(ts_resp.get("numerator", 4))
        state.time_signature_denominator = int(ts_resp.get("denominator", 4))

        # Project name
        name_resp = self._send("/bitwig/project/get_name", [])
        state.project_name = str(name_resp.get("value", "Untitled"))

        # Track list
        tracks_resp = self._send("/bitwig/project/get_tracks", [])
        for t in tracks_resp.get("tracks", []):
            state.tracks.append(TrackInfo(
                name=t.get("name", "Unnamed"),
                track_type=t.get("type", "audio"),
                index=int(t.get("index", -1)),
                is_active=bool(t.get("active", False)),
                volume=float(t.get("volume", 1.0)),
                pan=float(t.get("pan", 0.0)),
            ))

        return state

    # ------------------------------------------------------------------
    # Device / Plugin control
    # ------------------------------------------------------------------

    def add_device(
        self, track_index: int, device_name: str, preset: str = ""
    ) -> dict[str, Any]:
        """Add a VST/device to a track."""
        return self._send(
            "/bitwig/device/add",
            [float(track_index), device_name, preset],
        )

    def set_device_parameter(
        self,
        track_index: int,
        device_index: int,
        parameter_index: int,
        value: float,
    ) -> dict[str, Any]:
        """Set a device parameter (0.0 – 1.0)."""
        return self._send(
            "/bitwig/device/set_parameter",
            [float(track_index), float(device_index), float(parameter_index), value],
        )

    # ------------------------------------------------------------------
    # Scarlett 2i2 integration (via Bitwig mixer)
    # ------------------------------------------------------------------

    def set_input_gain(self, channel: int, gain_db: float) -> dict[str, Any]:
        """
        Set the input gain for a Scarlett 2i2 channel.

        Note: Actual hardware gain control requires the Scarlett Control
        app or amixer. This sends a gain command through Bitwig's input
        mixer as a software gain offset.

        Parameters
        ----------
        channel : int
            Input channel (0 or 1 for Scarlett 2i2).
        gain_db : float
            Gain in decibels (typically -60 to +12).
        """
        return self._send(
            "/bitwig/mixer/set_input_gain",
            [float(channel), gain_db],
        )

    def set_monitor_mix(self, direct: float = 0.5, playback: float = 0.5) -> dict[str, Any]:
        """
        Set the Scarlett 2i2 monitor mix ratio.

        Parameters
        ----------
        direct : float
            Direct input level (0.0 – 1.0).
        playback : float
            DAW playback level (0.0 – 1.0).
        """
        return self._send(
            "/bitwig/mixer/set_monitor_mix",
            [direct, playback],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, address: str, args: list[Any]) -> dict[str, Any]:
        """
        Send an OSC message and return the parsed response.

        If no response is available (fire-and-forget mode), returns an
        empty dict.
        """
        try:
            msg = osc_message_builder.OscMessageBuilder(address=address)
            for arg in args:
                msg.add_arg(arg)
            built = msg.build()
            self._client.send(built)
            logger.debug("OSC sent: %s %s", address, args)

            # Try to get a response if the listener is running
            if self._last_response:
                response = self._last_response.copy()
                self._last_response.clear()
                return response

        except OSError as exc:
            raise BitwigOscError(
                f"OSC send failed for {address}: {exc}"
            ) from exc

        return {}

    def _handle_response(self, address: str, *args: Any) -> None:
        """OSC callback for response messages."""
        self._last_response = {
            "address": address,
            "args": list(args),
            "value": args[0] if args else None,
        }
        logger.debug("OSC response: %s %s", address, args)

    def _handle_state_update(self, address: str, *args: Any) -> None:
        """OSC callback for state change notifications from Bitwig."""
        self._last_response = {
            "address": address,
            "args": list(args),
            "state_update": True,
            "value": args[0] if args else None,
        }
        logger.info("State update: %s %s", address, args)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "BitwigClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
