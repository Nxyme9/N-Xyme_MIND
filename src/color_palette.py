"""Color Palette — Extract color palettes from images"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ColorPalette:
    def extract(self, image_path: str, num_colors: int = 5) -> Dict:
        try:
            from PIL import Image
            import numpy as np

            img = Image.open(image_path).convert("RGB")
            img = img.resize((100, 100))
            pixels = np.array(img).reshape(-1, 3)
            from sklearn.cluster import KMeans

            kmeans = KMeans(n_clusters=num_colors, n_init=10)
            kmeans.fit(pixels)
            colors = []
            for center in kmeans.cluster_centers_:
                r, g, b = int(center[0]), int(center[1]), int(center[2])
                colors.append({"rgb": [r, g, b], "hex": f"#{r:02x}{g:02x}{b:02x}"})
            return {"colors": colors, "num_colors": num_colors}
        except ImportError:
            return {"error": "Pillow/sklearn not installed"}
