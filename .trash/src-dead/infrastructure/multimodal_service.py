"""
Multimodal Service — Image understanding via Ollama llava

Uses local llava:7b model for image analysis.

Usage:
    service = MultimodalService()
    result = service.analyze_image("photo.jpg")
    print(result.description)
"""

import base64
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ImageAnalysisResult:
    """Image analysis result."""

    description: str
    tags: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    text_content: Optional[str] = None
    model: str = "llava:7b"
    confidence: float = 0.0


class MultimodalService:
    """Image understanding via Ollama llava."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llava:7b",
    ):
        self.ollama_url = ollama_url
        self.model = model
        self._http_client = None
        logger.info(f"MultimodalService: Initialized (model={model})")

    def _get_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=60.0)
        return self._http_client

    def analyze_image(
        self,
        image_path: str,
        prompt: str = "Describe what you see in this image in detail.",
    ) -> ImageAnalysisResult:
        """Analyze an image using llava."""
        client = self._get_client()

        # Read and encode image
        image_data = self._read_image(image_path)
        if not image_data:
            return ImageAnalysisResult(
                description="Failed to read image",
                model=self.model,
            )

        # Call llava
        try:
            resp = client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()
            description = result.get("response", "")

            # Extract tags from description
            tags = self._extract_tags(description)
            objects = self._extract_objects(description)

            return ImageAnalysisResult(
                description=description,
                tags=tags,
                objects=objects,
                model=self.model,
                confidence=0.8,
            )
        except Exception as e:
            logger.error(f"MultimodalService: Analysis failed: {e}")
            return ImageAnalysisResult(
                description=f"Analysis failed: {e}",
                model=self.model,
            )

    def describe_image(self, image_path: str) -> str:
        """Get simple description of image."""
        result = self.analyze_image(image_path)
        return result.description

    def extract_text(self, image_path: str) -> Optional[str]:
        """Extract text from image (OCR)."""
        result = self.analyze_image(
            image_path,
            prompt="Extract all text visible in this image. Return only the text, no description.",
        )
        return result.description if result.description else None

    def identify_objects(self, image_path: str) -> List[str]:
        """Identify objects in image."""
        result = self.analyze_image(
            image_path,
            prompt="List all objects visible in this image. Return as comma-separated list.",
        )
        return [o.strip() for o in result.description.split(",") if o.strip()]

    def _read_image(self, image_path: str) -> Optional[str]:
        """Read and base64 encode image."""
        try:
            path = Path(image_path)
            if not path.exists():
                logger.error(f"MultimodalService: Image not found: {image_path}")
                return None

            with open(path, "rb") as f:
                image_bytes = f.read()

            return base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"MultimodalService: Failed to read image: {e}")
            return None

    def _extract_tags(self, description: str) -> List[str]:
        """Extract tags from description."""
        # Simple keyword extraction
        keywords = [
            "person",
            "people",
            "car",
            "building",
            "tree",
            "animal",
            "dog",
            "cat",
            "food",
            "table",
            "chair",
            "computer",
            "phone",
            "screen",
            "text",
            "logo",
            "indoor",
            "outdoor",
            "night",
            "day",
            "city",
            "nature",
            "water",
            "sky",
        ]
        desc_lower = description.lower()
        return [kw for kw in keywords if kw in desc_lower]

    def _extract_objects(self, description: str) -> List[str]:
        """Extract objects from description."""
        # Simple extraction - look for "I see" or "contains" patterns
        objects = []
        if "I see" in description:
            parts = description.split("I see")
            for part in parts[1:]:
                objects.extend(part.split(",")[:3])
        return [o.strip()[:50] for o in objects if o.strip()][:10]

    def close(self):
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()


def create_catalyst_multimodal() -> MultimodalService:
    """Create multimodal service for Catalyst."""
    return MultimodalService(
        ollama_url="http://localhost:11434",
        model="llava:7b",
    )
