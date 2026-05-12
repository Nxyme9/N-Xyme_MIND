# -*- coding: utf-8 -*-
"""
Metrics Collector - Track Training and Validation Metrics
================================================

Tracks all training and validation metrics with alert conditions.

Usage:
    from nx_trainer.metrics_collector import MetricsCollector

    collector = MetricsCollector()

    # Record training metrics
    collector.record_training(epoch=1, metrics={
        "train_loss": 0.5,
        "grad_norm": 2.3,
        "learning_rate": 1e-4,
    })

    # Record validation metrics
    collector.record_validation(
        accuracy=0.95,
        per_category={
            "memory_ops": 0.98,
            "github_ops": 0.92,
            "file_ops": 0.94,
        }
    )

    # Check for alerts
    alerts = collector.check_alerts()

    # Get history
    history = collector.get_history()

    # Export to JSON
    collector.export_json("metrics.json")
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("trainer.metrics")

# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class TrainingMetrics:
    """Training metrics for a single epoch/step."""

    epoch: int
    step: int

    # Loss metrics
    train_loss: float = 0.0
    prev_train_loss: float = 0.0

    # Gradient metrics
    grad_norm: float = 0.0

    # Learning
    learning_rate: float = 0.0

    # Adapter
    adapter_size_mb: float = 0.0
    target_modules_match: bool = True

    # Timing
    step_duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def loss_delta(self) -> float:
        """Change in loss from previous step."""
        return self.train_loss - self.prev_train_loss

    @property
    def loss_ratio(self) -> float:
        """Ratio of current to previous loss."""
        if self.prev_train_loss > 0:
            return self.train_loss / self.prev_train_loss
        return 0.0


@dataclass
class ValidationMetrics:
    """Validation metrics after an epoch."""

    epoch: int
    step: int

    # Accuracy metrics
    accuracy: float = 0.0
    prev_accuracy: float = 0.0
    accuracy_delta: float = 0.0

    # Per-category accuracy
    per_category: Dict[str, float] = field(default_factory=dict)
    prev_per_category: Dict[str, float] = field(default_factory=dict)

    # Loss metrics
    eval_loss: float = 0.0
    eval_loss_delta: float = 0.0
    prev_eval_loss: float = 0.0

    # Inference
    inference_latency_ms: float = 0.0

    # Timing
    validation_duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class Alert:
    """A triggered alert condition."""

    alert_type: str
    message: str
    severity: str  # warning, error, critical
    epoch: int
    step: int
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def __str__(self):
        return f"[{self.severity.upper()}] {self.alert_type}: {self.message}"


# ============================================================================
# METRICS COLLECTOR
# ============================================================================


class MetricsCollector:
    """
    Collects and tracks training and validation metrics.

    Tracks:
    - train_loss (during training)
    - eval_loss (after each epoch)
    - real_accuracy (after validation)
    - per_category_accuracy (after validation)
    - inference_latency (during validation)
    - adapter_size (after save)
    - target_modules_match (during config)

    Alert conditions:
    - loss_spike: train_loss > prev_loss * 1.5
    - accuracy_drop: real_accuracy < prev_accuracy - 0.05
    - overfitting: eval_loss < 0.05 and train_loss < 0.05
    - divergence: grad_norm > 10.0

    Usage:
        collector = MetricsCollector()
        collector.record_training(epoch=1, metrics={...})
        collector.record_validation(accuracy=0.95, per_category={...})
        alerts = collector.check_alerts()
    """

    def __init__(
        self,
        name: str = "default",
        output_dir: str = None,
    ):
        self.name = name
        self.output_dir = Path(output_dir) if output_dir else None

        # Historical metrics
        self.training_history: List[TrainingMetrics] = []
        self.validation_history: List[ValidationMetrics] = []
        self.alerts: List[Alert] = []

        # Current state
        self._current_epoch = 0
        self._current_step = 0
        self._latest_train_loss = 0.0
        self._latest_eval_loss = 0.0
        self._latest_accuracy = 0.0
        self._latest_grad_norm = 0.0
        self._has_trained = False
        self._best_accuracy = 0.0

        logger.info(f"MetricsCollector initialized: {name}")

    # ============================================================================
    # RECORDING METHODS
    # ============================================================================

    def record_training(
        self,
        epoch: int,
        metrics: Dict[str, Any],
    ) -> TrainingMetrics:
        """
        Record training metrics for an epoch/step.

        Args:
            epoch: Current epoch number
            metrics: Dict containing:
                - train_loss: Training loss (float)
                - prev_train_loss: Previous loss for delta (float, optional)
                - grad_norm: Gradient norm (float)
                - learning_rate: Learning rate (float)
                - adapter_size_mb: Adapter size in MB (float, optional)
                - target_modules_match: Target modules match (bool, optional)
                - step_duration_seconds: Step duration (float, optional)
                - step: Current step (int, optional)

        Returns:
            TrainingMetrics object
        """
        self._current_epoch = epoch
        self._current_step = metrics.get("step", self._current_step + 1)

        prev_loss = self._latest_train_loss
        train_loss = metrics.get("train_loss", 0.0)
        grad_norm = metrics.get("grad_norm", 0.0)
        lr = metrics.get("learning_rate", 0.0)

        record = TrainingMetrics(
            epoch=epoch,
            step=self._current_step,
            train_loss=train_loss,
            prev_train_loss=prev_loss,
            grad_norm=grad_norm,
            learning_rate=lr,
            adapter_size_mb=metrics.get("adapter_size_mb", 0.0),
            target_modules_match=metrics.get("target_modules_match", True),
            step_duration_seconds=metrics.get("step_duration_seconds", 0.0),
        )

        self.training_history.append(record)
        self._latest_train_loss = train_loss
        self._latest_grad_norm = grad_norm
        self._has_trained = True

        logger.info(
            f"Epoch {epoch} | Step {self._current_step} | "
            f"Loss: {train_loss:.4f} (delta: {record.loss_delta:+.4f}) | "
            f"Grad: {grad_norm:.2f} | LR: {lr:.2e}"
        )

        # Check for training-specific alerts
        self._check_training_alerts(record)

        return record

    def record_validation(
        self,
        accuracy: float,
        per_category: Optional[Dict[str, float]] = None,
        eval_loss: Optional[float] = None,
        inference_latency_ms: Optional[float] = None,
        epoch: Optional[int] = None,
        validation_duration_seconds: Optional[float] = None,
    ) -> ValidationMetrics:
        """
        Record validation metrics.

        Args:
            accuracy: Overall accuracy (0.0 to 1.0)
            per_category: Per-category accuracy dict (optional)
            eval_loss: Validation loss (optional)
            inference_latency_ms: Average inference latency in ms (optional)
            epoch: Current epoch (uses current if not provided)
            validation_duration_seconds: Total validation time (optional)

        Returns:
            ValidationMetrics object
        """
        epoch = epoch if epoch is not None else self._current_epoch
        per_category = per_category or {}
        eval_loss = eval_loss if eval_loss is not None else self._latest_eval_loss
        inference_latency_ms = inference_latency_ms or 0.0

        prev_accuracy = self._latest_accuracy
        prev_eval_loss = self._latest_eval_loss
        prev_per_category = {}

        # Get previous per-category if available
        if self.validation_history:
            last_val = self.validation_history[-1]
            prev_per_category = last_val.per_category.copy()

        record = ValidationMetrics(
            epoch=epoch,
            step=self._current_step,
            accuracy=accuracy,
            prev_accuracy=prev_accuracy,
            accuracy_delta=accuracy - prev_accuracy,
            per_category=per_category,
            prev_per_category=prev_per_category,
            eval_loss=eval_loss,
            prev_eval_loss=prev_eval_loss,
            eval_loss_delta=eval_loss - prev_eval_loss if prev_eval_loss else 0.0,
            inference_latency_ms=inference_latency_ms,
            validation_duration_seconds=validation_duration_seconds or 0.0,
        )

        self.validation_history.append(record)
        self._latest_accuracy = accuracy
        self._latest_eval_loss = eval_loss

        # Track best accuracy
        if accuracy > self._best_accuracy:
            self._best_accuracy = accuracy
            logger.info(f"New best accuracy: {accuracy:.1%}")

        logger.info(
            f"Validation | Epoch {epoch} | "
            f"Accuracy: {accuracy:.1%} (delta: {record.accuracy_delta:+.1%}) | "
            f"Eval Loss: {eval_loss:.4f} | "
            f"Latency: {inference_latency_ms:.1f}ms"
        )

        if per_category:
            logger.info("Per-Category:")
            for cat, acc in sorted(per_category.items()):
                logger.info(f"  {cat:15} {acc:.1%}")

        # Check for validation-specific alerts
        self._check_validation_alerts(record)

        return record

    # ============================================================================
    # ALERT CHECKING
    # ============================================================================

    def _check_training_alerts(self, record: TrainingMetrics):
        """Check for training-specific alert conditions."""
        # Loss spike: train_loss > prev_loss * 1.5
        if record.prev_train_loss > 0 and record.train_loss > record.prev_train_loss * 1.5:
            alert = Alert(
                alert_type="loss_spike",
                message=(
                    f"Loss spiked from {record.prev_train_loss:.4f} to {record.train_loss:.4f} "
                    f"({record.loss_ratio:.2f}x)"
                ),
                severity="error",
                epoch=record.epoch,
                step=record.step,
                details={
                    "current_loss": record.train_loss,
                    "prev_loss": record.prev_train_loss,
                    "ratio": record.loss_ratio,
                },
            )
            self.alerts.append(alert)
            logger.warning(str(alert))

        # Divergence: grad_norm > 10.0
        if record.grad_norm > 10.0:
            alert = Alert(
                alert_type="divergence",
                message=f"Gradient norm very high: {record.grad_norm:.2f}",
                severity="critical",
                epoch=record.epoch,
                step=record.step,
                details={"grad_norm": record.grad_norm},
            )
            self.alerts.append(alert)
            logger.error(str(alert))

        # Target modules mismatch
        if not record.target_modules_match:
            alert = Alert(
                alert_type="target_modules_mismatch",
                message="Adapter target modules do not match base model",
                severity="warning",
                epoch=record.epoch,
                step=record.step,
            )
            self.alerts.append(alert)
            logger.warning(str(alert))

    def _check_validation_alerts(self, record: ValidationMetrics):
        """Check for validation-specific alert conditions."""
        # Accuracy drop: real_accuracy < prev_accuracy - 0.05
        if record.prev_accuracy > 0:
            accuracy_drop = record.prev_accuracy - record.accuracy
            if accuracy_drop > 0.05:
                alert = Alert(
                    alert_type="accuracy_drop",
                    message=(
                        f"Accuracy dropped from {record.prev_accuracy:.1%} to {record.accuracy:.1%} "
                        f"(-{accuracy_drop:.1%})"
                    ),
                    severity="error",
                    epoch=record.epoch,
                    step=record.step,
                    details={
                        "current_accuracy": record.accuracy,
                        "prev_accuracy": record.prev_accuracy,
                        "drop": accuracy_drop,
                    },
                )
                self.alerts.append(alert)
                logger.warning(str(alert))

        # Check for per-category drops
        for cat, acc in record.per_category.items():
            prev_acc = record.prev_per_category.get(cat, 1.0)
            drop = prev_acc - acc
            if drop > 0.10:  # More than 10% drop in a category
                alert = Alert(
                    alert_type="category_accuracy_drop",
                    message=f"Category '{cat}' dropped from {prev_acc:.1%} to {acc:.1%}",
                    severity="warning",
                    epoch=record.epoch,
                    step=record.step,
                    details={
                        "category": cat,
                        "current_accuracy": acc,
                        "prev_accuracy": prev_acc,
                        "drop": drop,
                    },
                )
                self.alerts.append(alert)
                logger.warning(str(alert))

    def _check_overfitting_alert(self):
        """Check for overfitting condition."""
        # Need both train and eval history
        if not self.training_history or not self.validation_history:
            return

        train_record = self.training_history[-1]
        val_record = self.validation_history[-1]

        # Overfitting: eval_loss < 0.05 and train_loss < 0.05
        if val_record.eval_loss < 0.05 and train_record.train_loss < 0.05:
            # Check if eval loss is significantly lower than train loss (possible overfitting)
            if val_record.eval_loss < train_record.train_loss * 0.5:
                alert = Alert(
                    alert_type="overfitting",
                    message=(
                        f"Potential overfitting: eval_loss={val_record.eval_loss:.4f} << "
                        f"train_loss={train_record.train_loss:.4f}"
                    ),
                    severity="warning",
                    epoch=val_record.epoch,
                    step=val_record.step,
                    details={
                        "train_loss": train_record.train_loss,
                        "eval_loss": val_record.eval_loss,
                    },
                )
                self.alerts.append(alert)
                logger.warning(str(alert))

    def check_alerts(self) -> List[Alert]:
        """
        Get all triggered alerts.

        Returns:
            List of Alert objects
        """
        # Run overfitting check if we have enough data
        self._check_overfitting_alert()

        if not self.alerts:
            logger.info("No alerts triggered")
        else:
            logger.info(f"Alerts triggered: {len(self.alerts)}")
            for alert in self.alerts[-5:]:  # Show last 5
                logger.info(f"  {alert}")

        return self.alerts.copy()

    def get_alerts_by_type(self, alert_type: str) -> List[Alert]:
        """Get alerts filtered by type."""
        return [a for a in self.alerts if a.alert_type == alert_type]

    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts.clear()
        logger.info("Alerts cleared")

    # ============================================================================
    # HISTORY ACCESS
    # ============================================================================

    def get_history(self) -> Dict[str, Any]:
        """
        Get all recorded metrics.

        Returns:
            Dict with training_history, validation_history, alerts
        """
        return {
            "name": self.name,
            "total_epochs": self._current_epoch,
            "total_training_records": len(self.training_history),
            "total_validation_records": len(self.validation_history),
            "total_alerts": len(self.alerts),
            "best_accuracy": self._best_accuracy,
            "latest_train_loss": self._latest_train_loss,
            "latest_accuracy": self._latest_accuracy,
            "training_history": [
                {
                    "epoch": r.epoch,
                    "step": r.step,
                    "train_loss": r.train_loss,
                    "prev_train_loss": r.prev_train_loss,
                    "loss_delta": r.loss_delta,
                    "grad_norm": r.grad_norm,
                    "learning_rate": r.learning_rate,
                    "adapter_size_mb": r.adapter_size_mb,
                    "target_modules_match": r.target_modules_match,
                    "timestamp": r.timestamp,
                }
                for r in self.training_history
            ],
            "validation_history": [
                {
                    "epoch": r.epoch,
                    "step": r.step,
                    "accuracy": r.accuracy,
                    "prev_accuracy": r.prev_accuracy,
                    "accuracy_delta": r.accuracy_delta,
                    "per_category": r.per_category,
                    "eval_loss": r.eval_loss,
                    "inference_latency_ms": r.inference_latency_ms,
                    "timestamp": r.timestamp,
                }
                for r in self.validation_history
            ],
            "alerts": [
                {
                    "type": a.alert_type,
                    "message": a.message,
                    "severity": a.severity,
                    "epoch": a.epoch,
                    "step": a.step,
                    "details": a.details,
                    "timestamp": a.timestamp,
                }
                for a in self.alerts
            ],
        }

    def get_training_curve(self) -> List[Dict[str, float]]:
        """Get training loss curve data."""
        return [
            {
                "epoch": r.epoch,
                "step": r.step,
                "loss": r.train_loss,
                "grad_norm": r.grad_norm,
            }
            for r in self.training_history
        ]

    def get_validation_curve(self) -> List[Dict[str, float]]:
        """Get validation accuracy curve data."""
        return [
            {"epoch": r.epoch, "accuracy": r.accuracy, "eval_loss": r.eval_loss}
            for r in self.validation_history
        ]

    def get_per_category_curve(self, category: str) -> List[Dict[str, float]]:
        """Get per-category accuracy curve."""
        return [
            {"epoch": r.epoch, "accuracy": r.per_category.get(category, 0.0)}
            for r in self.validation_history
            if category in r.per_category
        ]

    # ============================================================================
    # EXPORT
    # ============================================================================

    def export_json(self, path: Union[str, Path]) -> Path:
        """
        Export all metrics to JSON file.

        Args:
            path: Output file path

        Returns:
            Path to exported file
        """
        path = Path(path)
        if self.output_dir:
            path = self.output_dir / path

        history = self.get_history()

        with open(path, "w") as f:
            json.dump(history, f, indent=2)

        logger.info(f"Metrics exported to: {path}")
        return path

    def export_csv(self, path: Union[str, Path]) -> Path:
        """
        Export training metrics to CSV.

        Args:
            path: Output file path

        Returns:
            Path to exported file
        """
        import csv

        path = Path(path)
        if self.output_dir:
            path = self.output_dir / path

        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "epoch",
                    "step",
                    "train_loss",
                    "eval_loss",
                    "accuracy",
                    "grad_norm",
                    "learning_rate",
                ]
            )

            for i, train_rec in enumerate(self.training_history):
                val_rec = self.validation_history[i] if i < len(self.validation_history) else None

                writer.writerow(
                    [
                        train_rec.epoch,
                        train_rec.step,
                        train_rec.train_loss,
                        val_rec.eval_loss if val_rec else "",
                        val_rec.accuracy if val_rec else "",
                        train_rec.grad_norm,
                        train_rec.learning_rate,
                    ]
                )

        logger.info(f"CSV exported to: {path}")
        return path

    # ============================================================================
    # SUMMARY
    # ============================================================================

    def print_summary(self):
        """Print a summary of collected metrics."""
        print("=" * 60)
        print(f"METRICS COLLECTOR: {self.name}")
        print("=" * 60)
        print(f"Training iterations: {len(self.training_history)}")
        print(f"Validation runs: {len(self.validation_history)}")
        print(f"Alerts triggered: {len(self.alerts)}")
        print(f"Best accuracy: {self._best_accuracy:.1%}")
        print(f"Latest train_loss: {self._latest_train_loss:.4f}")
        print(f"Latest accuracy: {self._latest_accuracy:.1%}")
        print("=" * 60)

        if self.training_history:
            print("\nTraining Curve (last 10):")
            for rec in self.training_history[-10:]:
                print(
                    f"  Epoch {rec.epoch:2d} Step {rec.step:4d}: loss={rec.train_loss:.4f} grad={rec.grad_norm:.2f}"
                )

        if self.validation_history:
            print("\nValidation Curve (last 10):")
            for rec in self.validation_history[-10:]:
                print(
                    f"  Epoch {rec.epoch:2d}: accuracy={rec.accuracy:.1%} eval_loss={rec.eval_loss:.4f}"
                )

        if self.alerts:
            print("\nRecent Alerts:")
            for alert in self.alerts[-5:]:
                print(f"  {alert}")

    # ============================================================================
    # STATIC METHODS
    # ============================================================================

    @staticmethod
    def load_from_json(path: Union[str, Path]) -> "MetricsCollector":
        """
        Load metrics from JSON file.

        Args:
            path: Path to JSON file

        Returns:
            MetricsCollector with loaded data
        """
        path = Path(path)

        with open(path) as f:
            data = json.load(f)

        collector = MetricsCollector(name=data.get("name", "loaded"))

        # Reconstruct training history
        for rec in data.get("training_history", []):
            collector.training_history.append(
                TrainingMetrics(
                    epoch=rec["epoch"],
                    step=rec["step"],
                    train_loss=rec.get("train_loss", 0.0),
                    prev_train_loss=rec.get("prev_train_loss", 0.0),
                    grad_norm=rec.get("grad_norm", 0.0),
                    learning_rate=rec.get("learning_rate", 0.0),
                    adapter_size_mb=rec.get("adapter_size_mb", 0.0),
                    target_modules_match=rec.get("target_modules_match", True),
                    timestamp=rec.get("timestamp", time.time()),
                )
            )

        # Reconstruct validation history
        for rec in data.get("validation_history", []):
            collector.validation_history.append(
                ValidationMetrics(
                    epoch=rec["epoch"],
                    step=rec["step"],
                    accuracy=rec.get("accuracy", 0.0),
                    prev_accuracy=rec.get("prev_accuracy", 0.0),
                    accuracy_delta=rec.get("accuracy_delta", 0.0),
                    per_category=rec.get("per_category", {}),
                    prev_per_category=rec.get("prev_per_category", {}),
                    eval_loss=rec.get("eval_loss", 0.0),
                    prev_eval_loss=rec.get("prev_eval_loss", 0.0),
                    inference_latency_ms=rec.get("inference_latency_ms", 0.0),
                    timestamp=rec.get("timestamp", time.time()),
                )
            )

        # Reconstruct alerts
        for alert in data.get("alerts", []):
            collector.alerts.append(
                Alert(
                    alert_type=alert["type"],
                    message=alert["message"],
                    severity=alert["severity"],
                    epoch=alert["epoch"],
                    step=alert["step"],
                    details=alert.get("details", {}),
                    timestamp=alert.get("timestamp", time.time()),
                )
            )

        collector._best_accuracy = data.get("best_accuracy", 0.0)
        collector._latest_train_loss = data.get("latest_train_loss", 0.0)
        collector._latest_accuracy = data.get("latest_accuracy", 0.0)

        logger.info(f"Loaded metrics from: {path}")
        return collector


# ============================================================================
# CLI
# ============================================================================


def main():
    """CLI for metrics collection."""
    import argparse

    parser = argparse.ArgumentParser(description="Metrics Collector")
    parser.add_argument("--record-training", help="Record training metrics (JSON)")
    parser.add_argument("--record-validation", help="Record validation metrics (JSON)")
    parser.add_argument("--check-alerts", action="store_true", help="Check alerts")
    parser.add_argument("--history", action="store_true", help="Show history")
    parser.add_argument("--export", help="Export to JSON file")
    parser.add_argument("--load", help="Load from JSON file")
    parser.add_argument("--summary", action="store_true", help="Print summary")

    args = parser.parse_args()

    collector = MetricsCollector()

    if args.load:
        collector = MetricsCollector.load_from_json(args.load)

    if args.record_training:
        metrics = json.loads(args.record_training)
        collector.record_training(
            epoch=metrics.get("epoch", 1),
            metrics=metrics,
        )

    if args.record_validation:
        metrics = json.loads(args.record_validation)
        collector.record_validation(
            accuracy=metrics.get("accuracy", 0.0),
            per_category=metrics.get("per_category"),
            eval_loss=metrics.get("eval_loss"),
            inference_latency_ms=metrics.get("inference_latency_ms"),
            epoch=metrics.get("epoch"),
        )

    if args.check_alerts:
        collector.check_alerts()

    if args.history:
        history = collector.get_history()
        print(json.dumps(history, indent=2))

    if args.summary:
        collector.print_summary()

    if args.export:
        collector.export_json(args.export)


if __name__ == "__main__":
    main()
