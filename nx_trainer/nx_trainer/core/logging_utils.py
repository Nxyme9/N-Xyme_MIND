"""Logging and monitoring utilities."""
import logging
import sys
from pathlib import Path
from typing import Optional
import torch


def setup_logging(
    output_dir: Optional[Path] = None,
    level: int = logging.INFO,
    log_steps: int = 10,
) -> logging.Logger:
    logger = logging.getLogger("nx_trainer")
    logger.setLevel(level)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(output_dir / "train.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


class TrainingMonitor:
    def __init__(self, logger: logging.Logger, log_steps: int = 10):
        self.logger = logger
        self.log_steps = log_steps
        self.step = 0
        self.epoch = 0
        self.loss_history = []
        self.gpu_memory_used = 0
        
    def update(self, loss: float, **metrics):
        self.step += 1
        self.loss_history.append(loss)
        
        if self.step % self.log_steps == 0:
            avg_loss = sum(self.loss_history[-self.log_steps:]) / self.log_steps
            gpu_mem = f"{torch.cuda.memory_allocated() / 1e9:.1f}GB" if torch.cuda.is_available() else "N/A"
            
            self.logger.info(
                f"Step {self.step} | Epoch {self.epoch} | "
                f"Loss: {avg_loss:.4f} | GPU: {gpu_mem}"
            )
            
            for k, v in metrics.items():
                if isinstance(v, float):
                    self.logger.info(f"  {k}: {v:.4f}")
    
    def set_epoch(self, epoch: int):
        self.epoch = epoch
        
    def get_stats(self):
        return {
            "step": self.step,
            "epoch": self.epoch,
            "avg_loss": sum(self.loss_history) / len(self.loss_history) if self.loss_history else 0,
            "gpu_memory_gb": torch.cuda.max_memory_allocated() / 1e9 if torch.cuda.is_available() else 0,
        }