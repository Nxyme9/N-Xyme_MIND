#!/usr/bin/env python3
"""
Rosetta Stone LoRA Fine-tuning Script
Fine-tunes Qwen2.5-0.5B on tool call translation data

Usage:
    python train_rosetta_lora.py --data datasets/rosetta_training.jsonl --output models/rosetta-lora
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
from trl import SFTTrainer

# Config
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIR = Path(__file__).parent / "models" / "rosetta-lora"


def load_training_data(data_path: str) -> List[Dict[str, str]]:
    """Load training data from JSONL file."""
    data = []
    with open(data_path, "r") as f:
        for line in f:
            item = json.loads(line.strip())
            # Support both formats: {"input": ..., "output": ...} and {"text": ...}
            if "text" in item:
                # Already formatted - use directly
                data.append({"input": "", "output": item["text"]})
            else:
                data.append({"input": item["input"], "output": item["output"]})
    print(f"Loaded {len(data)} training examples")
    return data


def format_for_training(item: Dict[str, str]) -> str:
    """Format training example for Qwen chat template."""
    # User asks something, assistant responds with tool call
    return f"""<|im_start|>user
{item["input"]}<|im_end|>
<|im_start|>assistant
{item["output"]}<|im_end|>"""


def prepare_dataset(data_path: str) -> Dataset:
    """Prepare dataset for training."""
    data = load_training_data(data_path)

    # Format all examples
    formatted = [format_for_training(item) for item in data]

    # Create HuggingFace dataset
    dataset = Dataset.from_dict({"text": formatted})

    # Split into train/eval (90/10)
    dataset = dataset.train_test_split(test_size=0.1)

    print(f"Train: {len(dataset['train'])} examples")
    print(f"Eval: {len(dataset['test'])} examples")

    return dataset


def setup_model():
    """Load base model and tokenizer."""
    print(f"Loading base model: {BASE_MODEL}")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL, trust_remote_code=True, padding_side="right"
    )

    # Ensure pad token is set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model with optimizations
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
        torch_dtype=torch.float16,  # FP16 for speed
        device_map="auto",  # Auto-detect device
    )

    # Resize embeddings if needed
    model.resize_token_embeddings(len(tokenizer))

    return model, tokenizer


def setup_lora(model):
    """Configure and apply LoRA."""
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,  # LoRA rank (higher = more params, better quality)
        lora_alpha=32,  # LoRA scaling
        lora_dropout=0.1,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        bias="none",
        inference_mode=False,
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model


def train(
    data_path: str,
    output_dir: str,
    epochs: int = 3,
    batch_size: int = 4,
    learning_rate: float = 2e-4,
    max_seq_length: int = 512,
    resume_from: str = None,
):
    """Main training function."""
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Prepare dataset
    dataset = prepare_dataset(data_path)

    # Load model and tokenizer
    model, tokenizer = setup_model()

    # Apply LoRA
    model = setup_lora(model)

    # Resume from checkpoint if specified
    if resume_from and Path(resume_from).exists():
        print(f"Resuming from checkpoint: {resume_from}")
        adapter_path = Path(resume_from)
        # Load the adapter weights
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, str(adapter_path), is_trainable=True)
        print(f"Loaded adapter from {resume_from}")

    # Training arguments - OPTIMIZED for RTX 3080 Ti + AMD 7800X3D
    training_args = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size
        * 2,  # Increase batch size with gradient checkpointing
        per_device_eval_batch_size=batch_size * 2,
        learning_rate=learning_rate,
        gradient_accumulation_steps=1,
        warmup_steps=20,
        logging_steps=5,
        save_steps=50,
        eval_strategy="steps",
        eval_steps=50,
        save_total_limit=2,
        fp16=True,
        report_to="none",
        remove_unused_columns=False,
        # GPU optimization
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        dataloader_prefetch_factor=2,
        dataloader_persistent_workers=True,
        # Memory optimization - trade VRAM for speed
        gradient_checkpointing=True,
        # Optimizer
        optim="adamw_torch_fused",
        # Remove unused warnings
        ignore_data_skip=True,
    )

    # Initialize trainer (no tokenizer or max_seq_length params in this version)
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        formatting_func=lambda x: x["text"],
    )

    print("\n" + "=" * 50)
    print("Starting Rosetta LoRA Fine-tuning")
    print("=" * 50)
    print(f"Data: {data_path}")
    print(f"Output: {output_dir}")
    print(f"Epochs: {epochs}, Batch: {batch_size}, LR: {learning_rate}")
    print("=" * 50 + "\n")

    # Train
    trainer.train()

    # Save final model
    print(f"\nSaving LoRA adapters to {output_path}")
    trainer.save_model(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    print("\n" + "=" * 50)
    print("Training Complete!")
    print(f"LoRA saved to: {output_path}")
    print("=" * 50)

    return str(output_path)


def merge_and_export(merged_path: str):
    """Merge LoRA with base model and export to GGUF."""
    # This would require additional setup - for now just save LoRA
    print(f"LoRA adapters saved to: {merged_path}")
    print("To use with llama-cpp-python, merge with base model using:")
    print("  peft convert to checkpoints, then export to GGUF")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Rosetta Stone model")
    parser.add_argument(
        "--data",
        type=str,
        default="datasets/rosetta_training.jsonl",
        help="Path to training data JSONL",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/rosetta-lora",
        help="Output directory for LoRA adapters",
    )
    parser.add_argument(
        "--epochs", type=int, default=3, help="Number of training epochs"
    )
    parser.add_argument("--batch", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume from checkpoint path (e.g., models/rosetta-lora-full/checkpoint-100)",
    )

    args = parser.parse_args()

    train(
        data_path=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch,
        learning_rate=args.lr,
        resume_from=args.resume,
    )
