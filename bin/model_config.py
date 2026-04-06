"""Model configuration loader with environment variable fallback defaults.

This module provides a centralized ModelConfig class for loading model
configuration from environment variables with sensible fallback defaults.
"""

import os
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """Centralized model configuration loader.

    Loads model configuration from environment variables with fallback defaults.
    Supports different model types for various task categories.

    Environment Variables:
        OLLAMA_MODEL: Ollama model identifier (default: llama3.2:3b)
        DEFAULT_CODING_MODEL: Default coding model (default: qwen2.5-coder:7b)
        PRIMARY_MODEL: Primary model for general tasks (default: opencode/qwen3.6-plus-free)
        FALLBACK_MODEL: Fallback model for retry scenarios (default: opencode/minimax-m2.5-free)
        OFFLINE_MODEL: Offline model for disconnected operation (default: ollama/llama3.2:3b)

    Example:
        >>> config = ModelConfig()
        >>> print(config.primary_model)
        opencode/qwen3.6-plus-free
        >>> print(config.get_model("coding"))
        qwen2.5-coder:7b
    """

    OLLAMA_MODEL: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    )
    DEFAULT_CODING_MODEL: str = field(
        default_factory=lambda: os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")
    )
    PRIMARY_MODEL: str = field(
        default_factory=lambda: os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free")
    )
    FALLBACK_MODEL: str = field(
        default_factory=lambda: os.getenv(
            "FALLBACK_MODEL", "opencode/minimax-m2.5-free"
        )
    )
    OFFLINE_MODEL: str = field(
        default_factory=lambda: os.getenv("OFFLINE_MODEL", "ollama/llama3.2:3b")
    )

    @property
    def ollama_model(self) -> str:
        """Ollama model identifier."""
        return self.OLLAMA_MODEL

    @property
    def default_coding_model(self) -> str:
        """Default coding model for code generation tasks."""
        return self.DEFAULT_CODING_MODEL

    @property
    def primary_model(self) -> str:
        """Primary model for general tasks."""
        return self.PRIMARY_MODEL

    @property
    def fallback_model(self) -> str:
        """Fallback model for retry scenarios."""
        return self.FALLBACK_MODEL

    @property
    def offline_model(self) -> str:
        """Offline model for disconnected operation."""
        return self.OFFLINE_MODEL

    def get_model(self, task_type: str) -> str:
        """Get appropriate model based on task type.

        Args:
            task_type: Type of task. Valid values:
                - "coding": Code generation tasks
                - "simple": Simple/single-step tasks
                - "complex": Complex reasoning tasks
                - "offline": Offline/disconnected operation
                - "default": Default primary model

        Returns:
            Model identifier string for the given task type.

        Raises:
            ValueError: If task_type is not recognized.

        Example:
            >>> config = ModelConfig()
            >>> config.get_model("coding")
            'qwen2.5-coder:7b'
            >>> config.get_model("offline")
            'ollama/llama3.2:3b'
        """
        task_type = task_type.lower().strip()

        model_map = {
            "coding": self.DEFAULT_CODING_MODEL,
            "simple": self.PRIMARY_MODEL,
            "complex": self.PRIMARY_MODEL,
            "offline": self.OFFLINE_MODEL,
            "default": self.PRIMARY_MODEL,
        }

        if task_type not in model_map:
            raise ValueError(
                f"Unknown task type: '{task_type}'. "
                f"Valid types: {', '.join(model_map.keys())}"
            )

        return model_map[task_type]

    def to_dict(self) -> dict:
        """Return all configuration as a dictionary.

        Returns:
            Dictionary containing all model configuration values.

        Example:
            >>> config = ModelConfig()
            >>> config.to_dict()
            {'OLLAMA_MODEL': 'llama3.2:3b', 'DEFAULT_CODING_MODEL': '...', ...}
        """
        return {
            "OLLAMA_MODEL": self.OLLAMA_MODEL,
            "DEFAULT_CODING_MODEL": self.DEFAULT_CODING_MODEL,
            "PRIMARY_MODEL": self.PRIMARY_MODEL,
            "FALLBACK_MODEL": self.FALLBACK_MODEL,
            "OFFLINE_MODEL": self.OFFLINE_MODEL,
        }

    def validate(self) -> bool:
        """Validate that all required models are configured.

        Checks that all model configuration values are non-empty strings.

        Returns:
            True if all models are properly configured, False otherwise.

        Example:
            >>> config = ModelConfig()
            >>> config.validate()
            True
        """
        required_models = [
            self.OLLAMA_MODEL,
            self.DEFAULT_CODING_MODEL,
            self.PRIMARY_MODEL,
            self.FALLBACK_MODEL,
            self.OFFLINE_MODEL,
        ]

        return all(
            model and isinstance(model, str) and model.strip()
            for model in required_models
        )


if __name__ == "__main__":
    import json

    config = ModelConfig()
    print(json.dumps(config.to_dict(), indent=2))
