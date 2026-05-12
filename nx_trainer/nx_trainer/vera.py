"""VeRA (Vector-based Random Matrix Adaptation) implementation for nx_trainer.

VeRA is a parameter-efficient LoRA variant that uses:
- A SINGLE pair of random matrices shared across ALL layers
- Small trainable scaling vectors (λb and λd) per layer
- ~10x fewer trainable parameters than standard LoRA

Paper: https://arxiv.org/abs/2310.11454 (ICLR 2024)

Key differences from LoRA:
- LoRA: trains two low-rank matrices (A and B) per layer
- VeRA: uses frozen random matrices shared across all layers,
  plus per-layer scaling vectors (b and d)
- ΔW = Λb × B × Λd × A where Λb, Λd are diagonal
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np


# Default VeRA scaling factors
VERA_DEFAULTS = {
    "rank": 16,  # VeRA typically uses smaller rank than LoRA
    "init_scale": 0.01,
}


@dataclass
class VeRAConfig:
    """Configuration for VeRA (Vector-based Random Matrix Adaptation).

    Args:
        r: VeRA rank (typically smaller than LoRA rank)
        target_modules: Target modules for VeRA
        seed: Random seed for reproducibility
        save_projection: Whether to save projection matrices (vs regenerate)
        init_strategy: How to initialize - 'random' or 'zeros'
    """

    r: int = field(default=16)
    target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )
    seed: int = field(default=42)
    save_projection: bool = field(default=True)
    init_strategy: str = field(default="random")


class VeRALayer(nn.Module):
    """VeRA layer with shared random matrices and per-layer scaling.

    Core formula: ΔW = Λb × B × Λd × A
    - A, B: Random matrices (shared across ALL layers, frozen)
    - λb, λd: Trainable scaling vectors (per layer)
    """

    def __init__(
        self,
        base_layer: nn.Linear,
        rank: int = 16,
        seed: int = 42,
        init_scale: float = 0.01,
    ):
        super().__init__()
        self.base_layer = base_layer
        self.rank = rank
        self.seed = seed

        in_features = base_layer.in_features
        out_features = base_layer.out_features

        # Freeze base layer
        for param in base_layer.parameters():
            param.requires_grad = False

        # Set random seed for reproducibility
        rng = np.random.default_rng(seed)

        # Shared random matrices A and B (frozen, shared across layers)
        # A: [rank, in_features], B: [out_features, rank]
        self.register_buffer(
            "A",
            torch.from_numpy(rng.standard_normal((rank, in_features)).astype(np.float32))
            * init_scale,
        )
        self.register_buffer(
            "B",
            torch.from_numpy(rng.standard_normal((out_features, rank)).astype(np.float32))
            * init_scale,
        )

        # Trainable scaling vectors (per layer)
        # λb: [out_features], λd: [rank]
        self.lambda_b = nn.Parameter(torch.ones(out_features))
        self.lambda_d = nn.Parameter(torch.ones(rank))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with VeRA adaptation.

        ΔW = Λb × B × Λd × A
        where Λb, Λd are diagonal matrices from λb, λd
        """
        # Base layer output
        base_output = self.base_layer(x)

        # VeRA forward: x @ (Λb @ B @ Λd @ A).T
        # = x @ A.T @ Λd @ B.T @ Λb

        # Apply A (rank x in) - x: [batch, seq, in] -> [batch, seq, rank]
        # (batch, seq, in) @ (rank, in).T = (batch, seq, rank)
        h = torch.einsum("bsi,ri->bsr", x, self.A)

        # Apply λd scaling: (batch, seq, rank) * (rank,) -> (batch, seq, rank)
        h = h * self.lambda_d.unsqueeze(0).unsqueeze(0)

        # Apply B: (batch, seq, rank) @ (out, rank).T = (batch, seq, out)
        h = torch.einsum("bsr,or->bso", h, self.B)

        # Apply λb scaling: (batch, seq, out) * (out,) -> (batch, seq, out)
        h = h * self.lambda_b.unsqueeze(0).unsqueeze(0)

        return base_output + h

    def extra_repr(self) -> str:
        return f"rank={self.rank}, seed={self.seed}"


class VeRAModel(nn.Module):
    """Complete VeRA model wrapper.

    Applies VeRA to all specified layers in a base model.
    All layers share the same random matrices A and B!
    """

    def __init__(
        self,
        base_model: nn.Module,
        config: VeRAConfig,
    ):
        super().__init__()
        self.base_model = base_model
        self.config = config
        selfvera_layers: Dict[str, VeRALayer] = {}
        self._apply_vera()

    def _apply_vera(self):
        """Apply VeRA to all target modules."""
        target_modules = set(self.config.target_modules)

        for name, module in self.base_model.named_modules():
            is_target = any(t in name for t in target_modules)
            if not is_target:
                continue

            if not isinstance(module, nn.Linear):
                continue

            # Create VeRA layer
            vera_layer = VeRALayer(
                base_layer=module,
                rank=self.config.r,
                seed=self.config.seed,
            )

            # Replace the module
            parent_name = ".".join(name.split(".")[:-1])
            child_name = name.split(".")[-1]

            if parent_name:
                parent = self.base_model.get_submodule(parent_name)
            else:
                parent = self.base_model

            self.vera_layers[name] = vera_layer
            setattr(parent, child_name, vera_layer)

    def forward(self, *args, **kwargs):
        """Forward pass through the model."""
        return self.base_model(*args, **kwargs)

    def print_trainable_params_summary(self):
        """Print a summary of trainable parameters."""
        total_params = 0
        trainable_params = 0
        vera_params = 0

        for name, param in self.base_model.named_parameters():
            num_params = param.numel()
            total_params += num_params

            if param.requires_grad:
                trainable_params += num_params
                if "lambda" in name:
                    vera_params += num_params

        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
        print(f"  - VeRA scaling vectors: {vera_params:,}")
        print(f"Trainable percentage: {100 * trainable_params / total_params:.4f}%")

        print(f"\nVeRA Configuration:")
        print(f"  Rank: {self.config.r}")
        print(f"  Seed: {self.config.seed}")
        print(f"  Shared matrices A, B: {self.config.r}x(in/out)")


def create_vera_model(
    base_model: nn.Module,
    config: VeRAConfig,
) -> VeRAModel:
    """Create a VeRA model from a base model.

    Args:
        base_model: The base model to adapt
        config: VeRA configuration

    Returns:
        VeRAModel wrapper
    """
    return VeRAModel(base_model, config)


def create_vera_optimizer(
    model: VeRAModel,
    lr: float = 1e-4,
    weight_decay: float = 0.01,
    **kwargs,
) -> torch.optim.Optimizer:
    """Create optimizer for VeRA model.

    Only optimizes the lambda scaling vectors (b and d).
    The random matrices A and B are frozen buffers.

    Args:
        model: VeRAModel
        lr: Learning rate
        weight_decay: Weight decay
        **kwargs: Additional optimizer arguments

    Returns:
        Optimizer
    """
    # Collect only lambda parameters (the trainable parts)
    lambda_params = []
    for module in model.vera_layers.values():
        lambda_params.extend([module.lambda_b, module.lambda_d])

    return torch.optim.AdamW(
        [{"params": lambda_params, "lr": lr, "weight_decay": weight_decay}], **kwargs
    )


# Comparison: VeRA vs LoRA parameter count
def compare_vera_lora_params(
    model_dim: int,
    hidden_dim: int,
    num_layers: int,
    rank: int = 16,
) -> Dict[str, int]:
    """Compare trainable parameters between VeRA and LoRA.

    Args:
        model_dim: Model dimension (e.g., 4096 for Llama 7B)
        hidden_dim: Hidden dimension (e.g., 11008 for Llama 7B)
        num_layers: Number of layers
        rank: LoRA/VeRA rank

    Returns:
        Dict with parameter counts
    """
    # LoRA: 2 matrices per layer (A: rank x in, B: out x rank)
    lora_params = 2 * num_layers * (model_dim * rank + hidden_dim * rank)

    # VeRA: Only scaling vectors per layer (λb: out, λd: rank)
    vera_params = num_layers * (hidden_dim + rank)

    return {
        "lora": lora_params,
        "vera": vera_params,
        "ratio": lora_params / vera_params if vera_params > 0 else 0,
    }


# Convenience function
def get_vera_model(
    base_model: nn.Module,
    tokenizer: Any,
    rank: int = 16,
    seed: int = 42,
) -> Tuple[VeRAModel, Any]:
    """Get a VeRA model ready for training.

    Args:
        base_model: Base transformer model
        tokenizer: Tokenizer
        rank: VeRA rank
        seed: Random seed

    Returns:
        Tuple of (VeRAModel, tokenizer)
    """
    config = VeRAConfig(r=rank, seed=seed)
    model = create_vera_model(base_model, config)
    model.print_trainable_params_summary()

    return model, tokenizer
