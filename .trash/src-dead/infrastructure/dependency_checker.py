"""Dependency Checker — Check Python package dependencies"""

import importlib, logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DependencyChecker:
    REQUIRED = ["httpx", "requests", "numpy"]
    OPTIONAL = [
        "librosa",
        "soundfile",
        "Pillow",
        "cryptography",
        "scipy",
        "mido",
        "psutil",
        "pydantic",
    ]

    def check_all(self) -> Dict:
        results = {"required": {}, "optional": {}}
        for pkg in self.REQUIRED:
            results["required"][pkg] = self._check(pkg)
        for pkg in self.OPTIONAL:
            results["optional"][pkg] = self._check(pkg)
        return results

    def _check(self, package: str) -> Dict:
        try:
            importlib.import_module(package.replace("-", "_"))
            return {"installed": True, "status": "ok"}
        except ImportError:
            return {"installed": False, "status": "missing"}

    def get_missing(self) -> List[str]:
        results = self.check_all()
        missing = []
        for pkg, info in results["required"].items():
            if not info["installed"]:
                missing.append(pkg)
        return missing
