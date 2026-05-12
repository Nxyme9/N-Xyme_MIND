"""Configuration management with YAML + CLI overrides + Pydantic validation."""
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
import yaml


class LoRAConfig(BaseModel):
    rank: int = 16
    alpha: int = 32
    target_modules: Optional[List[str]] = None
    dropout: float = 0.05
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


class QuantizationConfig(BaseModel):
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True


class TrainingConfig(BaseModel):
    method: str = "lora"
    optimizer: str = "adamw"
    epochs: int = 3
    batch_size: int = 8
    gradient_accumulation_steps: int = 1
    lr: float = 3e-4
    lr_scheduler: str = "cosine"
    warmup_steps: int = 100
    max_grad_norm: float = 1.0
    weight_decay: float = 0.01
    seed: int = 42


class MemoryConfig(BaseModel):
    gradient_checkpointing: bool = True
    flash_attention: bool = True
    mixed_precision: str = "bfloat16"
    fsdp: bool = False
    fsdp_config: Optional[Dict[str, Any]] = None


class DatasetConfig(BaseModel):
    path: Optional[str] = None
    format: str = "jsonl"
    max_length: int = 2048
    chat_template: Optional[str] = None
    train_split: float = 0.9
    shuffle: bool = True


class LoggingConfig(BaseModel):
    output_dir: Path = Field(default_factory=lambda: Path("./output"))
    log_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 500
    logging_dir: Optional[Path] = None
    report_to: str = "none"


class ExportConfig(BaseModel):
    format: str = "hf"
    quantization: Optional[str] = None
    push_to_hub: bool = False
    hub_repo_id: Optional[str] = None


class TrainConfig(BaseModel):
    model: Optional[str] = None
    lora: LoRAConfig = Field(default_factory=LoRAConfig)
    quantization: QuantizationConfig = Field(default_factory=QuantizationConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> "TrainConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_args(
        cls,
        model: Optional[str] = None,
        data: Optional[Path] = None,
        method: str = "lora",
        optimizer: str = "adamw",
        epochs: int = 3,
        batch_size: int = 8,
        lr: float = 3e-4,
        rank: int = 16,
        alpha: int = 32,
        output_dir: Path = Path("./output"),
    ) -> "TrainConfig":
        config = cls()
        
        if model:
            config.model = model
        
        if data:
            config.dataset.path = str(data)
        
        config.training.method = method
        config.training.optimizer = optimizer
        config.training.epochs = epochs
        config.training.batch_size = batch_size
        config.training.lr = lr
        config.lora.rank = rank
        config.lora.alpha = alpha
        config.logging.output_dir = output_dir
        
        return config

    @classmethod
    def merge(cls, yaml_path: Path, cli_config: "TrainConfig") -> "TrainConfig":
        if not yaml_path.exists():
            return cli_config
        
        yaml_config = cls.from_yaml(yaml_path)
        
        merged = cli_config.model_copy(deep=True)
        
        if yaml_config.model:
            merged.model = yaml_config.model
        
        if yaml_config.lora.rank != 16:
            merged.lora.rank = yaml_config.lora.rank
        if yaml_config.lora.alpha != 32:
            merged.lora.alpha = yaml_config.lora.alpha
        
        merged.training = yaml_config.training
        merged.memory = yaml_config.memory
        merged.dataset = yaml_config.dataset
        
        return merged

    @classmethod
    def default(cls) -> "TrainConfig":
        return cls()

    def validate_method(self):
        valid = ["lora", "qlora", "lora_plus", "ftt", "dpo", "kto", "orpo", "simpo"]
        if self.training.method.lower() not in valid:
            self.training.method = valid[0]
        return self

    def validate_optimizer(self):
        valid = ["adamw", "lion", "sophia", "galore", "adafactor"]
        if self.training.optimizer.lower() not in valid:
            self.training.optimizer = valid[0]
        return self