"""
Live auto-tuner — adjusts hyperparams during training based on metrics.
Story 6.3: Auto-adjusts LR, temperature, hard-neg ratio, curriculum phase.
"""
import numpy as np


class LiveTuner:
    """Adjusts training hyperparams in real-time based on metrics."""

    def __init__(self):
        self.history = []
        self.adjustments = []
        self.lr = 2e-4
        self.temperature = 0.05
        self.hard_neg_ratio = 1.0

    def step(self, metrics: dict) -> dict:
        """Called after each validation epoch. Returns adjusted hparams."""
        self.history.append(metrics)
        adjustments = {}

        # Check for loss plateau (3 epochs without >1% improvement)
        if len(self.history) >= 4:
            recent_losses = [h.get("loss", 0) for h in self.history[-4:]]
            if len(recent_losses) >= 4:
                improvements = [recent_losses[i] - recent_losses[i+1] for i in range(3)]
                avg_improvement = abs(np.mean(improvements)) / abs(recent_losses[0] + 1e-8)
                if avg_improvement < 0.01:  # Plateau detected
                    self.lr *= 0.5
                    self.hard_neg_ratio += 0.5
                    adjustments["lr"] = self.lr
                    adjustments["hard_neg_ratio"] = self.hard_neg_ratio
                    adjustments["reason"] = "loss_plateau"

        # Check gradient norms
        grad_norm = metrics.get("grad_norm", 0)
        if grad_norm > 1.0:
            self.lr *= 0.8
            adjustments["lr"] = self.lr
            adjustments["grad_clip"] = 1.0
            adjustments["reason"] = "gradient_spike"

        # Auto phase advance based on accuracy
        accuracy = metrics.get("accuracy", 0)
        if accuracy > 0.95:
            adjustments["phase"] = 4  # Sharpening
            self.temperature = 0.03
        elif accuracy > 0.90:
            adjustments["phase"] = 3  # Hard
            self.temperature = 0.05
        elif accuracy > 0.80:
            adjustments["phase"] = 2  # Medium
        else:
            adjustments["phase"] = 1  # Warmup

        if adjustments:
            self.adjustments.append(adjustments)

        return {
            "learning_rate": self.lr,
            "temperature": self.temperature,
            "hard_neg_ratio": self.hard_neg_ratio,
            "adjustments": adjustments
        }

    def reset(self):
        """Reset to defaults for a new training run."""
        self.history = []
        self.adjustments = []
        self.lr = 2e-4
        self.temperature = 0.05
        self.hard_neg_ratio = 1.0