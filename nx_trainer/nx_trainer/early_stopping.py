# -*- coding: utf-8 -*-
"""
Early Stopping Callback for Training
=====================================

Prevents overfitting by stopping when validation loss stops improving.

Usage:
    from nx_trainer.early_stopping import EarlyStoppingCallback

    callback = EarlyStoppingCallback(
        patience=3,
        min_delta=0.01,
        metric="loss",
        direction="minimize"
    )

    # In training loop:
    for epoch in range(epochs):
        train_loss = train_epoch()
        eval_loss = eval()

        should_stop = callback.on_eval_end(eval_loss, epoch)
        if should_stop:
            print("Early stopping triggered!")
            break
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger("trainer.early_stopping")


@dataclass
class EarlyStoppingConfig:
    """Configuration for early stopping."""

    patience: int = 3  # Number of epochs to wait for improvement
    min_delta: float = 0.01  # Minimum change to count as improvement
    metric: str = "loss"  # Metric to monitor
    direction: str = "minimize"  # "minimize" or "maximize"
    warmup_epochs: int = 1  # Don't trigger early stopping during warmup


@dataclass
class TrainingHistory:
    """Track training metrics over time."""

    epochs: list = field(default_factory=list)
    train_loss: list = field(default_factory=list)
    eval_loss: list = field(default_factory=list)
    accuracy: list = field(default_factory=list)
    learning_rate: list = field(default_factory=list)
    grad_norm: list = field(default_factory=list)

    def add(self, epoch: int, **metrics):
        self.epochs.append(epoch)
        for key, value in metrics.items():
            if key == "train_loss":
                self.train_loss.append(value)
            elif key == "eval_loss":
                self.eval_loss.append(value)
            elif key == "accuracy":
                self.accuracy.append(value)
            elif key == "lr":
                self.learning_rate.append(value)
            elif key == "grad_norm":
                self.grad_norm.append(value)

    def is_improving(
        self,
        current: float,
        window: int = 3,
        direction: str = None,
        min_delta: float = None,
    ) -> bool:
        """Check if metric is trending in the right direction."""
        if len(self.epochs) < window + 1:
            return True

        # Use provided values or fall back to config
        direction = direction or self.config.direction
        min_delta = min_delta or self.config.min_delta

        if direction == "minimize":
            recent = self.eval_loss[-window:]
            return current < min(recent) - min_delta
        else:
            recent = self.accuracy[-window:]
            return current > max(recent) + min_delta


class EarlyStoppingCallback:
    """
    Early stopping callback to prevent overfitting.

    Watches a metric and stops training when it stops improving.
    """

    def __init__(
        self,
        patience: int = 3,
        min_delta: float = 0.01,
        metric: str = "loss",
        direction: str = "minimize",
        warmup_epochs: int = 1,
        on_stopping: Optional[Callable] = None,
    ):
        self.config = EarlyStoppingConfig(
            patience=patience,
            min_delta=min_delta,
            metric=metric,
            direction=direction,
            warmup_epochs=warmup_epochs,
        )
        self.on_stopping = on_stopping

        # State
        self.best_value = None
        self.wait_count = 0
        self.should_stop = False
        self.stopped_epoch = 0

        logger.info(f"EarlyStopping initialized: {self}")

    def __repr__(self):
        return (
            f"EarlyStopping(patience={self.config.patience}, "
            f"min_delta={self.config.min_delta}, "
            f"metric={self.config.metric}, "
            f"direction={self.config.direction})"
        )

    def on_train_begin(self):
        """Called at the beginning of training."""
        self.best_value = None
        self.wait_count = 0
        self.should_stop = False
        logger.info("Training started - early stopping monitoring active")

    def on_epoch_end(self, epoch: int, **metrics) -> bool:
        """
        Called at the end of each epoch.

        Returns True if training should stop.
        """
        # Get current metric value
        if self.config.metric == "loss":
            current = metrics.get("eval_loss") or metrics.get("train_loss")
        elif self.config.metric == "accuracy":
            current = metrics.get("accuracy")
        else:
            current = metrics.get(self.config.metric)

        if current is None:
            logger.warning(f"Metric '{self.config.metric}' not found in metrics")
            return False

        # Check if in warmup period
        if epoch < self.config.warmup_epochs:
            logger.info(f"Epoch {epoch}: In warmup period, skipping early stopping check")
            return False

        # Initialize best value
        if self.best_value is None:
            self.best_value = current
            logger.info(f"Epoch {epoch}: Best {self.config.metric} = {current:.4f}")
            return False

        # Check for improvement
        if self.config.direction == "minimize":
            improved = current < (self.best_value - self.config.min_delta)
        else:
            improved = current > (self.best_value + self.config.min_delta)

        if improved:
            # Reset patience
            old_best = self.best_value
            self.best_value = current
            self.wait_count = 0
            logger.info(
                f"Epoch {epoch}: New best {self.config.metric} = {current:.4f} (was {old_best:.4f})"
            )
        else:
            # Increment patience counter
            self.wait_count += 1
            logger.info(
                f"Epoch {epoch}: No improvement. "
                f"{self.config.metric} = {current:.4f}, "
                f"best = {self.best_value:.4f}. "
                f"Waiting: {self.wait_count}/{self.config.patience}"
            )

            # Check if should stop
            if self.wait_count >= self.config.patience:
                self.should_stop = True
                self.stopped_epoch = epoch

                logger.warning("=" * 60)
                logger.warning(f"EARLY STOPPING TRIGGERED at epoch {epoch}")
                logger.warning(f"  Best {self.config.metric}: {self.best_value:.4f}")
                logger.warning(f"  Current {self.config.metric}: {current:.4f}")
                logger.warning(f"  No improvement for {self.wait_count} epochs")
                logger.warning("=" * 60)

                if self.on_stopping:
                    self.on_stopping(epoch, self.best_value, current)

                return True

        return False

    def get_summary(self) -> dict:
        """Get summary of early stopping behavior."""
        return {
            "stopped": self.should_stop,
            "stopped_epoch": self.stopped_epoch,
            "best_value": self.best_value,
            "wait_count": self.wait_count,
            "config": {
                "patience": self.config.patience,
                "min_delta": self.config.min_delta,
                "metric": self.config.metric,
                "direction": self.config.direction,
            },
        }


class CheckpointSelector:
    """
    Select best checkpoint based on validation metrics.

    Saves checkpoints at regular intervals and tracks which is best.
    """

    def __init__(
        self,
        metric: str = "loss",
        direction: str = "minimize",
        max_checkpoints: int = 3,
    ):
        self.metric = metric
        self.direction = direction
        self.max_checkpoints = max_checkpoints

        self.checkpoints = []  # List of (epoch, value, path)
        self.best_epoch = None
        self.best_value = None
        self.best_path = None

        logger.info(f"CheckpointSelector initialized: metric={metric}, direction={direction}")

    def on_checkpoint_save(self, epoch: int, value: float, path: str):
        """Called when a checkpoint is saved."""
        self.checkpoints.append((epoch, value, path))

        # Track best
        if self.best_value is None:
            self.best_value = value
            self.best_epoch = epoch
            self.best_path = path
        elif self.direction == "minimize" and value < self.best_value:
            self.best_value = value
            self.best_epoch = epoch
            self.best_path = path
        elif self.direction == "maximize" and value > self.best_value:
            self.best_value = value
            self.best_epoch = epoch
            self.best_path = path

        # Prune old checkpoints if over limit
        if len(self.checkpoints) > self.max_checkpoints:
            # Sort by metric value
            if self.direction == "minimize":
                sorted_checkpoints = sorted(self.checkpoints, key=lambda x: x[1], reverse=True)
            else:
                sorted_checkpoints = sorted(self.checkpoints, key=lambda x: x[1])

            # Remove worst checkpoints
            to_remove = sorted_checkpoints[: len(self.checkpoints) - self.max_checkpoints]
            self.checkpoints = sorted_checkpoints[len(to_remove) :]

            logger.info(f"Pruned {len(to_remove)} checkpoints, keeping {self.max_checkpoints} best")

    def get_best(self) -> tuple:
        """Return (epoch, value, path) of best checkpoint."""
        return self.best_epoch, self.best_value, self.best_path

    def get_all(self) -> list:
        """Return all checkpoints sorted by metric value."""
        if self.direction == "minimize":
            return sorted(self.checkpoints, key=lambda x: x[1])
        else:
            return sorted(self.checkpoints, key=lambda x: x[1], reverse=True)


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================


def create_early_stopping_callback(config: dict = None) -> EarlyStoppingCallback:
    """Create early stopping callback from config dict."""
    if config is None:
        config = {}

    return EarlyStoppingCallback(
        patience=config.get("patience", 3),
        min_delta=config.get("min_delta", 0.01),
        metric=config.get("metric", "loss"),
        direction=config.get("direction", "minimize"),
        warmup_epochs=config.get("warmup_epochs", 1),
    )


def integrate_with_training_loop(
    trainer,
    callbacks: list = None,
    eval_every: int = 1,
) -> dict:
    """
    Integrate early stopping with a training loop.

    This is a reference implementation showing how to use the callbacks.
    The actual trainer loop may differ.
    """
    callbacks = callbacks or []
    callbacks.append(create_early_stopping_callback())

    history = TrainingHistory()

    for epoch in range(trainer.config.epochs):
        # Train
        train_loss = trainer.train_epoch(epoch)

        # Evaluate
        if epoch % eval_every == 0:
            eval_loss = trainer.evaluate()

            # Record history
            history.add(epoch, train_loss=train_loss, eval_loss=eval_loss)

            # Check early stopping
            for callback in callbacks:
                if isinstance(callback, EarlyStoppingCallback):
                    should_stop = callback.on_epoch_end(
                        epoch,
                        eval_loss=eval_loss,
                        train_loss=train_loss,
                    )
                    if should_stop:
                        return {
                            "stopped": True,
                            "stopped_epoch": epoch,
                            "history": history,
                            "best_checkpoint": callback.best_value,
                        }

    return {
        "stopped": False,
        "epochs_completed": trainer.config.epochs,
        "history": history,
        "best_checkpoint": callbacks[0].best_value if callbacks else None,
    }
