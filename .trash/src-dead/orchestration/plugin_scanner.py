"""Plugin Scanner — Scan and catalog plugins/modules"""

import logging, importlib, pkgutil
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class PluginScanner:
    def __init__(self, scan_dirs: List[str] = None):
        self.scan_dirs = scan_dirs or ["src"]

    def scan(self) -> Dict[str, List[str]]:
        results = {}
        for scan_dir in self.scan_dirs:
            path = Path(scan_dir)
            if path.exists():
                modules = []
                for py_file in path.glob("*.py"):
                    if py_file.stem != "__init__":
                        modules.append(py_file.stem)
                results[scan_dir] = sorted(modules)
        return results

    def get_module_info(self, module_name: str) -> Dict:
        try:
            module = importlib.import_module(f"src.{module_name}")
            classes = [name for name, obj in vars(module).items() if isinstance(obj, type)]
            functions = [
                name
                for name, obj in vars(module).items()
                if callable(obj) and not isinstance(obj, type)
            ]
            return {"module": module_name, "classes": classes, "functions": functions}
        except Exception as e:
            return {"module": module_name, "error": str(e)}
