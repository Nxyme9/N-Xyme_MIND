"""Rosetta Stone Trainer - Train local LLMs to translate natural language to MCP tool calls.

This package provides a standalone training pipeline for fine-tuning local LLMs
(like Qwen2.5-0.5B) to translate natural language requests into MCP tool calls.

Bleeding-edge features added (2024-2025):
- Lion optimizer: 2x faster than AdamW
- GaLore: Memory-efficient training
- LoRA+: Per-layer learned learning rates
- ORPO: Memory-efficient preference optimization
- SimPO: Simplified preference optimization
- Multi-LoRA: Simultaneous expert adaptation

Usage:
    python -m nx_trainer.cli --help
    rosetta-train --method unsloth --data data.jsonl --epochs 3
"""

__version__ = "0.2.0"

from nx_trainer.config import DEFAULT_CONFIG, LoRAConfig, TrainingConfig, Optimizer
from nx_trainer.data_generator import DataGenerator
from nx_trainer.trainer import Trainer
from nx_trainer.evaluator import Evaluator
from nx_trainer.validator import DatasetValidator, validate_dataset
from nx_trainer.batch_inferrer import BatchInferrer, StreamingInferrer

# Bleeding-edge optimizers
from nx_trainer.optimizers import (
    Lion,
    Lion8Bit,
    Sophia,
    DAdaptation,
    GaLoreProjection,
    get_optimizer,
)

# Bleeding-edge trainers
from nx_trainer.orpo_trainer import ORPOTrainer, ORPOConfig, prepare_orpo_dataset
from nx_trainer.lora_plus import (
    LoRAPlusConfig,
    LoRAPlusLayer,
    LoRAPlusModel,
    create_lora_plus_model,
    create_lora_plus_optimizer,
    get_lora_plus_model,
)
from nx_trainer.pro_trainer import PROTrainer, PROConfig
from nx_trainer.rrhf_trainer import RRHFTrainer, RRHFConfig
from nx_trainer.bco_trainer import BCOTrainer, BCOConfig
from nx_trainer.vera import (
    VeRAConfig,
    VeRALayer,
    VeRAModel,
    create_vera_model,
    create_vera_optimizer,
    get_vera_model,
)
from nx_trainer.loco import (
    DiLoCoWorker,
    DiLoCoConfig,
    LoCoQuantizer,
    LoCoConfig,
    FLoCoRA,
    create_diloco_worker,
    create_loco_quantizer,
)
from nx_trainer.vllm_backend import (
    VLLMBackend,
    VLLMConfig,
    VLLM_AVAILABLE,
    get_vllm_backend,
    create_reward_scorer,
    create_response_generator,
)

__all__ = [
    # Core
    "__version__",
    "DEFAULT_CONFIG",
    "LoRAConfig",
    "TrainingConfig",
    "Optimizer",
    "DataGenerator",
    "Trainer",
    "Evaluator",
    "DatasetValidator",
    "validate_dataset",
    "BatchInferrer",
    "StreamingInferrer",
    # Bleeding-edge optimizers
    "Lion",
    "Lion8Bit",
    "Sophia",
    "DAdaptation",
    "GaLoreProjection",
    "get_optimizer",
    # Bleeding-edge trainers
    "ORPOTrainer",
    "ORPOConfig",
    "prepare_orpo_dataset",
    # LoRA+
    "LoRAPlusConfig",
    "LoRAPlusLayer",
    "LoRAPlusModel",
    "create_lora_plus_model",
    "create_lora_plus_optimizer",
    "get_lora_plus_model",
    # PRO trainer
    "PROTrainer",
    "PROConfig",
    # RRHF trainer
    "RRHFTrainer",
    "RRHFConfig",
    # BCO trainer
    "BCOTrainer",
    "BCOConfig",
    # VeRA variant
    "VeRAConfig",
    "VeRALayer",
    "VeRAModel",
    "create_vera_model",
    "create_vera_optimizer",
    "get_vera_model",
    # LoCo variants
    "DiLoCoWorker",
    "DiLoCoConfig",
    "LoCoQuantizer",
    "LoCoConfig",
    "FLoCoRA",
    "create_diloco_worker",
    "create_loco_quantizer",
    # vLLM backend
    "VLLMBackend",
    "VLLMConfig",
    "VLLM_AVAILABLE",
    "get_vllm_backend",
    "create_reward_scorer",
    "create_response_generator",
]
