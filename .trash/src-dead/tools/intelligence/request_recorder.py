"""Request Recording/Replay (VCR) — API request recording and replay.

Ported from ant-source-code-main/services/vcr.ts
Implements API request recording and replay for:
- Debugging API interactions
- Testing without hitting real APIs
- Replaying conversations for analysis
- Privacy controls (redact sensitive data)

Pattern: Records all API requests and responses, enabling replay,
debugging, and testing without network calls.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Default VCR storage path
DEFAULT_VCR_PATH = Path(".sisyphus/vcr")

# Sensitive data patterns to redact
SENSITIVE_PATTERNS = [
    r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[\w-]+",
    r"token['\"]?\s*[:=]\s*['\"]?[\w-]+",
    r"password['\"]?\s*[:=]\s*['\"]?[\w-]+",
    r"secret['\"]?\s*[:=]\s*['\"]?[\w-]+",
    r"authorization['\"]?\s*[:=]\s*['\"]?Bearer\s+[\w-]+",
]


@dataclass
class RecordedRequest:
    """A recorded API request."""

    id: str
    method: str
    url: str
    headers: dict[str, str]
    body: str | None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    duration_ms: float = 0.0
    status_code: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str | None = None
    error: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Generate a fingerprint for this request (for matching during replay)."""
        content = f"{self.method}:{self.url}:{self.body or ''}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "body": self.body,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "status_code": self.status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "error": self.error,
            "tags": self.tags,
            "metadata": self.metadata,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecordedRequest":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            method=data["method"],
            url=data["url"],
            headers=data.get("headers", {}),
            body=data.get("body"),
            timestamp=data.get("timestamp", ""),
            duration_ms=data.get("duration_ms", 0.0),
            status_code=data.get("status_code"),
            response_headers=data.get("response_headers", {}),
            response_body=data.get("response_body"),
            error=data.get("error"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class VCRRecorder:
    """Video Cassette Recorder for API requests."""

    def __init__(
        self,
        storage_path: Path | None = None,
        mode: str = "record",  # "record", "replay", "record-replay"
        redact_sensitive: bool = True,
    ):
        """Initialize VCR recorder.

        Args:
            storage_path: Path to store recordings.
            mode: Recording mode:
                - "record": Only record new requests
                - "replay": Only replay recorded requests
                - "record-replay": Record if not found, otherwise replay
            redact_sensitive: Whether to redact sensitive data.
        """
        self.storage_path = storage_path or DEFAULT_VCR_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.mode = mode
        self.redact_sensitive = redact_sensitive
        self.recordings: dict[str, RecordedRequest] = {}
        self._is_recording = True
        self._load_recordings()

    def start_recording(self) -> None:
        """Start recording requests."""
        self._is_recording = True

    def stop_recording(self) -> None:
        """Stop recording requests."""
        self._is_recording = False

    def record_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        status_code: int | None = None,
        response_headers: dict[str, str] | None = None,
        response_body: str | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RecordedRequest:
        """Record an API request and response.

        Args:
            method: HTTP method.
            url: Request URL.
            headers: Request headers.
            body: Request body.
            status_code: Response status code.
            response_headers: Response headers.
            response_body: Response body.
            error: Error message if any.
            duration_ms: Request duration in milliseconds.
            tags: Optional tags.
            metadata: Optional metadata.

        Returns:
            RecordedRequest object.
        """
        import uuid

        request = RecordedRequest(
            id=str(uuid.uuid4())[:8],
            method=method,
            url=url,
            headers=headers or {},
            body=body,
            status_code=status_code,
            response_headers=response_headers or {},
            response_body=response_body,
            error=error,
            duration_ms=duration_ms,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Redact sensitive data if enabled
        if self.redact_sensitive:
            request = self._redact_sensitive(request)

        # Store recording
        self.recordings[request.fingerprint] = request
        self._save_recording(request)

        logger.info(f"Recorded request: {method} {url} ({status_code})")
        return request

    def replay_request(
        self,
        method: str,
        url: str,
        body: str | None = None,
    ) -> RecordedRequest | None:
        """Find and return a recorded request matching the given parameters.

        Args:
            method: HTTP method.
            url: Request URL.
            body: Request body.

        Returns:
            RecordedRequest if found, None otherwise.
        """
        # Create a temporary request to generate fingerprint
        temp_request = RecordedRequest(
            id="temp",
            method=method,
            url=url,
            headers={},
            body=body,
        )
        fingerprint = temp_request.fingerprint

        recording = self.recordings.get(fingerprint)
        if recording:
            logger.info(f"Replayed request: {method} {url}")
            return recording

        logger.warning(f"No recording found for: {method} {url}")
        return None

    def handle_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        real_request_fn: Callable | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RecordedRequest:
        """Handle a request based on current mode.

        In "record" mode: executes real request and records it.
        In "replay" mode: returns recorded response if found.
        In "record-replay" mode: replays if found, otherwise records.

        Args:
            method: HTTP method.
            url: Request URL.
            headers: Request headers.
            body: Request body.
            real_request_fn: Function to execute real request.
            tags: Optional tags.
            metadata: Optional metadata.

        Returns:
            RecordedRequest with response.
        """
        # Try to replay first
        if self.mode in ("replay", "record-replay"):
            recording = self.replay_request(method, url, body)
            if recording:
                return recording

        # If in replay-only mode and no recording found
        if self.mode == "replay":
            raise ValueError(
                f"No recording found for {method} {url} and mode is 'replay'"
            )

        # Execute real request
        if real_request_fn is None:
            raise ValueError("real_request_fn required for recording mode")

        start_time = time.time() * 1000
        try:
            response = real_request_fn()
            duration_ms = time.time() * 1000 - start_time

            return self.record_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                status_code=response.get("status_code"),
                response_headers=response.get("headers", {}),
                response_body=response.get("body"),
                duration_ms=duration_ms,
                tags=tags,
                metadata=metadata,
            )
        except Exception as e:
            duration_ms = time.time() * 1000 - start_time
            return self.record_request(
                method=method,
                url=url,
                headers=headers,
                body=body,
                error=str(e),
                duration_ms=duration_ms,
                tags=tags,
                metadata=metadata,
            )

    def _redact_sensitive(self, request: RecordedRequest) -> RecordedRequest:
        """Redact sensitive data from request."""
        import re

        redacted = RecordedRequest(
            id=request.id,
            method=request.method,
            url=request.url,
            headers=dict(request.headers),
            body=request.body,
            timestamp=request.timestamp,
            duration_ms=request.duration_ms,
            status_code=request.status_code,
            response_headers=dict(request.response_headers),
            response_body=request.response_body,
            error=request.error,
            tags=list(request.tags),
            metadata=dict(request.metadata),
        )

        # Redact sensitive headers
        sensitive_headers = {"authorization", "cookie", "x-api-key", "x-auth-token"}
        for header in sensitive_headers:
            if header in redacted.headers:
                redacted.headers[header] = "[REDACTED]"

        # Redact sensitive patterns in body
        if redacted.body:
            for pattern in SENSITIVE_PATTERNS:
                redacted.body = re.sub(
                    pattern, "[REDACTED]", redacted.body, flags=re.IGNORECASE
                )

        return redacted

    def _save_recording(self, request: RecordedRequest) -> None:
        """Save recording to storage."""
        recording_file = self.storage_path / f"{request.fingerprint}.json"
        recording_file.write_text(json.dumps(request.to_dict(), indent=2))

    def _load_recordings(self) -> None:
        """Load recordings from storage."""
        for recording_file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(recording_file.read_text())
                request = RecordedRequest.from_dict(data)
                self.recordings[request.fingerprint] = request
            except Exception as e:
                logger.warning(f"Failed to load recording {recording_file}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get VCR statistics."""
        by_status: dict[str, int] = {}
        by_method: dict[str, int] = {}
        total_duration = 0.0

        for recording in self.recordings.values():
            status = str(recording.status_code) if recording.status_code else "error"
            by_status[status] = by_status.get(status, 0) + 1
            by_method[recording.method] = by_method.get(recording.method, 0) + 1
            total_duration += recording.duration_ms

        return {
            "total_recordings": len(self.recordings),
            "by_status": by_status,
            "by_method": by_method,
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / max(1, len(self.recordings)),
            "mode": self.mode,
            "is_recording": self._is_recording,
        }

    def clear_recordings(self) -> int:
        """Clear all recordings.

        Returns:
            Number of recordings cleared.
        """
        count = len(self.recordings)
        for recording_file in self.storage_path.glob("*.json"):
            recording_file.unlink()
        self.recordings.clear()
        return count


# Global singleton
_vcr = VCRRecorder()


def record_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
    status_code: int | None = None,
    response_body: str | None = None,
    error: str | None = None,
    duration_ms: float = 0.0,
    tags: list[str] | None = None,
) -> RecordedRequest:
    """Convenience function to record a request."""
    return _vcr.record_request(
        method,
        url,
        headers,
        body,
        status_code,
        response_body=response_body,
        error=error,
        duration_ms=duration_ms,
        tags=tags,
    )


def replay_request(
    method: str,
    url: str,
    body: str | None = None,
) -> RecordedRequest | None:
    """Convenience function to replay a request."""
    return _vcr.replay_request(method, url, body)


def get_vcr_stats() -> dict[str, Any]:
    """Convenience function to get VCR stats."""
    return _vcr.get_stats()
