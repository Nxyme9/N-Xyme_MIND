"""
Clipboard Handler — Detect clipboard content type and route appropriately

Handles images, text, and files from clipboard.

Usage:
    handler = ClipboardHandler()
    content = handler.detect()
    result = handler.process(content)
"""

import base64
import logging
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Clipboard content types."""

    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    HTML = "html"
    UNKNOWN = "unknown"


@dataclass
class ClipboardContent:
    """Detected clipboard content."""

    content_type: ContentType
    data: Any
    mime_type: str
    size_bytes: int
    filename: Optional[str] = None


class ClipboardHandler:
    """Detect and process clipboard content."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        vision_model: str = "llava:7b",
    ):
        self.ollama_url = ollama_url
        self.vision_model = vision_model
        self._http_client = None
        logger.info(f"ClipboardHandler: Initialized (vision={vision_model})")

    def _get_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def detect(self) -> Optional[ClipboardContent]:
        """Detect what's in clipboard."""
        try:
            # Try to get clipboard image (Windows)
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-Clipboard -Format Image -ErrorAction SilentlyContinue | Out-Null; if ($?) { 'IMAGE' } else { 'TEXT' }",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            content_type_str = result.stdout.strip()

            if content_type_str == "IMAGE":
                return self._get_image_from_clipboard()
            else:
                return self._get_text_from_clipboard()
        except Exception as e:
            logger.error(f"ClipboardHandler: Detection failed: {e}")
            return None

    def _get_image_from_clipboard(self) -> Optional[ClipboardContent]:
        """Get image from clipboard."""
        try:
            # Save clipboard image to temp file
            import tempfile

            temp_path = Path(tempfile.gettempdir()) / "clipboard_image.png"

            # PowerShell to save clipboard image
            ps_script = f"""
            $img = Get-Clipboard -Format Image
            if ($img) {{
                $img.Save('{temp_path}')
                Write-Output 'SAVED'
            }} else {{
                Write-Output 'NO_IMAGE'
            }}
            """
            result = subprocess.run(
                ["powershell", "-Command", ps_script], capture_output=True, text=True, timeout=10
            )

            if "SAVED" in result.stdout and temp_path.exists():
                with open(temp_path, "rb") as f:
                    image_data = f.read()

                return ClipboardContent(
                    content_type=ContentType.IMAGE,
                    data=base64.b64encode(image_data).decode(),
                    mime_type="image/png",
                    size_bytes=len(image_data),
                    filename="clipboard_image.png",
                )
        except Exception as e:
            logger.error(f"ClipboardHandler: Image extraction failed: {e}")

        return None

    def _get_text_from_clipboard(self) -> Optional[ClipboardContent]:
        """Get text from clipboard."""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard -Raw"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            text = result.stdout.strip()

            if text:
                return ClipboardContent(
                    content_type=ContentType.TEXT,
                    data=text,
                    mime_type="text/plain",
                    size_bytes=len(text.encode()),
                )
        except Exception as e:
            logger.error(f"ClipboardHandler: Text extraction failed: {e}")

        return None

    def process(self, content: ClipboardContent) -> Dict:
        """Process clipboard content appropriately."""
        if content.content_type == ContentType.IMAGE:
            return self._process_image(content)
        elif content.content_type == ContentType.TEXT:
            return self._process_text(content)
        else:
            return {"error": f"Unsupported content type: {content.content_type}"}

    def _process_image(self, content: ClipboardContent) -> Dict:
        """Process image using vision model."""
        try:
            client = self._get_client()

            # Call llava for image description
            resp = client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": "Describe this image in detail. What do you see?",
                    "images": [content.data],
                    "stream": False,
                },
                timeout=60,
            )
            resp.raise_for_status()
            description = resp.json().get("response", "")

            return {
                "type": "image",
                "description": description,
                "size_bytes": content.size_bytes,
                "model_used": self.vision_model,
                "suggestion": f"Image detected ({content.size_bytes} bytes). Here's what I see:\n\n{description}",
            }
        except Exception as e:
            logger.error(f"ClipboardHandler: Image processing failed: {e}")
            return {"type": "image", "error": str(e)}

    def _process_text(self, content: ClipboardContent) -> Dict:
        """Process text content."""
        return {
            "type": "text",
            "data": content.data,
            "size_bytes": content.size_bytes,
        }

    def route_content(self, content: ClipboardContent) -> str:
        """Route content to appropriate agent/model."""
        if content.content_type == ContentType.IMAGE:
            return "multimodal-looker"  # Route to vision agent
        elif content.content_type == ContentType.TEXT:
            if len(content.data) > 1000:
                return "explore"  # Long text = code/search
            else:
                return "main"  # Short text = normal chat
        else:
            return "main"

    def close(self):
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()
