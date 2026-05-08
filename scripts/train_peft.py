#!/usr/bin/env python3
"""Standard PEFT Fine-tuning for Rosetta Stone.

Uses HuggingFace transformers + PEFT (no Unsloth dependency).
Works on 12GB VRAM with LoRA adapters.

Usage:
    python scripts/train_peft.py --epochs 3
"""

import json
import os
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_dependencies():
    """Check if required packages are installed."""
    missing = []

    try:
        import transformers
    except ImportError:
        missing.append("transformers")

    try:
        import peft
    except ImportError:
        missing.append("peft")

    try:
        import torch
    except ImportError:
        missing.append("torch")

    try:
        import datasets
    except ImportError:
        missing.append("datasets")

    if missing:
        print(f"✗ Missing packages: {', '.join(missing)}")
        print("  Install with: pip install transformers peft torch datasets accelerate")
        return False

    print("✓ All dependencies installed")
    return True


def load_dataset():
    """Load and format the training data."""
    data_file = PROJECT_ROOT / "datasets" / "rosetta_training.jsonl"

    if not data_file.exists():
        # Try alternative location
        data_file = PROJECT_ROOT / "data" / "default_data.jsonl"

    print(f"Loading data from: {data_file}")

    if not data_file.exists():
        print(f"✗ Dataset not found at {data_file}")
        return None

    with open(data_file) as f:
        data = [json.loads(line) for line in f]

    print(f"Loaded {len(data)} training examples")
    return data


def format_example(example):
    """Format a single example for training."""
    # Rosetta Stone format: input → tool call
    return f"""User: {example["input"]}
Assistant: [TOOL_CALL]{{{example["output"]}}}[/TOOL_CALL]"""


def train_with_peft(epochs: int = 3, model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"):
    """Train using standard PEFT (HuggingFace transformers + PEFT)."""

    if not check_dependencies():
        return

    print("\n=== Rosetta Stone Training with PEFT ===\n")

    data = load_dataset()
    if not data:
        return

    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, TaskType
    from datasets import Dataset
    import torch

    # Load model and tokenizer
    print(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )

    # Add padding token
    tokenizer.pad_token = tokenizer.eos_token

    # Load model in 4-bit
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        trust_remote_code=True,
        load_in_4bit=True,
    )

    # Configure LoRA
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Format dataset
    formatted_data = [format_example(d) for d in data]
    dataset = Dataset.from_dict({"text": formatted_data})

    # Tokenize
    def tokenize(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=512,
            padding="max_length",
        )

    dataset = dataset.map(tokenize, batched=True)

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # causal LM, not MLM
    )

    # Training arguments
    output_dir = PROJECT_ROOT / "outputs" / "rosetta-peft"
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        warmup_steps=10,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        fp16=True,
        dataloader_num_workers=0,
        remove_unused_columns=False,
        optim="adamw_torch",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        report_to="none",
    )

    # Train
    print("\nStarting training...\n")
    trainer = TrainingArguments(
        train_dataset=dataset,
        data_collator=data_collator,
        **training_args,
    )

    from transformers import Trainer

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
    )

    trainer.train()

    # Save
    model_save_path = PROJECT_ROOT / "models" / "rosetta-peft"
    model.save_pretrained(str(model_save_path))
    tokenizer.save_pretrained(str(model_save_path))

    print(f"\n✓ Model saved to {model_save_path}")
    print("\nTo use with GGUF:")
    print(
        f"  1. Convert to GGUF: python -m transformers.convert import {model_save_path}"
    )
    print("  2. Or use with llama.cpp: apply lora to base model")


def main():
    parser = argparse.ArgumentParser(description="Train Rosetta Stone with PEFT")
    parser.add_argument(
        "--epochs", type=int, default=3, help="Number of training epochs"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Base model to train",
    )
    args = parser.parse_args()

    train_with_peft(args.epochs, args.model)


if __name__ == "__main__":
    main()
