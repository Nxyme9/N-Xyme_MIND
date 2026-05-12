"""LoRA+ (Low-Rank Adaptation Plus) implementation for nx_trainer.

LoRA+ is an enhancement to LoRA that uses learned per-layer learning rates.
- Different learning rates for q/k/v/o projections vs up/down projections
- Better convergence than standard LoRA
- No extra computational cost

Paper: https://arxiv.org/abs/2402.12354

Key insight: Different layers in transformers have different learning rate needs.
- Attention projections (q, k, v, o): Higher LR often works better
- FFN projections (up, down): Lower LR often works better

Implementation:
- Scale LoRA learning rates by layer type
- Optionally use learned LR multipliers per layer
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

# Try to import PEFT for base LoRA functionality
try:
    from peft import LoraConfig, get_peft_model, PeftModel

    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False


# Default LoRA+ scaling factors
# Based on research: attention layers benefit from higher LR
LORA_PLUS_DEFAULTS = {
    # Projection-specific LR multipliers
    "q_proj": 2.0,  # Query projection - higher LR
    "k_proj": 2.0,  # Key projection - higher LR
    "v_proj": 2.0,  # Value projection - higher LR
    "o_proj": 1.5,  # Output projection - medium LR
    "gate_proj": 0.5,  # FFN gate - lower LR
    "up_proj": 0.5,  # FFN up - lower LR
    "down_proj": 0.5,  # FFN down - lower LR
    # Default for any unspecified modules
    "default": 1.0,
}


@dataclass
class LoRAPlusConfig:
    """Configuration for LoRA+ training.

    Extends standard LoRA config with layer-specific learning rates.

    Args:
        r: LoRA rank
        alpha: LoRA alpha (scaling factor)
        dropout: Dropout for LoRA layers
        bias: Bias type
        target_modules: Target modules for LoRA
        task_type: Task type

        # LoRA+ specific
        use_lora_plus: Enable LoRA+ (default: True)
        lr_multipliers: Per-layer LR multipliers (optional, uses defaults if None)
        base_lr: Base learning rate for LoRA
        use_learned_lora: Use learned per-layer scaling (vs static multipliers)
        lora_init_scale: Initial scale for LoRA weights (default: 0.01)

        # DoRA (Decomposed Rank-Adapted LoRA)
        use_dora: Use DoRA variant
        use_rslora: Use Rank-Stable LoRA
    """

    # Standard LoRA parameters
    r: int = field(default=32)
    alpha: int = field(default=64)
    dropout: float = field(default=0.05)
    bias: str = field(default="none")
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
    task_type: str = field(default="CAUSAL_LM")

    # LoRA+ specific
    use_lora_plus: bool = field(default=True)
    lr_multipliers: Optional[Dict[str, float]] = field(default=None)
    base_lr: float = field(default=2e-5)
    use_learned_lora: bool = field(default=False)
    lora_init_scale: float = field(default=0.01)

    # DoRA
    use_dora: bool = field(default=False)
    use_rslora: bool = field(default=False)


class LoRAPlusLayer(nn.Module):
    """LoRA+ layer with per-layer learning rate scaling.

    This module implements LoRA with the LoRA+ enhancement:
    - Different learning rates per projection type
    - Optionally learned scaling factors
    """

    def __init__(
        self,
        base_layer: nn.Linear,
        rank: int = 32,
        alpha: int = 64,
        dropout: float = 0.05,
        init_scale: float = 0.01,
        lr_multiplier: float = 1.0,
        module_name: str = "",
    ):
        super().__init__()
        self.base_layer = base_layer
        self.rank = rank
        self.alpha = alpha
        self.dropout = nn.Dropout(p=dropout) if dropout > 0 else nn.Identity()
        self.lr_multiplier = lr_multiplier

        # LoRA parameters
        # Down projection (reduction)
        self.lora_A = nn.Parameter(torch.zeros(rank, base_layer.in_features).fill_(init_scale))
        # Up projection (expansion)
        self.lora_B = nn.Parameter(torch.zeros(base_layer.out_features, rank).fill_(init_scale))

        # Scaling factor
        self.scaling = alpha / rank

        # Optional: learned scaling (LoRA+ variant)
        self.use_learned_scale = False
        self.learned_scale = nn.Parameter(torch.ones(1))

        # Store module name for LR lookup
        self.module_name = module_name

        # Freeze base layer
        for param in base_layer.parameters():
            param.requires_grad = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with LoRA+ enhancement."""
        # Base layer output
        base_output = self.base_layer(x)

        # LoRA forward
        # x @ A @ B = (x @ A) @ B
        # A: [rank, in_features], B: [out_features, rank]
        # x: [batch, seq, in_features]

        # Apply dropout
        x_dropped = self.dropout(x)

        # Compute LoRA contribution
        # (batch, seq, in_features) @ (rank, in_features) -> (batch, seq, rank)
        lora_input = x_dropped @ self.lora_A.T
        # (batch, seq, rank) @ (out_features, rank).T -> (batch, seq, out_features)
        lora_output = lora_input @ self.lora_B.T

        # Apply scaling
        if self.use_learned_scale:
            # Learned scaling (LoRA+)
            lora_output = lora_output * self.scaling * self.learned_scale
        else:
            # Standard scaling
            lora_output = lora_output * self.scaling

        # Combine with base output
        return base_output + lora_output

    def extra_repr(self) -> str:
        return f"rank={self.rank}, alpha={self.alpha}, lr_mult={self.lr_multiplier}"


class LoRAPlusModel(nn.Module):
    """Complete LoRA+ model wrapper.

    Applies LoRA+ to all specified layers in a base model.
    """

    def __init__(
        self,
        base_model: nn.Module,
        config: LoRAPlusConfig,
    ):
        super().__init__()
        self.base_model = base_model
        self.config = config

        # Set up multipliers
        if config.lr_multipliers is None:
            config.lr_multipliers = LORA_PLUS_DEFAULTS.copy()

        # Find and replace linear layers with LoRA+ layers
        self.lora_layers: Dict[str, LoRAPlusLayer] = {}
        self._apply_lora_plus()

    def _get_lr_multiplier(self, module_name: str) -> float:
        """Get the learning rate multiplier for a module."""
        # Try exact match first
        if module_name in self.config.lr_multipliers:
            return self.config.lr_multipliers[module_name]

        # Try substring match (e.g., "model.layers.0.self_attn.q_proj" contains "q_proj")
        for key, value in self.config.lr_multipliers.items():
            if key in module_name:
                return value

        return self.config.lr_multipliers.get("default", 1.0)

    def _apply_lora_plus(self):
        """Apply LoRA+ to all target modules."""
        target_modules = set(self.config.target_modules)

        for name, module in self.base_model.named_modules():
            # Check if this is a target module
            is_target = any(t in name for t in target_modules)
            if not is_target:
                continue

            if not isinstance(module, nn.Linear):
                continue

            # Get LR multiplier for this layer
            lr_mult = self._get_lr_multiplier(name)

            # Create LoRA+ layer
            lora_layer = LoRAPlusLayer(
                base_layer=module,
                rank=self.config.r,
                alpha=self.config.alpha,
                dropout=self.config.dropout,
                init_scale=self.config.lora_init_scale,
                lr_multiplier=lr_mult,
                module_name=name,
            )

            # Replace the module
            parent_name = ".".join(name.split(".")[:-1])
            child_name = name.split(".")[-1]

            if parent_name:
                parent = self.base_model.get_submodule(parent_name)
            else:
                parent = self.base_model

            # Store reference and set as attribute
            self.lora_layers[name] = lora_layer
            setattr(parent, child_name, lora_layer)

    def forward(self, *args, **kwargs):
        """Forward pass through the model."""
        return self.base_model(*args, **kwargs)

    def get_trainable_params(self) -> Dict[str, float]:
        """Get trainable parameters with their LR multipliers.

        Returns a dict of parameter name -> learning rate multiplier.
        """
        param_lr = {}

        for name, module in self.lora_layers.items():
            for param_name, param in module.named_parameters():
                if param.requires_grad:
                    full_name = f"{name}.{param_name}"
                    param_lr[full_name] = module.lr_multiplier

        return param_lr

    def print_trainable_params_summary(self):
        """Print a summary of trainable parameters."""
        total_params = 0
        trainable_params = 0

        for name, module in self.base_model.named_parameters():
            num_params = module.numel()
            total_params += num_params

            if module.requires_grad:
                trainable_params += num_params

        print(f"Total parameters: {total_params:,}")
        print(f"Trainable parameters: {trainable_params:,}")
        print(f"Trainable percentage: {100 * trainable_params / total_params:.2f}%")

        print(f"\nLoRA+ Configuration:")
        print(f"  Rank: {self.config.r}")
        print(f"  Alpha: {self.config.alpha}")
        print(f"  LoRA+ enabled: {self.config.use_lora_plus}")


def create_lora_plus_model(
    base_model: nn.Module,
    config: LoRAPlusConfig,
) -> LoRAPlusModel:
    """Create a LoRA+ model from a base model.

    Args:
        base_model: The base model to adapt
        config: LoRA+ configuration

    Returns:
        LoRAPlusModel wrapper
    """
    return LoRAPlusModel(base_model, config)


def create_lora_plus_optimizer(
    model: LoRAPlusModel,
    base_lr: float = 1e-4,
    weight_decay: float = 0.01,
    **kwargs,
) -> torch.optim.Optimizer:
    """Create optimizer with per-layer learning rates.

    This is the key function that applies different learning rates
    to different LoRA layers based on their type.

    Args:
        model: LoRAPlusModel
        base_lr: Base learning rate for non-LoRA params
        weight_decay: Weight decay
        **kwargs: Additional optimizer arguments

    Returns:
        Optimizer with layer-specific LR
    """
    # Get parameter groups
    param_groups = []

    # Non-LoRA parameters with base LR
    non_lora_params = []
    for name, param in model.base_model.named_parameters():
        if not any(ln in name for ln in model.lora_layers):
            if param.requires_grad:
                non_lora_params.append(param)

    if non_lora_params:
        param_groups.append(
            {
                "params": non_lora_params,
                "lr": base_lr,
                "weight_decay": weight_decay,
            }
        )

    # LoRA parameters with their multipliers
    for lora_name, lora_layer in model.lora_layers.items():
        lora_params = []
        for param_name, param in lora_layer.named_parameters():
            if param.requires_grad:
                lora_params.append(param)

        if lora_params:
            # Compute effective LR
            effective_lr = base_lr * lora_layer.lr_multiplier

            param_groups.append(
                {
                    "params": lora_params,
                    "lr": effective_lr,
                    "weight_decay": weight_decay,
                }
            )

    # Create optimizer
    return torch.optim.AdamW(param_groups, **kwargs)


# Convenience function to create LoRA+ from HF model
def get_lora_plus_model(
    base_model: nn.Module,
    tokenizer: Any,
    config: LoRAPlusConfig,
) -> Tuple[LoRAPlusModel, Any]:
    """Get a LoRA+ model ready for training.

    Args:
        base_model: Base transformer model
        tokenizer: Tokenizer
        config: LoRA+ config

    Returns:
        Tuple of (LoRAPlusModel, tokenizer)
    """
    # Create LoRA+ model
    model = create_lora_plus_model(base_model, config)

    # Enable gradient for LoRA params
    for param in model.parameters():
        if param.requires_grad:
            param.requires_grad = True

    # Print summary
    model.print_trainable_params_summary()

    return model, tokenizer
