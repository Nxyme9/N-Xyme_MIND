"""GIF Creator — Create animated GIFs"""

import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class GIFCreator:
    def create(
        self, image_paths: List[str], output_path: str, duration_ms: int = 100, loop: int = 0
    ) -> Dict:
        try:
            from PIL import Image

            images = [Image.open(p) for p in image_paths if Path(p).exists()]
            if not images:
                return {"success": False, "error": "No images found"}
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                duration=duration_ms,
                loop=loop,
                optimize=True,
            )
            return {"success": True, "output": output_path, "frames": len(images)}
        except ImportError:
            return {"success": False, "error": "Pillow not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
