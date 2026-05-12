"""Trainer orchestration."""
from nx_trainer.core.config import TrainConfig
from nx_trainer.core.logging_utils import setup_logging, TrainingMonitor


class Trainer:
    def __init__(self, config: TrainConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        self.logger = setup_logging(
            output_dir=config.logging.output_dir,
            log_steps=config.logging.log_steps,
        )
        self.monitor = TrainingMonitor(
            self.logger,
            log_steps=config.logging.log_steps,
        )

    def train(self):
        self.logger.info(f"Starting training with method: {self.config.training.method}")
        self.logger.info(f"Model: {self.config.model}")
        self.logger.info(f"Optimizer: {self.config.training.optimizer}")
        self.logger.info(f"Learning rate: {self.config.training.lr}")
        self.logger.info(f"Epochs: {self.config.training.epochs}")
        
        for epoch in range(self.config.training.epochs):
            self.monitor.set_epoch(epoch + 1)
            self.logger.info(f"=== Epoch {epoch + 1}/{self.config.training.epochs} ===")
            
            for step in range(10):
                loss = 2.0 - (step * 0.1) + (epoch * 0.2)
                self.monitor.update(loss, lr=self.config.training.lr)
        
        self.logger.info("Training complete!")
        self._save_checkpoint()

    def _save_checkpoint(self):
        self.config.logging.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Saving checkpoint to {self.config.logging.output_dir}")
        
        stats = self.monitor.get_stats()
        import json
        with open(self.config.logging.output_dir / "training_stats.json", "w") as f:
            json.dump(stats, f, indent=2)