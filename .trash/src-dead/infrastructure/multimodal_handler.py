"""Multimodal Handler — Process multiple input types"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class MultimodalHandler:
    def __init__(self):
        self._processors = {}

    def register_processor(self, input_type: str, processor):
        self._processors[input_type] = processor

    def process(self, input_type: str, data) -> Dict:
        processor = self._processors.get(input_type)
        if not processor:
            return {"error": f"No processor for '{input_type}'"}
        try:
            return processor(data)
        except Exception as e:
            return {"error": str(e)}

    def detect_type(self, data) -> str:
        if isinstance(data, str):
            if data.endswith((".jpg", ".png", ".gif", ".bmp")):
                return "image"
            elif data.endswith((".mp3", ".wav", ".flac")):
                return "audio"
            elif data.endswith((".mp4", ".avi", ".mkv")):
                return "video"
            return "text"
        return "unknown"

    def list_types(self) -> List[str]:
        return list(self._processors.keys())
