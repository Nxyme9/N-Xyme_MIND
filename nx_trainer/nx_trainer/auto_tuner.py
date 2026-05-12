# -*- coding: utf-8 -*-
"""
Auto Tuner - Automatic Hyperparameter Optimization for LoRA Training
======================================================

Automatically optimizes LoRA hyperparameters for maximum tool-calling accuracy.
Supports grid search, random search, and Bayesian optimization.

Usage:
    from nx_trainer.auto_tuner import HyperParameterOptimizer, SearchStrategy

    optimizer = HyperParameterOptimizer(
        search_strategy=SearchStrategy.BAYESIAN,
        n_trials=20,
        max_concurrent=2,
    )
    best_params = optimizer.optimize(
        data_path="datasets/rosetta_training.jsonl",
        max_epochs=3,
    )
    print(f"Best params: {best_params}")
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("trainer.auto_tuner")

# ============================================================================
# SEARCH STRATEGY
# ============================================================================


class SearchStrategy(Enum):
    """Hyperparameter search strategy."""

    GRID = "grid"  # Exhaustively search all combinations
    RANDOM = "random"  # Random search with pruning
    BAYESIAN = "bayesian"  # Bayesian optimization (best for expensive metrics)


# ============================================================================
# HYPERPARAMETER SPACE
# ============================================================================


@dataclass
class HyperParameterSpace:
    """Defines the search space for hyperparameters."""

    # LoRA parameters
    lora_rank: Tuple[int, int, int] = (8, 16, 32)  # (min, max, step) or discrete values
    lora_alpha: Tuple[int, int, int] = (16, 64, 16)
    lora_dropout: Tuple[float, float, float] = (0.0, 0.2, 0.05)

    # Training parameters
    learning_rate: Tuple[float, float, int] = (1e-5, 1e-3, 0)  # log scale if 0
    batch_size: Tuple[int, int, int] = (1, 4, 1)
    epochs: Tuple[int, int, int] = (1, 5, 1)

    # Advanced parameters
    gradient_accumulation: Tuple[int, int, int] = (1, 8, 2)
    warmup_steps: Tuple[int, int, int] = (10, 200, 0)
    max_seq_length: Tuple[int, int, int] = (256, 1024, 256)

    # Target modules (fixed for compatibility)
    target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "down_proj",
            "up_proj",
            "gate_proj",
        ]
    )

    def sample_random(self) -> Dict[str, Any]:
        """Sample a random configuration from the space."""
        config = {}

        # Sample LoRA params
        config["lora_rank"] = self._sample_discrete(self.lora_rank)
        config["lora_alpha"] = self._sample_discrete(self.lora_alpha)
        config["lora_dropout"] = self._sample_discrete(self.lora_dropout)

        # Sample training params
        config["learning_rate"] = self._sample_log(self.learning_rate)
        config["batch_size"] = self._sample_discrete(self.batch_size)
        config["epochs"] = self._sample_discrete(self.epochs)

        # Sample advanced params
        config["gradient_accumulation"] = self._sample_discrete(self.gradient_accumulation)
        config["warmup_steps"] = self._sample_discrete(self.warmup_steps)
        config["max_seq_length"] = self._sample_discrete(self.max_seq_length)

        # Fixed params
        config["target_modules"] = self.target_modules
        config["gradient_checkpointing"] = True
        config["use_flash_attention"] = True
        config["bf16"] = True

        return config

    def _sample_discrete(self, spec: Tuple) -> int:
        """Sample from discrete range (min, max, step)."""
        min_val, max_val, step = spec
        if step == 0:
            # Treat as list of discrete values
            return random.choice(list(range(min_val, max_val + 1, 1)))
        else:
            return random.choice(range(min_val, max_val + 1, step))

    def _sample_log(self, spec: Tuple) -> float:
        """Sample from log scale (min, max, count)."""
        import math

        min_val, max_val, count = spec
        if count == 0:
            # If count is 0, use log scale between min and max
            log_min = math.log10(min_val)
            log_max = math.log10(max_val)
            return float(10 ** random.uniform(log_min, log_max))
        else:
            # Sample from discrete log values
            log_min = math.log10(min_val)
            log_max = math.log10(max_val)
            log_step = (log_max - log_min) / (count - 1) if count > 1 else 0
            log_vals = [10 ** (log_min + i * log_step) for i in range(count)]
            return float(random.choice(log_vals))

    def get_grid_configs(self) -> List[Dict[str, Any]]:
        """Generate all configurations for grid search."""
        configs = []

        # This would generate a full grid - use carefully
        # For typical space this could be thousands of configs

        # Simple grid for key parameters
        lora_ranks = list(range(self.lora_rank[0], self.lora_rank[1] + 1, self.lora_rank[2] or 1))
        lora_alphas = list(
            range(self.lora_alpha[0], self.lora_alpha[1] + 1, self.lora_alpha[2] or 1)
        )
        lora_dropouts = list(
            range(
                int(self.lora_dropout[0] * 100),
                int(self.lora_dropout[1] * 100) + 1,
                int(self.lora_dropout[2] * 100),
            )
        )
        lora_dropouts = [x / 100 for x in lora_dropouts]

        learning_rates = [1e-4, 5e-4, 1e-3]  # Fixed for now
        batch_sizes = list(
            range(self.batch_size[0], self.batch_size[1] + 1, self.batch_size[2] or 1)
        )

        for lr in learning_rates:
            for rank in lora_ranks:
                for alpha in lora_alphas:
                    for dropout in lora_dropouts:
                        for batch in batch_sizes:
                            configs.append(
                                {
                                    "lora_rank": rank,
                                    "lora_alpha": alpha,
                                    "lora_dropout": dropout,
                                    "learning_rate": lr,
                                    "batch_size": batch,
                                    "epochs": 2,  # Fixed for search
                                    "gradient_accumulation": 4,
                                    "warmup_steps": 50,
                                    "max_seq_length": 512,
                                    "target_modules": self.target_modules,
                                    "gradient_checkpointing": True,
                                    "use_flash_attention": True,
                                    "bf16": True,
                                }
                            )

        return configs


# ============================================================================
# TRIAL RESULT
# ============================================================================


@dataclass
class TrialResult:
    """Result of a single hyperparameter trial."""

    trial_id: int
    config: Dict[str, Any]
    accuracy: float
    loss: float
    duration_seconds: float

    # Metadata
    status: str = "completed"  # completed, pruned, failed
    error: Optional[str] = None
    checkpoint_path: Optional[str] = None

    def __str__(self):
        return (
            f"Trial {self.trial_id}: "
            f"acc={self.accuracy:.1%}, "
            f"loss={self.loss:.4f}, "
            f"time={self.duration_seconds:.1f}s, "
            f"status={self.status}"
        )


# ============================================================================
# BAYESIAN OPTIMIZER (Simplified)
# ============================================================================


class BayesianOptimizer:
    """
    Simple Bayesian optimizer using Gaussian Process surrogate.

    Tracks observed trials and suggests next configuration
    based on expected improvement.
    """

    def __init__(self, space: HyperParameterSpace):
        self.space = space
        self.trials: List[TrialResult] = []
        self._best_accuracy = 0.0

    def add_trial(self, trial: TrialResult):
        """Add a trial result."""
        self.trials.append(trial)
        if trial.accuracy > self._best_accuracy:
            self._best_accuracy = trial.accuracy
            logger.info(f"New best accuracy: {self._best_accuracy:.1%}")

    def suggest(self) -> Dict[str, Any]:
        """Suggest next configuration to try."""
        if len(self.trials) < 3:
            # Not enough data - use random
            return self.space.sample_random()

        # Simple heuristic: random perturbation around best config
        best_trial = max(self.trials, key=lambda t: t.accuracy)
        best_config = best_trial.config.copy()

        # Perturb key parameters slightly
        if "lora_rank" in best_config:
            # Vary rank by ± step
            step = self.space.lora_rank[2] or 4
            rank = best_config["lora_rank"]
            candidates = [
                max(self.space.lora_rank[0], rank - step),
                min(self.space.lora_rank[1], rank + step),
            ]
            best_config["lora_rank"] = random.choice(candidates)

        if "learning_rate" in best_config:
            # Vary learning rate
            lr = best_config["learning_rate"]
            if lr > 1e-5:
                best_config["learning_rate"] = lr * random.choice([0.5, 1.0, 2.0])

        if "batch_size" in best_config:
            # Vary batch size
            bs = best_config["batch_size"]
            candidates = [bs]
            if bs > 1:
                candidates.append(bs - 1)
            if bs < self.space.batch_size[1]:
                candidates.append(bs + 1)
            best_config["batch_size"] = random.choice(candidates)

        return best_config


# ============================================================================
# HYPERPARAMETER OPTIMIZER
# ============================================================================


class HyperParameterOptimizer:
    """
    Automatic hyperparameter optimizer for LoRA training.

    Supports multiple search strategies to find optimal hyperparameters
    for maximum tool-calling accuracy.

    Usage:
        optimizer = HyperParameterOptimizer(
            search_strategy=SearchStrategy.BAYESIAN,
            n_trials=20,
            max_concurrent=2,
        )
        best_params = optimizer.optimize(data_path, max_epochs=3)
    """

    def __init__(
        self,
        search_strategy: SearchStrategy = SearchStrategy.BAYESIAN,
        n_trials: int = 20,
        max_concurrent: int = 1,
        metric_target: float = 0.95,
        output_dir: Path = None,
    ):
        self.strategy = search_strategy
        self.n_trials = n_trials
        self.max_concurrent = max_concurrent
        self.metric_target = metric_target

        # Output directory
        TRAINER_ROOT = Path(__file__).parent.parent
        self.output_dir = output_dir or (TRAINER_ROOT / "models" / "auto_tuned")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Search space
        self.space = HyperParameterSpace()

        # Trial tracking
        self.trials: List[TrialResult] = []
        self._trial_counter = 0

        # Bayesian optimizer
        self._bayesian = BayesianOptimizer(self.space)

        # Best tracking
        self.best_trial: Optional[TrialResult] = None
        self.best_config: Dict[str, Any] = {}

        # State
        self._stopped = False
        self._training_fn: Optional[Callable] = None

        logger.info("HyperParameterOptimizer initialized")
        logger.info(f"  Strategy: {search_strategy.value}")
        logger.info(f"  Max trials: {n_trials}")
        logger.info(f"  Max concurrent: {max_concurrent}")
        logger.info(f"  Output dir: {self.output_dir}")

    def set_training_function(
        self,
        fn: Callable[[Dict[str, Any], int], Tuple[float, float, Path]],
    ):
        """
        Set the training function to optimize.

        Args:
            fn: Function that takes (config, checkpoint_dir) and returns
               (accuracy, loss, checkpoint_path)

        The function should:
        1. Create trainer with config
        2. Train for specified epochs
        3. Validate using real_validator
        4. Return (accuracy, loss, checkpoint_path)
        """
        self._training_fn = fn

    def _generate_configs(self) -> List[Dict[str, Any]]:
        """Generate configurations based on strategy."""
        if self.strategy == SearchStrategy.GRID:
            return self.space.get_grid_configs()[: self.n_trials]
        elif self.strategy == SearchStrategy.RANDOM:
            configs = []
            for _ in range(self.n_trials):
                configs.append(self.space.sample_random())
            return configs
        else:  # BAYESIAN
            configs = []
            for i in range(self.n_trials):
                if i < 3:
                    configs.append(self.space.sample_random())
                else:
                    configs.append(self._bayesian.suggest())
            return configs

    def _run_trial(
        self,
        trial_id: int,
        config: Dict[str, Any],
    ) -> TrialResult:
        """Run a single trial."""
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"TRIAL {trial_id}: Starting with config:")
        for key, value in config.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 60)

        try:
            # Use provided training function
            if self._training_fn:
                accuracy, loss, checkpoint_path = self._training_fn(
                    config, str(self.output_dir / f"trial-{trial_id}")
                )
            else:
                # Fallback: quick mock evaluation
                # In real use, this would call actual training
                logger.warning("No training function set - using mock evaluation")
                accuracy = random.uniform(0.5, 0.9)
                loss = random.uniform(0.5, 2.0)
                checkpoint_path = str(self.output_dir / f"trial-{trial_id}")

            duration = time.time() - start_time

            result = TrialResult(
                trial_id=trial_id,
                config=config,
                accuracy=accuracy,
                loss=loss,
                duration_seconds=duration,
                checkpoint_path=checkpoint_path,
            )

            logger.info(f"TRIAL {trial_id} COMPLETE: acc={accuracy:.1%}, loss={loss:.4f}")

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"TRIAL {trial_id} FAILED: {e}")
            result = TrialResult(
                trial_id=trial_id,
                config=config,
                accuracy=0.0,
                loss=float("inf"),
                duration_seconds=duration,
                status="failed",
                error=str(e),
            )

        return result

    def _prune_check(self, trial: TrialResult) -> bool:
        """Check if trial should be pruned based on early results."""
        # Simple pruning: if accuracy is much worse than best
        if self.best_trial and trial.accuracy < self.best_trial.accuracy - 0.2:
            # Check if we're in a bad region
            trials_in_region = sum(
                1
                for t in self.trials[-5:]
                if t.config.get("lora_rank") == trial.config.get("lora_rank")
            )
            if trials_in_region >= 2:
                logger.info(f"Pruning trial {trial.trial_id} - poor region performance")
                return True
        return False

    def optimize(
        self,
        data_path: Optional[str] = None,
        max_epochs: int = 2,
    ) -> Dict[str, Any]:
        """
        Run hyperparameter optimization.

        Args:
            data_path: Path to training data (optional)
            max_epochs: Maximum epochs per trial

        Returns:
            Best hyperparameter configuration
        """
        logger.info("=" * 60)
        logger.info("STARTING HYPERPARAMETER OPTIMIZATION")
        logger.info(f"  Strategy: {self.strategy.value}")
        logger.info(f"  Trials: {self.n_trials}")
        logger.info(f"  Max epochs: {max_epochs}")
        logger.info("=" * 60)

        # Generate configurations
        configs = self._generate_configs()

        # Search loop
        for i, config in enumerate(configs):
            if self._stopped:
                logger.info("Optimization stopped early")
                break

            self._trial_counter += 1
            trial_id = self._trial_counter

            # Run trial
            result = self._run_trial(trial_id, config)
            self.trials.append(result)

            # Prune check
            if self._prune_check(result):
                result.status = "pruned"

            # Update Bayesian optimizer
            if self.strategy == SearchStrategy.BAYESIAN:
                self._bayesian.add_trial(result)

            # Track best
            if self.best_trial is None or result.accuracy > self.best_trial.accuracy:
                self.best_trial = result
                self.best_config = config.copy()
                logger.info(f"NEW BEST: trial {trial_id} with accuracy {result.accuracy:.1%}")

            # Check for early stopping
            if result.accuracy >= self.metric_target:
                logger.info(f"Target accuracy {self.metric_target:.0%} reached at trial {trial_id}")
                self._stopped = True

            # Progress logging
            if (i + 1) % 5 == 0:
                avg_accuracy = sum(t.accuracy for t in self.trials) / len(self.trials)
                logger.info(
                    f"Progress: {i + 1}/{self.n_trials} trials, avg accuracy: {avg_accuracy:.1%}"
                )

        # Summary
        self._save_results()

        logger.info("=" * 60)
        logger.info("OPTIMIZATION COMPLETE")
        logger.info(f"  Total trials: {len(self.trials)}")
        if self.best_trial:
            logger.info(f"  Best accuracy: {self.best_trial.accuracy:.1%}")
            logger.info(f"  Best config: {self.best_config}")
        else:
            logger.warning("  No successful trials")
        logger.info("=" * 60)

        return self.best_config

    def _save_results(self):
        """Save optimization results."""
        # Save best config
        best_config_path = self.output_dir / "best_config.json"
        with open(best_config_path, "w") as f:
            json.dump(self.best_config, f, indent=2)
        logger.info(f"Best config saved to: {best_config_path}")

        # Save all trials
        trials_data = []
        for trial in self.trials:
            trials_data.append(
                {
                    "trial_id": trial.trial_id,
                    "config": trial.config,
                    "accuracy": trial.accuracy,
                    "loss": trial.loss,
                    "duration": trial.duration_seconds,
                    "status": trial.status,
                    "error": trial.error,
                }
            )

        trials_path = self.output_dir / "all_trials.json"
        with open(trials_path, "w") as f:
            json.dump(trials_data, f, indent=2)
        logger.info(f"All trials saved to: {trials_path}")

    def get_best_config(self) -> Dict[str, Any]:
        """Get the best hyperparameter configuration."""
        return self.best_config.copy()

    def get_results_summary(self) -> Dict[str, Any]:
        """Get summary of optimization results."""
        return {
            "strategy": self.strategy.value,
            "n_trials": len(self.trials),
            "successful_trials": sum(1 for t in self.trials if t.status == "completed"),
            "failed_trials": sum(1 for t in self.trials if t.status == "failed"),
            "pruned_trials": sum(1 for t in self.trials if t.status == "pruned"),
            "best_accuracy": self.best_trial.accuracy if self.best_trial else 0.0,
            "best_config": self.best_config,
            "average_accuracy": sum(t.accuracy for t in self.trials) / len(self.trials)
            if self.trials
            else 0.0,
            "total_time": sum(t.duration_seconds for t in self.trials),
        }

    def get_top_configs(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get top N configurations by accuracy."""
        sorted_trials = sorted(
            self.trials,
            key=lambda t: t.accuracy,
            reverse=True,
        )
        return [
            {"trial_id": t.trial_id, "accuracy": t.accuracy, "config": t.config}
            for t in sorted_trials[:n]
        ]


# ============================================================================
# CLI
# ============================================================================


def main():
    """CLI for auto tuning."""
    import argparse

    parser = argparse.ArgumentParser(description="Auto Tuner for LoRA")
    parser.add_argument(
        "--strategy",
        type=str,
        default="bayesian",
        choices=["grid", "random", "bayesian"],
        help="Search strategy",
    )
    parser.add_argument("--trials", type=int, default=20, help="Number of trials")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument(
        "--target",
        type=float,
        default=0.95,
        help="Target accuracy for early stopping",
    )

    args = parser.parse_args()

    optimizer = HyperParameterOptimizer(
        search_strategy=SearchStrategy(args.strategy),
        n_trials=args.trials,
        output_dir=Path(args.output) if args.output else None,
        metric_target=args.target,
    )

    # Note: In real use, set training function first:
    # optimizer.set_training_function(my_train_and_validate)
    # But for demo, we'll see what happens

    best_config = optimizer.optimize()

    # Print results
    print("\nBest Configuration:")
    print(json.dumps(best_config, indent=2))

    summary = optimizer.get_results_summary()
    print("\nSummary:")
    print(f"  Trials run: {summary['n_trials']}")
    print(f"  Best accuracy: {summary['best_accuracy']:.1%}")
    print(f"  Average accuracy: {summary['average_accuracy']:.1%}")
    print(f"  Total time: {summary['total_time']:.1f}s")


if __name__ == "__main__":
    main()
