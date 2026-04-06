"""Preset Manager — CRUD for presets"""

import json, logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PresetManager:
    def __init__(self, preset_dir: str = "data/presets"):
        self.preset_dir = Path(preset_dir)
        self.preset_dir.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, data: Dict, category: str = "default"):
        path = self.preset_dir / category
        path.mkdir(exist_ok=True)
        (path / f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"PresetManager: Saved '{name}' in '{category}'")

    def load(self, name: str, category: str = "default") -> Optional[Dict]:
        path = self.preset_dir / category / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    def list_presets(self, category: str = "default") -> List[str]:
        path = self.preset_dir / category
        if not path.exists():
            return []
        return [f.stem for f in path.glob("*.json")]

    def list_categories(self) -> List[str]:
        return [d.name for d in self.preset_dir.iterdir() if d.is_dir()]

    def delete(self, name: str, category: str = "default") -> bool:
        path = self.preset_dir / category / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False
