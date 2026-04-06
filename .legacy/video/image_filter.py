"""Image Filter — Apply filters to images"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ImageFilter:
    def apply(self, image_path: str, filter_type: str, output_path: str) -> Dict:
        try:
            from PIL import Image, ImageFilter

            img = Image.open(image_path)
            filters = {
                "blur": ImageFilter.GaussianBlur(radius=2),
                "sharpen": ImageFilter.SHARPEN,
                "edge": ImageFilter.FIND_EDGES,
                "emboss": ImageFilter.EMBOSS,
                "contour": ImageFilter.CONTOUR,
                "grayscale": None,
            }
            if filter_type == "grayscale":
                img = img.convert("L").convert("RGB")
            elif filter_type in filters:
                img = img.filter(filters[filter_type])
            img.save(output_path)
            return {"success": True, "output": output_path}
        except ImportError:
            return {"success": False, "error": "Pillow not installed"}
