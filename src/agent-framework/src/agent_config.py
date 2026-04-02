import yaml
from pathlib import Path
from typing import Dict, Any, List
import jsonschema


class AgentConfig:
    """Load and validate agent configurations from YAML files."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validate()

    @classmethod
    def load(cls, filepath: str) -> "AgentConfig":
        """Load agent configuration from a YAML file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Agent config not found: {filepath}")

        with open(path, "r") as f:
            config = yaml.safe_load(f)
        return cls(config)

    def validate(self):
        """Validate the agent configuration against schema."""
        schema = {
            "type": "object",
            "required": [
                "name",
                "description",
                "type",
                "version",
                "author",
                "capabilities",
                "config",
                "permissions",
                "skills",
            ],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "type": {"type": "string"},
                "version": {"type": "string"},
                "author": {"type": "string"},
                "capabilities": {"type": "array", "items": {"type": "string"}},
                "config": {"type": "object"},
                "permissions": {"type": "array", "items": {"type": "string"}},
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "description"],
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                        },
                    },
                },
            },
        }
        try:
            jsonschema.validate(instance=self.config, schema=schema)
        except jsonschema.ValidationError as e:
            raise ValueError(f"Invalid agent configuration: {e}")

    def get_name(self) -> str:
        return self.config["name"]

    def get_type(self) -> str:
        return self.config["type"]

    def get_capabilities(self) -> List[str]:
        return self.config["capabilities"]

    def get_permissions(self) -> List[str]:
        return self.config["permissions"]

    def get_skills(self) -> List[Dict[str, str]]:
        return self.config["skills"]

    def get_config(self) -> Dict[str, Any]:
        return self.config["config"]

    def __repr__(self):
        return f"<AgentConfig name={self.get_name()} type={self.get_type()}>"
