#!/usr/bin/env python3
"""
RosEnna Trainer — contrastive embedding model training pipeline.

Usage:
  python train.py --data /path/to/data --output /path/to/model.gguf
  
Stories 3.1-3.6:
- Loads config → loads data → augments → builds model → trains → exports
"""

import argparse
import os
import sys
import torch

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ModelConfig,
    TrainingConfig,
    CurriculumConfig,
    DataConfig,
    ExportConfig,
)
from data.dataset import RosEnnaDataset, ContrastiveDataset, load_all
from data.augment import augment_dataset, AugmentedDataset
from model.encoder import RosEnnaEncoder
from model.quantize import merge_and_export, export_for_inference
from training.loop import train


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="RosEnna Trainer - Contrastive embedding model training"
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Directory with JSONL training data"
    )
    parser.add_argument(
        "--output",
        default="rosenna-v1-q8_0.gguf",
        help="Output GGUF path"
    )
    parser.add_argument(
        "--config",
        help="Override config path (not implemented)"
    )
    parser.add_argument(
        "--resume",
        help="Resume from checkpoint"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override max epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Override batch size"
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device to use (cuda/cpu)"
    )
    parser.add_argument(
        "--quantization",
        default="q8_0",
        help="Quantization type (q8_0, q4_0, etc.)"
    )
    parser.add_argument(
        "--val-split",
        type=float,
        default=0.1,
        help="Validation split ratio"
    )
    parser.add_argument(
        "--no-augment",
        action="store_true",
        help="Disable data augmentation"
    )

    return parser.parse_args()


def load_data(data_dir: str, val_split: float = 0.1, augment: bool = True):
    """
    Load and prepare training data.

    Args:
        data_dir: Directory with JSONL files
        val_split: Fraction for validation
        augment: Whether to apply augmentation

    Returns:
        Tuple of (train_dataset, val_dataset)
    """
    print(f"\n{'='*60}")
    print(f"Loading data from: {data_dir}")
    print(f"{'='*60}")

    # Load raw data
    dataset = load_all(data_dir, min_examples_per_tool=100)
    print(f"Loaded {len(dataset)} examples")
    print(f"Tools: {len(dataset.get_unique_tools())}")

    if augment:
        print("\nApplying data augmentation (15x expansion)...")
        augmented = augment_dataset(dataset)
        print(f"Augmented to {len(augmented)} examples")

        # Create augmented dataset
        from torch.utils.data import TensorDataset, random_split

        # For contrastive training, we need pairs
        # The augmented data has query->tool pairs
        train_data = augmented
    else:
        train_data = dataset.examples

    # Split into train/val
    n_total = len(train_data)
    n_val = int(n_total * val_split)
    n_train = n_total - n_val

    print(f"\nDataset split: {n_train} train, {n_val} validation")

    # Create simple datasets
    train_dataset = train_data[:n_train]
    val_dataset = train_data[n_train:]

    return train_dataset, val_dataset


def build_model(config: ModelConfig, device: str):
    """
    Build the DoRA encoder model.

    Args:
        config: Model configuration
        device: Device to load on

    Returns:
        RosEnnaEncoder model
    """
    print(f"\n{'='*60}")
    print(f"Building model: {config.base_model}")
    print(f"{'='*60}")

    model = RosEnnaEncoder(
        base_model=config.base_model,
        embedding_dim=config.embedding_dim,
        lora_r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        lora_target=config.lora_target,
        load_in_4bit=config.load_in_4bit,
        device=device,
    )

    # Print model info
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {n_params:,}")
    print(f"VRAM estimate: < 11GB with 4-bit")

    return model


def train_model(
    model,
    train_dataset,
    val_dataset,
    config: TrainingConfig,
    device: str,
):
    """
    Train the model.

    Args:
        model: RosEnnaEncoder
        train_dataset: Training data
        val_dataset: Validation data
        config: Training configuration
        device: Device

    Returns:
        Trained model and history
    """
    print(f"\n{'='*60}")
    print(f"Starting training")
    print(f"Batch size: {config.batch_size}")
    print(f"Gradient accumulation: {config.grad_accum_steps}")
    print(f"Learning rate: {config.lr}")
    print(f"Max epochs: {config.max_epochs}")
    print(f"{'='*60}")

    # Train
    history = train(
        config=config,
        model=model,
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        device=device,
    )

    print(f"\nTraining complete!")
    print(f"Best validation accuracy: {max(history.get('val_acc', [0])):.4f}")

    return model, history


def export_model(
    model,
    output_path: str,
    quantization: str = "q8_0",
):
    """
    Export model to GGUF format.

    Args:
        model: Trained model
        output_path: Output file path
        quantization: Quantization type

    Returns:
        Path to exported model
    """
    print(f"\n{'='*60}")
    print(f"Exporting model to: {output_path}")
    print(f"Quantization: {quantization}")
    print(f"{'='*60}")

    output_path = merge_and_export(
        model=model,
        output_path=output_path,
        quantization=quantization,
    )

    print(f"Model exported: {output_path}")

    return output_path


def main():
    """Main entry point."""
    args = parse_args()

    # Print configuration
    print("\n" + "="*60)
    print("RosEnna Trainer - Starting")
    print("="*60)
    print(f"Data directory: {args.data}")
    print(f"Output file: {args.output}")
    print(f"Device: {args.device}")
    print(f"Quantization: {args.quantization}")
    print(f"Augmentation: {not args.no_augment}")
    print(f"Validation split: {args.val_split}")

    # Create configs
    model_config = ModelConfig()
    training_config = TrainingConfig()

    # Override with CLI args
    if args.epochs:
        training_config.max_epochs = args.epochs
    if args.batch_size:
        training_config.batch_size = args.batch_size

    # Step 1: Load data
    train_data, val_data = load_data(
        args.data,
        val_split=args.val_split,
        augment=not args.no_augment,
    )

    # Step 2: Build model
    device = args.device
    model = build_model(model_config, device)

    # Resume from checkpoint if requested
    if args.resume:
        print(f"\nResuming from checkpoint: {args.resume}")
        model.load_adapters(args.resume)

    # Step 3: Train
    model, history = train_model(
        model,
        train_data,
        val_data,
        training_config,
        device,
    )

    # Step 4: Export
    export_path = export_model(
        model,
        args.output,
        args.quantization,
    )

    print("\n" + "="*60)
    print("RosEnna Trainer - Complete!")
    print(f"Output: {export_path}")
    print("="*60)


if __name__ == "__main__":
    main()