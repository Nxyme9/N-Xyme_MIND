"""LoCo (Low-Rank Communication) variants for distributed training.

Implements multiple low-communication training methods:
1. DiLoCo: Distributed Low-Communication training
2. LoCo: Low-bit Communication with error feedback
3. FLoCoRA: Federated LoRA

Paper: https://arxiv.org/abs/2311.08105 (DiLoCo)
"""

import torch
import torch.nn as nn
import torch.distributed as dist
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from nx_trainer.vera import VeRAConfig


@dataclass
class DiLoCoConfig:
    """Configuration for DiLoCo (Distributed Low-Communication) training.

    Args:
        num_inner_steps: Number of local updates before sync (H)
        outer_lr: Learning rate for outer optimizer
        momentum: Momentum for outer optimizer (Nesterov)
        warmup_steps: Warmup steps for outer LR
    """

    num_inner_steps: int = field(default=500)
    outer_lr: float = field(default=1e-3)
    momentum: float = field(default=0.9)
    warmup_steps: int = field(default=100)


@dataclass
class LoCoConfig:
    """Configuration for LoCo (Low-bit Communication) training.

    Args:
        bits: Number of bits for quantization (default: 4)
        momentum: Momentum for error feedback
    """

    bits: int = field(default=4)
    momentum: float = field(default=0.9)


class DiLoCoWorker:
    """DiLoCo worker for distributed low-communication training.

    Each worker:
    1. Does H local training steps with inner optimizer
    2. Computes pseudo-gradients: Δ = θ(t-1) - θ(t)_i
    3. All-reduce pseudo-gradients across workers
    4. Updates with outer optimizer (Nesterov momentum)
    5. Syncs parameters back to workers

    Key benefit: 500x less communication than standard DDP
    """

    def __init__(
        self,
        model: nn.Module,
        config: DiLoCoConfig,
        inner_optimizer: Optional[torch.optim.Optimizer] = None,
    ):
        self.model = model
        self.config = config
        self.inner_optimizer = inner_optimizer or torch.optim.AdamW(model.parameters(), lr=1e-4)

        # Outer optimizer (Nesterov momentum)
        self.params = list(model.parameters())
        self.velocity = [torch.zeros_like(p) for p in self.params]
        self.outer_lr = config.outer_lr
        self.momentum = config.momentum

        # State
        self.step_count = 0
        self.prev_params = [p.clone() for p in self.params]

    def _sync_parameters(self, new_params: List[torch.Tensor]):
        """Sync parameters from averaged values."""
        for p, new_p in zip(self.params, new_params):
            p.data.copy_(new_p.data)

    def local_step(self, loss_fn, *args, **kwargs):
        """Perform one local training step (inner optimizer).

        Args:
            loss_fn: Loss function to evaluate
            *args, **kwargs: Arguments for loss_fn

        Returns:
            Loss value
        """
        self.inner_optimizer.zero_grad()
        loss = loss_fn(*args, **kwargs)
        loss.backward()
        self.inner_optimizer.step()

        self.step_count += 1
        return loss.item()

    def compute_pseudo_gradients(self) -> List[torch.Tensor]:
        """Compute pseudo-gradients: θ(t-1) - θ(t)_i

        These are the differences between parameters before local training
        and after local training. They represent the worker's contribution.
        """
        pseudo_grads = []
        for prev_p, curr_p in zip(self.prev_params, self.params):
            pseudo_grads.append(prev_p - curr_p)

        # Update previous parameters for next round
        for prev_p, curr_p in zip(self.prev_params, self.params):
            prev_p.data.copy_(curr_p.data)

        return pseudo_grads

    def sync_and_update(self, pseudo_grads: List[torch.Tensor]):
        """All-reduce pseudo-gradients and update with outer optimizer.

        Args:
            pseudo_grads: Local pseudo-gradients
        """
        if not dist.is_initialized():
            return

        world_size = dist.get_world_size()

        # All-reduce pseudo-gradients
        for pg in pseudo_grads:
            dist.all_reduce(pg, op=dist.ReduceOp.SUM)
            pg.div_(world_size)

        # Update with Nesterov momentum
        for i, (p, pg) in enumerate(zip(self.params, pseudo_grads)):
            # Nesterov momentum update
            self.velocity[i] = self.momentum * self.velocity[i] + pg
            p.data.add_(self.velocity[i], alpha=-self.outer_lr)

    def step(self, loss_fn, *args, **kwargs) -> float:
        """Full DiLoCo step: local training + sync.

        Performs H local steps, then synchronizes with other workers.

        Returns:
            Average loss over the step
        """
        local_losses = []

        # Local training steps
        for _ in range(self.config.num_inner_steps):
            loss = self.local_step(loss_fn, *args, **kwargs)
            local_losses.append(loss)

        # Compute pseudo-gradients
        pseudo_grads = self.compute_pseudo_gradients()

        # Sync and update
        self.sync_and_update(pseudo_grads)

        return sum(local_losses) / len(local_losses) if local_losses else 0.0


class LoCoQuantizer:
    """Low-bit communication quantizer with error feedback.

    Compresses gradients to low bits (e.g., 4-bit) before communication,
    using error feedback to compensate for quantization loss.

    Paper: https://arxiv.org/abs/2407.04480
    """

    def __init__(self, config: LoCoConfig):
        self.config = config
        self.error = None  # Accumulated quantization error

    def quantize(self, tensor: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Quantize tensor to low bits.

        Args:
            tensor: Input tensor

        Returns:
            Tuple of (quantized tensor, original tensor for reconstruction)
        """
        bits = self.config.bits
        num_levels = 2**bits

        # Find range
        vmin = tensor.min()
        vmax = tensor.max()

        # Quantize to levels
        scale = (vmax - vmin) / (num_levels - 1)
        quantized = ((tensor - vmin) / scale).round().clamp(0, num_levels - 1)

        # Dequantize
        dequantized = quantized * scale + vmin

        # Store error for feedback
        self.error = tensor - dequantized

        return quantized, tensor

    def decompress(
        self, quantized: torch.Tensor, original_range: Tuple[float, float]
    ) -> torch.Tensor:
        """Decompress quantized tensor.

        Args:
            quantized: Quantized tensor
            original_range: Original (vmin, vmax)

        Returns:
            Decompressed tensor
        """
        vmin, vmax = original_range
        bits = self.config.bits
        num_levels = 2**bits

        scale = (vmax - vmin) / (num_levels - 1)
        decompressed = quantized * scale + vmin

        # Apply error feedback
        if self.error is not None:
            decompressed = decompressed + self.config.momentum * self.error

        return decompressed


class FLoCoRA:
    """Federated LoRA with low communication.

    Combines LoRA adapters with federated learning to reduce
    communication overhead by only sharing adapter parameters.

    Paper: https://arxiv.org/abs/2406.14082

    Benefits:
    - 4.8x communication reduction
    - <1% accuracy loss
    - Quantization can further reduce to 18.6x
    """

    def __init__(
        self,
        base_model: nn.Module,
        config: VeRAConfig,  # Reuse VeRA config for LoRA params
    ):
        self.base_model = base_model
        self.config = config
        self.lora_state = {}  # Store LoRA parameters

    def get_lora_params(self) -> Dict[str, torch.Tensor]:
        """Get only LoRA parameters for communication.

        Returns:
            Dict of LoRA parameter name -> tensor
        """
        lora_params = {}

        for name, param in self.base_model.named_parameters():
            if "lora" in name.lower() or "adapter" in name.lower():
                lora_params[name] = param.data.clone()

        return lora_params

    def apply_lora_params(self, lora_params: Dict[str, torch.Tensor]):
        """Apply received LoRA parameters.

        Args:
            lora_params: Dict of LoRA parameters from server/other clients
        """
        for name, param in lora_params.items():
            if name in dict(self.base_model.named_parameters()):
                self.base_model.named_parameters()[name].data.copy_(param.data)

    def federated_averaging(self, client_params_list: List[Dict[str, torch.Tensor]]):
        """Average LoRA parameters across clients.

        Args:
            client_params_list: List of client LoRA parameter dicts
        """
        if not client_params_list:
            return

        num_clients = len(client_params_list)

        # Average each parameter
        for key in client_params_list[0].keys():
            total = sum(cp[key] for cp in client_params_list)
            averaged = total / num_clients

            # Apply averaged parameters
            if key in dict(self.base_model.named_parameters()):
                self.base_model.named_parameters()[key].data.copy_(averaged)


# Factory functions
def create_diloco_worker(
    model: nn.Module,
    num_inner_steps: int = 500,
    outer_lr: float = 1e-3,
    **kwargs,
) -> DiLoCoWorker:
    """Create a DiLoCo worker.

    Args:
        model: Model to train
        num_inner_steps: Local steps before sync
        outer_lr: Outer optimizer learning rate
        **kwargs: Additional DiLoCoConfig parameters

    Returns:
        DiLoCoWorker
    """
    config = DiLoCoConfig(num_inner_steps=num_inner_steps, outer_lr=outer_lr, **kwargs)
    return DiLoCoWorker(model, config)


def create_loco_quantizer(bits: int = 4) -> LoCoQuantizer:
    """Create a LoCo quantizer.

    Args:
        bits: Quantization bits

    Returns:
        LoCoQuantizer
    """
    config = LoCoConfig(bits=bits)
    return LoCoQuantizer(config)


# Example usage
def example_diloco_training():
    """Example showing DiLoCo training loop."""
    import torch

    # Create model and worker
    model = nn.Linear(100, 100)
    worker = create_diloco_worker(model, num_inner_steps=10, outer_lr=1e-3)

    # Dummy loss function
    def loss_fn():
        return torch.randn(1, requires_grad=True)

    # Training loop
    for step in range(100):
        loss = worker.step(loss_fn)

        if step % 10 == 0:
            print(f"Step {step}, Loss: {loss:.4f}")

    print("DiLoCo training complete!")


if __name__ == "__main__":
    example_diloco_training()
