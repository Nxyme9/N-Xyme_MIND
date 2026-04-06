"""Model serialization and versioning for learning-engine."""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Optional


class ModelSerializer:
    """Handles serialization and deserialization of learned models."""
    
    @staticmethod
    def to_json(model: Any) -> str:
        """Serialize model to JSON string."""
        if hasattr(model, 'to_json'):
            return model.to_json()
        # Fallback: use pickle then base64 encode
        return pickle.dumps(model).hex()
    
    @staticmethod
    def from_json(data: str, model_class: type) -> Any:
        """Deserialize model from JSON string."""
        try:
            # Try JSON first
            return json.loads(data)
        except json.JSONDecodeError:
            # Fallback: try hex-encoded pickle
            return pickle.loads(bytes.fromhex(data))
    
    @staticmethod
    def save_to_file(model: Any, path: Path) -> None:
        """Save model to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(ModelSerializer.to_json(model))
    
    @staticmethod
    def load_from_file(path: Path, model_class: type) -> Any:
        """Load model from file."""
        with open(path, 'r') as f:
            data = f.read()
        return ModelSerializer.from_json(data, model_class)


class ModelVersioning:
    """Version control for learned models."""
    
    def __init__(self, versions_dir: Path | None = None):
        self._versions_dir = versions_dir or Path("context/memory/model_versions")
        self._versions_dir.mkdir(parents=True, exist_ok=True)
        self._versions: dict[str, list[dict]] = {}
    
    def save_version(self, model_name: str, model: Any, metadata: dict | None = None) -> str:
        """Save a new version of a model."""
        import time
        
        version_id = f"v{int(time.time() * 1000)}"
        
        if model_name not in self._versions:
            self._versions[model_name] = []
        
        version_info = {
            "version_id": version_id,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        
        # Save model to version file
        model_path = self._versions_dir / f"{model_name}_{version_id}.json"
        ModelSerializer.save_to_file(model, model_path)
        
        self._versions[model_name].append(version_info)
        return version_id
    
    def get_versions(self, model_name: str) -> list[dict]:
        """Get all versions of a model."""
        return self._versions.get(model_name, [])
    
    def load_version(self, model_name: str, version_id: str) -> Optional[Any]:
        """Load a specific version of a model."""
        model_path = self._versions_dir / f"{model_name}_{version_id}.json"
        if not model_path.exists():
            return None
        
        # Determine model class from model_name
        # This is a placeholder - actual implementation would store class info
        return ModelSerializer.load_from_file(model_path, dict)


class ModelRollback:
    """Rollback capabilities for models."""
    
    def __init__(self, versioning: ModelVersioning):
        self._versioning = versioning
    
    def rollback(self, model_name: str, target_version: str) -> bool:
        """Rollback model to a previous version."""
        model = self._versioning.load_version(model_name, target_version)
        if model is None:
            return False
        
        # Save current as a new version before rollback
        # (In real implementation, would load current model first)
        return True