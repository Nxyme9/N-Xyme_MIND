"""
athena.core.edge_node
=====================

iOS Edge Node Webhook for the Bionic Unit sensor network.
Extracted from OpenClaw's Gateway/Node topology ("The Great Steal 2.0").

Architecture:
  [iOS Shortcut] --(HTTP POST)--> [athenad /ingest] --(Filesystem)--> [.context/ingest/]

Accepts camera, location, voice, and text payloads from any HTTP client.
Designed to be triggered by iOS Shortcuts, curl, or any webhook source.
"""

import base64
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from pydantic import BaseModel

from athena.core.config import get_project_root

logger = logging.getLogger("athenad")

PROJECT_ROOT = get_project_root()
INGEST_DIR = PROJECT_ROOT / ".context" / "ingest"


# --- Pydantic Models ---


class IngestPayload(BaseModel):
    type: str  # camera, location, voice, text
    data: str  # base64 for binary, raw string for text/location
    metadata: Optional[Dict[str, Any]] = None


class IngestResponse(BaseModel):
    status: str
    type: str
    file_path: str
    timestamp: float


# --- Processing Logic ---


def _ensure_ingest_dir():
    """Create ingest directory if it doesn't exist."""
    INGEST_DIR.mkdir(parents=True, exist_ok=True)


def _timestamp_prefix() -> str:
    """Generate a sortable timestamp prefix for filenames."""
    return time.strftime("%Y%m%d-%H%M%S")


def process_ingest(payload: IngestPayload) -> IngestResponse:
    """
    Route and save an ingest payload by type.

    Supported types:
      - camera: base64-encoded image → .jpg
      - voice:  base64-encoded audio → .m4a
      - location: JSON string with lat/lng → .json
      - text: raw string → .md
    """
    _ensure_ingest_dir()
    prefix = _timestamp_prefix()
    source = "unknown"
    if payload.metadata and "source" in payload.metadata:
        source = payload.metadata["source"]

    now = time.time()

    if payload.type == "camera":
        filename = f"{prefix}-camera-{source}.jpg"
        filepath = INGEST_DIR / filename
        image_data = base64.b64decode(payload.data)
        filepath.write_bytes(image_data)
        logger.info(f"📸 Camera ingest saved: {filename} ({len(image_data)} bytes)")

    elif payload.type == "voice":
        filename = f"{prefix}-voice-{source}.m4a"
        filepath = INGEST_DIR / filename
        audio_data = base64.b64decode(payload.data)
        filepath.write_bytes(audio_data)
        logger.info(f"🎙️ Voice ingest saved: {filename} ({len(audio_data)} bytes)")

    elif payload.type == "location":
        filename = f"{prefix}-location-{source}.json"
        filepath = INGEST_DIR / filename
        # Data should be a JSON string with lat/lng
        location_data = {
            "raw": payload.data,
            "metadata": payload.metadata or {},
            "ingested_at": now,
        }
        filepath.write_text(json.dumps(location_data, indent=2), encoding="utf-8")
        logger.info(f"📍 Location ingest saved: {filename}")

    elif payload.type == "text":
        filename = f"{prefix}-capture-{source}.md"
        filepath = INGEST_DIR / filename
        content = f"# Quick Capture\n\n"
        content += f"> Ingested: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"> Source: {source}\n\n"
        content += payload.data
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"📝 Text ingest saved: {filename}")

    else:
        # Fallback: save raw data as .bin
        filename = f"{prefix}-raw-{payload.type}.bin"
        filepath = INGEST_DIR / filename
        filepath.write_text(payload.data, encoding="utf-8")
        logger.info(f"📦 Raw ingest saved: {filename}")

    return IngestResponse(
        status="saved",
        type=payload.type,
        file_path=str(filepath),
        timestamp=now,
    )
