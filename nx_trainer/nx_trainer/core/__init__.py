"""
N-Xyme Trainer - Core Infrastructure

A bleeding-edge LLM trainer supporting:
- Training Methods: LoRA, QLoRA, LoRA+, FTT, DPO, KTO, ORPO, SimPO
- Optimizers: AdamW, Lion, Sophia, GaLore, Adafactor
- Memory: Flash Attention 2, gradient checkpointing, 4-bit NF4
- Export: GGUF, Ollama, HuggingFace, merged models
"""

__version__ = "0.1.0"
__author__ = "N-Xyme Team"

from nx_trainer.core.cli import app
from nx_trainer.core.config import TrainConfig
from nx_trainer.core.registry import PluginRegistry

__all__ = [
    "app",
    "TrainConfig",
    "PluginRegistry",
    "__version__",
]