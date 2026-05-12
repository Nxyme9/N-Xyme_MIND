"""Default configurations for Rosetta Stone Trainer.

Optimized for:
- RTX 3080 Ti (12.5GB VRAM)
- Qwen2.5-0.5B/1.5B models
- Tool-calling fine-tuning
- Speed + VRAM efficiency (Unsloth 2x faster, 70% less VRAM)

Uses Pydantic for validation and serialization.
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class QuantizeMethod(str, Enum):
    """GGUF quantization methods."""

    Q4_K_M = "q4_k_m"  # Balanced (recommended)
    Q8_0 = "q8_0"  # High quality
    F16 = "f16"  # Best quality
    Q5_K_M = "q5_k_m"  # Medium
    Q3_K_M = "q3_k_m"  # Small


class Optimizer(str, Enum):
    """Optimizer choices - including bleeding-edge optimizers."""

    ADAMW_8BIT = "adamw_8bit"
    ADAMW_TORCH = "adamw_torch"
    SGD = "sgd"
    # Bleeding-edge optimizers (2024-2025)
    LION = "lion"  # Lion optimizer - 2x faster than AdamW
    LION_8BIT = "lion_8bit"  # 8-bit Lion
    SOPHIA = "sophia"  # Sophia optimizer - better convergence
    D_ADAPTATION = "d_adaptation"  # D-Adaptation - learning rate free
    GALORE = "galore"  # GaLore - memory-efficient training


class LRScheduler(str, Enum):
    """Learning rate scheduler types."""

    COSINE = "cosine"
    LINEAR = "linear"
    CONSTANT = "constant"
    POLYNOMIAL = "polynomial"


class LoRAConfig(BaseModel):
    """LoRA (Low-Rank Adaptation) configuration for fine-tuning.

    Research-backed defaults for tool-calling:
    - r (rank): 32 (higher for more capacity)
    - alpha: 64 (2x rank - research recommendation)
    - target_modules: all linear layers (q,k,v,o,gate,up,down)
    - dropout: 0.05 (light dropout)
    """

    model_config = {"frozen": False}

    r: int = Field(default=32, ge=1, le=128, description="LoRA rank (rank)")
    alpha: int = Field(default=64, ge=1, le=256, description="LoRA alpha (scaling)")
    dropout: float = Field(default=0.05, ge=0.0, le=0.5, description="LoRA dropout")
    bias: str = Field(default="none", description="Bias type: none, all, lora_only")
    target_modules: List[str] = Field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        description="Target modules for LoRA",
    )
    task_type: str = Field(default="CAUSAL_LM", description="Task type for PEFT")
    use_rslora: bool = Field(default=False, description="Use Rank-Stable LoRA")
    use_dora: bool = Field(default=False, description="Use DoRA (Decomposed Rank-Adapted)")
    # Training mode for future preference optimization (GRPO/SimPO/KTO)
    training_mode: str = Field(
        default="sft",
        description="Training mode: sft, grpo, simpo, kto (future)",
    )
    # Multi-LoRA support (for simultaneous expert adaptation)
    num_loras: int = Field(default=1, ge=1, le=8, description="Number of LoRA adapters (future)")
    lora_names: List[str] = Field(
        default_factory=list,
        description="Names for multiple LoRA adapters (future)",
    )

    @field_validator("target_modules", mode="before")
    @classmethod
    def _parse_target_modules(cls, v):
        if isinstance(v, str):
            return [m.strip() for m in v.split(",")]
        return v


class TrainingConfig(BaseModel):
    """Training configuration - research-optimized for tool-calling."""

    model_config = {"frozen": False}

    model_name: str = Field(
        default="Qwen/Qwen2.5-1.5B-Instruct", description="HuggingFace model name"
    )
    max_seq_length: int = Field(
        default=2048, ge=128, le=8192, description="Maximum sequence length"
    )
    dtype: Optional[str] = Field(default=None, description="Data type (bf16/fp16/fp32)")
    load_in_4bit: bool = Field(default=True, description="Load model in 4-bit quantized")
    per_device_train_batch_size: int = Field(
        default=4, ge=1, le=32, description="Batch size per device"
    )
    gradient_accumulation_steps: int = Field(
        default=8, ge=1, le=64, description="Gradient accumulation"
    )
    warmup_steps: int = Field(default=10, ge=0, description="Warmup steps")
    warmup_ratio: float = Field(default=0.1, ge=0.0, le=1.0, description="Warmup ratio")
    num_train_epochs: int = Field(default=3, ge=1, le=100, description="Number of epochs")
    learning_rate: float = Field(default=2e-5, ge=1e-6, le=1e-2, description="Learning rate")
    fp16: bool = Field(default=True, description="Use FP16")
    bf16: bool = Field(default=True, description="Use BF16 (if supported)")
    logging_steps: int = Field(default=10, ge=1, description="Logging frequency")
    save_steps: int = Field(default=999999, description="Save checkpoint every N steps")
    eval_steps: int = Field(default=999999, description="Evaluation frequency")
    optim: Optimizer = Field(default=Optimizer.ADAMW_8BIT, description="Optimizer")
    weight_decay: float = Field(default=0.01, ge=0.0, le=1.0, description="Weight decay")
    lr_scheduler_type: LRScheduler = Field(default=LRScheduler.COSINE, description="LR scheduler")
    seed: int = Field(default=3407, description="Random seed")
    output_dir: str = Field(default="outputs/rosetta", description="Output directory")
    # Performance optimizations
    dataloader_num_workers: int = Field(default=4, ge=0, description="DataLoader workers")
    remove_unused_columns: bool = Field(default=False, description="Remove unused columns")
    group_by_length: bool = Field(default=False, description="Group by length for efficiency")
    # LoRA-specific
    lora_dropout: float = Field(default=0.05, ge=0.0, le=0.5, description="LoRA dropout")
    # Advanced
    max_grad_norm: float = Field(default=1.0, ge=0.1, description="Gradient clipping")
    label_smoothing: float = Field(default=0.0, ge=0.0, le=1.0, description="Label smoothing")
    # Training mode for future preference optimization
    training_mode: str = Field(
        default="sft",
        description="Training mode: sft, grpo, simpo, kto",
    )

    def to_training_args(self) -> Dict[str, Any]:
        """Convert to transformers TrainingArguments compatible dict."""
        return {
            "per_device_train_batch_size": self.per_device_train_batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "warmup_steps": self.warmup_steps,
            "warmup_ratio": self.warmup_ratio,
            "num_train_epochs": self.num_train_epochs,
            "learning_rate": self.learning_rate,
            "fp16": self.fp16,
            "bf16": self.bf16,
            "logging_steps": self.logging_steps,
            "optim": self.optim.value if isinstance(self.optim, Optimizer) else self.optim,
            "weight_decay": self.weight_decay,
            "lr_scheduler_type": self.lr_scheduler_type.value
            if isinstance(self.lr_scheduler, LRScheduler)
            else self.lr_scheduler_type,
            "seed": self.seed,
            "dataloader_num_workers": self.dataloader_num_workers,
            "remove_unused_columns": self.remove_unused_columns,
            "group_by_length": self.group_by_length,
            "max_grad_norm": self.max_grad_norm,
            "label_smoothing_factor": self.label_smoothing,
        }


class GGUFExportConfig(BaseModel):
    """GGUF export configuration for llama-server compatibility."""

    quantize_method: QuantizeMethod = Field(
        default=QuantizeMethod.Q4_K_M, description="Quantization method"
    )
    base_model_name: str = Field(
        default="Qwen/Qwen2.5-1.5B-Instruct", description="Base model name"
    )
    output_dir: Union[str, Path] = Field(default="outputs/gguf", description="Output directory")
    threads: int = Field(default=16, ge=1, le=128, description="CPU threads for conversion")
    use_gpu: bool = Field(default=True, description="Use GPU for conversion if available")
    imatrix: Optional[Path] = Field(default=None, description="Importance matrix for quantization")

    def get_output_path(self, quant: Optional[str] = None) -> Path:
        """Get output file path."""
        q = quant or self.quantize_method.value
        out_dir = Path(self.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / f"rosetta-{q}.gguf"


class OllamaConfig(BaseModel):
    """Ollama configuration for Modelfile-based training."""

    model_name: str = Field(default="qwen2.5:1.5b", description="Ollama model")
    system_prompt: str = Field(
        default="""You are a tool call translator. Your job is to convert 
simple user requests into proper MCP tool calls.

Format: [TOOL_CALL]{tool => "tool_name", args => { --arg "value" }}[/TOOL_CALL]

Examples:
- "search memory for security" → [TOOL_CALL]{tool => "memory_search", args => { --query "security" }}[/TOOL_CALL]
- "show me README.md" → [TOOL_CALL]{tool => "read_file", args => { --path "README.md" }}[/TOOL_CALL]
- "check git status" → [TOOL_CALL]{tool => "git_status", args => { --repo_path "." }}[/TOOL_CALL]""",
        description="System prompt",
    )
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Generation temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: int = Field(default=40, ge=1, description="Top-k sampling")


class ModelPreset(str, Enum):
    """Pre-configured model presets."""

    QWEN2_5_0_5B = "qwen2.5-0.5b"
    QWEN2_5_1_5B = "qwen2.5-1.5b"
    QWEN2_5_3B = "qwen2.5-3b"
    LLAMA3_2_1B = "llama3.2-1b"
    LLAMA3_2_3B = "llama3.2-3b"


# Optimal model configs for different VRAM levels
# Research-backed: lr=1e-5 to 3e-5 for tool-calling, target all linear layers
MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "qwen2.5-0.5b": {
        "model_name": "Qwen/Qwen2.5-0.5B-Instruct",
        "max_seq_length": 2048,
        "lora_r": 32,
        "lora_alpha": 64,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "batch_size": 4,
        "gradient_accumulation": 4,
        "learning_rate": 2e-5,
        "epochs": 3,
        "vram_requirement": "4-5GB",
    },
    "qwen2.5-1.5b": {
        "model_name": "Qwen/Qwen2.5-1.5B-Instruct",
        "max_seq_length": 2048,
        "lora_r": 32,
        "lora_alpha": 64,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "batch_size": 4,
        "gradient_accumulation": 8,
        "learning_rate": 2e-5,
        "epochs": 3,
        "vram_requirement": "6GB",
    },
    "qwen2.5-3b": {
        "model_name": "Qwen/Qwen2.5-3B-Instruct",
        "max_seq_length": 2048,
        "lora_r": 32,
        "lora_alpha": 64,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "batch_size": 2,
        "gradient_accumulation": 16,
        "learning_rate": 1e-5,
        "epochs": 3,
        "vram_requirement": "8GB",
    },
    "llama3.2-1b": {
        "model_name": "meta-llama/Llama-3.2-1B-Instruct",
        "max_seq_length": 1024,
        "lora_r": 16,
        "lora_alpha": 16,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "batch_size": 4,
        "gradient_accumulation": 4,
        "learning_rate": 2e-5,
        "epochs": 3,
        "vram_requirement": "4-5GB",
    },
    "llama3.2-3b": {
        "model_name": "meta-llama/Llama-3.2-3B-Instruct",
        "max_seq_length": 1024,
        "lora_r": 8,
        "lora_alpha": 16,
        "target_modules": [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        "batch_size": 1,
        "gradient_accumulation": 8,
        "learning_rate": 1e-5,
        "epochs": 3,
        "vram_requirement": "8GB",
    },
}


# Default tool definitions for data generation - COMPLETE SYSTEM TOOLS
# Synced from AGENTS.md MCP tools + nx_mcps actual functions
DEFAULT_TOOLS: Dict[str, Dict[str, str]] = {
    # === Filesystem MCP ===
    "read_file": {"filePath": "str", "limit": "int", "offset": "int"},
    "write_file": {"content": "str", "filePath": "str"},
    "edit_file": {"newString": "str", "oldString": "str", "filePath": "str"},
    "list_directory": {"path": "str"},
    "search_files": {"pattern": "str"},
    # === Git MCP ===
    "git_status": {"repo_path": "str"},
    "git_diff": {"repo_path": "str", "target": "str"},
    "git_log": {"repo_path": "str", "max_count": "int"},
    "git_commit": {"message": "str", "files": "str"},
    # === GitHub MCP ===
    "github_list_issues": {"owner": "str", "repo": "str", "state": "str"},
    "github_create_pr": {"title": "str", "body": "str", "head": "str", "base": "str"},
    "github_search_code": {"q": "str"},
    "github_list_pull_requests": {"owner": "str", "repo": "str", "state": "str"},
    # === Context7 MCP ===
    "context7_resolve_library_id": {"libraryName": "str", "query": "str"},
    "context7_query_docs": {"libraryId": "str", "query": "str"},
    # === Fetch/Web MCP ===
    "fetch_url": {"url": "str", "format": "str"},
    "fetch_json": {"url": "str"},
    # === Sequential Thinking MCP ===
    "sequential_thinking": {
        "thought": "str",
        "nextThoughtNeeded": "bool",
        "thoughtNumber": "int",
        "totalThoughts": "int",
        "needsMoreThoughts": "bool",
    },
    # === Memory (Knowledge Graph) MCP ===
    "memory_search": {"query": "str", "limit": "int"},
    "memory_write": {"content": "str", "kind": "str", "scope": "str"},
    "memory_recall": {"session_id": "str", "limit": "int"},
    # === Athena MCP ===
    "athena_smart_search": {"query": "str"},
    "athena_agentic_search": {"query": "str", "context": "str"},
    "athena_quicksave": {"content": "str", "tags": "str"},
    # === NX Context MCP ===
    "get_active_context": {},
    "get_product_context": {},
    "get_user_context": {},
    "get_constraints": {},
    "get_user_profile": {},
    "inject_context": {"context_type": "str"},
    "get_capabilities": {},
    # === NX Mind MCP ===
    "get_mind_state": {},
    "update_mind_state": {"phase": "str", "project": "str", "active_tasks": "str"},
    "get_session_history": {"limit": "int"},
    "log_task_completion": {"task_id": "str", "success": "bool", "description": "str"},
    # === Trigger Guardian MCP ===
    "register_trigger": {"phrase": "str", "handler": "str", "pattern_type": "str"},
    "list_triggers": {},
    "check_trigger": {"input_text": "str"},
    "execute_trigger": {"phrase": "str"},
    # === Unified Memory MCP ===
    "unified_search": {"query": "str", "limit": "int"},
    "unified_create_memory": {"content": "str", "kind": "str"},
    "unified_get_stats": {},
    # === Learning Engine ===
    "route_task": {"task_description": "str"},
    "record_outcome": {"task": "str", "agent": "str", "success": "bool", "latency_ms": "int"},
    "get_learning_stats": {},
    "get_recommendations": {"task_description": "str"},
    # === Browser/TUI ===
    "browser_navigate": {"url": "str"},
    "browser_click": {"selector": "str"},
    "browser_fill": {"selector": "str", "value": "str"},
    "browser_screenshot": {"path": "str", "full_page": "bool"},
    # === Notion MCP ===
    "notion_get_page": {"page_id": "str"},
    "notion_create_page": {"parent": "str", "properties": "str"},
    "notion_query_db": {"data_source_id": "str", "filter": "str"},
    # === Health/System ===
    "get_health": {"level": "str"},
    "system_health_check": {},
    "brain_health_check": {},
    # === Intelligence/Routing ===
    "nx_intelligence_route": {"task_description": "str"},
    "nx_learning_route": {"task_description": "str"},
    "nx_brain_route": {"task_description": "str"},
    # === Quality Gates ===
    "run_typecheck": {},
    "run_lint": {},
    "run_format": {},
    "run_tests": {},
    "run_secrets_scan": {},
    # === Pipeline ===
    "pipeline_spawn": {"agent": "str", "task": "str"},
    "pipeline_orchestrate": {"user_input": "str"},
    "detect_state": {"user_input": "str"},
}


DEFAULT_CONFIG = {
    "lora": LoRAConfig(),
    "training": TrainingConfig(),
    "ollama": OllamaConfig(),
}
