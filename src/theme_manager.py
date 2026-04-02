"""Theme Manager — UI theme management"""

import json, logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

THEMES = {
    "dark": {"bg": "#1a1a2e", "fg": "#eaeaea", "accent": "#0f3460", "highlight": "#e94560"},
    "light": {"bg": "#ffffff", "fg": "#333333", "accent": "#007bff", "highlight": "#ff6b6b"},
    "monokai": {"bg": "#272822", "fg": "#f8f8f2", "accent": "#a6e22e", "highlight": "#f92672"},
    "nord": {"bg": "#2e3440", "fg": "#eceff4", "accent": "#88c0d0", "highlight": "#bf616a"},
}


class ThemeManager:
    def __init__(self, theme_dir: str = "data/themes"):
        self.theme_dir = Path(theme_dir)
        self.theme_dir.mkdir(parents=True, exist_ok=True)
        self._current = "dark"

    def get_theme(self, name: str = None) -> Dict:
        name = name or self._current
        if name in THEMES:
            return THEMES[name]
        path = self.theme_dir / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return THEMES["dark"]

    def set_theme(self, name: str):
        self._current = name

    def list_themes(self) -> List[str]:
        return list(THEMES.keys()) + [f.stem for f in self.theme_dir.glob("*.json")]

    def save_theme(self, name: str, colors: Dict):
        (self.theme_dir / f"{name}.json").write_text(json.dumps(colors, indent=2), encoding="utf-8")
