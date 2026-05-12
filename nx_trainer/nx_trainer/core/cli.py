"""CLI entry points for N-Xyme Trainer."""
import typer
from typing import Optional
from pathlib import Path
import torch

app = typer.Typer(
    name="trainer",
    help="N-Xyme Trainer - Bleeding-edge LLM training",
    add_completion=False,
)


@app.command()
def train(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to YAML config file",
        exists=True,
        file_okay=True,
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Model name or path (HuggingFace or local)",
    ),
    data: Optional[Path] = typer.Option(
        None,
        "--data",
        "-d",
        help="Path to training data (JSONL, CSV)",
        exists=True,
    ),
    method: str = typer.Option(
        "lora",
        "--method",
        help="Training method: lora, qlora, lora_plus, ftt, dpo, kto, orpo, simpo",
    ),
    optimizer: str = typer.Option(
        "adamw",
        "--optimizer",
        help="Optimizer: adamw, lion, sophia, galore, adafactor",
    ),
    epochs: int = typer.Option(3, "--epochs", "-e", help="Number of epochs"),
    batch_size: int = typer.Option(8, "--batch-size", "-b", help="Batch size"),
    lr: float = typer.Option(
        3e-4,
        "--lr",
        help="Learning rate",
    ),
    rank: int = typer.Option(
        16,
        "--rank",
        "-r",
        help="LoRA rank",
    ),
    alpha: int = typer.Option(
        32,
        "--alpha",
        help="LoRA alpha",
    ),
    output_dir: Path = typer.Option(
        Path("./output"),
        "--output",
        "-o",
        help="Output directory",
    ),
    gpu: Optional[int] = typer.Option(
        None,
        "--gpu",
        "-g",
        help="GPU ID to use (default: auto-detect)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output",
    ),
):
    """Train a model with specified parameters."""
    if gpu is not None:
        torch.cuda.set_device(gpu)
    
    from nx_trainer.core.config import TrainConfig
    from nx_trainer.core.trainer import Trainer
    
    config_obj = TrainConfig.from_args(
        model=model,
        data=data,
        method=method,
        optimizer=optimizer,
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
        rank=rank,
        alpha=alpha,
        output_dir=output_dir,
    )
    
    if config:
        config_obj = TrainConfig.merge(config, config_obj)
    
    trainer = Trainer(config_obj, verbose=verbose)
    trainer.train()


@app.command()
def eval(
    model: Path = typer.Argument(..., help="Path to model or adapter"),
    data: Path = typer.Argument(..., help="Path to evaluation data"),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for results",
    ),
    batch_size: int = typer.Option(16, "--batch-size", help="Batch size"),
):
    """Evaluate a trained model."""
    from nx_trainer.core.evaluation import Evaluator
    
    evaluator = Evaluator(
        model_path=model,
        data_path=data,
        batch_size=batch_size,
    )
    results = evaluator.evaluate()
    
    if output:
        import json
        output.write_text(json.dumps(results, indent=2))
        typer.echo(f"Results saved to {output}")
    else:
        typer.echo(results)


@app.command()
def export(
    model: Path = typer.Argument(..., help="Path to model or adapter"),
    output: Path = typer.Argument(..., help="Output path"),
    format: str = typer.Option(
        "gguf",
        "--format",
        "-f",
        help="Export format: gguf, ollama, hf, merged",
    ),
    quantization: Optional[str] = typer.Option(
        None,
        "--quantize",
        "-q",
        help="Quantization: q2_k, q3_k_s, q3_k_m, q3_k_l, q4_0, q4_k_m, q5_0, q5_k_s, q5_k_m, q8_0",
    ),
):
    """Export trained model to different formats."""
    from nx_trainer.core.export import Exporter
    
    exporter = Exporter(
        model_path=model,
        output_path=output,
        format=format,
        quantization=quantization,
    )
    exporter.export()
    typer.echo(f"Model exported to {output}")


@app.command()
def config(
    validate: Optional[Path] = typer.Option(
        None,
        "--validate",
        help="Validate a config file",
        exists=True,
    ),
    show: bool = typer.Option(
        False,
        "--show",
        help="Show default config",
    ),
):
    """Manage configuration files."""
    from nx_trainer.core.config import TrainConfig
    
    if validate:
        TrainConfig.from_yaml(validate)
        typer.echo(f"✓ Config valid: {validate}")
        return
    
    if show:
        config = TrainConfig.default()
        import yaml
        print(yaml.dump(config.model_dump(), default_flow_style=False))
        return
    
    typer.echo("Use --validate or --show")


@app.command()
def info():
    """Show system information and available options."""
    import platform
    
    info = {
        "platform": platform.system(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }
    
    if torch.cuda.is_available():
        info["cuda_version"] = torch.version.cuda
        info["gpu_count"] = torch.cuda.device_count()
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["gpu_memory"] = f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
    
    for key, value in info.items():
        typer.echo(f"{key}: {value}")


if __name__ == "__main__":
    app()