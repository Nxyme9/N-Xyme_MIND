"""
BMAD Configuration Module
Provides access to BMAD manifests and configuration.
"""

import os
import csv
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent


def get_skill_manifest():
    """Load and return skill manifest as list of dicts."""
    manifest_path = _CONFIG_DIR / "skill-manifest.csv"
    with open(manifest_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_workflow_manifest():
    """Load and return workflow manifest."""
    manifest_path = _CONFIG_DIR / "workflow-manifest.csv"
    with open(manifest_path, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)


# Re-export for convenience
manifest = {"skills": get_skill_manifest(), "workflows": get_workflow_manifest()}
