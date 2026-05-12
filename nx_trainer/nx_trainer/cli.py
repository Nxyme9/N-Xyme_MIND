"""Command-line interface for Rosetta Stone Trainer.

Optimized for speed + VRAM efficiency with Unsloth.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from nx_trainer import __version__
from nx_trainer.config import (
    GGUFExportConfig,
    LoRAConfig,
    MODEL_CONFIGS,
    TrainingConfig,
)
from nx_trainer.data_generator import DataGenerator
from nx_trainer.evaluator import Evaluator
from nx_trainer.trainer import Trainer
from nx_trainer.validator import validate_dataset


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with optimized defaults."""
    parser = argparse.ArgumentParser(
        prog="rosetta-train",
        description="Train local LLMs to translate natural language to MCP tool calls",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick start with preset (recommended)
  rosetta-train train --preset qwen2.5-0.5b --data data.jsonl

  # Full custom training
  rosetta-train train --method unsloth --model Qwen/Qwen2.5-1.5B-Instruct \\
      --data data.jsonl --epochs 3 --lora-r 16 --batch-size 1

  # Export to GGUF for llama-server
  rosetta-train export --lora-path outputs/rosetta/rosetta-lora --quant q4_k_m
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"rosetta-stone-trainer {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === GENERATE ===
    gen_parser = subparsers.add_parser("generate", help="Generate training data")
    gen_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("rosetta_training.jsonl"),
        help="Output path (default: rosetta_training.jsonl)",
    )
    gen_parser.add_argument(
        "--num-variations", "-n", type=int, default=10, help="Variations per template (default: 10)"
    )
    gen_parser.add_argument(
        "--templates", type=str, default="default", help="Template set: default, minimal, extended"
    )

    # === TRAIN ===
    train_parser = subparsers.add_parser("train", help="Train the model")
    train_parser.add_argument(
        "--preset",
        "-p",
        type=str,
        help="Model preset (overrides other args): qwen2.5-0.5b, qwen2.5-1.5b, qwen2.5-3b, llama3.2-1b, llama3.2-3b",
    )
    train_parser.add_argument(
        "--method",
        "-m",
        choices=["unsloth", "ollama"],
        default="unsloth",
        help="Training method (default: unsloth)",
    )
    train_parser.add_argument(
        "--data", "-d", type=Path, required=True, help="Path to training data JSONL file"
    )
    train_parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("outputs/rosetta"),
        help="Output directory (default: outputs/rosetta)",
    )
    train_parser.add_argument(
        "--model", type=str, help="Base model (default: Qwen/Qwen2.5-0.5B-Instruct)"
    )
    train_parser.add_argument(
        "--epochs", "-e", type=int, default=3, help="Training epochs (default: 3)"
    )
    train_parser.add_argument(
        "--batch-size", type=int, help="Per-device batch size (default: varies by model)"
    )
    train_parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank (default: 16)")
    train_parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha (default: 32)")
    train_parser.add_argument(
        "--learning-rate", "-lr", type=float, default=2e-4, help="Learning rate (default: 2e-4)"
    )
    train_parser.add_argument(
        "--max-seq-length", type=int, default=512, help="Max sequence length (default: 512)"
    )
    train_parser.add_argument(
        "--warmup-steps", type=int, default=10, help="Warmup steps (default: 10)"
    )

    # === EXPORT ===
    export_parser = subparsers.add_parser("export", help="Export to GGUF/llama-server")
    export_parser.add_argument(
        "--lora-path", "-l", type=Path, required=True, help="Path to trained LoRA adapters"
    )
    export_parser.add_argument("--output", "-o", type=Path, help="Output GGUF path")
    export_parser.add_argument(
        "--quant",
        "-q",
        type=str,
        default="q4_k_m",
        choices=["q4_k_m", "q8_0", "f16"],
        help="Quantization method (default: q4_k_m)",
    )
    export_parser.add_argument(
        "--base-model", type=str, help="Base model for GGUF (default: from config)"
    )

    # === TEST ===
    test_parser = subparsers.add_parser("test", help="Test the trained model")
    test_parser.add_argument(
        "--ollama-model", type=str, default="rosetta", help="Ollama model name (default: rosetta)"
    )
    test_parser.add_argument("--data", type=Path, help="Path to test data JSONL file")
    test_parser.add_argument("--gguf", type=Path, help="Use GGUF file instead of Ollama")

    # === PREPARE ===
    prep_parser = subparsers.add_parser("prepare", help="Convert data to fine-tuning format")
    prep_parser.add_argument("--input", "-i", type=Path, required=True, help="Input JSONL file")
    prep_parser.add_argument("--output", "-o", type=Path, help="Output JSON file")

    # === VALIDATE ===
    val_parser = subparsers.add_parser("validate", help="Validate training data")
    val_parser.add_argument(
        "--data", "-d", type=Path, required=True, help="Path to training data JSONL file"
    )
    val_parser.add_argument(
        "--max-length", type=int, default=2048, help="Max sequence length (default: 2048)"
    )

    # === INFO ===
    subparsers.add_parser("info", help="Show system/GPU info")

    # === BENCHMARK ===
    bench_parser = subparsers.add_parser("benchmark", help="Show expected performance benchmarks")
    bench_parser.add_argument(
        "--preset",
        "-p",
        type=str,
        help="Model preset to benchmark: qwen2.5-0.5b, qwen2.5-1.5b, qwen2.5-3b, llama3.2-1b, llama3.2-3b",
    )
    bench_parser.add_argument(
        "--export", "-e", action="store_true", help="Export benchmark results to file"
    )

    return parser


def cmd_info(args: argparse.Namespace) -> int:
    """Show system info."""
    import torch

    print("=== System Info ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        print(f"BF16 supported: {torch.cuda.is_bf16_supported()}")

    print("\n=== Available Models ===")
    for name, cfg in MODEL_CONFIGS.items():
        print(
            f"  {name}: {cfg['vram_requirement']} VRAM, lr={cfg['learning_rate']}, r={cfg['lora_r']}"
        )

    print("\n=== Unsloth Status ===")
    t = Trainer()
    print(f"  Available: {t.check_unsloth_available()}")
    print(f"  Ollama: {t.check_ollama_available()}")

    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle generate command."""
    print(f"Generating training data ({args.num_variations} variations per template)...")

    generator = DataGenerator()
    training_data = generator.generate(
        num_variations=args.num_variations,
        output_path=args.output,
    )

    print(f"Generated {len(training_data)} training pairs")
    print(f"Saved to: {args.output}")

    return 0


def cmd_train(args: argparse.Namespace) -> int:
    """Handle train command with preset support."""
    # Validate data path
    if not args.data.exists():
        print(f"ERROR: Data file not found: {args.data}")
        return 1

    # Run dataset validation pre-flight check
    print("\n=== Running Dataset Validation ===")
    if not validate_dataset(args.data):
        print("\n⚠ Dataset validation failed. Fix errors before training.")
        return 1
    print("✓ Dataset validation passed\n")

    # Check method availability
    if args.method == "unsloth":
        if not Trainer.check_unsloth_available():
            print("WARNING: Unsloth not installed. Falling back to Ollama.")
            print("  Install Unsloth: pip install unsloth")
            args.method = "ollama"

    if args.method == "ollama":
        if not Trainer.check_ollama_available():
            print("ERROR: Ollama not available. Please install Ollama first.")
            return 1

    # Apply preset if specified
    if args.preset:
        if args.preset not in MODEL_CONFIGS:
            print(f"ERROR: Unknown preset: {args.preset}")
            print(f"Available: {list(MODEL_CONFIGS.keys())}")
            return 1
        cfg = MODEL_CONFIGS[args.preset]
        print(f"Using preset: {args.preset}")
        print(f"  Model: {cfg['model_name']}")
        print(f"  VRAM: {cfg['vram_requirement']}")

        # Apply preset defaults
        lora_config = LoRAConfig(r=cfg["lora_r"], alpha=cfg["lora_alpha"])
        training_config = TrainingConfig(
            model_name=cfg["model_name"],
            num_train_epochs=cfg["epochs"],
            per_device_train_batch_size=cfg["batch_size"],
            gradient_accumulation_steps=cfg["gradient_accumulation"],
            learning_rate=cfg["learning_rate"],
            max_seq_length=cfg["max_seq_length"],
            output_dir=str(args.output_dir),
        )
    else:
        # Custom config
        lora_config = LoRAConfig(r=args.lora_r, alpha=args.lora_alpha)
        batch_size = args.batch_size or 2
        training_config = TrainingConfig(
            model_name=args.model or "Qwen/Qwen2.5-0.5B-Instruct",
            num_train_epochs=args.epochs,
            per_device_train_batch_size=batch_size,
            learning_rate=args.learning_rate,
            max_seq_length=args.max_seq_length,
            warmup_steps=args.warmup_steps,
            output_dir=str(args.output_dir),
        )

    # Create trainer and train
    trainer = Trainer(lora_config=lora_config, training_config=training_config)

    print(f"\n=== Training with {args.method.upper()} ===\n")
    print(f"Data: {args.data}")
    print(f"Output: {args.output_dir}")
    print(f"Epochs: {training_config.num_train_epochs}")
    print(f"Model: {training_config.model_name}")
    if args.method == "unsloth":
        print(f"LoRA r={lora_config.r}, alpha={lora_config.alpha}")
        print(f"Batch: {training_config.per_device_train_batch_size}")
        print(f"LR: {training_config.learning_rate}")
    print()

    success = trainer.train(data_path=args.data, method=args.method, output_dir=args.output_dir)

    if success:
        print("\n✓ Training completed successfully!")
        return 0
    else:
        print("\n✗ Training failed")
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """Handle export command."""
    if not args.lora_path.exists():
        print(f"ERROR: LoRA path not found: {args.lora_path}")
        return 1

    config = GGUFExportConfig(
        quantize_method=args.quant,
        base_model_name=args.base_model or "Qwen/Qwen2.5-0.5B-Instruct",
        output_dir=str(args.output or "outputs/gguf"),
    )

    trainer = Trainer()
    output_path = args.output or Path(config.output_dir) / f"rosetta-{args.quant}.gguf"

    success = trainer.export_to_gguf(args.lora_path, output_path, config)

    if success:
        print("\n✓ Export completed!")
        return 0
    else:
        print("\n✗ Export failed")
        return 1


def cmd_test(args: argparse.Namespace) -> int:
    """Handle test command."""
    evaluator = Evaluator()

    if args.data:
        # Load test cases from file
        test_cases = evaluator.load_test_data(args.data)
        print(f"Loaded {len(test_cases)} test cases from {args.data}")
    else:
        test_cases = None
        print("Using default test cases")

    # Run interactive test
    evaluator.run_interactive_test(ollama_model=args.ollama_model)

    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    """Handle prepare command."""
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        return 1

    output_path = args.output or args.input.with_suffix(".json")

    print(f"Preparing {args.input} -> {output_path}")

    generator = DataGenerator()
    formatted = generator.prepare_for_fine_tuning(args.input, output_path)

    print(f"Prepared {len(formatted)} fine-tuning examples")
    print(f"Saved to: {output_path}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle validate command."""
    if not args.data.exists():
        print(f"ERROR: Data file not found: {args.data}")
        return 1

    is_valid = validate_dataset(args.data, args.max_length)
    return 0 if is_valid else 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Handle benchmark command - show expected performance."""
    import torch

    print("=" * 60)
    print("Rosetta Stone Trainer - Benchmark")
    print("=" * 60)

    # System info
    print("\n[System]")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  GPU: {gpu}")
        print(f"  VRAM: {vram:.1f} GB")
        print(f"  BF16: {torch.cuda.is_bf16_supported()}")

    # Unsloth availability
    print("\n[Training Backends]")
    t = Trainer()
    print(f"  Unsloth: {t.check_unsloth_available()}")
    print(f"  Ollama: {t.check_ollama_available()}")

    # Model presets
    print("\n[Available Presets]")
    print("  Model          | VRAM  | LoRA r | LR      | Epochs")
    print("  ---------------|-------|--------|---------|-------")
    for name, cfg in MODEL_CONFIGS.items():
        print(
            f"  {name:15} | {cfg['vram_requirement']:5} | {cfg['lora_r']:6} | {cfg['learning_rate']:.1e} | {cfg['epochs']}"
        )

    # Expected performance
    print("\n[Expected Training Performance]")
    print("  Model          | VRAM  | Speedup | Quality")
    print("  --------------|-------|---------|--------")
    print("  Qwen2.5-0.5B  | 6GB   | 2x      | 90%+")
    print("  Qwen2.5-1.5B  | 8GB   | 2x      | 92%+")
    print("  Qwen2.5-3B    | 10GB  | 1.8x    | 93%+")
    print("  Llama3.2-1B   | 6GB   | 2x      | 89%+")
    print("  Llama3.2-3B   | 10GB  | 1.8x    | 91%+")

    print("\n[Unsloth Optimizations]")
    print("  - 4-bit quantization (70% less VRAM)")
    print("  - Gradient checkpointing (save VRAM)")
    print("  - AdamW 8-bit (50% less memory)")
    print("  - Flash Attention / Xformers (speed boost)")
    print("  - Linear warmup (stable training)")

    # If preset specified, show detailed info
    if args.preset:
        if args.preset not in MODEL_CONFIGS:
            print(f"\nERROR: Unknown preset: {args.preset}")
            print(f"Available: {list(MODEL_CONFIGS.keys())}")
            return 1

        cfg = MODEL_CONFIGS[args.preset]
        print(f"\n[Preset: {args.preset}]")
        print(f"  Model: {cfg['model_name']}")
        print(f"  VRAM Required: {cfg['vram_requirement']}")
        print(f"  LoRA r: {cfg['lora_r']}, alpha: {cfg['lora_alpha']}")
        print(f"  Learning Rate: {cfg['learning_rate']}")
        print(f"  Batch Size: {cfg['batch_size']}")
        print(f"  Gradient Accumulation: {cfg['gradient_accumulation']}")
        print(f"  Max Seq Length: {cfg['max_seq_length']}")
        print(f"  Epochs: {cfg['epochs']}")

    print("\n" + "=" * 60)
    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    # Dispatch to command handler
    handlers = {
        "generate": cmd_generate,
        "train": cmd_train,
        "test": cmd_test,
        "prepare": cmd_prepare,
        "export": cmd_export,
        "validate": cmd_validate,
        "info": cmd_info,
        "benchmark": cmd_benchmark,
    }

    if args.command in handlers:
        return handlers[args.command](args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
