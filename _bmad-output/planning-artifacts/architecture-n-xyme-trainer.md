---
project_name: N-Xyme Trainer
version: "1.0"
created: "2026-04-27"
author: N-Xyme
document_type: Architecture Document
status: draft
depends_on:
  - prd-n-xyme-trainer.md
---

# Architecture Document: N-Xyme Trainer

> **Purpose**: Define the technical architecture for implementing N-Xyme Trainer v1.0

## Executive Summary

This document specifies the architecture for N-Xyme Trainer, a modular LLM fine-tuning framework supporting bleeding-edge 2024-2026 techniques. The architecture defines a **Protocol-based Plugin System** with hexagonal component boundaries, enabling extensibility through entry points while supporting dual backends (HuggingFace + llama.cpp).

---

# 1. Overview & Goals

## 1.1 Product Context

N-Xyme Trainer is a CLI-first Python package for fine-tuning large language models. It provides:
- Unified interface for multiple training methods (LoRA, QLoRA, LoRA+, VeRA, KTO, DPO, ORPO, SimPO)
- Advanced optimizers (AdamW, Lion, Sophia, GaLore)
- Multi-model support (Qwen, Llama, Mistral, Phi)
- Export to production formats (HF Safetensors, GGUF, Ollama)

## 1.2 Architecture Goals

| Goal | Description | Success Criteria |
|------|-------------|-----------------|
| **Modularity** | Plugin-based architecture with clear boundaries | New optimizer/method added via single decorator |
| **Extensibility** | Entry points for custom components | External packages can register via `entry_points` |
| **Dual Backends** | HF for training, llama.cpp for export | Seamless backend switching |
| **Config Flexibility** | YAML primary, CLI overrides, Python API | All config sources work uniformly |
| **Graceful Degradation** | Fallbacks when features unavailable | No hard crashes, clear error paths |

## 1.3 Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Training speed | Within 10% of Unsloth |
| Memory usage | Competitive with Axolotl |
| Model support | Up to 70B parameters |
| Startup time | CLI help < 1s |
| Config validation | 100% coverage |

---

# 2. Architecture Pattern: Protocol-based Plugin System

## 2.1 Core Principle

The architecture follows a **Protocol-based Plugin System** where:

1. **Protocol**: Abstract interface defining contract (methods to implement)
2. **Plugin**: Concrete implementation conforming to protocol
3. **Registry**: Central lookup mapping protocol → plugin
4. **Factory**: Creates plugin instances based on configuration

```
┌──────────────────────────────────────────────────────────────┐
│                    Protocol Contract                         │
│  (Abstract Base Class or Protocol + Type Hints)              │
│  - validate()                                            │
│  - get_trainer() → BaseTrainer                            │
│  - get_optimizer() → torch.optim.Optimizer                 │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Plugin Implementations                  │
│  - LoRATrainer, QLoRATrainer, LoRAPlusTrainer              │
│  - Lion, Sophia, GaLore optimizers                       │
│  - HFBackend, LlamaCppBackend                           │
└─────────────────���────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Registry + Factory                     │
│  - @register_protocol(protocol_name)                         │
│  - get_plugin(name, config) → instance                 │
└──────────────────────────────────────────────────────────────┘
```

## 2.2 Protocol Definitions

### TrainerProtocol

```python
# nx_trainer/protocols/trainer.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import torch

class TrainerProtocol(ABC):
    """Protocol for all training methods."""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate training configuration.
        
        Returns:
            (is_valid, error_message)
        """
        ...
    
    @abstractmethod
    def create_trainer(
        self,
        model: Any,
        tokenizer: Any,
        training_config: Dict[str, Any],
    ) -> "TrainerInstance":
        """Create trainer instance for the training loop."""
        ...
    
    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """List supported model architectures."""
        ...


class TrainerInstance(ABC):
    """Instance of a configured trainer."""
    
    @abstractmethod
    def train(self, dataset: Any) -> Dict[str, float]:
        """Execute training on dataset.
        
        Returns:
            Training metrics (loss, etc.)
        """
        ...
    
    @abstractmethod
    def save(self, output_path: Path) -> None:
        """Save trained model/adaptors."""
        ...
    
    @abstractmethod
    def get_required_vram(self, model_size: int) -> int:
        """Estimate VRAM requirement in bytes."""
        ...
```

### OptimizerProtocol

```python
# nx_trainer/protocols/optimizer.py
from abc import ABC, abstractmethod
from typing import Any, Dict
import torch
from torch.optim import Optimizer

class OptimizerProtocol(ABC):
    """Protocol for all optimizers."""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate optimizer configuration."""
        ...
    
    @abstractmethod
    def create(
        self,
        parameters: Any,
        lr: float,
        weight_decay: float,
    ) -> Optimizer:
        """Create optimizer instance."""
        ...
    
    @abstractmethod
    def get_name(self) -> str:
        """Return canonical name."""
        ...
    
    @abstractmethod
    def get_vram_savings(self) -> float:
        """Return VRAM savings vs AdamW (0.0-1.0)."""
        ...
```

### BackendProtocol

```python
# nx_trainer/protocols/backend.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import torch

class BackendProtocol(ABC):
    """Protocol for execution backends."""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate backend configuration."""
        ...
    
    @abstractmethod
    def load_model(
        self,
        model_name: str,
        config: Dict[str, Any],
    ) -> tuple[Any, Any]:
        """Load model and tokenizer.
        
        Returns:
            (model, tokenizer)
        """
        ...
    
    @abstractmethod
    def export_model(
        self,
        model: Any,
        tokenizer: Any,
        output_path: Path,
        format: str,
    ) -> Path:
        """Export model to specified format."""
        ...
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return backend capabilities."""
        ...
```

## 2.3 Registration System

```python
# nx_trainer/core/registry.py
from typing import Any, Callable, Dict, Type, TypeVar, Optional
from dataclasses import dataclass
from functools import wraps
import importlib.metadata

T = TypeVar('T')

@dataclass
class PluginMetadata:
    """Metadata for a registered plugin."""
    name: str
    version: str
    description: str
    author: str
    dependencies: list[str] = None
    config_schema: Dict[str, Any] = None


class PluginRegistry:
    """Central registry for all plugins."""
    
    _trainers: Dict[str, Type[TrainerProtocol]] = {}
    _optimizers: Dict[str, Type[OptimizerProtocol]] = {}
    _backends: Dict[str, Type[BackendProtocol]] = {}
    _preprocessors: Dict[str, Callable] = {}
    _postprocessors: Dict[str, Callable] = {}
    
    @classmethod
    def register_trainer(cls, name: str = None):
        """Decorator to register a trainer plugin."""
        def decorator(trainer_cls: Type[TrainerProtocol]) -> Type[TrainerProtocol]:
            plugin_name = name or trainer_cls.__name__.replace('Trainer', '').lower()
            cls._trainers[plugin_name] = trainer_cls
            return trainer_cls
        return decorator
    
    @classmethod
    def register_optimizer(cls, name: str = None):
        """Decorator to register an optimizer plugin."""
        def decorator(optimizer_cls: Type[OptimizerProtocol]) -> Type[OptimizerProtocol]:
            plugin_name = name or optimizer_cls.__name__.lower()
            cls._optimizers[plugin_name] = optimizer_cls
            return optimizer_cls
        return decorator
    
    @classmethod
    def register_backend(cls, name: str = None):
        """Decorator to register a backend."""
        def decorator(backend_cls: Type[BackendProtocol]) -> Type[BackendProtocol]:
            plugin_name = name or backend_cls.__name__.replace('Backend', '').lower()
            cls._backends[plugin_name] = backend_cls
            return backend_cls
        return decorator
    
    @classmethod
    def get_trainer(cls, name: str) -> Optional[Type[TrainerProtocol]]:
        """Get trainer class by name."""
        return cls._trainers.get(name)
    
    @classmethod
    def get_optimizer(cls, name: str) -> Optional[Type[OptimizerProtocol]]:
        """Get optimizer class by name."""
        return cls._optimizers.get(name)
    
    @classmethod
    def list_trainers(cls) -> list[str]:
        """List all registered trainers."""
        return list(cls._trainers.keys())
    
    @classmethod
    def list_optimizers(cls) -> list[str]:
        """List all registered optimizers."""
        return list(cls._optimizers.keys())
    
    @classmethod
    def load_entry_points(cls):
        """Load plugins from entry_points (for external packages)."""
        # Load from package metadata
        for entry in importlib.metadata.entry_points(group='nxyme_trainer.plugins'):
            # External packages register via entry_points
            plugin_func = entry.load()
            # Register based on plugin type
            if hasattr(plugin_func, '_plugin_type'):
                if plugin_func._plugin_type == 'trainer':
                    cls._trainers[entry.name] = plugin_func
                elif plugin_func._plugin_type == 'optimizer':
                    cls._optimizers[entry.name] = plugin_func
```

## 2.4 Entry Points (Extensibility)

External packages can register plugins via `entry_points` in their `pyproject.toml`:

```toml
# pyproject.toml of external package
[project]
name = "nxyme-trainer-galore"
version = "1.0.0"

[project.entry-points."nxyme_trainer.plugins"]
galore = "nxyme_galore.plugin:register_optimizer"

[tool.nxyme_trainer]
plugin_type = "optimizer"
description = "GaLore optimizer plugin"
```

---

# 3. Component Design

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                         CLI Layer (Typer)                        │
│    train | eval | export | config | models | data                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Configuration Manager                        │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│    │  YAML      │ │  CLI      │ │  Python   │             │
│    │  Loader   │ │  Override│ │  API     ���             │
│    └─────────────┘ └─────────────┘ └─────────────┘             │
│                         │                                    │
│                         ▼                                    │
│              Config Validator + Merger                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Core Orchestrator                           │
│    ┌──────────────────────────────────────────────────┐          │
│    │           TrainingOrchestrator              │          │
│    │  - validate_config()                        │          │
│    │  - create_pipeline()                    │          │
│    │  - execute()                      │          │
│    │  - handle_errors()               │          │
│    └──────────────────────────────────────────────────┘          │
│                         │                                    │
└─────────────────────────┼─────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Model     │ │   Dataset    │ │   Training  │
│   Factory  │ │   Pipeline   │ │   Loop      │
└───────────────┘ └───────────────┘ └───────────────┘
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ HF Backend   │ │ Optimizer    │ │ Export      │
│ (training)  │ │ Registry    │ │ Manager    │
└───────────────┘ └───────────────┘ └───────────────┘
```

## 3.1 ModelFactory

**Responsibility**: Load models from various sources, apply configurations

```python
# nx_trainer/components/model_factory.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import torch
from dataclasses import dataclass
from enum import Enum

class ModelSource(str, Enum):
    """Possible model sources."""
    HUGGINGFACE = "huggingface"
    GGUF = "gguf"
    LOCAL = "local"
    SAFETENSORS = "safetensors"


@dataclass
class ModelConfig:
    """Model configuration."""
    name: str
    source: ModelSource
    torch_dtype: Optional[str] = None
    attn_implementation: str = "flash_attention_2"
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    max_seq_length: int = 2048


class ModelFactory:
    """Factory for creating model instances."""
    
    def __init__(self, registry: "PluginRegistry"):
        self.registry = registry
        self._backends = {
            ModelSource.HUGGINGFACE: self._load_huggingface,
            ModelSource.GGUF: self._load_gguf,
            ModelSource.LOCAL: self._load_local,
        }
    
    def create(
        self,
        config: ModelConfig,
        adapter_config: Optional[Dict[str, Any]] = None,
    ) -> tuple[Any, Any]:
        """Create model and tokenizer.
        
        Args:
            config: Model configuration
            adapter_config: Optional adapter (LoRA, VeRA, etc.) config
            
        Returns:
            (model, tokenizer)
        """
        loader = self._backends.get(config.source)
        if not loader:
            raise ValueError(f"Unknown source: {config.source}")
        
        model, tokenizer = loader(config)
        
        # Apply adapter if specified
        if adapter_config:
            model = self._apply_adapter(model, tokenizer, adapter_config)
        
        return model, tokenizer
    
    def _load_huggingface(self, config: ModelConfig) -> tuple[Any, Any]:
        """Load from HuggingFace Hub."""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import unsloth
        
        # Try Unsloth first for optimization
        try:
            model, tokenizer = FastLanguageModel.from_pretrained(
                config.name,
                max_seq_length=config.max_seq_length,
                dtype=config.torch_dtype or self._detect_dtype(),
                load_in_4bit=config.load_in_4bit,
                load_in_8bit=config.load_in_8bit,
                token=os.getenv("HF_TOKEN"),
                attn_implementation=config.attn_implementation,
            )
            return model, tokenizer
        except ImportError:
            pass
        
        # Fallback to standard transformers
        dtype = self._parse_dtype(config.torch_dtype)
        
        model = AutoModelForCausalLM.from_pretrained(
            config.name,
            torch_dtype=dtype,
            load_in_4bit=config.load_in_4bit,
            load_in_8bit=config.load_in_8bit,
            attn_implementation=config.attn_implementation,
            token=os.getenv("HF_TOKEN"),
        )
        
        tokenizer = AutoTokenizer.from_pretrained(
            config.name,
            token=os.getenv("HF_TOKEN"),
        )
        
        return model, tokenizer
    
    def _load_gguf(self, config: ModelConfig) -> tuple[Any, Any]:
        """Load GGUF model (inference only)."""
        # GGUF models are inference-only
        # Return None for tokenizer, use llama.cpp for inference
        return None, None
    
    def _apply_adapter(
        self,
        model: Any,
        tokenizer: Any,
        adapter_config: Dict[str, Any],
    ) -> Any:
        """Apply adapter (LoRA, VeRA, etc.) to model."""
        adapter_type = adapter_config.get("type", "lora")
        
        adapter_registry = {
            "lora": self._apply_lora,
            "qlora": self._apply_qlora,
            "lora_plus": self._apply_lora_plus,
            "vera": self._apply_vera,
        }
        
        apply_fn = adapter_registry.get(adapter_type)
        if not apply_fn:
            raise ValueError(f"Unknown adapter: {adapter_type}")
        
        return apply_fn(model, adapter_config)
```

## 3.2 DatasetPipeline

**Responsibility**: Load, preprocess, tokenize, and batch data

```python
# nx_trainer/components/dataset_pipeline.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json

class DataFormat(str, Enum):
    """Supported data formats."""
    JSONL = "jsonl"
    JSON = "json"
    CSV = "csv"
    DPO = "dpo"        # {"prompt", "chosen", "rejected"}
    KTO = "kto"       # {"prompt", "completion", "label"}
    CHATML = "chatml"  # [{"role": "user", "content": "..."}]
    ALPACA = "alpaca"   # {"instruction", "input", "output"}
    HUGGINGFACE = "huggingface"  # HF datasets


@dataclass
class DatasetConfig:
    """Dataset configuration."""
    path: str
    format: DataFormat
    max_length: int = 4096
    train_split: float = 0.9
    validation_split: float = 0.1
    preprocessing: Optional[Dict[str, Any]] = None


class DatasetPipeline:
    """Pipeline for loading and processing datasets."""
    
    def __init__(self, tokenizer: Any):
        self.tokenizer = tokenizer
        self._formatters = {
            DataFormat.JSONL: self._format_jsonl,
            DataFormat.DPO: self._format_dpo,
            DataFormat.KTO: self._format_kto,
            DataFormat.CHATML: self._format_chatml,
            DataFormat.ALPACA: self._format_alpaca,
        }
    
    def load(
        self,
        config: DatasetConfig,
        split: str = "train",
    ) -> "Dataset":
        """Load dataset for specified split."""
        formatter = self._formatters.get(config.format)
        if not formatter:
            raise ValueError(f"Unknown format: {config.format}")
        
        # Load raw data
        raw_data = self._load_raw(config.path)
        
        # Format data
        formatted = formatter(raw_data)
        
        # Tokenize and create Dataset
        dataset = self._tokenize(formatted, config.max_length)
        
        # Split if needed
        if split == "train":
            return dataset.select(range(int(len(dataset) * config.train_split)))
        else:
            return dataset.select(range(int(len(dataset) * config.train_split), len(dataset)))
    
    def _load_raw(self, path: str) -> list[Dict]:
        """Load raw data from file."""
        path = Path(path)
        
        if path.suffix == ".jsonl" or path.suffix == ".jsonl":
            with open(path) as f:
                return [json.loads(line) for line in f]
        elif path.suffix == ".json":
            with open(path) as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported file: {path}")
    
    def _format_chatml(self, data: list[Dict]) -> list[str]:
        """Format as ChatML."""
        results = []
        for item in data:
            messages = item.get("messages", [])
            text = self.tokenizer.apply_chat_template(messages, tokenize=False)
            results.append({"text": text})
        return results
    
    def _format_dpo(self, data: list[Dict]) -> list[Dict]:
        """Format for DPO training."""
        return [
            {
                "prompt": item["prompt"],
                "chosen": item["chosen"],
                "rejected": item["rejected"],
            }
            for item in data
        ]
    
    def _tokenize(self, data: list[Dict], max_length: int) -> "Dataset":
        """Tokenize and create HF Dataset."""
        from datasets import Dataset
        
        def tokenize_fn(examples):
            return self.tokenizer(
                examples["text"],
                truncation=True,
                max_length=max_length,
                padding="max_length",
            )
        
        ds = Dataset.from_list(data)
        ds = ds.map(tokenize_fn, batched=True, remove_columns=ds.column_names)
        return ds
```

## 3.3 TrainerOrchestrator

**Responsibility**: Coordinate training pipeline, manage lifecycle

```python
# nx_trainer/components/orchestrator.py
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
import logging
from enum import Enum

class TrainingState(str, Enum):
    """Training states."""
    INITIALIZING = "initializing"
    PREPARING = "preparing"
    TRAINING = "training"
    CHECKPOINTING = "checkpointing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingResult:
    """Training result."""
    state: TrainingState
    metrics: Dict[str, float]
    checkpoint_path: Optional[Path]
    error: Optional[str]


class TrainerOrchestrator:
    """Orchestrates the training pipeline."""
    
    def __init__(
        self,
        model_factory: "ModelFactory",
        dataset_pipeline: "DatasetPipeline",
        optimizer_registry: "OptimizerRegistry",
        export_manager: "ExportManager",
    ):
        self.model_factory = model_factory
        self.dataset_pipeline = dataset_pipeline
        self.optimizer_registry = optimizer_registry
        self.export_manager = export_manager
        self.logger = logging.getLogger(__name__)
    
    def execute(self, config: Dict[str, Any]) -> TrainingResult:
        """Execute training based on configuration."""
        self.logger.info("Initializing training pipeline")
        
        # Validate configuration
        is_valid, error = self._validate_config(config)
        if not is_valid:
            return TrainingResult(
                state=TrainingState.FAILED,
                metrics={},
                checkpoint_path=None,
                error=error,
            )
        
        try:
            # Phase 1: Load model
            self.logger.info("Loading model")
            model, tokenizer = self.model_factory.create(
                config["model"],
                config.get("adapter"),
            )
            
            # Phase 2: Load dataset
            self.logger.info("Loading dataset")
            dataset = self.dataset_pipeline.load(
                config["dataset"],
                split="train",
            )
            
            # Phase 3: Create optimizer
            self.logger.info("Creating optimizer")
            optimizer = self.optimizer_registry.create(
                config["optimizer"],
                model.parameters(),
                config["training"]["learning_rate"],
                config["training"]["weight_decay"],
            )
            
            # Phase 4: Create trainer
            self.logger.info("Creating trainer")
            trainer = self._create_trainer(
                model,
                tokenizer,
                dataset,
                optimizer,
                config,
            )
            
            # Phase 5: Train
            self.logger.info("Starting training")
            metrics = trainer.train()
            
            # Phase 6: Save checkpoint
            checkpoint_path = self._save_checkpoint(model, tokenizer, config)
            
            return TrainingResult(
                state=TrainingState.COMPLETED,
                metrics=metrics,
                checkpoint_path=checkpoint_path,
                error=None,
            )
            
        except Exception as e:
            self.logger.exception("Training failed")
            return TrainingResult(
                state=TrainingState.FAILED,
                metrics={},
                checkpoint_path=None,
                error=str(e),
            )
    
    def _create_trainer(
        self,
        model: Any,
        tokenizer: Any,
        dataset: Any,
        optimizer: Any,
        config: Dict[str, Any],
    ) -> Any:
        """Create trainer instance based on method."""
        method = config.get("method", {}).get("name", "lora")
        
        trainer_registry = {
            "lora": LoRATrainer,
            "qlora": QLoRATrainer,
            "lora_plus": LoRAPlusTrainer,
            "vera": VeRATrainer,
        }
        
        trainer_cls = trainer_registry.get(method)
        if not trainer_cls:
            raise ValueError(f"Unknown method: {method}")
        
        return trainer_cls(
            model=model,
            tokenizer=tokenizer,
            dataset=dataset,
            optimizer=optimizer,
            config=config,
        )
```

## 3.4 OptimizerRegistry

**Responsibility**: Manage optimizer instances with memory optimization

```python
# nx_trainer/components/optimizer_registry.py
from typing import Any, Dict, Type
import torch
from torch.optim import Optimizer, AdamW
from dataclasses import dataclass

@dataclass
class OptimizerInfo:
    """Optimizer metadata."""
    name: str
    class_path: str
    vrams_savings: float  # 0.0-1.0 vs AdamW
    requires_grad: bool
    description: str


class OptimizerRegistry:
    """Registry for optimizers."""
    
    # Built-in optimizers
    OPTIMIZERS: Dict[str, OptimizerInfo] = {
        "adamw": OptimizerInfo(
            name="adamw",
            class_path="torch.optim.AdamW",
            vrams_savings=0.0,
            requires_grad=False,
            description="Standard AdamW optimizer",
        ),
        "adamw_8bit": OptimizerInfo(
            name="adamw_8bit",
            class_path="bitsandbytes.optim.AdamW8bit",
            vrams_savings=0.5,
            requires_grad=False,
            description="8-bit AdamW for memory savings",
        ),
        "lion": OptimizerInfo(
            name="lion",
            class_path="nx_trainer.optimizers.Lion",
            vrams_savings=0.3,
            requires_grad=False,
            description="Lion optimizer - 2x faster",
        ),
        "lion_8bit": OptimizerInfo(
            name="lion_8bit",
            class_path="nx_trainer.optimizers.Lion8Bit",
            vrams_savings=0.6,
            requires_grad=False,
            description="8-bit Lion for memory savings",
        ),
        "sophia": OptimizerInfo(
            name="sophia",
            class_path="nx_trainer.optimizers.Sophia",
            vrams_savings=0.0,
            requires_grad=False,
            description="Sophia - better convergence",
        ),
        "galore": OptimizerInfo(
            name="galore",
            class_path="nx_trainer.optimizers.GaLoreOptim",
            vrams_savings=0.65,
            requires_grad=True,
            description="GaLore - 65% less VRAM",
        ),
        "adafactor": OptimizerInfo(
            name="adafactor",
            class_path="transformers.AdaFactor",
            vrams_savings=0.4,
            requires_grad=False,
            description="Sublinear memory optimizer",
        ),
    }
    
    def __init__(self):
        self._custom_optimizers: Dict[str, Type[Optimizer]] = {}
    
    def register(self, name: str, optimizer_cls: Type[Optimizer]):
        """Register custom optimizer."""
        self._custom_optimizers[name] = optimizer_cls
    
    def create(
        self,
        name: str,
        parameters: Any,
        lr: float,
        weight_decay: float,
        **kwargs,
    ) -> Optimizer:
        """Create optimizer instance."""
        # Check custom optimizers first
        if name in self._custom_optimizers:
            return self._custom_optimizers[name](parameters, lr=lr, weight_decay=weight_decay, **kwargs)
        
        # Check built-in optimizers
        if name not in self.OPTIMIZERS:
            raise ValueError(f"Unknown optimizer: {name}. Available: {list(self.OPTIMIZERS.keys())}")
        
        info = self.OPTIMIZERS[name]
        
        # Lazy import
        if info.class_path.startswith("nx_trainer."):
            module_path = info.class_path.replace(".", ".")
            import importlib
            module, cls_name = module_path.rsplit(".", 1)
            module = importlib.import_module(module)
            cls = getattr(module, cls_name)
        else:
            # Standard library or external
            if "bitsandbytes" in info.class_path:
                from bitsandbytes.optim import AdamW8bit
                cls = AdamW8bit
            elif info.class_path == "transformers.AdaFactor":
                from transformers import AdaFactor
                cls = AdaFactor
            else:
                module, cls_name = info.class_path.rsplit(".", 1)
                import importlib
                module = importlib.import_module(module)
                cls = getattr(module, cls_name)
        
        return cls(parameters, lr=lr, weight_decay=weight_decay, **kwargs)
    
    def list_available(self) -> list[str]:
        """List available optimizers."""
        return list(self.OPTIMIZERS.keys()) + list(self._custom_optimizers.keys())
```

## 3.5 ExportManager

**Responsibility**: Export models to various formats

```python
# nx_trainer/components/export_manager.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import subprocess

class ExportFormat(str, Enum):
    """Export formats."""
    HF_SAFETENSORS = "safetensors"  # HuggingFace SafeTensors
    HF_PT = "pt"                 # PyTorch
    GGUF_Q2_K = "gguf_q2_k"
    GGUF_Q4_K_M = "gguf_q4_k_m"  # Recommended
    GGUF_Q8_0 = "gguf_q8_0"
    OLLAMA = "ollama"


@dataclass
class ExportConfig:
    """Export configuration."""
    format: ExportFormat
    input_path: Path
    output_path: Path
    base_model: Optional[str] = None
    quant_method: Optional[str] = None


class ExportManager:
    """Manager for model exports."""
    
    def __init__(
        self,
        hf_backend: "HFBackend",
        llama_cpp_backend: "LlamaCppBackend",
    ):
        self.hf_backend = hf_backend
        self.llama_cpp_backend = llama_cpp_backend
    
    def export(self, config: ExportConfig) -> Path:
        """Export model to specified format."""
        exporters = {
            ExportFormat.HF_SAFETENSORS: self._export_hf,
            ExportFormat.HF_PT: self._export_hf,
            ExportFormat.GGUF_Q2_K: self._export_gguf,
            ExportFormat.GGUF_Q4_K_M: self._export_gguf,
            ExportFormat.GGUF_Q8_0: self._export_gguf,
            ExportFormat.OLLAMA: self._export_ollama,
        }
        
        exporter = exporters.get(config.format)
        if not exporter:
            raise ValueError(f"Unknown format: {config.format}")
        
        return exporter(config)
    
    def _export_hf(self, config: ExportConfig) -> Path:
        """Export to HuggingFace format."""
        return self.hf_backend.export(config)
    
    def _export_gguf(self, config: ExportConfig) -> Path:
        """Export to GGUF format."""
        return self.llama_cpp_backend.export(config)
    
    def _export_ollama(self, config: ExportConfig) -> Path:
        """Export to Ollama Modelfile."""
        modelfile = f"""FROM {config.base_model or 'auto'}
ADAPTER {config.input_path}

SYSTEM
You are a helpful AI assistant.
"""
        
        modelfile_path = config.output_path.with_suffix(".Modelfile")
        with open(modelfile_path, "w") as f:
            f.write(modelfile)
        
        return modelfile_path
```

---

# 4. Backend Strategy

## 4.1 Dual Backend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Backend Abstraction                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              BackendProtocol                        │   │
│  │  - validate()                                      │   │
│  │  - load_model()                                   │   │
│  │  - export_model()                                │   │
│  │  - get_capabilities()                           │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────���─���────────────┘
                    │                    │
        ┌───────────┴───────────┐  ┌──────┴────────┐
        ▼                       ▼                 ▼
┌───────────────┐      ┌───────────────┐   ┌───────────────┐
│  HF Backend   │      │ llama.cpp     │   │   Fallback   │
│  (training)  │      │ Backend      │   │   (degrad.)  │
└───────────────┘      │  (export)    │   └───────────────┘
        │              └───────────────┘
        ▼                      ▼
┌───────────────┐      ┌───────────────┐
│  Training    │      │  GGUF        │
│  SFT/DPOKTO  │      │  Convert   │
│  Export HF   │      │  Inference │
└───────────────┘      └───────────────┘
```

## 4.2 HF Backend

```python
# nx_trainer/backends/huggingface.py
from typing import Any, Dict
from pathlib import Path
from PluginRegistry import register_backend, BackendProtocol

@register_backend("huggingface")
class HFBackend(BackendProtocol):
    """HuggingFace backend for training."""
    
    def validate(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate HF backend config."""
        required = ["model_name"]
        for field in required:
            if field not in config:
                return False, f"Missing required field: {field}"
        return True, None
    
    def load_model(self, model_name: str, config: Dict[str, Any]) -> tuple[Any, Any]:
        """Load model from HuggingFace."""
        # Try Unsloth first
        try:
            from unsloth import FastLanguageModel
            
            return FastLanguageModel.from_pretrained(
                model_name,
                max_seq_length=config.get("max_seq_length", 2048),
                dtype=config.get("dtype"),
                load_in_4bit=config.get("load_in_4bit", False),
            )
        except ImportError:
            pass
        
        # Fallback to transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=getattr(torch, config.get("dtype", "bfloat16")),
            load_in_4bit=config.get("load_in_4bit", False),
        )
        
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        return model, tokenizer
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return HF backend capabilities."""
        return {
            "training": True,
            "inference": True,
            "export_formats": ["safetensors", "pt"],
            "max_seq_length": 8192,
            "quantization": ["4bit", "8bit"],
            "methods": ["lora", "qlora", "lora_plus", "vera", "dpo", "kto", "orpo"],
        }
```

## 4.3 llama.cpp Backend

```python
# nx_trainer/backends/llamacpp.py
from typing import Any, Dict, Optional
from pathlib import Path
from PluginRegistry import register_backend, BackendProtocol

@register_backend("llamacpp")
class LlamaCppBackend(BackendProtocol):
    """llama.cpp backend for GGUF export and inference."""
    
    def __init__(self):
        self.llama_cpp_available = self._check_llama_cpp()
    
    def _check_llama_cpp(self) -> bool:
        """Check if llama.cpp is available."""
        import shutil
        return shutil.which("llama-convert") is not None or \
               Path.home() / "llama.cpp" / "convert.py"
    
    def validate(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate GGUF export config."""
        if not self.llama_cpp_available:
            return False, "llama.cpp not found"
        return True, None
    
    def load_model(self, model_path: str, config: Dict[str, Any]) -> tuple[Any, Any]:
        """Load GGUF model (for inference only)."""
        # GGUF models cannot be trained, only used for inference
        return None, None
    
    def export_model(
        self,
        model: Any,
        tokenizer: Any,
        output_path: Path,
        format: str,
    ) -> Path:
        """Export to GGUF format."""
        # Use llama.cpp convert_lora_to_gguf.py
        import subprocess
        
        script_path = self._find_convert_script()
        
        cmd = [
            "python3",
            str(script_path),
            "--input", str(model),
            "--output", str(output_path),
            "--format", format,
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Export failed: {result.stderr}")
        
        return output_path
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return llama.cpp capabilities."""
        return {
            "training": False,
            "inference": True,
            "export_formats": ["gguf_q2_k", "gguf_q4_k_m", "gguf_q8_0"],
            "quantization": ["q2_k", "q3_k", "q4_k_m", "q5_k", "q6_k", "q8_0"],
            "methods": [],
        }
```

## 4.4 Backend Selection Logic

```python
# nx_trainer/core/backend_selector.py
def select_backend(task: str, config: Dict[str, Any]) -> str:
    """Select optimal backend for task."""
    
    if task == "train":
        # Use HF for training (llama.cpp doesn't support training)
        return "huggingface"
    
    elif task == "export":
        # Select based on format
        export_format = config.get("format", "hf")
        
        if export_format.startswith("gguf"):
            return "llamacpp"
        else:
            return "huggingface"
    
    elif task == "inference":
        # Prefer llama.cpp for inference (fast)
        if config.get("use_llama_cpp", True):
            return "llamacpp"
        else:
            return "huggingface"
    
    else:
        return "huggingface"  # Default
```

---

# 5. Configuration Design

## 5.1 Configuration Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Configuration Sources                    │
│                                                             │
│   ┌───────────┐     ┌───────────┐     ┌───────────┐         │
│   │  Defaults │ ←── │   YAML   │ ←── │   CLI     │         │
│   │   (lowest)│     │  (merge) │     │ (override)│         │
│   └───────────┘     └───────────┘     └───────────┘         │
│        ↑                                        │          │
│        └────────────────────────────────────────┘          │
│                        ▼                                    │
│            ┌─────────────────────┐                        │
│            │  Merged + Validated  │                        │
│            │    Final Config      │                        │
│            └─────────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## 5.2 YAML Configuration Schema

```yaml
# config.yaml - Complete configuration schema
version: "1.0"

# Model configuration
model:
  name: Qwen/Qwen2.5-7B-Instruct
  source: huggingface  # huggingface, gguf, local
  torch_dtype: bfloat16  # bfloat16, float16, float32
  attn_implementation: flash_attention_2
  load_in_4bit: false
  max_seq_length: 4096

# Training method
method:
  name: qlora  # lora, qlora, lora_plus, vera, dpo, kto, orpo, simpo
  rank: 32
  alpha: 64
  dropout: 0.05
  loraplus_lr_ratio: 16  # for lora_plus
  target_modules:
    - q_proj
    - k_proj
    - v_proj
    - o_proj
    - gate_proj
    - up_proj
    - down_proj

# Optimizer
optimizer:
  name: lion  # adamw, adamw_8bit, lion, lion_8bit, sophia, galore, adafactor
  lr: 3e-5
  weight_decay: 0.01
  beta1: 0.9
  beta2: 0.999
  eps: 1e-8

# Dataset
dataset:
  path: ./data/training.jsonl
  format: jsonl  # jsonl, json, dpo, kto, chatml, alpaca
  max_length: 4096
  validation_split: 0.1
  preprocessing:
    chat_template: qwen  # auto, qwen, llama, mistral

# Training parameters
training:
  epochs: 3
  batch_size: 4
  gradient_accumulation: 4
  max_grad_norm: 1.0
  warmup_steps: 100
  warmup_ratio: 0.1
  logging_steps: 10
  save_steps: 500
  eval_steps: 500
  seed: 3407

# Export configuration
export:
  formats:
    - lora_adapter
    - merged_hf
    - gguf_q4_k_m
  output_dir: ./output
  merge_strategy: linear  # linear, slerp, tiler

# Hardware
hardware:
  gpu: auto  # auto, cuda, cpu
  vram_budget_gb: 16
  use_fsdp: false

# Callbacks
callbacks:
  - type: early_stopping
    patience: 3
    min_delta: 0.001
  - type: checkpoint
    save_total_limit: 3
  - type: logging
    log_level: info
```

## 5.3 Configuration Loader

```python
# nx_trainer/core/config_loader.py
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, field
import yaml
from pydantic import BaseModel, Field, field_validator
import click

@dataclass
class ConfigSource:
    """Source of configuration with priority."""
    data: Dict[str, Any]
    source: str  # "defaults", "yaml", "cli", "python"
    priority: int  # Higher = more priority


class ConfigLoader:
    """Load and merge configuration from multiple sources."""
    
    DEFAULTS_PATH = Path(__file__).parent / "default_config.yaml"
    
    def __init__(self):
        self.defaults = self._load_defaults()
        self.sources: list[ConfigSource] = []
    
    def load(
        self,
        yaml_path: Optional[str] = None,
        cli_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Load configuration from all sources.
        
        Priority (low to high): defaults → yaml → python → cli
        """
        # Start with defaults
        self.sources = [ConfigSource(self.defaults, "defaults", 0)]
        
        # Add YAML if provided
        if yaml_path:
            yaml_data = self._load_yaml(yaml_path)
            self.sources.append(ConfigSource(yaml_data, "yaml", 1))
        
        # Add CLI overrides (highest priority)
        if cli_overrides:
            self.sources.append(ConfigSource(cli_overrides, "cli", 2))
        
        # Merge all sources
        return self._merge_sources()
    
    def _merge_sources(self) -> Dict[str, Any]:
        """Merge sources by priority (later overrides earlier)."""
        result = {}
        
        # Sort by priority
        sorted_sources = sorted(self.sources, key=lambda s: s.priority)
        
        for source in sorted_sources:
            result = self._deep_merge(result, source.data)
        
        return result
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def validate(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate configuration."""
        # Required fields
        required = ["model", "dataset"]
        for field in required:
            if field not in config:
                return False, f"Missing required section: {field}"
        
        # Model fields
        if "name" not in config.get("model", {}):
            return False, "Missing model.name"
        
        # Dataset fields
        if "path" not in config.get("dataset", {}):
            return False, "Missing dataset.path"
        
        return True, None
```

## 5.4 CLI Integration

```python
# nx_trainer/cli.py
import typer
from typing import Optional, List
from pathlib import Path
import yaml

app = typer.Typer(help="N-Xyme Trainer - LLM Fine-tuning CLI")

@app.command()
def train(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="YAML config file"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name"),
    method: Optional[str] = typer.Option(None, "--method", help="Training method"),
    data: Optional[Path] = typer.Option(None, "--data", "-d", help="Training data"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    # Training params
    epochs: Optional[int] = typer.Option(None, "--epochs", "-e", help="Number of epochs"),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", help="Batch size"),
    lr: Optional[float] = typer.Option(None, "--lr", help="Learning rate"),
    optimizer: Optional[str] = typer.Option(None, "--optimizer", help="Optimizer"),
    # LoRA params
    lora_r: Optional[int] = typer.Option(None, "--lora-r", help="LoRA rank"),
    lora_alpha: Optional[int] = typer.Option(None, "--lora-alpha", help="LoRA alpha"),
):
    """Train a model."""
    # Build CLI overrides
    cli_overrides = {}
    
    if model:
        cli_overrides.setdefault("model", {})["name"] = model
    if method:
        cli_overrides.setdefault("method", {})["name"] = method
    if data:
        cli_overrides.setdefault("dataset", {})["path"] = str(data)
    if output:
        cli_overrides["output_dir"] = str(output)
    if epochs:
        cli_overrides.setdefault("training", {})["epochs"] = epochs
    if batch_size:
        cli_overrides.setdefault("training", {})["batch_size"] = batch_size
    if lr:
        cli_overrides.setdefault("optimizer", {})["lr"] = lr
    if optimizer:
        cli_overrides.setdefault("optimizer", {})["name"] = optimizer
    if lora_r:
        cli_overrides.setdefault("method", {})["rank"] = lora_r
    
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load(
        yaml_path=str(config) if config else None,
        cli_overrides=cli_overrides if cli_overrides else None,
    )
    
    # Validate
    is_valid, error = config_loader.validate(config)
    if not is_valid:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1)
    
    # Execute training
    orchestrator = TrainerOrchestrator(...)
    result = orchestrator.execute(config)
    
    if result.state == TrainingState.COMPLETED:
        typer.echo(f"✓ Training completed. Checkpoint: {result.checkpoint_path}")
    else:
        typer.echo(f"✗ Training failed: {result.error}", err=True)
        raise typer.Exit(1)


@app.command()
def export(
    input: Path = typer.Argument(..., help="Input model directory"),
    format: str = typer.Option("gguf_q4_k_m", "--format", "-f", help="Export format"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path"),
):
    """Export model to different formats."""
    # Export implementation
    ...
```

---

# 6. Error Handling & Degradation

## 6.1 Error Classification

```python
# nx_trainer/core/errors.py
from enum import Enum
from dataclasses import dataclass

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # Must fix
    ERROR = "error"        # Should fix
    WARNING = "warning"    # Can continue
    INFO = "info"         # Informational


@dataclass
class TrainerError:
    """Trainer error with metadata."""
    code: str
    message: str
    severity: ErrorSeverity
    suggestion: str
    recoverable: bool


ERROR_CATALOG = {
    "E001": TrainerError(
        code="E001",
        message="Model not found",
        severity=ErrorSeverity.CRITICAL,
        suggestion="Check model name or use --model to specify",
        recoverable=False,
    ),
    "E002": TrainerError(
        code="E002",
        message="Dataset not found",
        severity=ErrorSeverity.CRITICAL,
        suggestion="Check data path or use --data to specify",
        recoverable=False,
    ),
    "E003": TrainerError(
        code="E003",
        message="CUDA out of memory",
        severity=ErrorSeverity.ERROR,
        suggestion="Reduce batch_size, enable 4-bit quantization, or use --gradient-checkpointing",
        recoverable=True,
    ),
    "E004": TrainerError(
        code="E004",
        message="Optimizer not available",
        severity=ErrorSeverity.WARNING,
        suggestion="Falling back to AdamW",
        recoverable=True,
    ),
    "E005": TrainerError(
        code="E005",
        message="Training method not available",
        severity=ErrorSeverity.WARNING,
        suggestion="Falling back to LoRA",
        recoverable=True,
    ),
}
```

## 6.2 Graceful Degradation

```python
# nx_trainer/core/degradation.py
class DegradationStrategy:
    """Handle feature unavailability gracefully."""
    
    # Fallback chains for features
    FALLBACKS = {
        "optimizer": {
            "galore": ["adamw_8bit", "adamw"],
            "sophia": ["adamw"],
            "lion_8bit": ["adamw_8bit", "adamw"],
        },
        "method": {
            "lora_plus": ["lora"],
            "vera": ["lora"],
            "simpo": ["dpo"],
            "orpo": ["dpo"],
        },
        "attn_implementation": {
            "flash_attention_2": ["flash_attention", "sdpa", "eager"],
        },
        "training_backend": {
            "unsloth": ["transformers"],
            "transformers": ["slow"],
        },
        "export_format": {
            "gguf_q8_0": ["gguf_q4_k_m", "hf"],
        },
    }
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def resolve(self, feature: str, requested: str) -> str:
        """Resolve feature with fallback."""
        if self._is_available(feature, requested):
            return requested
        
        fallbacks = self.FALLBACKS.get(feature, {})
        fallback_chain = fallbacks.get(requested, [])
        
        for fallback in fallback_chain:
            if self._is_available(feature, fallback):
                self.logger.warning(
                    f"{feature}.{requested} not available, falling back to {fallback}"
                )
                return fallback
        
        # Last resort: return original
        self.logger.warning(
            f"No fallback available for {feature}.{requested}, using as-is"
        )
        return requested
    
    def _is_available(self, feature: str, value: str) -> bool:
        """Check if feature value is available."""
        try:
            if feature == "optimizer":
                # Check if optimizer can be imported
                if value == "galore":
                    from nx_trainer.optimizers import GaLoreOptim
                    return True
                elif value == "lion":
                    from nx_trainer.optimizers import Lion
                    return True
                elif value == "sophia":
                    from nx_trainer.optimizers import Sophia
                    return True
            
            elif feature == "attn_implementation":
                import torch
                return hasattr(torch.nn, value) or value in ["flash_attention_2"]
            
            elif feature == "training_backend":
                if value == "unsloth":
                    import unsloth
                    return True
                elif value == "transformers":
                    return True
            
            return True
        
        except ImportError:
            return False
```

## 6.3 Training Error Recovery

```python
# nx_trainer/core/recovery.py
class TrainingRecovery:
    """Recovery strategies for training errors."""
    
    @staticmethod
    def handle_oom(config: Dict, error: Exception) -> Dict:
        """Handle OOM error with config adjustments."""
        adjustments = {}
        
        # Step 1: Enable 4-bit quantization
        if not config.get("model", {}).get("load_in_4bit", False):
            adjustments["load_in_4bit"] = True
            return adjustments, "Enabled 4-bit quantization"
        
        # Step 2: Reduce batch size
        current_batch = config.get("training", {}).get("batch_size", 4)
        if current_batch > 1:
            adjustments["batch_size"] = current_batch // 2
            return adjustments, f"Reduced batch_size to {adjustments['batch_size']}"
        
        # Step 3: Enable gradient checkpointing
        if not config.get("training", {}).get("gradient_checkpointing", False):
            adjustments["gradient_checkpointing"] = True
            return adjustments, "Enabled gradient checkpointing"
        
        # Step 4: Use DeepSpeed
        adjustments["use_deepspeed"] = True
        return adjustments, "Recommended: Use DeepSpeed for better memory management"
    
    @staticmethod
    def handle_checkpoint_error(checkpoint_path: Path) -> Optional[Path]:
        """Find working checkpoint for recovery."""
        if checkpoint_path.exists():
            return checkpoint_path
        
        # Try finding partial checkpoint
        partial = checkpoint_path.parent / "partial"
        if partial.exists():
            checkpoints = sorted(partial.glob("checkpoint-*"))
            if checkpoints:
                return checkpoints[-1]
        
        return None
```

---

# 7. Extension Points

## 7.1 Adding New Optimizers

```python
# Example: Adding GaLore optimizer

# File: nx_trainer/optimizers/galore.py
from torch.optim import Optimizer
import torch
from nx_trainer.core.registry import PluginRegistry

@PluginRegistry.register_optimizer("galore")
class GaLoreOptim(Optimizer):
    """GaLore optimizer - 65% less VRAM than AdamW."""
    
    def __init__(self, params, lr=1e-4, weight_decay=0.01, galore_density=0.25):
        defaults = dict(lr=lr, weight_decay=weight_decay, galore_density=galore_density)
        super().__init__(params, defaults)
    
    @torch.no_grad()
    def step(self, closure=None):
        """Step function."""
        # Implementation
        ...
```

## 7.2 Adding New Training Methods

```python
# Example: Adding SimPO trainer

# File: nx_trainer/methods/simpo/__init__.py
from nx_trainer.core.registry import PluginRegistry

@PluginRegistry.register_trainer("simpo")
class SimPOTrainer:
    """Simple Preference Optimization trainer."""
    
    def __init__(self, model, dataset, optimizer, config):
        self.model = model
        self.dataset = dataset
        self.config = config
    
    def train(self) -> dict:
        """Execute SimPO training."""
        from trl import SimPOTrainer
        
        trainer = SimPOTrainer(
            model=self.model,
            train_dataset=self.dataset,
            tokenizer=self.config.get("tokenizer"),
            args=self.config.get("training_args"),
            max_prompt_length=self.config.get("max_prompt_length", 512),
            max_length=self.config.get("max_length", 1024),
        )
        
        return trainer.train()
    
    def validate(self, test_config: Dict) -> tuple[bool, str]:
        """Validate SimPO config."""
        required = ["beta", "loss_type"]
        for field in required:
            if field not in test_config:
                return False, f"Missing: {field}"
        
        if test_config.get("beta", 0) <= 0:
            return False, "beta must be positive"
        
        return True, None
```

## 7.3 Adding New Models

```python
# Example: Adding a new model architecture

# File: nx_trainer/models/example.py
class ExampleModelConfig:
    """Configuration for Example model."""
    
    SUPPORTED_ARCHITECTURES = [
        "ExampleForCausalLM",
    ]
    
    @staticmethod
    def detect_architecture(model) -> str:
        """Auto-detect model architecture."""
        if hasattr(model, "config"):
            arch = model.config.architectures[0] if model.config.architectures else None
            if arch in ExampleModelConfig.SUPPORTED_ARCHITECTURES:
                return arch
        
        return "unknown"
    
    @staticmethod
    def get_target_modules() -> list[str]:
        """Get target modules for LoRA."""
        return ["q_proj", "k_proj", "v_proj", "o_proj"]
```

## 7.4 Entry Points Registration

```python
# pyproject.toml (for external packages)
[project.entry-points."nxyme_trainer.plugins"]
galore = "nxyme_galore:register_plugin"

[project.entry-points."nxyme_trainer.trainers"]
simpo = "nxyme_trainer.methods.simpo:register"

[project.entry-points."nxyme_trainer.optimizers"]  
galore = "nxyme_galore.optimizers:register"
```

---

# 8. Data Flow

## 8.1 Training Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                TRAINING DATA FLOW                         │
└─────────────────────────────────────────────────────────────────────────────┘

1. DATA LOADING
   ┌────────────────────────────────────────────────────────┐
   │  config.yaml / CLI                                 │
   │    ↓                                             │
   │  ConfigLoader.load()                               │
   │    ↓                                             │
   │  DatasetConfig (path, format, max_length)           │
   └────────────────────────────────────────────────────────┘
                          ↓
2. DATA PARSING
   ┌────────────────────────────────────────────────────────┐
   │  DatasetPipeline.load()                           │
   │    ↓                                             │
   │  detect format (jsonl/dpo/kto/chatml)           │
   │    ↓                                             │
   │  formatter.format()                             │
   │    - apply_chat_template()                     │
   │    - convert_to_dpo()                         │
   │    - convert_to_kto()                        │
   │    ↓                                             │
   │  List[Dict] with "text"/"prompt"/"chosen"/etc      │
   └────────────────────────────────────────────────────────┘
                          ↓
3. TOKENIZATION
   ┌────────────────────────────────────────────────────────┐
   │  tokenizer()                                 │
   │    - truncation=True                       │
   │    - max_length=4096                      │
   │    - padding=max_length                     │
   │    ↓                                             │
   │  Dataset with input_ids, attention_mask          │
   └────────────────────────────────────────────────────────┘
                          ↓
4. BATCHING
   ┌────────────────────────────────────────────────────────┐
   │  DataLoader                                    │
   │    - batch_size=4                           │
   │    - shuffle=True                           │
   │    - drop_last=False                       │
   │    ↓                                             │
   │  Batch(input_ids, attention_mask, labels) │
   └────────────────────────────────────────────────────────┘
                          ↓
5. TRAINING LOOP
   ┌────────────────────────────────────────────────────────┐
   │  for epoch in epochs:                           │
   │    for batch in dataloader:                   │
   │      # Forward pass                          │
   │      outputs = model(**batch)                 │
   │      loss = outputs.loss                    │
   │                                            │
   │      # Backward pass                        │
   │      loss.backward()                       │
   │      optimizer.step()                      │
   │      scheduler.step()                      │
   │                                            │
   │      # Logging                             │
   │      if step % logging_steps == 0:          │
   │        log_metrics(loss, lr, gpu_mem)      │
   │                                            │
   │      # Checkpoint                          │
   │      if step % save_steps == 0:              │
   │        save_checkpoint()                    │
   └────────────────────────────────────────────────────────┘
```

## 8.2 Export Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                EXPORT DATA FLOW                         │
└─────────────────────────────────────────────────────────────────────────────┘

1. MODEL LOADING
   ┌────────────────────────────────────────────────────────┐
   │  ModelFactory.create()                           │
   │    ��                                             │
   │  load adapter (if exists)                      │
   │    - load PEFT model                          │
   │    - merge adapter                          │
   └────────────────────────────────────────────────────────┘
                          ↓
2. BACKEND SELECTION
   ┌────────────────────────────────────────────────────────┐
   │  select by format                                   │
   │    ↓                                             │
   │  GGUF → llama.cpp Backends                    │
   │  HF  → HF Backend                             │
   │  Ollama → Ollama Backend                       │
   └────────────────────────────────────────────────────────┘
                          ↓
3. EXPORT
   ┌────────────────────────────────────────────────────────┐
   │  llama.cpp:                                    │
   │    - convert_lora_to_gguf.py                 │
   │    - quantize (q2_k, q4_k_m, q8_0)         │
   │    ↓                                             │
   │  HF:                                         │
   │    - save_pretrained()                     │
   │    - safetensors format                     │
   │    ↓                                             │
   │  Ollama:                                    │
   │    - create Modelfile                       │
   └────────────────────────────────────────────────────────┘
                          ↓
4. OUTPUT
   ┌────────────────────────────────────────────────────────┐
   │  output_path = Path                          │
   │    Format:                                  │
   │    - model-q4_k_m.gguf                    │
   │    - adapter.safetensors                 │
   │    - model.Modelfile                      │
   └────────────────────────────────────────────────────────┘
```

---

# 9. Technology Stack

## 9.1 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `torch` | ≥2.0 | Core ML framework |
| `transformers` | ≥4.35 | Model loading |
| `peft` | ≥0.8 | LoRA implementation |
| `trl` | ≥0.8 | DPO/KTO/ORPO training |
| `unsloth` | ≥2024 | Fast training (optional) |
| `bitsandbytes` | ≥0.41 | 4-bit quantization |
| `llama-cpp` | ≥0.2 | GGUF export |

## 9.2 CLI & Config

| Package | Version | Purpose |
|---------|---------|---------|
| `typer` | ≥0.12 | CLI framework |
| `pydantic` | ≥2.5 | Config validation |
| `pyyaml` | ≥6.0 | YAML parsing |
| `click` | ≥8.1 | Alternative CLI |

## 9.3 Utilities

| Package | Version | Purpose |
|---------|---------|---------|
| `tqdm` | ≥4.65 | Progress bars |
| `loguru` | ≥0.12 | Logging |
| `dotenv` | ≥1.0 | Environment variables |

## 9.4 Development

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥7.4 | Testing |
| `pytest-cov` | ≥4.1 | Coverage |
| `ruff` | ≥0.1 | Linting |
| `mypy` | ≥1.7 | Type checking |

---

# 10. File Structure

```
nx_trainer/
├── __init__.py                 # Package exports + version
├── cli.py                     # CLI entry points (train, eval, export, config)
├── pyproject.toml            # Package config + entry points
│
├── core/
│   ├── __init__.py
│   ├── registry.py          # Plugin registry
│   ├── config_loader.py    # YAML/CLI config loading
│   ├── Orchestrator.py     # Training orchestration
│   ├── errors.py          # Error definitions
│   ├── degradation.py    # Graceful degradation
│   └── backend_selector.py # Backend selection
│
├── protocols/
│   ├── __init__.py
│   ├── trainer.py         # TrainerProtocol
│   ├── optimizer.py      # OptimizerProtocol
│   └── backend.py       # BackendProtocol
│
├── components/
│   ├── __init__.py
│   ├── model_factory.py  # ModelFactory
│   ├── dataset_pipeline.py  # DatasetPipeline
│   ├── optimizer_registry.py  # OptimizerRegistry
│   └── export_manager.py # ExportManager
│
├── backends/
│   ├── __init__.py
│   ├── huggingface.py  # HuggingFace backend
│   ├── llamacpp.py   # llama.cpp backend
│   └── fallback.py   # Fallback backend
│
├── optimizers/
│   ├── __init__.py
│   ├── lion.py       # Lion optimizer
│   ├── sophia.py   # Sophia optimizer
│   ├── galore.py   # GaLore optimizer
│   └── registry.py  # Optimizer registry (deprecated, use components)
│
├── methods/
│   ├── __init__.py
│   ├── lora/
│   ├── lora_plus/
│   ├── vera/
│   ├── dpo/
│   ├── kto/
│   ├── orpo/
│   └── simpo/
│
├── models/
│   ├── __init__.py
│   ├── qwen.py
│   ├── llama.py
│   └── registry.py
│
├── export/
│   ├── __init__.py
│   ├── hf.py        # HF export
│   ├── gguf.py     # GGUF export
│   └── ollama.py   # Ollama export
│
└── utils/
    ├── __init__.py
    ├── memory.py   # Memory utilities
    ├── logging.py # Logging utilities
    └── validation.py  # Config validation
```

---

# Appendix A: Protocol Contracts Summary

| Protocol | Methods | Plugin Type |
|----------|---------|-------------|
| `TrainerProtocol` | `validate()`, `create_trainer()`, `get_supported_models()` | trainer |
| `OptimizerProtocol` | `validate()`, `create()`, `get_name()`, `get_vram_savings()` | optimizer |
| `BackendProtocol` | `validate()`, `load_model()`, `export_model()`, `get_capabilities()` | backend |

---

# Appendix B: Error Codes

| Code | Severity | Description | Recovery |
|------|----------|-------------|----------|
| E001 | CRITICAL | Model not found | Check model name |
| E002 | CRITICAL | Dataset not found | Check data path |
| E003 | ERROR | CUDA OOM | Reduce batch, enable 4-bit |
| E004 | WARNING | Optimizer unavailable | Fallback to AdamW |
| E005 | WARNING | Method unavailable | Fallback to LoRA |
| E006 | WARNING | Backend unavailable | Fallback to HF |
| W001 | INFO | Using fallback | Informational |

---

# Appendix C: Testing Strategy

```python
# tests/test_registry.py
def test_registry_trainer_registration():
    registry = PluginRegistry()
    
    @registry.register_trainer("test")
    class TestTrainer:
        pass
    
    assert registry.get_trainer("test") == TestTrainer

def test_registry_optimizer_fallback():
    strategy = DegradationStrategy()
    
    # Should return fallback when original unavailable
    result = strategy.resolve("optimizer", "unavailable_optimizer")
    assert result in ["adamw_8bit", "adamw"]


# tests/test_config.py
def test_config_merge():
    loader = ConfigLoader()
    
    config = loader.load(
        yaml_path="tests/fixtures/config.yaml",
        cli_overrides={"model": {"name": "test"}},
    )
    
    assert config["model"]["name"] == "test"  # CLI override
    assert config["dataset"]["path"] == "data.jsonl"  # YAML
```

---

*Document Version: 1.0*
*Created: 2026-04-27*
*Status: Ready for Implementation*