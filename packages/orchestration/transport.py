"""
HTTP/WebSocket Transport — Real-time communication with auto-reconnection.

Ported from: cli/transports/WebSocketTransport.ts (Claude Code)
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

KEEP_ALIVE_FRAME = '{"type":"keep_alive"}'
DEFAULT_MAX_BUFFER_SIZE = 1000
DEFAULT_BASE_RECONNECT_DELAY = 1.0
DEFAULT_MAX_RECONNECT_DELAY = 30.0
DEFAULT_RECONNECT_GIVE_UP_MS = 600000
DEFAULT_PING_INTERVAL = 10.0
DEFAULT_KEEPALIVE_INTERVAL = 300.0
SLEEP_DETECTION_THRESHOLD_MS = 60000
PERMANENT_CLOSE_CODES = {1002, 4001, 4003}


class TransportState(str, Enum):
    IDLE = "idle"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class TransportOptions:
    """WebSocket transport options."""
    auto_reconnect: bool = True
    is_bridge: bool = False


class CircularBuffer:
    """Fixed-size circular buffer for message replay."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)

    def push(self, item: Any) -> None:
        self.buffer.append(item)

    def get_all(self) -> list:
        return list(self.buffer)

    def clear(self) -> None:
        self.buffer.clear()


class WebSocketTransport:
    """WebSocket transport with auto-reconnection and message buffering."""

    def __init__(
        self,
        url: str,
        headers: Optional[dict] = None,
        session_id: Optional[str] = None,
        refresh_headers: Optional[Callable[[], dict]] = None,
        options: Optional[TransportOptions] = None,
    ):
        self.url = url
        self.headers = headers or {}
        self.session_id = session_id
        self.refresh_headers = refresh_headers
        self.options = options or TransportOptions()

        self.ws: Optional[Any] = None
        self.last_sent_id: Optional[str] = None
        self.state = TransportState.IDLE

        self.on_data: Optional[Callable[[str], None]] = None
        self.on_close_callback: Optional[Callable[[int], None]] = None
        self.on_connect_callback: Optional[Callable[[], None]] = None

        self.reconnect_attempts = 0
        self.reconnect_start_time: Optional[float] = None
        self.reconnect_timer: Optional[threading.Timer] = None
        self.last_reconnect_attempt_time: Optional[float] = None
        self.last_activity_time: float = 0

        self.ping_interval: Optional[threading.Timer] = None
        self.pong_received = True

        self.keepalive_interval: Optional[threading.Timer] = None
        self.message_buffer = CircularBuffer(DEFAULT_MAX_BUFFER_SIZE)

        self._connected = threading.Event()
        self._closed = threading.Event()

    def connect(self, timeout: float = 30.0) -> bool:
        """Connect to WebSocket server."""
        if self.state not in (TransportState.IDLE, TransportState.RECONNECTING):
            logger.debug(f"Cannot connect, state is {self.state.value}")
            return False

        self.state = TransportState.RECONNECTING
        connect_start_time = time.time()

        headers = dict(self.headers)
        if self.last_sent_id:
            headers["X-Last-Request-Id"] = self.last_sent_id

        try:
            self.ws = self._create_websocket(headers)

            if not self._connected.wait(timeout=timeout):
                logger.error("Connection timeout")
                self._cleanup_ws()
                return False

            self._handle_open_event(connect_start_time)
            return True

        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.state = TransportState.CLOSED
            return False

    def _create_websocket(self, headers: dict) -> Any:
        """Create WebSocket connection (ws package)."""
        try:
            import websockets
            return websockets.connect(
                self.url,
                extra_headers=headers,
            )
        except ImportError:
            logger.warning("ws package not available, using HTTP fallback")
            return None

    def _handle_open_event(self, connect_start_time: float) -> None:
        """Handle successful connection."""
        connect_duration = (time.time() - connect_start_time) * 1000
        logger.info(f"Connected after {connect_duration:.0f}ms")

        self.reconnect_attempts = 0
        self.reconnect_start_time = None
        self.last_reconnect_attempt_time = None
        self.last_activity_time = time.time()
        self.state = TransportState.CONNECTED

        if self.on_connect_callback:
            self.on_connect_callback()

        self._start_ping_interval()
        self._start_keepalive_interval()

    def send(self, data: dict) -> bool:
        """Send JSON data over WebSocket."""
        if not self.ws or self.state != TransportState.CONNECTED:
            logger.debug("Not connected")
            return False

        try:
            line = json.dumps(data)
            if hasattr(self.ws, "send"):
                self.ws.send(line)
            else:
                self._http_post(line)
            self.last_activity_time = time.time()
            self.message_buffer.push(data)
            return True
        except Exception as e:
            logger.error(f"Send error: {e}")
            self._handle_connection_error()
            return False

    def _http_post(self, data: str) -> None:
        """HTTP fallback for sending data."""
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler())
            request = urllib.request.Request(
                self.url,
                data=data.encode(),
                headers={**self.headers, "Content-Type": "application/json"},
            )
            opener.open(request, timeout=5)
        except urllib.error.URLError:
            pass

    def _start_ping_interval(self) -> None:
        """Start periodic ping for connection health check."""
        def ping():
            if self.state == TransportState.CONNECTED:
                try:
                    if hasattr(self.ws, "ping"):
                        self.ws.ping()
                    self.pong_received = False
                except Exception:
                    pass

        self.ping_interval = threading.Timer(DEFAULT_PING_INTERVAL, ping)
        self.ping_interval.daemon = True
        self.ping_interval.start()

    def _start_keepalive_interval(self) -> None:
        """Start keep-alive for proxy idle timeout."""
        def keepalive():
            if self.state == TransportState.CONNECTED:
                self.send({"type": "keep_alive"})

        self.keepalive_interval = threading.Timer(
            DEFAULT_KEEPALIVE_INTERVAL,
            keepalive,
        )
        self.keepalive_interval.daemon = True
        self.keepalive_interval.start()

    def _handle_connection_error(self, close_code: int = 0) -> None:
        """Handle connection error with reconnection logic."""
        if close_code in PERMANENT_CLOSE_CODES:
            logger.warning(f"Permanent close: {close_code}")
            self.state = TransportState.CLOSED
            self._cleanup()
            if self.on_close_callback:
                self.on_close_callback(close_code)
            return

        if not self.options.auto_reconnect:
            self.state = TransportState.CLOSED
            self._cleanup()
            return

        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule reconnection with exponential backoff."""
        if self.reconnect_start_time is None:
            self.reconnect_start_time = time.time()

        elapsed = (time.time() - self.reconnect_start_time) * 1000
        if elapsed > DEFAULT_RECONNECT_GIVE_UP_MS:
            logger.error("Reconnection timeout")
            self.state = TransportState.CLOSED
            self._cleanup()
            return

        self.state = TransportState.RECONNECTING

        delay = min(
            DEFAULT_BASE_RECONNECT_DELAY * (2 ** self.reconnect_attempts),
            DEFAULT_MAX_RECONNECT_DELAY,
        )
        if self.last_reconnect_attempt_time:
            gap = time.time() - self.last_reconnect_attempt_time
            if gap > SLEEP_DETECTION_THRESHOLD_MS / 1000:
                self.reconnect_attempts = 0

        self.reconnect_attempts += 1
        self.last_reconnect_attempt_time = time.time()

        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self.reconnect_attempts})")
        self.reconnect_timer = threading.Timer(delay, self._do_reconnect)
        self.reconnect_timer.daemon = True
        self.reconnect_timer.start()

    def _do_reconnect(self) -> None:
        """Attempt reconnection."""
        if self.connect(timeout=10.0):
            self._replay_buffered_messages()

    def _replay_buffered_messages(self) -> None:
        """Replay buffered messages on reconnection."""
        for msg in self.message_buffer.get_all():
            self.send(msg)

    def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        self.state = TransportState.CLOSING
        self._cleanup()
        self.state = TransportState.CLOSED
        logger.info("Disconnected")

    def _cleanup(self) -> None:
        """Clean up resources."""
        self._cleanup_ws()
        self._cleanup_timers()
        if self.on_close_callback:
            self.on_close_callback(0)

    def _cleanup_ws(self) -> None:
        """Clean up WebSocket."""
        if self.ws:
            try:
                if hasattr(self.ws, "close"):
                    self.ws.close()
            except Exception:
                pass
            self.ws = None

    def _cleanup_timers(self) -> None:
        """Clean up timers."""
        for timer in (self.ping_interval, self.keepalive_interval, self.reconnect_timer):
            if timer:
                timer.cancel()
        self.ping_interval = None
        self.keepalive_interval = None
        self.reconnect_timer = None

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.state == TransportState.CONNECTED


class HTTPTransport:
    """HTTP transport fallback (no WebSocket)."""

    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers or {}

    def get(self, path: str = "", timeout: float = 30.0) -> Optional[dict]:
        """HTTP GET request."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            logger.error(f"GET error: {e}")
            return None

    def post(
        self,
        path: str,
        data: Optional[dict] = None,
        timeout: float = 30.0,
    ) -> Optional[dict]:
        """HTTP POST request."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            body = json.dumps(data).encode() if data else None
            request = urllib.request.Request(
                url,
                data=body,
                headers={**self.headers, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            logger.error(f"POST error: {e}")
            return None


def create_transport(
    url: str,
    headers: Optional[dict] = None,
    session_id: Optional[str] = None,
    options: Optional[TransportOptions] = None,
) -> WebSocketTransport:
    """Create transport (CLI entry point)."""
    if url.startswith("ws://") or url.startswith("wss://"):
        return WebSocketTransport(url, headers, session_id, options=options)
    return HTTPTransport(url, headers)


__all__ = [
    "TransportState",
    "TransportOptions",
    "CircularBuffer",
    "WebSocketTransport",
    "HTTPTransport",
    "create_transport",
]