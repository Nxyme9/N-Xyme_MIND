"""
Training Loop for RosEnna Trainer.
Implements contrastive learning training with curriculum phases.
"""

import os
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import Optimizer
from torch.optim.lr_scheduler import LambdaLR
from tqdm import tqdm

from model.losses import (
    multi_negatives_ranking_loss,
    gist_embed_loss,
    accuracy_at_k,
)
from training.curriculum import get_phase, PHASES


@dataclass
class TrainingState:
    """Training state for logging and checkpointing."""
    epoch: int
    global_step: int
    phase_name: str
    loss: float
    accuracy: float
    lr: float
    temperature: float
    vram_mb: float


class TrainingLoop:
    """
    Training loop for contrastive embedding model.
    Handles gradient accumulation, curriculum phases, and checkpointing.
    """

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        optimizer: Optional[Optimizer] = None,
        device: str = "cuda",
        grad_clip: float = 1.0,
        grad_accum_steps: int = 1,
        checkpoint_dir: str = "checkpoints",
        log_interval: int = 10,
    ):
        """
        Initialize training loop.

        Args:
            model: The model to train
            train_loader: Training data loader
            val_loader: Optional validation data loader
            optimizer: Optimizer (created if None)
            device: Device to train on
            grad_clip: Gradient clipping threshold
            grad_accum_steps: Gradient accumulation steps
            checkpoint_dir: Directory to save checkpoints
            log_interval: Logging interval in steps
        """
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device
        self.grad_clip = grad_clip
        self.grad_accum_steps = grad_accum_steps
        self.checkpoint_dir = checkpoint_dir
        self.log_interval = log_interval

        # Setup optimizer if not provided
        if optimizer is None:
            self.optimizer = self._create_optimizer()
        else:
            self.optimizer = optimizer

        # Training state
        self.current_epoch = 0
        self.global_step = 0
        self.best_val_acc = 0.0

        # Create checkpoint directory
        os.makedirs(checkpoint_dir, exist_ok=True)

    def _create_optimizer(self) -> Optimizer:
        """Create optimizer with different learning rates for backbone and head."""
        # Separate parameters for different learning rates
        backbone_params = []
        head_params = []

        for name, param in self.model.named_parameters():
            if "pooler" in name or "head" in name:
                head_params.append(param)
            else:
                backbone_params.append(param)

        # Use different learning rates
        optimizer = torch.optim.AdamW([
            {"params": backbone_params, "lr": 2e-4},
            {"params": head_params, "lr": 1e-3},
        ])

        return optimizer

    def _create_scheduler(self, total_steps: int):
        """Create learning rate scheduler."""
        def warmup_schedule(step):
            warmup_ratio = 0.1
            warmup_steps = int(total_steps * warmup_ratio)
            if step < warmup_steps:
                return step / warmup_steps
            return 1.0

        scheduler = LambdaLR(self.optimizer, warmup_schedule)
        return scheduler

    def train(
        self,
        max_epochs: int = 10,
        temperature: float = 0.05,
        use_hard_negatives: bool = False,
    ) -> Dict[str, Any]:
        """
        Run the full training loop.

        Args:
            max_epochs: Maximum number of epochs
            temperature: Default temperature for loss
            use_hard_negatives: Whether to use hard negatives

        Returns:
            Training history dictionary
        """
        history = {
            "train_loss": [],
            "train_acc": [],
            "val_loss": [],
            "val_acc": [],
            "phase": [],
        }

        total_batches = len(self.train_loader)
        total_steps = total_batches * max_epochs
        scheduler = self._create_scheduler(total_steps)

        for epoch in range(max_epochs):
            self.current_epoch = epoch

            # Get current phase from curriculum
            phase = get_phase(epoch)
            current_temp = phase.temperature
            current_hard_neg = phase.hard_negatives_only

            # Log phase info
            print(f"\n{'='*60}")
            print(f"Epoch {epoch + 1}/{max_epochs}")
            print(f"Phase: {phase.name} - {phase.description}")
            print(f"Temperature: {current_temp}, Hard Negatives: {current_hard_neg}")
            print(f"Negatives per anchor: {phase.negatives_per_anchor}")
            print(f"{'='*60}")

            # Train one epoch
            train_loss, train_acc = self._train_epoch(
                temperature=current_temp,
                use_hard_negatives=current_hard_neg,
                negatives_per_anchor=phase.negatives_per_anchor,
            )

            history["train_loss"].append(train_loss)
            history["train_acc"].append(train_acc)
            history["phase"].append(phase.name)

            # Validation
            if self.val_loader is not None:
                val_loss, val_acc = self._validate(
                    temperature=current_temp,
                    use_hard_negatives=current_hard_neg,
                )
                history["val_loss"].append(val_loss)
                history["val_acc"].append(val_acc)

                print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")

                # Save best model
                if val_acc > self.best_val_acc:
                    self.best_val_acc = val_acc
                    self._save_checkpoint("best.pt", {"val_acc": val_acc})

            # Save periodic checkpoint
            self._save_checkpoint(f"epoch_{epoch + 1}.pt", {"epoch": epoch})

        return history

    def _train_epoch(
        self,
        temperature: float,
        use_hard_negatives: bool,
        negatives_per_anchor: int,
    ) -> tuple:
        """
        Train for one epoch.

        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()

        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        optimizer = self.optimizer

        progress_bar = tqdm(self.train_loader, desc=f"Training")

        for batch_idx, batch in enumerate(progress_bar):
            # Get batch data
            anchors = batch["anchor"]  # List of query strings
            positives = batch["positive"]  # List of tool description strings
            negatives = batch.get("negative", [])  # Optional hard negatives

            # Encode to embeddings
            anchor_emb = self.model.encode_batch(anchors).to(self.device)
            positive_emb = self.model.encode_batch(positives).to(self.device)

            # Compute loss based on curriculum settings
            if use_hard_negatives and len(negatives) > 0:
                # Use GIST loss with hard negatives
                negative_emb = self.model.encode_batch(negatives).to(self.device)
                loss = gist_embed_loss(
                    anchor_emb,
                    positive_emb,
                    negative_emb,
                    temperature=temperature,
                )
            else:
                # Use standard MNR loss
                loss = multi_negatives_ranking_loss(
                    anchor_emb,
                    positive_emb,
                    temperature=temperature,
                )

            # Gradient accumulation
            loss = loss / self.grad_accum_steps

            loss.backward()

            # Update weights every grad_accum_steps
            if (batch_idx + 1) % self.grad_accum_steps == 0:
                # Gradient clipping
                if self.grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.grad_clip
                    )

                optimizer.step()
                optimizer.zero_grad()

            # Compute accuracy for this batch
            with torch.no_grad():
                acc = accuracy_at_k(anchor_emb, positive_emb, k=1)

            # Update metrics
            batch_size = anchor_emb.size(0)
            total_loss += loss.item() * self.grad_accum_steps
            total_correct += int(acc * batch_size)
            total_samples += batch_size

            # Update progress bar
            progress_bar.set_postfix({
                "loss": f"{total_loss / (batch_idx + 1):.4f}",
                "acc": f"{total_correct / total_samples:.4f}",
                "temp": f"{temperature}",
            })

            self.global_step += 1

        avg_loss = total_loss / len(self.train_loader)
        avg_acc = total_correct / total_samples

        return avg_loss, avg_acc

    def _validate(
        self,
        temperature: float,
        use_hard_negatives: bool,
    ) -> tuple:
        """
        Run validation.

        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.eval()

        total_loss = 0.0
        total_correct = 0
        total_samples = 0

        with torch.no_grad():
            for batch in self.val_loader:
                anchors = batch["anchor"]
                positives = batch["positive"]

                anchor_emb = self.model.encode_batch(anchors).to(self.device)
                positive_emb = self.model.encode_batch(positives).to(self.device)

                loss = multi_negatives_ranking_loss(
                    anchor_emb,
                    positive_emb,
                    temperature=temperature,
                )

                acc = accuracy_at_k(anchor_emb, positive_emb, k=1)

                batch_size = anchor_emb.size(0)
                total_loss += loss.item() * batch_size
                total_correct += int(acc * batch_size)
                total_samples += batch_size

        avg_loss = total_loss / len(self.val_loader)
        avg_acc = total_correct / total_samples

        return avg_loss, avg_acc

    def _save_checkpoint(self, filename: str, metadata: dict):
        """Save model checkpoint."""
        filepath = os.path.join(self.checkpoint_dir, filename)

        checkpoint = {
            "model_state": self.model.state_dict() if hasattr(self.model, 'state_dict') else {},
            "optimizer_state": self.optimizer.state_dict(),
            "metadata": metadata,
        }

        # For PEFT models, save adapters
        if hasattr(self.model, 'save_pretrained'):
            base_path = filepath.replace(".pt", "")
            self.model.save_pretrained(base_path)

        torch.save(checkpoint, filepath)
        print(f"Checkpoint saved: {filepath}")


def train(
    config,
    model,
    train_dataset,
    val_dataset=None,
    device: str = "cuda",
):
    """
    Main training function.

    Args:
        config: TrainingConfig from config.py
        model: RosEnnaEncoder model
        train_dataset: Training dataset
        val_dataset: Optional validation dataset
        device: Device to train on

    Returns:
        Training history dictionary
    """
    from torch.utils.data import DataLoader

    # Create data loaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=2,
        pin_memory=True,
    )

    val_loader = None
    if val_dataset is not None:
        val_loader = DataLoader(
            val_dataset,
            batch_size=config.batch_size,
            shuffle=False,
            num_workers=2,
            pin_memory=True,
        )

    # Create training loop
    loop = TrainingLoop(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        grad_clip=config.grad_clip,
        grad_accum_steps=config.grad_accum_steps,
    )

    # Run training
    history = loop.train(
        max_epochs=config.max_epochs,
        temperature=config.temperature,
    )

    return history