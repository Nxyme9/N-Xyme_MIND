"""Demucs Separator — Audio source separation"""

import logging, subprocess
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class DemucsSeparator:
    def __init__(self, output_dir: str = "data/separated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def separate(self, audio_path: str, model: str = "htdemucs") -> Dict:
        try:
            result = subprocess.run(
                ["python", "-m", "demucs", "-n", model, "-o", str(self.output_dir), audio_path],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0:
                output_path = self.output_dir / model / Path(audio_path).stem
                return {
                    "success": True,
                    "output_dir": str(output_path),
                    "stems": ["vocals", "drums", "bass", "other"],
                }
            return {"success": False, "error": result.stderr}
        except FileNotFoundError:
            return {"success": False, "error": "demucs not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
